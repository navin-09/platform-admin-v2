import uuid
from datetime import date

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.security import hash_password
from app.exceptions.exceptions import (
    EmailExistsError,
    LastAdminError,
    UserNotFoundError,
)
from app.models.enums import AuditAction, AuditResourceType, Status
from app.models.platform_admin import PlatformAdmin
from app.repositories import rbac_repository, user_repository
from app.schemas.user import UserCreate, UserReplace, UserUpdate
from app.services import audit_service


async def _ensure_email_available(
    email: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    existing = await user_repository.get_user_by_email(email)
    if existing is not None and (exclude_id is None or existing.id != exclude_id):
        raise EmailExistsError()


async def _guard_last_active_admin(admin_id: uuid.UUID) -> None:
    """Reject deactivating the last active admin — nobody could log in afterwards."""
    if await user_repository.count_active_admins(exclude_id=admin_id) == 0:
        raise LastAdminError()


async def create_user(data: UserCreate, actor_id: uuid.UUID | None = None) -> PlatformAdmin:
    await _ensure_email_available(data.email)
    # The API field ``name`` maps to the admin's ``username`` (Display Name) column.
    user = PlatformAdmin(
        username=data.name,
        email=data.email,
        status=data.status,
        hashed_password=hash_password(data.password),
        created_by=actor_id,
        updated_by=actor_id,
    )
    user = await user_repository.create_user(user)
    await rbac_repository.assign_super_admin(user.id, actor_id=actor_id)
    await audit_service.record(
        action=AuditAction.USER_CREATE,
        resource_type=AuditResourceType.USER,
        resource_id=str(user.id),
        details={"email": user.email, "name": user.username},
    )
    return user


async def list_users(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: Status | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[list[PlatformAdmin], int]:
    return await user_repository.list_users(
        page=page,
        limit=limit,
        search=search,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )


async def get_user(user_id: uuid.UUID) -> PlatformAdmin:
    user = await user_repository.get_user(user_id)
    if user is None:
        raise UserNotFoundError()
    return user


async def update_user(
    user_id: uuid.UUID, data: UserUpdate, actor_id: uuid.UUID | None = None
) -> PlatformAdmin:
    user = await get_user(user_id)
    payload = data.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in payload:
        payload["username"] = payload.pop("name")
    if "email" in payload:
        await _ensure_email_available(email=payload["email"], exclude_id=user_id)
    if payload.get("status") == Status.INACTIVE and user.status == Status.ACTIVE:
        await _guard_last_active_admin(user_id)
        payload["current_refresh_jti"] = None
    if actor_id is not None:
        payload["updated_by"] = actor_id
    user = await user_repository.update_user(user=user, data=payload)
    await audit_service.record(
        action=AuditAction.USER_UPDATE,
        resource_type=AuditResourceType.USER,
        resource_id=str(user.id),
        details=data.model_dump(exclude_unset=True, exclude_none=True, mode="json"),
    )
    return user


async def replace_user(
    user_id: uuid.UUID, data: UserReplace, actor_id: uuid.UUID | None = None
) -> PlatformAdmin:
    user = await get_user(user_id)
    await _ensure_email_available(email=data.email, exclude_id=user_id)
    payload = {
        "username": data.name,
        "email": data.email,
        "hashed_password": hash_password(data.password),
        "failed_login_attempts": 0,
        "locked_until": None,
    }
    if actor_id is not None:
        payload["updated_by"] = actor_id
    user = await user_repository.update_user(user=user, data=payload)
    await audit_service.record(
        action=AuditAction.USER_REPLACE,
        resource_type=AuditResourceType.USER,
        resource_id=str(user.id),
        details={"email": data.email, "name": data.name},
    )
    return user


async def delete_user(user_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
    user = await get_user(user_id)
    if user.status == Status.ACTIVE:
        await _guard_last_active_admin(user_id)
    user.current_refresh_jti = None
    if actor_id is not None:
        user.updated_by = actor_id
    await user_repository.delete_user(user)
    await audit_service.record(
        action=AuditAction.USER_DELETE,
        resource_type=AuditResourceType.USER,
        resource_id=str(user_id),
    )
