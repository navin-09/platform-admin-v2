"""Export record persistence and audit-log streaming (all SQL)."""

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlmodel import col

from app.core.config import settings
from app.database.session import get_session
from app.models.audit_log import AuditLog
from app.models.enums import Status
from app.models.export import Export
from app.models.platform_admin import PlatformAdmin


async def create_export(
    *,
    module: str,
    reason: str,
    file_format: str,
    classification: str,
    filters: dict[str, object] | None,
    created_by: str,
) -> Export:
    db = get_session()
    entry = Export(
        module=module,
        reason=reason,
        file_format=file_format,
        classification=classification,
        filters=filters,
        created_by=created_by,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_export(export_id: uuid.UUID) -> Export | None:
    db = get_session()
    return await db.get(Export, export_id)


async def update_export(export: Export) -> None:
    """Persist in-place changes to an export row (status, counts, path, expiry)."""
    db = get_session()
    db.add(export)
    await db.commit()


def _audit_filters(
    actor: str | None,
    action: str | None,
    resource_type: str | None,
    actor_type: str | None,
) -> list[Any]:
    filters: list[Any] = []
    if actor:
        filters.append(col(AuditLog.actor) == actor)
    if action:
        filters.append(col(AuditLog.action) == action)
    if resource_type:
        filters.append(col(AuditLog.resource_type) == resource_type)
    if actor_type:
        filters.append(col(AuditLog.actor_type) == actor_type)
    return filters


async def count_audit_logs(
    actor: str | None,
    action: str | None,
    resource_type: str | None,
    actor_type: str | None,
) -> int:
    db = get_session()
    filters = _audit_filters(actor, action, resource_type, actor_type)
    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*filters))
    return total or 0


def _platform_admin_filters(search: str | None, status: str | None) -> list[Any]:
    filters: list[Any] = []
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                col(PlatformAdmin.username).ilike(pattern),
                col(PlatformAdmin.email).ilike(pattern),
            )
        )
    if status is not None:
        filters.append(col(PlatformAdmin.status) == Status(status))
    return filters


async def count_platform_admins(search: str | None, status: str | None) -> int:
    """Count Platform Admins matching the users-list filters (search/status)."""
    db = get_session()
    filters = _platform_admin_filters(search, status)
    total = await db.scalar(select(func.count()).select_from(PlatformAdmin).where(*filters))
    return total or 0


async def stream_platform_admins(
    search: str | None,
    status: str | None,
) -> AsyncIterator[PlatformAdmin]:
    """Stream matching Platform Admins in list order (created_at ASC, id ASC)."""
    db = get_session()
    chunk_size = settings.export_stream_chunk_size
    last_created_at: datetime | None = None
    last_id: uuid.UUID | None = None
    while True:
        filters = _platform_admin_filters(search, status)
        if last_created_at is not None and last_id is not None:
            filters.append(
                or_(
                    col(PlatformAdmin.created_at) > last_created_at,
                    and_(
                        col(PlatformAdmin.created_at) == last_created_at,
                        col(PlatformAdmin.id) > last_id,
                    ),
                )
            )
        result = await db.execute(
            select(PlatformAdmin)
            .where(*filters)
            .order_by(col(PlatformAdmin.created_at), col(PlatformAdmin.id))
            .limit(chunk_size)
        )
        rows: list[PlatformAdmin] = list(result.scalars().all())
        if not rows:
            return
        for row in rows:
            yield row
        if len(rows) < chunk_size:
            return
        last_created_at = rows[-1].created_at
        last_id = rows[-1].id


async def stream_audit_logs(
    actor: str | None,
    action: str | None,
    resource_type: str | None,
    actor_type: str | None,
) -> AsyncIterator[AuditLog]:
    """Stream matching audit logs (created_at DESC, id DESC) via keyset pagination."""
    db = get_session()
    chunk_size = settings.export_stream_chunk_size
    last_created_at: datetime | None = None
    last_id: uuid.UUID | None = None
    while True:
        filters = _audit_filters(actor, action, resource_type, actor_type)
        if last_created_at is not None and last_id is not None:
            filters.append(
                or_(
                    col(AuditLog.created_at) < last_created_at,
                    and_(
                        col(AuditLog.created_at) == last_created_at,
                        col(AuditLog.id) < last_id,
                    ),
                )
            )
        result = await db.execute(
            select(AuditLog)
            .where(*filters)
            .order_by(col(AuditLog.created_at).desc(), col(AuditLog.id).desc())
            .limit(chunk_size)
        )
        rows: list[AuditLog] = list(result.scalars().all())
        if not rows:
            return
        for row in rows:
            yield row
        if len(rows) < chunk_size:
            return
        last_created_at = rows[-1].created_at
        last_id = rows[-1].id
