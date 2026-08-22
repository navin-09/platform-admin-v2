"""Audit repository tests (mocked session)."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories import audit_repository


async def test_create_audit_log_commits_and_refreshes() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with patch.object(audit_repository, "get_session", return_value=db):
        entry = await audit_repository.create_audit_log(actor="admin", action="user.create")
    assert entry.action == "user.create"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


async def test_list_audit_logs_empty() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=0)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    with patch.object(audit_repository, "get_session", return_value=db):
        entries, total = await audit_repository.list_audit_logs(page=1, limit=20)
    assert entries == []
    assert total == 0


async def test_list_audit_logs_with_filters() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=0)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    with patch.object(audit_repository, "get_session", return_value=db):
        entries, total = await audit_repository.list_audit_logs(
            page=1, limit=20, actor="admin", action="user.create", resource_type="user"
        )
    assert entries == []
    assert total == 0
