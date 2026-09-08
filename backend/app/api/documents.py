import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_client_ip, get_current_user
from app.db.session import SessionLocal, get_db
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.patient import Patient
from app.models.user import User
from app.schemas.document import DocumentChunkOut, DocumentConfirmRequest, DocumentOut
from app.services.audit import log_action
from app.services.ingestion import run_ingestion_pipeline

router = APIRouter(tags=["documents"])
settings = get_settings()


def _run_pipeline_in_background(document_id: uuid.UUID) -> None:
    """BackgroundTasks in FastAPI runs after the response is sent but shares the
    request's asyncio loop; it does NOT get the request's DB session (which is
    closed by then), so this opens its own short-lived session."""
    import asyncio

    db = SessionLocal()
    try:
        asyncio.run(run_ingestion_pipeline(db, document_id))
    finally:
        db.close()


@router.post("/patients/{patient_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    patient_id: uuid.UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    doc_id = uuid.uuid4()
    patient_dir = Path(settings.upload_dir) / str(patient_id)
    patient_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "upload").suffix
    storage_path = patient_dir / f"{doc_id}{ext}"
    storage_path.write_bytes(contents)

    document = Document(
        id=doc_id,
        patient_id=patient_id,
        filename=file.filename or f"upload{ext}",
        storage_path=str(storage_path),
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(contents),
        status=DocumentStatus.uploaded,
        uploaded_by=user.id,
    )
    db.add(document)
    log_action(
        db,
        user_id=user.id,
        patient_id=patient_id,
        action="upload_document",
        resource_type="document",
        resource_id=str(doc_id),
        extra={"filename": document.filename},
        ip_address=get_client_ip(request),
    )
    db.commit()
    db.refresh(document)

    background_tasks.add_task(_run_pipeline_in_background, document.id)
    return document


@router.get("/patients/{patient_id}/documents", response_model=list[DocumentOut])
def list_documents(
    patient_id: uuid.UUID,
    status_filter: DocumentStatus | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Document).filter(Document.patient_id == patient_id)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    return query.order_by(Document.created_at.desc()).all()


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkOut])
def get_document_chunks(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    path = Path(document.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Original file is missing from storage")
    log_action(
        db,
        user_id=user.id,
        patient_id=document.patient_id,
        action="view_document",
        resource_type="document",
        resource_id=str(document.id),
        ip_address=get_client_ip(request),
    )
    db.commit()
    return FileResponse(path, media_type=document.mime_type, filename=document.filename)


@router.patch("/documents/{document_id}/confirm", response_model=DocumentOut)
def confirm_document_metadata(
    document_id: uuid.UUID,
    body: DocumentConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Human confirmation of the auto-detected type/date, per the design brief
    ("auto-detect type/date with human confirmation")."""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if body.doc_type is not None:
        document.doc_type = body.doc_type
        document.doc_type_confirmed = True
    if body.doc_date is not None:
        document.doc_date = body.doc_date
        document.doc_date_confirmed = True
        from app.models.document import DateConfidence

        document.doc_date_confidence = DateConfidence.user_confirmed
    db.commit()
    db.refresh(document)
    return document
