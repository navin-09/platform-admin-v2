"""Platform Admin data access (all SQL) — the Users API is mapped onto platform_admins."""

import uuid
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlmodel import col

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.database.session import get_session
from app.models.enums import Status
from app.models.platform_admin import PlatformAdmin


async def create_user(user: PlatformAdmin) -> PlatformAdmin:
    db = get_session()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: Status | None = None,
) -> tuple[list[PlatformAdmin], int]:
    db = get_session()
    filters: list[ColumnElement[bool]] = []
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                col(PlatformAdmin.username).ilike(pattern),
                col(PlatformAdmin.email).ilike(pattern),
            )
        )
    if status is not None:
        filters.append(col(PlatformAdmin.status) == status)

    total = await db.scalar(select(func.count()).select_from(PlatformAdmin).where(*filters))
    result = await db.execute(
        select(PlatformAdmin)
        .where(*filters)
        .order_by(col(PlatformAdmin.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_user(user_id: uuid.UUID) -> PlatformAdmin | None:
    return await get_session().get(PlatformAdmin, user_id)


async def get_user_by_email(email: str) -> PlatformAdmin | None:
    result = await get_session().execute(
        select(PlatformAdmin).where(col(PlatformAdmin.email) == email)
    )
    return result.scalar_one_or_none()


async def update_user(user: PlatformAdmin, data: dict[str, Any]) -> PlatformAdmin:
    db = get_session()
    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(user: PlatformAdmin) -> None:
    """Soft-delete: mark the admin inactive rather than removing the row."""
    db = get_session()
    user.status = Status.INACTIVE
    await db.commit()


async def count_active_admins(exclude_id: uuid.UUID | None = None) -> int:
    """Count active Platform Admins, optionally excluding one id (last-admin guard)."""
    db = get_session()
    filters: list[ColumnElement[bool]] = [col(PlatformAdmin.status) == Status.ACTIVE]
    if exclude_id is not None:
        filters.append(col(PlatformAdmin.id) != exclude_id)
    total = await db.scalar(select(func.count()).select_from(PlatformAdmin).where(*filters))
    return total or 0
