import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ChatSession(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    patient = relationship("Patient", backref="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatSession {self.id} patient={self.patient_id}>"


class ChatMessage(UUIDPKMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # [{document_id, chunk_id, doc_name, page, section_label, snippet}]
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # True if any cited source is still awaiting curation -- the UI flags the
    # answer as provisional per spec ("flag answers that rely on sections still
    # pending curation").
    pending_curation_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatMessage {self.role} session={self.session_id}>"
