import datetime
import uuid

from pydantic import BaseModel

from app.models.document import DateConfidence, DocumentStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    doc_type: str | None
    doc_type_confirmed: bool
    doc_date: datetime.date | None
    doc_date_confidence: DateConfidence
    doc_date_confirmed: bool
    status: DocumentStatus
    error_message: str | None
    ocr_used: bool
    page_count: int | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class DocumentConfirmRequest(BaseModel):
    doc_type: str | None = None
    doc_date: datetime.date | None = None


class DocumentChunkOut(BaseModel):
    id: uuid.UUID
    chunk_index: int
    text: str
    page: int | None
    section_label: str | None

    model_config = {"from_attributes": True}
