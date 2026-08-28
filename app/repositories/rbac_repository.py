"""RBAC data access (all SQL) — resolve an admin's granted screen permissions."""

import uuid
from typing import cast

from sqlalchemy import select
from sqlmodel import col

from app.database.session import get_session
from app.models.enums import Status
from app.models.platform_admin_role import PlatformAdminRole
from app.models.role import Role
from app.models.role_screen import RoleScreen
from app.models.screen import Screen


async def screen_permissions_for_admin(admin_id: uuid.UUID) -> set[tuple[str, bool, bool]]:
    """Return the (screen code, read, write) rows for the admin's active roles/screens."""
    db = get_session()
    result = await db.execute(
        select(col(RoleScreen.screen_code), col(RoleScreen.read), col(RoleScreen.write))
        .join(PlatformAdminRole, col(PlatformAdminRole.role_id) == col(RoleScreen.role_id))
        .join(Role, col(Role.id) == col(RoleScreen.role_id))
        .join(Screen, col(Screen.code) == col(RoleScreen.screen_code))
        .where(
            col(PlatformAdminRole.platform_admin_id) == admin_id,
            col(Role.status) == Status.ACTIVE,
            col(Screen.status) == Status.ACTIVE,
        )
    )
    permissions: set[tuple[str, bool, bool]] = set()
    for row in result.all():
        permissions.add((cast(str, row[0]), cast(bool, row[1]), cast(bool, row[2])))
    return permissions


async def role_names_for_admin(admin_id: uuid.UUID) -> set[str]:
    """Return the names of every role assigned to an admin."""
    db = get_session()
    result = await db.execute(
        select(col(Role.name))
        .join(PlatformAdminRole, col(PlatformAdminRole.role_id) == col(Role.id))
        .where(col(PlatformAdminRole.platform_admin_id) == admin_id)
    )
    return set(result.scalars().all())
