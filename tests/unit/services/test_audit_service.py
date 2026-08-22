"""Audit service tests (repositories mocked)."""

from unittest.mock import AsyncMock, patch

from app.services import audit_service


async def test_record_is_best_effort_on_failure() -> None:
    with patch.object(
        audit_service.audit_repository,
        "create_audit_log",
        new=AsyncMock(side_effect=RuntimeError("db down")),
    ):
        await audit_service.record(actor="admin", action="user.create")


async def test_record_writes_entry() -> None:
    with patch.object(
        audit_service.audit_repository,
        "create_audit_log",
        new=AsyncMock(return_value=None),
    ):
        await audit_service.record(actor="admin", action="user.create")


async def test_list_audit_logs() -> None:
    with patch.object(
        audit_service.audit_repository,
        "list_audit_logs",
        new=AsyncMock(return_value=([], 0)),
    ):
        entries, total = await audit_service.list_audit_logs(page=1, limit=20)
    assert entries == []
    assert total == 0
