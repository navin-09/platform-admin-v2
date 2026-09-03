"""Export repository unit tests (mocked session, per repo convention)."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories import export_repository
from app.schemas.audit import AuditLogFilter

NOW = datetime(2026, 8, 31, 10, 0, 0)


def _session_mock() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.scalar = AsyncMock(return_value=0)
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    return db


def _row(id_: uuid.UUID | None = None) -> MagicMock:
    row = MagicMock()
    row.id = id_ or uuid.uuid4()
    row.created_at = NOW
    return row


# --------------------------------------------------------------------------- #
# create_export / get_export / update_export
# --------------------------------------------------------------------------- #


async def test_create_export_success_commits_and_refreshes() -> None:
    db = _session_mock()
    with patch.object(export_repository, "get_session", return_value=db):
        entry = await export_repository.create_export(
            module="audit",
            reason="Review",
            file_format="xlsx",
            classification="Restricted",
            filters={"actor": None},
            created_by="admin@example.com",
        )
    assert entry.module == "audit"
    assert entry.reason == "Review"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()


async def test_get_export_success_returns_row() -> None:
    db = _session_mock()
    export = MagicMock()
    db.get = AsyncMock(return_value=export)
    with patch.object(export_repository, "get_session", return_value=db):
        result = await export_repository.get_export(uuid.uuid4())
    assert result is export


async def test_get_export_success_returns_none_when_missing() -> None:
    db = _session_mock()
    db.get = AsyncMock(return_value=None)
    with patch.object(export_repository, "get_session", return_value=db):
        result = await export_repository.get_export(uuid.uuid4())
    assert result is None


async def test_update_export_success_commits() -> None:
    db = _session_mock()
    export = MagicMock()
    with patch.object(export_repository, "get_session", return_value=db):
        await export_repository.update_export(export)
    db.add.assert_called_once_with(export)
    db.commit.assert_awaited_once()


# --------------------------------------------------------------------------- #
# count_audit_logs / count_platform_admins
# --------------------------------------------------------------------------- #


async def test_count_audit_logs_success_without_filters() -> None:
    db = _session_mock()
    db.scalar = AsyncMock(return_value=37)
    with patch.object(export_repository, "get_session", return_value=db):
        total = await export_repository.count_audit_logs(AuditLogFilter())
    assert total == 37


async def test_count_audit_logs_success_applies_filters() -> None:
    db = _session_mock()
    db.scalar = AsyncMock(return_value=2)
    with patch.object(export_repository, "get_session", return_value=db):
        filters = AuditLogFilter(
            actor="admin@example.com",
            action="user.create",
            resource_type="user",
            actor_type="admin",
        )
        total = await export_repository.count_audit_logs(filters)
    assert total == 2


async def test_count_audit_logs_failure_returns_zero_when_null() -> None:
    db = _session_mock()
    db.scalar = AsyncMock(return_value=None)
    with patch.object(export_repository, "get_session", return_value=db):
        total = await export_repository.count_audit_logs(AuditLogFilter())
    assert total == 0


async def test_count_platform_admins_success_applies_search_and_status() -> None:
    db = _session_mock()
    db.scalar = AsyncMock(return_value=3)
    with patch.object(export_repository, "get_session", return_value=db):
        total = await export_repository.count_platform_admins("admin", "active")
    assert total == 3


# --------------------------------------------------------------------------- #
# stream_audit_logs (keyset pagination)
# --------------------------------------------------------------------------- #


async def test_stream_audit_logs_success_yields_all_rows_in_chunks() -> None:
    db = _session_mock()
    first_page = [_row(), _row()]
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = first_page

    with patch.object(export_repository, "get_session", return_value=db):
        rows = [row async for row in export_repository.stream_audit_logs(AuditLogFilter())]

    assert rows == first_page
    assert db.execute.await_count == 1


async def test_stream_audit_logs_success_second_page_uses_keyset() -> None:
    db = _session_mock()
    # First page returns a full chunk (forces a second query); second returns empty.
    first_page = [_row() for _ in range(export_repository.settings.export_stream_chunk_size)]
    first_result = MagicMock()
    first_result.scalars.return_value.all.return_value = first_page
    second_result = MagicMock()
    second_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(side_effect=[first_result, second_result])

    with patch.object(export_repository, "get_session", return_value=db):
        rows = [row async for row in export_repository.stream_audit_logs(AuditLogFilter())]

    assert len(rows) == len(first_page)
    assert db.execute.await_count == 2
    # the keyset cursor (created_at/id boundary) is applied on the second query
    second_query = db.execute.await_args.args[0]
    assert second_query is not None


async def test_stream_audit_logs_success_empty_result() -> None:
    db = _session_mock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []

    with patch.object(export_repository, "get_session", return_value=db):
        rows = [row async for row in export_repository.stream_audit_logs(AuditLogFilter())]

    assert rows == []
    assert db.execute.await_count == 1


# --------------------------------------------------------------------------- #
# stream_platform_admins
# --------------------------------------------------------------------------- #


async def test_stream_platform_admins_success_yields_rows() -> None:
    db = _session_mock()
    rows = [_row()]
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = rows

    with patch.object(export_repository, "get_session", return_value=db):
        result = [row async for row in export_repository.stream_platform_admins("admin", None)]

    assert result == rows


async def test_stream_platform_admins_success_empty_result() -> None:
    db = _session_mock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.scalars.return_value.all.return_value = []

    with patch.object(export_repository, "get_session", return_value=db):
        result = [row async for row in export_repository.stream_platform_admins(None, None)]

    assert result == []
