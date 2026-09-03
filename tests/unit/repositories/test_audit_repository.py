"""Audit repository unit tests (mocked session, per repo convention)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.audit_intent import AuditIntent
from app.repositories import audit_repository
from app.schemas.audit import AuditLogFilter

NOW = datetime(2026, 9, 3, 12, 0, 0)


def _intent(action: str) -> AuditIntent:
    return AuditIntent(payload={"actor": "admin", "action": action}, created_at=NOW)


async def test_create_audit_intent_commits() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    with patch.object(audit_repository, "get_session", return_value=db):
        intent = await audit_repository.create_audit_intent(
            payload={"action": "user.create"}, created_at=NOW
        )
    assert intent.payload == {"action": "user.create"}
    assert intent.created_at == NOW
    db.add.assert_called_once()
    db.commit.assert_awaited_once()


async def test_promote_audit_intents_empty_outbox_returns_zero() -> None:
    db = MagicMock()
    db.commit = AsyncMock()
    empty = MagicMock()
    empty.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=empty)
    with patch.object(audit_repository, "get_session", return_value=db):
        promoted = await audit_repository.promote_audit_intents()
    assert promoted == 0
    db.commit.assert_not_awaited()


async def test_promote_audit_intents_forges_chained_entries() -> None:
    db = MagicMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    intents = [_intent("user.create"), _intent("user.update")]
    intents_result = MagicMock()
    intents_result.scalars.return_value.all.return_value = intents
    db.execute = AsyncMock(side_effect=[intents_result, MagicMock()])  # select, advisory lock
    # per entry: MAX(seq), tip hash
    db.scalar = AsyncMock(side_effect=[0, None, 1, "a" * 64])
    with patch.object(audit_repository, "get_session", return_value=db):
        promoted = await audit_repository.promote_audit_intents()

    assert promoted == 2
    assert db.add.call_count == 2
    assert db.delete.await_count == 2
    db.commit.assert_awaited_once()

    first = db.add.call_args_list[0].args[0]
    second = db.add.call_args_list[1].args[0]
    assert first.seq == 1
    assert first.prev_hash is None
    assert first.entry_hash is not None and len(first.entry_hash) == 64
    assert second.seq == 2
    # entry 2 chains onto the stubbed committed tip (real linking is verified live)
    assert second.prev_hash == "a" * 64
    assert first.action == "user.create"
    assert second.created_at == NOW  # evidence time is the action time, not promotion


async def test_list_audit_logs_empty() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=0)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    with patch.object(audit_repository, "get_session", return_value=db):
        entries, total = await audit_repository.list_audit_logs(AuditLogFilter(), page=1, limit=20)
    assert entries == []
    assert total == 0


async def test_list_audit_logs_with_filters() -> None:
    db = MagicMock()
    db.scalar = AsyncMock(return_value=0)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    filters = AuditLogFilter(actor="admin", action="user.create", resource_type="user")
    with patch.object(audit_repository, "get_session", return_value=db):
        entries, total = await audit_repository.list_audit_logs(filters, page=1, limit=20)
    assert entries == []
    assert total == 0


async def test_list_audit_logs_with_date_filters() -> None:
    from datetime import date

    db = MagicMock()
    db.scalar = AsyncMock(return_value=0)
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []
    filters = AuditLogFilter(from_date=date(2026, 8, 1), to_date=date(2026, 8, 31))
    with patch.object(audit_repository, "get_session", return_value=db):
        entries, total = await audit_repository.list_audit_logs(filters, page=1, limit=20)
    assert entries == []
    assert total == 0
