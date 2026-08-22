"""Audit recording and listing business logic."""

import logging
from typing import Any

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.tracing import traced
from app.models.audit_log import AuditLog
from app.repositories import audit_repository

logger = logging.getLogger("app.services.audit")


@traced("audit_service.record")
async def record(
    actor: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    try:
        await audit_repository.create_audit_log(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
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
) -> tuple[list[AuditLog], int]:
    return await audit_repository.list_audit_logs(
        page=page, limit=limit, actor=actor, action=action, resource_type=resource_type
    )
