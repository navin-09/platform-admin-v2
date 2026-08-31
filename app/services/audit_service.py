"""Audit recording and listing business logic."""

import logging
from datetime import date
from typing import Any

from app.core.audit_context import get_current_actor, get_request_metadata
from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.tracing import traced
from app.models.audit_log import AuditLog
from app.repositories import audit_repository
from app.utils.redact import redact

logger = logging.getLogger("app.services.audit")


@traced("audit_service.record")
async def record(
    action: str,
    actor: str | None = None,
    actor_type: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    url: str | None = None,
    payload: dict[str, Any] | None = None,
    response: dict[str, Any] | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    # The service layer stays actor-agnostic: when no actor is passed, resolve
    # it (and its type) from the ambient request context (ADR-0014/0015).
    if actor is None:
        ambient = get_current_actor()
        if ambient is not None:
            actor = ambient.actor
            actor_type = ambient.actor_type
    metadata = get_request_metadata()
    if metadata is not None:
        if url is None:
            url = metadata.url
        if ip_address is None:
            ip_address = metadata.ip_address
        if user_agent is None:
            user_agent = metadata.user_agent
        if request_id is None:
            request_id = metadata.request_id
    try:
        await audit_repository.create_audit_log(
            actor=actor,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=redact(details),
            url=url,
            payload=redact(payload),
            response=redact(response),
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except Exception:
        logger.exception("audit write failed (best-effort); action=%s", action)


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
