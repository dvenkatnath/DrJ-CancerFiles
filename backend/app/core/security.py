"""
Password hashing + JWT issuance/verification.

NOTE on refresh-token revocation: refresh tokens here are stateless signed JWTs
(type=refresh) validated only by signature + expiry, not checked against a
server-side store. That is a deliberate scope simplification for this build --
logging out discards the tokens client-side but a still-valid refresh token
technically keeps working until it expires. Before going to production at a
client site, add a `revoked_refresh_tokens` table (or a jti allowlist) and
check it in `decode_token`; this is called out again in the README.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, role: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str, role: str) -> str:
    return _create_token(
        user_id, role, "access", timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(user_id: str, role: str) -> str:
    return _create_token(
        user_id, role, "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


class TokenError(Exception):
    pass


def decode_token(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise TokenError(str(e)) from e
    if payload.get("type") != expected_type:
        raise TokenError(f"expected a {expected_type} token, got {payload.get('type')}")
    return payload
