"""User data access (all SQL)."""

import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlmodel import col

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.database.session import get_session
from app.models.enums import UserStatus
from app.models.user import User


async def create_user(user: User) -> User:
    db = get_session()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: UserStatus | None = None,
) -> tuple[list[User], int]:
    db = get_session()
    filters = []
    if search:
        pattern = f"%{search}%"
        filters.append(or_(col(User.name).ilike(pattern), col(User.email).ilike(pattern)))
    if status is not None:
        filters.append(col(User.status) == status)

    total = await db.scalar(select(func.count()).select_from(User).where(*filters))
    result = await db.execute(
        select(User)
        .where(*filters)
        .order_by(col(User.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_user(user_id: uuid.UUID) -> User | None:
    return await get_session().get(User, user_id)


async def get_user_by_email(email: str) -> User | None:
    result = await get_session().execute(select(User).where(col(User.email) == email))
    return result.scalar_one_or_none()


async def update_user(user: User, data: dict[str, Any]) -> User:
    db = get_session()
    for field, value in data.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(user: User) -> None:
    db = get_session()
    await db.delete(user)
    await db.commit()
