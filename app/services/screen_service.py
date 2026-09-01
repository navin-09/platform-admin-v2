"""Screen business rules (CRUD, code auto-generation, protection, super_admin permission)."""

import uuid

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.exceptions.exceptions import (
    ProtectedResourceError,
    ScreenCodeExistsError,
    ScreenNotFoundError,
)
from app.models.enums import AuditAction, AuditResourceType, Status
from app.models.screen import Screen
from app.repositories import role_repository, screen_repository
from app.schemas.screen import ScreenCreate, ScreenUpdate
from app.services import audit_service

PROTECTED_SCREEN_CODES = {"S1", "S2", "S3", "S4"}
SUPER_ADMIN_ROLE_NAME = "super_admin"


async def _ensure_code_available(code: str) -> None:
    if await screen_repository.get_screen_by_code(code) is not None:
        raise ScreenCodeExistsError()


async def create_screen(data: ScreenCreate, actor_id: uuid.UUID | None = None) -> Screen:
    code = data.code if data.code else await screen_repository.next_screen_code()
    await _ensure_code_available(code)
    super_admin = await role_repository.get_role_by_name(SUPER_ADMIN_ROLE_NAME)
    screen = Screen(
        code=code,
        name=data.name,
        sort_order=data.sort_order,
        status=data.status,
        created_by=actor_id,
        updated_by=actor_id,
    )
    screen = await screen_repository.create_screen(
        screen, super_admin_role_id=super_admin.id if super_admin else None
    )
    await audit_service.record(
        action=AuditAction.SCREEN_CREATE,
        resource_type=AuditResourceType.SCREEN,
        resource_id=screen.code,
        details={"code": screen.code, "name": screen.name},
    )
    return screen


async def list_screens(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: Status | None = None,
) -> tuple[list[Screen], int]:
    return await screen_repository.list_screens(
        page=page, limit=limit, search=search, status=status
    )


async def get_screen(screen_id: uuid.UUID) -> Screen:
    screen = await screen_repository.get_screen(screen_id)
    if screen is None:
        raise ScreenNotFoundError()
    return screen


async def update_screen(
    screen_id: uuid.UUID, data: ScreenUpdate, actor_id: uuid.UUID | None = None
) -> Screen:
    screen = await get_screen(screen_id)
    payload = data.model_dump(exclude_unset=True, exclude_none=True)
    if screen.code in PROTECTED_SCREEN_CODES and payload.get("status") == Status.INACTIVE:
        raise ProtectedResourceError()
    if actor_id is not None:
        payload["updated_by"] = actor_id
    screen = await screen_repository.update_screen(screen=screen, data=payload)
    await audit_service.record(
        action=AuditAction.SCREEN_UPDATE,
        resource_type=AuditResourceType.SCREEN,
        resource_id=screen.code,
        details=data.model_dump(exclude_unset=True, exclude_none=True, mode="json"),
    )
    return screen


async def delete_screen(screen_id: uuid.UUID, actor_id: uuid.UUID | None = None) -> None:
    screen = await get_screen(screen_id)
    if screen.code in PROTECTED_SCREEN_CODES:
        raise ProtectedResourceError()
    if actor_id is not None:
        screen.updated_by = actor_id
    await screen_repository.delete_screen(screen)
    await audit_service.record(
        action=AuditAction.SCREEN_DELETE,
        resource_type=AuditResourceType.SCREEN,
        resource_id=screen.code,
    )
