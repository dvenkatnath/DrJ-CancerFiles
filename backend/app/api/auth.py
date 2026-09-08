from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_client_ip, get_current_user
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenPair, UserOut
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    log_action(
        db,
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
    )
    db.commit()

    return TokenPair(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id), user.role.value),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except TokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid refresh token: {e}") from e

    user = db.get(User, payload["sub"]) if _is_uuid(payload["sub"]) else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return TokenPair(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id), user.role.value),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Refresh tokens are stateless JWTs in this build (see app.core.security
    # module docstring) -- logout is an audit event + the client discarding its
    # tokens. A production/on-prem hardening pass should add server-side
    # refresh-token revocation.
    log_action(
        db,
        user_id=user.id,
        action="logout",
        resource_type="user",
        resource_id=str(user.id),
        ip_address=get_client_ip(request),
    )
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


def _is_uuid(value: str) -> bool:
    import uuid

    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False
