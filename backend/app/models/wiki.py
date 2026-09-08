import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class WikiSectionType(str, enum.Enum):
    at_a_glance = "at_a_glance"
    problem_list = "problem_list"
    medications = "medications"
    allergies = "allergies"
    lab_highlights = "lab_highlights"
    visit_timeline = "visit_timeline"
    care_plan = "care_plan"
    notes = "notes"


class ChangeSource(str, enum.Enum):
    ai_extraction = "ai_extraction"
    curator_edit = "curator_edit"
    physician_edit = "physician_edit"
    system_seed = "system_seed"


class WikiSection(UUIDPKMixin, TimestampMixin, Base):
    """
    Living structured summary, one row per (patient, section_type). `content` is a
    JSON array of "facts": [{id, text, sources:[{document_id, page, section}],
    confidence, status, last_updated}] -- see docs/architecture.md for the exact
    shape. Per-statement source attribution and confidence live inside `content`
    rather than as separate columns so the frontend can render heterogeneous
    section layouts (a med list vs. a timeline) from the same table.
    """

    __tablename__ = "wiki_sections"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_type: Mapped[WikiSectionType] = mapped_column(
        Enum(WikiSectionType, name="wiki_section_type"), nullable=False
    )
    content: Mapped[list | dict] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # True once every fact currently in `content` has been curator-approved at least
    # once. A single new AI-proposed fact flips this back to False until reviewed.
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    patient = relationship("Patient", backref="wiki_sections")
    revisions: Mapped[list["WikiRevision"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="WikiRevision.version"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WikiSection {self.patient_id}/{self.section_type} v{self.version}>"


class WikiRevision(UUIDPKMixin, Base):
    __tablename__ = "wiki_revisions"

    wiki_section_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("wiki_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[list | dict] = mapped_column(JSONB, nullable=False)
    change_source: Mapped[ChangeSource] = mapped_column(
        Enum(ChangeSource, name="change_source"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    section = relationship("WikiSection", back_populates="revisions")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<WikiRevision section={self.wiki_section_id} v{self.version}>"
