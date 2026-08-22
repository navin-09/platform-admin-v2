"""User business rules."""

import uuid

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.security import hash_password
from app.exceptions.errors import email_already_registered, user_not_found
from app.models.enums import UserStatus
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserCreate, UserReplace, UserUpdate


async def _ensure_email_available(
    email: str,
    exclude_id: uuid.UUID | None = None,
) -> None:
    existing = await user_repository.get_user_by_email(email)
    if existing is not None and (exclude_id is None or existing.id != exclude_id):
        raise email_already_registered()


async def create_user(data: UserCreate) -> User:
    await _ensure_email_available(data.email)
    user = User(
        name=data.name,
        email=data.email,
        status=data.status,
        hashed_password=hash_password(data.password),
    )
    return await user_repository.create_user(user)


async def list_users(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: UserStatus | None = None,
) -> tuple[list[User], int]:
    return await user_repository.list_users(page=page, limit=limit, search=search, status=status)


async def get_user(user_id: uuid.UUID) -> User:
    user = await user_repository.get_user(user_id)
    if user is None:
        raise user_not_found()
    return user


async def update_user(user_id: uuid.UUID, data: UserUpdate) -> User:
    user = await get_user(user_id)
    payload = data.model_dump(exclude_unset=True, exclude_none=True)
    if "email" in payload:
        await _ensure_email_available(email=payload["email"], exclude_id=user_id)
    return await user_repository.update_user(user=user, data=payload)


async def replace_user(user_id: uuid.UUID, data: UserReplace) -> User:
    user = await get_user(user_id)
    await _ensure_email_available(email=data.email, exclude_id=user_id)
    payload = {
        "name": data.name,
        "email": data.email,
        "hashed_password": hash_password(data.password),
    }
    return await user_repository.update_user(user=user, data=payload)


async def delete_user(user_id: uuid.UUID) -> None:
    user = await get_user(user_id)
    await user_repository.delete_user(user)
