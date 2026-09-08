import enum
import datetime
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

settings = get_settings()


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    extracting = "extracting"
    summarized = "summarized"
    pending_review = "pending_review"
    curated = "curated"
    error = "error"


class DateConfidence(str, enum.Enum):
    parsed_exact = "parsed_exact"
    parsed_fuzzy = "parsed_fuzzy"
    user_confirmed = "user_confirmed"
    unresolved = "unresolved"


class Document(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    doc_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    doc_type_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    doc_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    doc_date_confidence: Mapped[DateConfidence] = mapped_column(
        Enum(DateConfidence, name="date_confidence"), nullable=False, default=DateConfidence.unresolved
    )
    doc_date_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), nullable=False, default=DocumentStatus.uploaded, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    patient = relationship("Patient", backref="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Document {self.filename} status={self.status}>"


class DocumentChunk(UUIDPKMixin, Base):
    """
    One retrievable unit of text for RAG. Lives in the SAME Postgres instance as
    the relational data -- vector column + HNSW index, no separate vector DB at
    this scale (see README for the Qdrant escape hatch if volume grows).
    """

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim), nullable=True)

    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"
