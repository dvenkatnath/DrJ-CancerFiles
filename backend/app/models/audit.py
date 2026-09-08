import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPKMixin


class AuditLog(UUIDPKMixin, Base):
    """
    Append-only audit trail of PHI access and edits. Every view/edit of a patient
    record, document, or wiki section is logged here -- who, what, when. Never
    updated or deleted by the app; only ever inserted.
    """

    __tablename__ = "audit_log"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action} user={self.user_id} patient={self.patient_id}>"
