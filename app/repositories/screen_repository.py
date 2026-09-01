"""Screen data access (all SQL)."""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlmodel import col

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.database.session import get_session
from app.models.enums import Status
from app.models.role_screen import RoleScreen
from app.models.screen import Screen


async def create_screen(screen: Screen, super_admin_role_id: uuid.UUID | None = None) -> Screen:
    """Create a screen and, atomically, its bootstrap super_admin permission."""
    db = get_session()
    db.add(screen)
    if super_admin_role_id is not None:
        # ``screen_code`` FKs to ``screens.code`` (not the PK), so SQLAlchemy's
        # automatic insert-dependency ordering doesn't cover it; flush the
        # screen first or the RoleScreen insert can race ahead of it.
        await db.flush()
        db.add(
            RoleScreen(
                role_id=super_admin_role_id,
                screen_code=screen.code,
                read=True,
                write=True,
                created_by=screen.created_by,
                updated_by=screen.updated_by,
            )
        )
    await db.commit()
    await db.refresh(screen)
    return screen


async def list_screens(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: Status | None = None,
) -> tuple[list[Screen], int]:
    db = get_session()
    filters = []
    if search:
        pattern = f"%{search}%"
        filters.append(or_(col(Screen.name).ilike(pattern), col(Screen.code).ilike(pattern)))
    if status is not None:
        filters.append(col(Screen.status) == status)

    total = await db.scalar(select(func.count()).select_from(Screen).where(*filters))
    result = await db.execute(
        select(Screen)
        .where(*filters)
        .order_by(col(Screen.sort_order), col(Screen.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_screen(screen_id: uuid.UUID) -> Screen | None:
    return await get_session().get(Screen, screen_id)


async def get_screen_by_code(code: str) -> Screen | None:
    result = await get_session().execute(select(Screen).where(col(Screen.code) == code))
    return result.scalar_one_or_none()


async def active_screen_codes() -> set[str]:
    """Return the codes of every active screen (for permission validation)."""
    db = get_session()
    result = await db.execute(select(col(Screen.code)).where(col(Screen.status) == Status.ACTIVE))
    return set(result.scalars().all())


async def next_screen_code() -> str:
    """Return the next ``S{n}`` code — one past the largest numeric ``S`` suffix."""
    db = get_session()
    result = await db.execute(select(col(Screen.code)))
    max_suffix = 0
    for code in result.scalars().all():
        if code.startswith("S") and code[1:].isdigit():
            max_suffix = max(max_suffix, int(code[1:]))
    return f"S{max_suffix + 1}"


async def update_screen(screen: Screen, data: dict[str, Any]) -> Screen:
    db = get_session()
    for field, value in data.items():
        setattr(screen, field, value)
    await db.commit()
    await db.refresh(screen)
    return screen


async def delete_screen(screen: Screen) -> None:
    """Soft-delete: mark the screen inactive rather than removing the row."""
    db = get_session()
    screen.status = Status.INACTIVE
    await db.commit()
