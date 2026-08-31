import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import bcrypt
from jose import jwt

from app.core.config import settings

# bcrypt only hashes the first 72 bytes; truncate explicitly because
# bcrypt >= 4.1 raises instead of silently truncating.
_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    """Encode and truncate to bcrypt's 72-byte limit."""
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(_truncate(plain), hashed.encode("utf-8"))


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "user_id": subject,
        "jti": str(uuid.uuid4()),
        "exp": now + expires_delta,
        "type": token_type,
    }
    if extra_claims:
        payload.update(extra_claims)
    return cast(str, jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm))


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, "refresh", timedelta(days=settings.refresh_token_expire_days))


def create_access_token(
    subject: str,
    refresh_token: str,
    permissions: list[str],
    *,
    email: str,
    username: str,
    roles: list[str],
) -> str:
    """Create an access token bound to its sibling refresh token session (rjti)."""
    refresh_payload = decode_token(refresh_token)
    extra_claims = {
        "rjti": refresh_payload["jti"],
        "rexp": refresh_payload["exp"],
        "email": email,
        "username": username,
        "roles": roles,
        "permissions": permissions,
    }
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        extra_claims,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode a token. Raises ``jose.JWTError`` if invalid or expired."""
    return cast(
        dict[str, Any],
        jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm]),
    )
