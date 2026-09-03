"""Verify the audit hash chain end-to-end: walk seq order, recompute every hash."""

import asyncio

from sqlalchemy import select
from sqlmodel import col

from app.database.database import async_session_factory
from app.models.audit_log import AuditLog
from app.utils.audit_chain import entry_digest


async def verify() -> tuple[int, list[str]]:
    """Return (sealed entry count, problems); rows without a hash predate the chain."""
    async with async_session_factory() as db:
        result = await db.execute(select(AuditLog).order_by(col(AuditLog.seq)))
        rows = list(result.scalars().all())

    problems: list[str] = []
    sealed = 0
    prev_hash: str | None = None
    for row in rows:
        if row.entry_hash is None:
            continue  # rows written before the chain existed — not part of the evidence
        if row.prev_hash != prev_hash:
            problems.append(f"seq {row.seq}: prev_hash does not link to the previous entry")
        expected = entry_digest(prev_hash, row.chain_fields())
        if row.entry_hash != expected:
            problems.append(f"seq {row.seq}: entry_hash does not match the row's sealed fields")
        prev_hash = row.entry_hash
        sealed += 1
    return sealed, problems


def main() -> None:
    sealed, problems = asyncio.run(verify())
    print(f"sealed entries: {sealed}")
    for problem in problems:
        print(f"TAMPER: {problem}")
    if problems:
        raise SystemExit(1)
    print("audit chain OK")


if __name__ == "__main__":
    main()
