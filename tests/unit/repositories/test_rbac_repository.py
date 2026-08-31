"""RBAC repository tests (mocked session)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories import rbac_repository


async def test_screen_permissions_for_admin() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.all.return_value = [
        ("S1", True, False),
        ("S2", True, False),
    ]
    with patch.object(rbac_repository, "get_session", return_value=db):
        result = await rbac_repository.screen_permissions_for_admin(uuid.uuid4())
    assert result == {("S1", True, False), ("S2", True, False)}


async def test_assign_super_admin_adds_assignment_when_missing() -> None:
    db = MagicMock()
    role = MagicMock()
    role.id = uuid.uuid4()
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role
    none_result = MagicMock()
    none_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(side_effect=[role_result, none_result])
    db.add = MagicMock()
    db.commit = AsyncMock()
    with patch.object(rbac_repository, "get_session", return_value=db):
        await rbac_repository.assign_super_admin(uuid.uuid4())
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


async def test_assign_super_admin_noop_when_role_missing() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalar_one_or_none.return_value = None
    with patch.object(rbac_repository, "get_session", return_value=db):
        await rbac_repository.assign_super_admin(uuid.uuid4())
    db.commit.assert_not_called()


async def test_assign_super_admin_noop_when_already_assigned() -> None:
    db = MagicMock()
    role = MagicMock()
    role.id = uuid.uuid4()
    role_result = MagicMock()
    role_result.scalar_one_or_none.return_value = role
    existing_result = MagicMock()
    existing_result.scalar_one_or_none.return_value = MagicMock()
    db.execute = AsyncMock(side_effect=[role_result, existing_result])
    with patch.object(rbac_repository, "get_session", return_value=db):
        await rbac_repository.assign_super_admin(uuid.uuid4())
    db.add.assert_not_called()
    db.commit.assert_not_called()
