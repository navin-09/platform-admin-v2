"""Authentication dependency: resolve the current admin from the bearer token."""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import decode_token
from app.exceptions.errors import not_authenticated
from app.models.platform_admin import PlatformAdmin
from app.services import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


def _admin_id_from(credentials: HTTPAuthorizationCredentials | None) -> uuid.UUID:
    if credentials is None:
        raise not_authenticated()
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise not_authenticated() from None
    if payload.get("type") != "access":
        raise not_authenticated()
    subject = payload.get("sub")
    if not subject:
        raise not_authenticated()
    try:
        return uuid.UUID(str(subject))
    except ValueError:
        raise not_authenticated() from None


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> PlatformAdmin:
    return await auth_service.get_admin_by_id(_admin_id_from(credentials))
