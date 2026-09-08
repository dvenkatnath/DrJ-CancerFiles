import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.schemas.auth import UserOut

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles(UserRole.admin))])
settings = get_settings()


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.physician


class UserUpdateRequest(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.full_name).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreateRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        role=body.role,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    patient_id: uuid.UUID | None
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    created_at: object

    model_config = {"from_attributes": True}


@router.get("/audit-log", response_model=list[AuditLogOut])
def audit_log(
    patient_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if patient_id:
        query = query.filter(AuditLog.patient_id == patient_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()


@router.get("/ingestion-settings")
def ingestion_settings():
    """Read-only view of the current env-driven ingestion/LLM configuration --
    editing these is a deployment-time (.env) change, not a runtime one, so
    there is nothing to PATCH here; this just makes the effective config
    visible to an admin without shelling in."""
    return {
        "environment": settings.environment,
        "llm_mode": settings.llm_mode,
        "openai_base_url": settings.openai_base_url,
        "chat_model": settings.chat_model,
        "extraction_model": settings.extraction_model,
        "embedding_model": settings.embedding_model,
        "embedding_dim": settings.embedding_dim,
        "llm_context_tokens": settings.llm_context_tokens,
        "max_upload_mb": settings.max_upload_mb,
        "vector_backend": settings.vector_backend,
        "sso_enabled": settings.sso_enabled,
        "mfa_enabled": settings.mfa_enabled,
    }
