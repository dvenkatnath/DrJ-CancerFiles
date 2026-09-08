import enum
import uuid

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class UserRole(str, enum.Enum):
    physician = "physician"
    curator = "curator"
    admin = "admin"


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.physician
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Placeholder hooks for SSO/MFA (per spec: not implemented, wired later) ---
    sso_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email} ({self.role})>"
