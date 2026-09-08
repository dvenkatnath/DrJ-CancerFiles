import datetime
import uuid

from pydantic import BaseModel

from app.models.chat import MessageRole


class ChatSessionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    user_id: uuid.UUID
    title: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class Citation(BaseModel):
    document_id: uuid.UUID
    chunk_id: uuid.UUID | None = None
    document_name: str
    page: int | None = None
    section_label: str | None = None
    snippet: str


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    role: MessageRole
    content: str
    citations: list[dict]
    pending_curation_flag: bool
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class AskRequest(BaseModel):
    session_id: uuid.UUID | None = None
    question: str
