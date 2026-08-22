"""Platform Admin lookup (all SQL)."""

import uuid

from sqlalchemy import select
from sqlmodel import col

from app.database.session import get_session
from app.models.platform_admin import PlatformAdmin


async def get_admin_by_email(email: str) -> PlatformAdmin | None:
    result = await get_session().execute(
        select(PlatformAdmin).where(col(PlatformAdmin.email) == email)
    )
    return result.scalar_one_or_none()


async def get_admin_by_id(admin_id: uuid.UUID) -> PlatformAdmin | None:
    return await get_session().get(PlatformAdmin, admin_id)
