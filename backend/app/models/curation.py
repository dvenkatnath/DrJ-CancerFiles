import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin
from app.models.wiki import WikiSectionType


class CurationStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    published = "published"
    rejected = "rejected"


class CurationPriority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


class SectionDecision(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    edited = "edited"
    rejected = "rejected"


class Curation(UUIDPKMixin, TimestampMixin, Base):
    """
    One review unit: the AI-proposed wiki changes for a single document, awaiting
    human curation. `proposed_changes` is a JSON map of section_type -> {additions,
    modifications, deletions, confidence} exactly as produced by the extraction
    pipeline, kept immutable as the record of what the model proposed; the actual
    reviewer decisions live in CurationSectionDecision rows.
    """

    __tablename__ = "curations"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[CurationStatus] = mapped_column(
        Enum(CurationStatus, name="curation_status"), nullable=False, default=CurationStatus.pending, index=True
    )
    priority: Mapped[CurationPriority] = mapped_column(
        Enum(CurationPriority, name="curation_priority"), nullable=False, default=CurationPriority.normal
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    proposed_changes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    document = relationship("Document", backref="curations")
    patient = relationship("Patient", backref="curations")
    section_decisions: Mapped[list["CurationSectionDecision"]] = relationship(
        back_populates="curation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Curation doc={self.document_id} status={self.status}>"


class CurationSectionDecision(UUIDPKMixin, Base):
    __tablename__ = "curation_section_decisions"

    curation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("curations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_type: Mapped[WikiSectionType] = mapped_column(
        Enum(WikiSectionType, name="wiki_section_type", create_type=False), nullable=False
    )
    decision: Mapped[SectionDecision] = mapped_column(
        Enum(SectionDecision, name="section_decision"), nullable=False, default=SectionDecision.pending
    )
    final_content: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    curation = relationship("Curation", back_populates="section_decisions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CurationSectionDecision {self.section_type} {self.decision}>"
