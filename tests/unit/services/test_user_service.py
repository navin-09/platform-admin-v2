"""User service tests (repositories mocked)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.errors import ApiError
from app.models.enums import UserStatus
from app.models.user import User
from app.schemas.user import UserCreate, UserReplace, UserUpdate
from app.services import user_service


def _user(email: str = "alice@example.com") -> User:
    return User(
        id=uuid.uuid4(),
        email=email,
        name="Alice",
        status=UserStatus.ACTIVE,
        hashed_password="hash",
    )


async def test_create_user() -> None:
    with (
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_service.user_repository,
            "create_user",
            new=AsyncMock(side_effect=lambda user: user),
        ),
        patch.object(user_service, "hash_password", return_value="hashed"),
    ):
        created = await user_service.create_user(
            UserCreate(name="Alice", email="alice@example.com", password="S3cureP@ss")
        )
    assert created.email == "alice@example.com"
    assert created.hashed_password == "hashed"


async def test_create_user_duplicate_email() -> None:
    with patch.object(
        user_service.user_repository,
        "get_user_by_email",
        new=AsyncMock(return_value=_user()),
    ):
        with pytest.raises(ApiError):
            await user_service.create_user(
                UserCreate(name="Alice", email="alice@example.com", password="S3cureP@ss")
            )


async def test_get_user_not_found() -> None:
    with patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=None)):
        with pytest.raises(ApiError):
            await user_service.get_user(uuid.uuid4())


async def test_get_user_found() -> None:
    user = _user()
    with patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)):
        result = await user_service.get_user(user.id)
    assert result.id == user.id


async def test_list_users() -> None:
    with patch.object(
        user_service.user_repository,
        "list_users",
        new=AsyncMock(return_value=([], 0)),
    ):
        users, total = await user_service.list_users(page=1, limit=20)
    assert users == []
    assert total == 0


async def test_update_user_applies_fields() -> None:
    user = _user()

    async def _apply(user, data):
        for key, value in data.items():
            setattr(user, key, value)
        return user

    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_service.user_repository, "update_user", new=AsyncMock(side_effect=_apply)
        ),
    ):
        result = await user_service.update_user(user_id=user.id, data=UserUpdate(name="Bob"))
    assert result.name == "Bob"


async def test_update_user_email_change() -> None:
    user = _user()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_service.user_repository,
            "update_user",
            new=AsyncMock(side_effect=lambda user, data: user),
        ),
    ):
        result = await user_service.update_user(
            user_id=user.id, data=UserUpdate(email="new@example.com")
        )
    assert result is user


async def test_replace_user() -> None:
    user = _user()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(user_service, "hash_password", return_value="hashed"),
        patch.object(
            user_service.user_repository,
            "update_user",
            new=AsyncMock(side_effect=lambda user, data: user),
        ),
    ):
        result = await user_service.replace_user(
            user_id=user.id,
            data=UserReplace(name="Alice", email="alice@example.com", password="S3cureP@ss"),
        )
    assert result is user


async def test_delete_user() -> None:
    user = _user()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(user_service.user_repository, "delete_user", new=AsyncMock(return_value=None)),
    ):
        await user_service.delete_user(user.id)
