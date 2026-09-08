import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    mfa_enabled: bool

    model_config = {"from_attributes": True}
