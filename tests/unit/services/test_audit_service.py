"""Audit service unit tests — repository faked (see tests/unit/fakes.py)."""

from unittest.mock import AsyncMock, patch

from app.core.audit_context import (
    reset_current_actor,
    reset_request_metadata,
    set_current_actor,
    set_request_metadata,
)
from app.services import audit_service
from tests.unit.fakes import FakeAuditRepository


async def test_record_success_writes_entry() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    await audit_service.record(actor="admin", action="user.create")

    assert repo.created[0]["actor"] == "admin"
    assert repo.created[0]["action"] == "user.create"


async def test_record_success_redacts_sensitive_fields() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    await audit_service.record(
        actor="admin",
        action="user.update",
        details={"password": "s3cret", "name": "Bob"},
        payload={"access_token": "tok", "email": "a@b.c"},
        response={"refresh_token": "tok2", "status": "ok"},
    )

    assert repo.created[0]["details"] == {"password": "***", "name": "Bob"}
    assert repo.created[0]["payload"] == {"access_token": "***", "email": "a@b.c"}
    assert repo.created[0]["response"] == {"refresh_token": "***", "status": "ok"}


async def test_record_failure_is_best_effort() -> None:
    """A failing audit write must never break the caller (best-effort)."""
    repo = FakeAuditRepository()

    async def _boom(**kwargs):
        raise RuntimeError("db down")

    repo.create_audit_log = _boom
    audit_service.audit_repository = repo

    await audit_service.record(actor="admin", action="user.create")  # must not raise


async def test_record_success_resolves_actor_from_context() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    token = set_current_actor("admin@example.com", "admin")
    try:
        await audit_service.record(action="user.create")
    finally:
        reset_current_actor(token)

    assert repo.created[0]["actor"] == "admin@example.com"
    assert repo.created[0]["actor_type"] == "admin"


async def test_record_success_resolves_request_metadata_from_context() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    token = set_request_metadata(
        url="/api/v1/users",
        ip_address="203.0.113.7",
        user_agent="pytest",
        request_id="req-123",
    )
    try:
        await audit_service.record(action="user.create")
    finally:
        reset_request_metadata(token)

    entry = repo.created[0]
    assert entry["url"] == "/api/v1/users"
    assert entry["ip_address"] == "203.0.113.7"
    assert entry["user_agent"] == "pytest"
    assert entry["request_id"] == "req-123"


async def test_record_success_explicit_metadata_wins_over_context() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    token = set_request_metadata(
        url="/ambient", ip_address="203.0.113.1", user_agent="ambient", request_id="ambient-id"
    )
    try:
        await audit_service.record(
            action="user.create", ip_address="198.51.100.9", user_agent="explicit"
        )
    finally:
        reset_request_metadata(token)

    entry = repo.created[0]
    assert entry["ip_address"] == "198.51.100.9"
    assert entry["user_agent"] == "explicit"
    assert entry["url"] == "/ambient"


async def test_list_audit_logs_success_empty() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    entries, total = await audit_service.list_audit_logs(page=1, limit=20)

    assert entries == []
    assert total == 0


async def test_list_audit_logs_success_returns_entries() -> None:
    repo = FakeAuditRepository()
    repo.entries = [object()]
    audit_service.audit_repository = repo

    entries, total = await audit_service.list_audit_logs(page=1, limit=20)

    assert len(entries) == 1
    assert total == 1


async def test_list_audit_logs_with_date_filters() -> None:
    from datetime import date

    from_date = date(2026, 8, 1)
    to_date = date(2026, 8, 31)
    with patch.object(
        audit_service.audit_repository,
        "list_audit_logs",
        new=AsyncMock(return_value=([], 0)),
    ) as mock_list:
        entries, total = await audit_service.list_audit_logs(
            page=1, limit=20, from_date=from_date, to_date=to_date
        )
    assert entries == []
    assert total == 0
    mock_list.assert_awaited_once_with(
        page=1,
        limit=20,
        actor=None,
        action=None,
        resource_type=None,
        actor_type=None,
        from_date=from_date,
        to_date=to_date,
    )
