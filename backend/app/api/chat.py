import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.patient import Patient
from app.models.user import User
from app.schemas.chat import AskRequest, ChatMessageOut, ChatSessionOut
from app.services.audit import log_action
from app.services.rag import stream_answer

router = APIRouter(tags=["chat"])

STARTER_QUESTIONS = [
    "Summarize the latest lab trends",
    "What medications changed at the last visit?",
    "Any documented allergies?",
    "What's the current problem list?",
    "What is the care plan going forward?",
]


@router.get("/patients/{patient_id}/chat/starters")
def get_starter_questions(patient_id: uuid.UUID):
    return {"starters": STARTER_QUESTIONS}


@router.get("/patients/{patient_id}/chat/sessions", response_model=list[ChatSessionOut])
def list_sessions(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(ChatSession)
        .filter(ChatSession.patient_id == patient_id, ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )


@router.post("/patients/{patient_id}/chat/sessions", response_model=ChatSessionOut, status_code=201)
def create_session(patient_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    session = ChatSession(patient_id=patient_id, user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_messages(session_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()


@router.post("/chat/sessions/{session_id}/ask")
async def ask(
    session_id: uuid.UUID,
    body: AskRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    prior = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    history = [{"role": m.role.value, "content": m.content} for m in prior]

    user_msg = ChatMessage(session_id=session_id, role=MessageRole.user, content=body.question, citations=[])
    db.add(user_msg)
    if session.title is None:
        session.title = body.question[:80]
    db.commit()

    log_action(
        db,
        user_id=user.id,
        patient_id=session.patient_id,
        action="ask_chat",
        resource_type="chat_session",
        resource_id=str(session_id),
        ip_address=get_client_ip(request),
    )
    db.commit()

    token_stream, citations, pending_flag = await stream_answer(db, session.patient_id, body.question, history)

    async def event_generator():
        full_text = []
        try:
            async for chunk in token_stream:
                full_text.append(chunk)
                yield f"data: {json.dumps({'delta': chunk})}\n\n"
        finally:
            assistant_msg = ChatMessage(
                session_id=session_id,
                role=MessageRole.assistant,
                content="".join(full_text),
                citations=citations,
                pending_curation_flag=pending_flag,
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            yield (
                "data: "
                + json.dumps(
                    {
                        "done": True,
                        "message_id": str(assistant_msg.id),
                        "citations": citations,
                        "pending_curation_flag": pending_flag,
                    }
                )
                + "\n\n"
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
