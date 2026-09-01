"""Screen repository tests (mocked session)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.enums import Status
from app.models.screen import Screen
from app.repositories import screen_repository


def _screen() -> Screen:
    return Screen(id=uuid.uuid4(), code="S5", name="Reports", sort_order=0, status=Status.ACTIVE)


async def test_active_screen_codes() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = ["S1", "S3"]
    with patch.object(screen_repository, "get_session", return_value=db):
        assert await screen_repository.active_screen_codes() == {"S1", "S3"}


async def test_get_screen_returns_none_when_missing() -> None:
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with patch.object(screen_repository, "get_session", return_value=db):
        assert await screen_repository.get_screen(uuid.uuid4()) is None


async def test_get_screen_by_code() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalar_one_or_none.return_value = "some-screen"
    with patch.object(screen_repository, "get_session", return_value=db):
        assert await screen_repository.get_screen_by_code("S5") == "some-screen"


async def test_create_screen_with_super_admin_grant_commits() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    screen = _screen()
    with patch.object(screen_repository, "get_session", return_value=db):
        result = await screen_repository.create_screen(screen, super_admin_role_id=uuid.uuid4())
    assert result is screen
    assert db.add.call_count == 2
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(screen)


async def test_create_screen_without_grant() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    screen = _screen()
    with patch.object(screen_repository, "get_session", return_value=db):
        await screen_repository.create_screen(screen)
    assert db.add.call_count == 1
    db.commit.assert_awaited_once()


async def test_list_screens_with_filters() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=1)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    with patch.object(screen_repository, "get_session", return_value=db):
        screens, total = await screen_repository.list_screens(
            page=1, limit=20, search="a", status=Status.ACTIVE
        )
    assert screens == []
    assert total == 1


async def test_next_screen_code() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = ["S1", "S2", "S9", "REPORTS"]
    with patch.object(screen_repository, "get_session", return_value=db):
        assert await screen_repository.next_screen_code() == "S10"


async def test_next_screen_code_when_no_numeric_codes() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = ["REPORTS"]
    with patch.object(screen_repository, "get_session", return_value=db):
        assert await screen_repository.next_screen_code() == "S1"


async def test_update_screen_applies_fields_and_commits() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    screen = _screen()
    with patch.object(screen_repository, "get_session", return_value=db):
        result = await screen_repository.update_screen(screen, {"name": "New"})
    assert result is screen
    assert screen.name == "New"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(screen)


async def test_delete_screen_soft_deletes() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    screen = _screen()
    with patch.object(screen_repository, "get_session", return_value=db):
        await screen_repository.delete_screen(screen)
    assert screen.status is Status.INACTIVE
    db.commit.assert_awaited_once()
