"""Seed the RBAC catalog and backfill super_admin (idempotent)."""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, col

from app.database.database import async_session_factory
from app.models.platform_admin import PlatformAdmin
from app.models.platform_admin_role import PlatformAdminRole
from app.models.role import Role
from app.models.role_screen import RoleScreen
from app.models.screen import Screen

SUPER_ADMIN_ROLE_NAME = "super_admin"

SCREENS = [
    ("S1", "User Management", 1, True, True),
    ("S2", "Audit Logs", 2, True, False),
    ("S3", "Role Management", 3, True, True),
    ("S4", "Screen Management", 4, True, True),
]


async def ensure_catalog(db: AsyncSession) -> None:
    """Seed screens and grant super_admin every screen permission."""
    role = await _get_or_create(db, Role, SUPER_ADMIN_ROLE_NAME)
    for code, name, sort_order, read, write in SCREENS:
        await _get_or_create_screen(db, code, name, sort_order)
        await _get_or_create_permission(db, role.id, code, read=read, write=write)


async def assign_super_admin(db: AsyncSession, admin_id: uuid.UUID) -> None:
    """Ensure the given admin holds the super_admin role (no-op if already assigned)."""
    role = await _get_or_create(db, Role, SUPER_ADMIN_ROLE_NAME)
    existing = await db.execute(
        select(PlatformAdminRole).where(
            col(PlatformAdminRole.platform_admin_id) == admin_id,
            col(PlatformAdminRole.role_id) == role.id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(PlatformAdminRole(platform_admin_id=admin_id, role_id=role.id))


async def seed() -> None:
    """Seed the catalog and assign super_admin to every admin that has no roles."""
    async with async_session_factory() as db:
        await ensure_catalog(db)
        admins = (await db.execute(select(PlatformAdmin))).scalars().all()
        for admin in admins:
            await assign_super_admin(db, admin.id)
        await db.commit()
    print("RBAC catalog and super_admin assignments are ready.")


async def _get_or_create[T: SQLModel](db: AsyncSession, model: type[T], name: str) -> T:
    """Return the row with ``name``, creating (and flushing) it if absent."""
    # ``model`` is a generic SQLModel type, so the column is fetched by name
    # (ruff B009 prefers attribute access, which mypy rejects on ``type[T]``).
    name_column = getattr(model, "name")  # noqa: B009
    row = (await db.execute(select(model).where(col(name_column) == name))).scalar_one_or_none()
    if row is None:
        row = model(name=name)
        db.add(row)
        await db.flush()
    return row


async def _get_or_create_screen(db: AsyncSession, code: str, name: str, sort_order: int) -> Screen:
    """Return the screen with ``code``, creating (and flushing) it if absent."""
    row = (await db.execute(select(Screen).where(col(Screen.code) == code))).scalar_one_or_none()
    if row is None:
        row = Screen(code=code, name=name, sort_order=sort_order)
        db.add(row)
        await db.flush()
    return row


async def _get_or_create_permission(
    db: AsyncSession, role_id: uuid.UUID, screen_code: str, *, read: bool, write: bool
) -> RoleScreen:
    """Return the role's screen permission row, creating (and flushing) it if absent."""
    row = (
        await db.execute(
            select(RoleScreen).where(
                col(RoleScreen.role_id) == role_id,
                col(RoleScreen.screen_code) == screen_code,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = RoleScreen(role_id=role_id, screen_code=screen_code, read=read, write=write)
        db.add(row)
        await db.flush()
    return row


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
