"""Audit log data access (all SQL)."""

from typing import Any

from sqlalchemy import func, select
from sqlmodel import col

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.database.session import get_session
from app.models.audit_log import AuditLog


async def create_audit_log(
    actor: str | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    db = get_session()
    entry = AuditLog(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_audit_logs(
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    actor: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
) -> tuple[list[AuditLog], int]:
    db = get_session()
    filters = []
    if actor:
        filters.append(col(AuditLog.actor) == actor)
    if action:
        filters.append(col(AuditLog.action) == action)
    if resource_type:
        filters.append(col(AuditLog.resource_type) == resource_type)

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    result = await db.execute(
        select(AuditLog)
        .where(*filters)
        .order_by(col(AuditLog.created_at).desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0
