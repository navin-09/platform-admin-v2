"""Role repository tests (mocked session)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.enums import Status
from app.models.role import Role
from app.repositories import role_repository


def _role() -> Role:
    return Role(id=uuid.uuid4(), name="support-agent", description=None, status=Status.ACTIVE)


async def test_get_role_returns_none_when_missing() -> None:
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with patch.object(role_repository, "get_session", return_value=db):
        assert await role_repository.get_role(uuid.uuid4()) is None


async def test_get_role_by_name() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalar_one_or_none.return_value = "some-role"
    with patch.object(role_repository, "get_session", return_value=db):
        assert await role_repository.get_role_by_name("support-agent") == "some-role"


async def test_create_role_commits_and_refreshes() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    role = _role()
    with patch.object(role_repository, "get_session", return_value=db):
        result = await role_repository.create_role(role, [])
    assert result is role
    db.add.assert_called_once_with(role)
    db.add_all.assert_called_once_with([])
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(role)


async def test_list_roles_with_filters() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=1)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    with patch.object(role_repository, "get_session", return_value=db):
        roles, total = await role_repository.list_roles(
            page=1, limit=20, search="a", status=Status.ACTIVE
        )
    assert roles == []
    assert total == 1


async def test_update_role_applies_fields_and_commits() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    role = _role()
    with patch.object(role_repository, "get_session", return_value=db):
        result = await role_repository.update_role(role, {"name": "New"})
    assert result is role
    assert role.name == "New"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(role)


async def test_update_role_replaces_permissions() -> None:
    db = MagicMock()
    db.execute = AsyncMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    role = _role()
    rows = []
    with patch.object(role_repository, "get_session", return_value=db):
        result = await role_repository.update_role(role, {}, permissions=rows)
    assert result is role
    db.execute.assert_awaited_once()
    db.add_all.assert_called_once_with(rows)
    db.commit.assert_awaited_once()


async def test_delete_role_soft_deletes() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    role = _role()
    with patch.object(role_repository, "get_session", return_value=db):
        await role_repository.delete_role(role)
    assert role.status is Status.INACTIVE
    db.commit.assert_awaited_once()


async def test_permissions_for_role() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.all.return_value = [("S1", 1, True, True)]
    with patch.object(role_repository, "get_session", return_value=db):
        rows = await role_repository.permissions_for_role(uuid.uuid4())
    assert rows == [("S1", 1, True, True)]


async def test_permissions_for_roles() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    role_id = uuid.uuid4()
    db.execute.return_value.all.return_value = [(role_id, "S1", 1, True, False)]
    with patch.object(role_repository, "get_session", return_value=db):
        result = await role_repository.permissions_for_roles([role_id])
    assert result == {role_id: [("S1", 1, True, False)]}


async def test_permissions_for_roles_empty() -> None:
    assert await role_repository.permissions_for_roles([]) == {}
