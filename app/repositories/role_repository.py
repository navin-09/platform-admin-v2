"""Role data access (all SQL)."""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, and_, delete, func, select
from sqlmodel import col

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.database.session import get_session
from app.models.enums import Status
from app.models.role import Role
from app.models.role_screen import RoleScreen
from app.models.screen import Screen


async def create_role(role: Role, permissions: list[RoleScreen]) -> Role:
    """Create a role and its screen permissions in one commit."""
    db = get_session()
    db.add(role)
    db.add_all(permissions)
    await db.commit()
    await db.refresh(role)
    return role


async def list_roles(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: Status | None = None,
) -> tuple[list[Role], int]:
    db = get_session()
    filters: list[ColumnElement[bool]] = []
    if search:
        pattern = f"%{search}%"
        filters.append(col(Role.name).ilike(pattern))
    if status is not None:
        filters.append(col(Role.status) == status)

    total = await db.scalar(select(func.count()).select_from(Role).where(*filters))
    result = await db.execute(
        select(Role)
        .where(*filters)
        .order_by(col(Role.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_role(role_id: uuid.UUID) -> Role | None:
    return await get_session().get(Role, role_id)


async def get_role_by_name(name: str) -> Role | None:
    result = await get_session().execute(select(Role).where(col(Role.name) == name))
    return result.scalar_one_or_none()


async def update_role(
    role: Role,
    data: dict[str, Any],
    permissions: list[RoleScreen] | None = None,
) -> Role:
    """Apply field updates and, when provided, replace permissions, in one commit."""
    db = get_session()
    for field, value in data.items():
        setattr(role, field, value)
    if permissions is not None:
        await db.execute(delete(RoleScreen).where(col(RoleScreen.role_id) == role.id))
        db.add_all(permissions)
    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(role: Role) -> None:
    """Soft-delete: mark the role inactive rather than removing the row."""
    db = get_session()
    role.status = Status.INACTIVE
    await db.commit()


async def permissions_for_role(role_id: uuid.UUID) -> list[tuple[str, int, bool, bool]]:
    """Return the role's ``(code, sort_order, read, write)`` rows on active screens."""
    db = get_session()
    result = await db.execute(
        select(
            col(Screen.code),
            col(Screen.sort_order),
            col(RoleScreen.read),
            col(RoleScreen.write),
        )
        .join(
            RoleScreen,
            and_(
                col(RoleScreen.screen_code) == col(Screen.code),
                col(RoleScreen.role_id) == role_id,
            ),
        )
        .where(col(Screen.status) == Status.ACTIVE)
        .order_by(col(Screen.sort_order), col(Screen.code))
    )
    return [
        (str(code), int(sort_order), bool(read), bool(write))
        for code, sort_order, read, write in result.all()
    ]


async def permissions_for_roles(
    role_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[tuple[str, int, bool, bool]]]:
    """Return a per-role mapping of ``(code, sort_order, read, write)`` rows for active screens."""
    if not role_ids:
        return {}
    db = get_session()
    result = await db.execute(
        select(
            col(RoleScreen.role_id),
            col(Screen.code),
            col(Screen.sort_order),
            col(RoleScreen.read),
            col(RoleScreen.write),
        )
        .join(Screen, col(Screen.code) == col(RoleScreen.screen_code))
        .where(col(RoleScreen.role_id).in_(role_ids), col(Screen.status) == Status.ACTIVE)
        .order_by(col(Screen.sort_order), col(Screen.code))
    )
    mapping: dict[uuid.UUID, list[tuple[str, int, bool, bool]]] = {
        role_id: [] for role_id in role_ids
    }
    for role_id, code, sort_order, read, write in result.all():
        mapping[role_id].append((str(code), int(sort_order), bool(read), bool(write)))
    return mapping
