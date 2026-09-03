"""Audit service unit tests — repository faked (see tests/unit/fakes.py)."""

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, patch

from app.core.audit_context import (
    claimed_actor,
    reset_current_actor,
    reset_request_metadata,
    set_current_actor,
    set_request_metadata,
)
from app.exceptions.exceptions import AppError
from app.schemas.audit import AuditLogFilter
from app.services import audit_service
from app.services.audit_service import AuditEvent
from tests.unit.fakes import FakeAuditRepository


def _event(**overrides: Any) -> AuditEvent:
    """Build a baseline Audit Event; keyword overrides customize it."""
    base: dict[str, Any] = {"action": "user.create", "resource_type": "user"}
    base.update(overrides)
    return AuditEvent(**base)


class _BoomError(AppError):
    status_code = 400
    code = "E_TEST_BOOM"
    message = "boom"


async def test_record_success_queues_intent() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    async with claimed_actor("admin", "admin"):
        await audit_service.record(_event())

    queued = repo.intents[0]["payload"]
    assert queued["actor"] == "admin"
    assert queued["action"] == "user.create"


async def test_record_success_redacts_sensitive_fields() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    await audit_service.record(
        _event(
            action="user.update",
            details={"password": "s3cret", "name": "Bob"},
            payload={"access_token": "tok", "email": "a@b.c"},
            response={"refresh_token": "tok2", "status": "ok"},
        )
    )

    queued = repo.intents[0]["payload"]
    assert queued["details"] == {"password": "***", "name": "Bob"}
    assert queued["payload"] == {"access_token": "***", "email": "a@b.c"}
    assert queued["response"] == {"refresh_token": "***", "status": "ok"}


async def test_record_failure_is_best_effort() -> None:
    """A failing intent write must never break the caller (best-effort)."""
    repo = FakeAuditRepository()

    async def _boom(**kwargs):
        raise RuntimeError("db down")

    repo.create_audit_intent = _boom
    audit_service.audit_repository = repo

    await audit_service.record(_event())  # must not raise


async def test_record_success_resolves_actor_from_context() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    token = set_current_actor("admin@example.com", "admin")
    try:
        await audit_service.record(_event())
    finally:
        reset_current_actor(token)

    assert repo.intents[0]["payload"]["actor"] == "admin@example.com"
    assert repo.intents[0]["payload"]["actor_type"] == "admin"


async def test_claimed_actor_supplies_identity() -> None:
    """Pre-auth flows claim an identity via ``claimed_actor``; record inherits it."""
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    async with claimed_actor("claimed@example.com", "admin"):
        await audit_service.record(_event())

    assert repo.intents[0]["payload"]["actor"] == "claimed@example.com"
    assert repo.intents[0]["payload"]["actor_type"] == "admin"


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
        await audit_service.record(_event())
    finally:
        reset_request_metadata(token)

    queued = repo.intents[0]["payload"]
    assert queued["url"] == "/api/v1/users"
    assert queued["ip_address"] == "203.0.113.7"
    assert queued["user_agent"] == "pytest"
    assert queued["request_id"] == "req-123"


async def test_record_failure_merges_error_code_into_details() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    await audit_service.record_failure(
        _event(action="auth.login.failure", details={"attempt": 3}),
        _BoomError(),
    )

    queued = repo.intents[0]["payload"]
    assert queued["action"] == "auth.login.failure"
    assert queued["details"] == {"attempt": 3, "error_code": "E_TEST_BOOM"}


async def test_promote_intents_delegates_to_repository() -> None:
    repo = FakeAuditRepository()
    repo.promoted = 3
    audit_service.audit_repository = repo

    assert await audit_service.promote_intents() == 3


async def test_list_audit_logs_success_empty() -> None:
    repo = FakeAuditRepository()
    audit_service.audit_repository = repo

    entries, total = await audit_service.list_audit_logs(AuditLogFilter(), page=1, limit=20)

    assert entries == []
    assert total == 0


async def test_list_audit_logs_success_returns_entries() -> None:
    repo = FakeAuditRepository()
    repo.entries = [object()]
    audit_service.audit_repository = repo

    entries, total = await audit_service.list_audit_logs(AuditLogFilter(), page=1, limit=20)

    assert len(entries) == 1
    assert total == 1


async def test_list_audit_logs_with_date_filters() -> None:
    from_date = date(2026, 8, 1)
    to_date = date(2026, 8, 31)
    filters = AuditLogFilter(from_date=from_date, to_date=to_date)
    with patch.object(
        audit_service.audit_repository,
        "list_audit_logs",
        new=AsyncMock(return_value=([], 0)),
    ) as mock_list:
        entries, total = await audit_service.list_audit_logs(filters, page=1, limit=20)
    assert entries == []
    assert total == 0
    mock_list.assert_awaited_once_with(filters=filters, page=1, limit=20)
