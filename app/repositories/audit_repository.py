"""Audit evidence persistence: durable intent intake, chained entry promotion."""

from datetime import datetime, time
from typing import Any

from sqlalchemy import func, select
from sqlmodel import col

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.database.session import get_session
from app.models.audit_intent import AuditIntent
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogFilter

# Postgres advisory-lock key serializing hash-chain writers (released at commit).
_CHAIN_LOCK_KEY = 727_411
_PROMOTE_BATCH_SIZE = 200


def audit_log_filters(filters: AuditLogFilter) -> list[Any]:
    """The WHERE conditions for an AuditLogFilter — the single filter→SQL mapping."""
    conditions: list[Any] = []
    if filters.actor:
        conditions.append(col(AuditLog.actor) == filters.actor)
    if filters.action:
        conditions.append(col(AuditLog.action) == filters.action)
    if filters.resource_type:
        conditions.append(col(AuditLog.resource_type) == filters.resource_type)
    if filters.actor_type:
        conditions.append(col(AuditLog.actor_type) == filters.actor_type)
    if filters.from_date is not None:
        conditions.append(col(AuditLog.created_at) >= datetime.combine(filters.from_date, time.min))
    if filters.to_date is not None:
        conditions.append(col(AuditLog.created_at) <= datetime.combine(filters.to_date, time.max))
    return conditions


async def create_audit_intent(
    payload: dict[str, Any],
    created_at: datetime,
) -> AuditIntent:
    """Durably record the intent; the forwarder forges the Audit Entry later."""
    db = get_session()
    intent = AuditIntent(payload=payload, created_at=created_at)
    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return intent


async def _chain_entries(db: Any, entries: list[AuditLog]) -> None:
    """Assign seq/prev_hash/entry_hash to each entry, extending the committed tip."""
    for entry in entries:
        tip_seq = await db.scalar(select(func.coalesce(func.max(AuditLog.seq), 0)))
        tip_hash = await db.scalar(
            select(col(AuditLog.entry_hash)).where(col(AuditLog.seq) == tip_seq)
        )
        entry.seq = int(tip_seq or 0) + 1
        entry.prev_hash = tip_hash
        entry.entry_hash = entry.compute_entry_hash(tip_hash)
        db.add(entry)


async def promote_audit_intents() -> int:
    """Forge chained Audit Entries from the oldest intents atomically; return count.

    Insert + delete share one transaction, so a crash retries the batch without
    duplicating evidence. Returns 0 when the outbox is empty.
    """
    db = get_session()
    result = await db.execute(
        select(AuditIntent).order_by(col(AuditIntent.created_at)).limit(_PROMOTE_BATCH_SIZE)
    )
    intents = list(result.scalars().all())
    if not intents:
        return 0

    # Serialize with the chain write discipline; lock releases at this commit.
    await db.execute(select(func.pg_advisory_xact_lock(_CHAIN_LOCK_KEY)))
    entries = [AuditLog(**intent.payload, created_at=intent.created_at) for intent in intents]
    await _chain_entries(db, entries)
    for intent in intents:
        await db.delete(intent)
    await db.commit()
    return len(entries)


async def list_audit_logs(
    filters: AuditLogFilter,
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[AuditLog], int]:
    db = get_session()
    conditions = audit_log_filters(filters)
    total = await db.scalar(select(func.count()).select_from(AuditLog).where(*conditions))
    result = await db.execute(
        select(AuditLog)
        .where(*conditions)
        .order_by(col(AuditLog.created_at).desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0
