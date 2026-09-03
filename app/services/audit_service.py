"""Audit recording and listing business logic."""

import logging
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from app.core.audit_context import get_current_actor, get_request_metadata
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.tracing import traced
from app.exceptions.exceptions import AppError
from app.models.audit_log import AuditLog
from app.repositories import audit_repository
from app.utils.redact import redact

logger = logging.getLogger("app.services.audit")


@dataclass(frozen=True)
class AuditEvent:
    """One consequential action claimed for recording (see CONTEXT.md)."""

    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    # Reserved for the mandatory change reason the BRD requires on governed actions.
    reason: str | None = None


@traced("audit_service.record")
async def record(event: AuditEvent) -> None:
    # Actor-agnostic: identity (actor + type) and HTTP facts come from the current
    # request, never from the event — set by get_current_admin, claimed_actor,
    # system_actor, and the request middleware (ADR-0014/0015).
    request_actor = get_current_actor()
    actor = request_actor.actor if request_actor is not None else None
    actor_type = request_actor.actor_type if request_actor is not None else None
    metadata = get_request_metadata()
    url = metadata.url if metadata is not None else None
    ip_address = metadata.ip_address if metadata is not None else None
    user_agent = metadata.user_agent if metadata is not None else None
    request_id = metadata.request_id if metadata is not None else None
    try:
        await audit_repository.create_audit_log(
            actor=actor,
            actor_type=actor_type,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            details=redact(event.details),
            url=url,
            payload=redact(event.payload),
            response=redact(event.response),
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        logger.exception("audit write failed (best-effort); action=%s", event.action)


async def record_failure(event: AuditEvent, exc: AppError) -> None:
    """Record a failed action, merging the error's Result Code into details."""
    details = dict(event.details or {})
    details.setdefault("error_code", exc.code)
    await record(replace(event, details=details))


@traced("audit_service.list_audit_logs")
async def list_audit_logs(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    actor: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    actor_type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[list[AuditLog], int]:
    return await audit_repository.list_audit_logs(
        page=page,
        limit=limit,
        actor=actor,
        action=action,
        resource_type=resource_type,
        actor_type=actor_type,
        from_date=from_date,
        to_date=to_date,
    )
