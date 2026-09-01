"""Authentication and authorization dependencies (resolve the admin, check permissions)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.audit_context import reset_current_actor, set_current_actor
from app.core.security import decode_token
from app.exceptions.exceptions import AuthenticationError, PermissionDeniedError
from app.models.enums import ActorType, AuditAction, AuditResourceType, PermissionName
from app.models.platform_admin import PlatformAdmin
from app.services import audit_service, auth_service, rbac_service

bearer_scheme = HTTPBearer(auto_error=False)


def _access_token_payload(credentials: HTTPAuthorizationCredentials | None) -> dict[str, Any]:
    if credentials is None:
        raise AuthenticationError()
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise AuthenticationError() from None
    if payload.get("type") != "access":
        raise AuthenticationError()
    return payload


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AsyncIterator[PlatformAdmin]:
    """Resolve the Current Admin and expose it as the ambient audit actor."""
    admin = await auth_service.get_admin_from_payload(_access_token_payload(credentials))
    token = set_current_actor(admin.email, ActorType.ADMIN.value)
    try:
        yield admin
    finally:
        reset_current_actor(token)


async def require_super_admin(
    request: Request,
    admin: PlatformAdmin = Depends(get_current_admin),
) -> None:
    """Dependency allowing the request only if the Current Admin holds the super_admin role."""
    if not await rbac_service.is_super_admin(admin.id):
        await _record_denial(request=request, admin=admin, permission=PermissionName.AUDIT_READ)
        raise PermissionDeniedError()
    return None


def require_permission(
    required: PermissionName,
) -> Callable[..., Awaitable[None]]:
    """Dependency allowing the request only if the Current Admin holds ``required``."""

    async def _dependency(
        request: Request,
        admin: PlatformAdmin = Depends(get_current_admin),
    ) -> None:
        granted = await rbac_service.permissions_for_admin(admin.id)
        if required.value not in granted:
            await _record_denial(request=request, admin=admin, permission=required)
            raise PermissionDeniedError()
        return None

    return _dependency


async def _record_denial(
    request: Request,
    admin: PlatformAdmin,
    permission: PermissionName,
) -> None:
    """Record an ``access.denied`` Audit Entry before the 403 is raised."""
    await audit_service.record(
        actor=admin.email,
        actor_type=ActorType.ADMIN.value,
        action=AuditAction.ACCESS_DENIED,
        resource_type=_denial_resource_type(permission),
        details={
            "permission": permission.value,
            "display_name": admin.username,
            "method": request.method,
            "path": request.url.path,
        },
    )


_SCREEN_RESOURCE_TYPES = {
    "S1": AuditResourceType.USER,
    "S2": AuditResourceType.AUDIT,
    "S3": AuditResourceType.ROLE,
    "S4": AuditResourceType.SCREEN,
}


def _denial_resource_type(permission: PermissionName) -> AuditResourceType | None:
    """Map a permission's screen code to its audit resource type."""
    return _SCREEN_RESOURCE_TYPES.get(permission.value.split(".", 1)[0])
