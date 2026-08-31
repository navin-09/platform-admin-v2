"""Role business rules (CRUD, name uniqueness, permission management, protection)."""

import uuid

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.exceptions.exceptions import (
    ProtectedResourceError,
    RoleNameExistsError,
    RoleNotFoundError,
    ValidationError,
    field_errors,
)
from app.models.enums import AuditAction, AuditResourceType, Status
from app.models.role import Role
from app.models.role_screen import RoleScreen
from app.repositories import role_repository, screen_repository
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.services import audit_service

SUPER_ADMIN_ROLE_NAME = "super_admin"


async def _ensure_name_available(name: str, exclude_id: uuid.UUID | None = None) -> None:
    existing = await role_repository.get_role_by_name(name)
    if existing is not None and (exclude_id is None or existing.id != exclude_id):
        raise RoleNameExistsError()


def _normalize_permissions(permissions: list[str]) -> dict[str, tuple[bool, bool]]:
    """Map permission strings to ``{screen_code: (read, write)}`` — write implies read."""
    by_code: dict[str, tuple[bool, bool]] = {}
    for permission in permissions:
        code, operation = permission.rsplit(".", 1)
        read, write = by_code.get(code, (False, False))
        if operation == "W":
            by_code[code] = (True, True)
        else:
            by_code[code] = (True, write)
    return by_code


def _screen_code_key(code: str) -> tuple[int, str, str]:
    """Numeric-aware sort key so ``S2`` sorts before ``S10``; non-numeric codes sort last."""
    if len(code) > 1 and code[0] == "S" and code[1:].isdigit():
        return (0, f"{int(code[1:]):08d}", code)
    return (1, "", code)


def _expand_permissions(rows: list[tuple[str, int, bool, bool]]) -> list[str]:
    """Expand (code, sort_order, read, write) rows into ordered permission strings."""
    expanded: list[tuple[int, tuple[int, str, str], str, str]] = []
    for code, sort_order, read, write in rows:
        key = _screen_code_key(code)
        if read or write:
            expanded.append((sort_order, key, code, "R"))
        if write:
            expanded.append((sort_order, key, code, "W"))
    expanded.sort(key=lambda item: (item[0], item[1], item[3]))
    return [f"{code}.{operation}" for _, _, code, operation in expanded]


async def _validate_screen_codes(by_code: dict[str, tuple[bool, bool]]) -> None:
    if not by_code:
        return
    valid = await screen_repository.active_screen_codes()
    invalid = [code for code in by_code if code not in valid]
    if invalid:
        raise ValidationError(
            data=field_errors(
                [("permissions", f"Unknown or inactive screen: {code}") for code in invalid]
            )
        )


def _permission_rows(role_id: uuid.UUID, by_code: dict[str, tuple[bool, bool]]) -> list[RoleScreen]:
    return [
        RoleScreen(role_id=role_id, screen_code=code, read=read, write=write)
        for code, (read, write) in by_code.items()
    ]


def _to_read(role: Role, rows: list[tuple[str, int, bool, bool]]) -> RoleRead:
    return RoleRead(
        id=role.id,
        name=role.name,
        description=role.description,
        status=role.status,
        permissions=_expand_permissions(rows),
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


async def _get_role(role_id: uuid.UUID) -> Role:
    role = await role_repository.get_role(role_id)
    if role is None:
        raise RoleNotFoundError()
    return role


async def _read_role(role: Role) -> RoleRead:
    return _to_read(role, await role_repository.permissions_for_role(role.id))


async def create_role(data: RoleCreate) -> RoleRead:
    await _ensure_name_available(data.name)
    by_code = _normalize_permissions(data.permissions)
    await _validate_screen_codes(by_code)
    role = Role(name=data.name, description=data.description, status=data.status)
    role = await role_repository.create_role(role, _permission_rows(role.id, by_code))
    rows = await role_repository.permissions_for_role(role.id)
    await audit_service.record(
        action=AuditAction.ROLE_CREATE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(role.id),
        details={"name": role.name, "permissions": _expand_permissions(rows)},
    )
    return _to_read(role, rows)


async def list_roles(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: Status | None = None,
) -> tuple[list[RoleRead], int]:
    roles, total = await role_repository.list_roles(
        page=page, limit=limit, search=search, status=status
    )
    permission_map = await role_repository.permissions_for_roles([role.id for role in roles])
    return [_to_read(role, permission_map.get(role.id, [])) for role in roles], total


async def get_role(role_id: uuid.UUID) -> RoleRead:
    return await _read_role(await _get_role(role_id))


async def update_role(role_id: uuid.UUID, data: RoleUpdate) -> RoleRead:
    role = await _get_role(role_id)
    payload = data.model_dump(exclude_unset=True, exclude_none=True)
    permissions = payload.pop("permissions", None)
    if role.name == SUPER_ADMIN_ROLE_NAME:
        if "name" in payload and payload["name"] != SUPER_ADMIN_ROLE_NAME:
            raise ProtectedResourceError()
        if payload.get("status") == Status.INACTIVE:
            raise ProtectedResourceError()
        if permissions is not None:
            raise ProtectedResourceError()
    if "name" in payload:
        await _ensure_name_available(name=payload["name"], exclude_id=role_id)
    rows: list[RoleScreen] | None = None
    if permissions is not None:
        by_code = _normalize_permissions(permissions)
        await _validate_screen_codes(by_code)
        rows = _permission_rows(role_id, by_code)
    role = await role_repository.update_role(role=role, data=payload, permissions=rows)
    details = {
        key: value
        for key, value in data.model_dump(
            exclude_unset=True, exclude_none=True, mode="json"
        ).items()
        if key != "permissions"
    }
    if permissions is not None:
        details["permissions"] = _expand_permissions(
            await role_repository.permissions_for_role(role_id)
        )
    await audit_service.record(
        action=AuditAction.ROLE_UPDATE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(role_id),
        details=details,
    )
    return await _read_role(role)


async def delete_role(role_id: uuid.UUID) -> None:
    role = await _get_role(role_id)
    if role.name == SUPER_ADMIN_ROLE_NAME:
        raise ProtectedResourceError()
    await role_repository.delete_role(role)
    await audit_service.record(
        action=AuditAction.ROLE_DELETE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(role_id),
    )
