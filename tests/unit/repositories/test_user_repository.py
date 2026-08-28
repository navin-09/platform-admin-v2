"""Platform Admin repository tests (mocked session)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.enums import Status
from app.models.platform_admin import PlatformAdmin
from app.repositories import user_repository


def _user() -> PlatformAdmin:
    return PlatformAdmin(
        id=uuid.uuid4(),
        email="alice@example.com",
        username="Alice",
        status=Status.ACTIVE,
        hashed_password="hash",
    )


async def test_get_user_returns_none_when_missing() -> None:
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with patch.object(user_repository, "get_session", return_value=db):
        assert await user_repository.get_user(uuid.uuid4()) is None


async def test_get_user_by_email() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalar_one_or_none.return_value = "some-admin"
    with patch.object(user_repository, "get_session", return_value=db):
        assert await user_repository.get_user_by_email("a@b.com") == "some-admin"


async def test_create_user_commits_and_refreshes() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    user = _user()
    with patch.object(user_repository, "get_session", return_value=db):
        result = await user_repository.create_user(user)
    assert result is user
    db.add.assert_called_once_with(user)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)


async def test_list_users_with_filters() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=1)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    with patch.object(user_repository, "get_session", return_value=db):
        users, total = await user_repository.list_users(
            page=1, limit=20, search="a", status=Status.ACTIVE
        )
    assert users == []
    assert total == 1


async def test_update_user_applies_fields_and_commits() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    user = _user()
    with patch.object(user_repository, "get_session", return_value=db):
        result = await user_repository.update_user(user, {"username": "Bob"})
    assert result is user
    assert user.username == "Bob"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)


async def test_delete_user_soft_deletes() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    user = _user()
    with patch.object(user_repository, "get_session", return_value=db):
        await user_repository.delete_user(user)
    assert user.status is Status.INACTIVE
    db.commit.assert_awaited_once()


async def test_count_active_admins_excludes_id() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=2)
    with patch.object(user_repository, "get_session", return_value=db):
        total = await user_repository.count_active_admins(exclude_id=uuid.uuid4())
    assert total == 2
