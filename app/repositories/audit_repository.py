from datetime import date, datetime, time
from typing import Any

from sqlalchemy import func, select
from sqlmodel import col

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.database.session import get_session
from app.models.audit_log import AuditLog


async def create_audit_log(
    actor: str | None,
    action: str,
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
) -> AuditLog:
    db = get_session()
    entry = AuditLog(
        actor=actor,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        url=url,
        payload=payload,
        response=response,
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
    actor_type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[list[AuditLog], int]:
    db = get_session()
    filters = []
    if actor:
        filters.append(col(AuditLog.actor) == actor)
    if action:
        filters.append(col(AuditLog.action) == action)
    if resource_type:
        filters.append(col(AuditLog.resource_type) == resource_type)
    if actor_type:
        filters.append(col(AuditLog.actor_type) == actor_type)
    if from_date is not None:
        filters.append(col(AuditLog.created_at) >= datetime.combine(from_date, time.min))
    if to_date is not None:
        filters.append(col(AuditLog.created_at) <= datetime.combine(to_date, time.max))

    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    result = await db.execute(
        select(AuditLog)
        .where(*filters)
        .order_by(col(AuditLog.created_at).desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0
