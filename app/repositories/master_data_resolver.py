"""Master-data FK graph resolution (batched per level; no N+1)."""

import uuid

from sqlalchemy import select
from sqlmodel import SQLModel

from app.core.master_data import REGISTRY, Collection, TableSpec, fk_edges, record_id, table_of
from app.database.session import get_session


async def resolve_graph(
    spec: TableSpec,
    ids: list[uuid.UUID],
) -> dict[tuple[str, uuid.UUID], SQLModel]:
    """Resolve the FK graph reachable from ``ids`` in ``spec``'s table, batched per level."""
    nodes: dict[tuple[str, uuid.UUID], SQLModel] = {}
    visited: set[tuple[str, uuid.UUID]] = set()
    frontier: list[tuple[str, list[uuid.UUID]]] = [(spec.table, ids)]

    for _ in range(spec.max_depth):
        if not frontier:
            break
        next_frontier: list[tuple[str, list[uuid.UUID]]] = []
        for table_name, table_ids in frontier:
            fresh_ids = [i for i in table_ids if (table_name, i) not in visited]
            if not fresh_ids:
                continue
            target_spec = REGISTRY[table_name]
            rows = await _fetch_by_ids(target_spec.model, fresh_ids)
            for row in rows:
                key = (table_name, record_id(row))
                nodes[key] = row
                visited.add(key)
            next_frontier.extend(_reference_targets(target_spec.model, rows))
            next_frontier.extend(await _collection_targets(target_spec, fresh_ids))
        frontier = next_frontier

    return nodes


async def _fetch_by_ids(model: type[SQLModel], ids: list[uuid.UUID]) -> list[SQLModel]:
    """Fetch rows by primary key in one ``IN`` query."""
    db = get_session()
    pk = table_of(model).c["id"]
    result = await db.execute(select(model).where(pk.in_(ids)))
    return list(result.scalars().all())


def _reference_targets(
    model: type[SQLModel], rows: list[SQLModel]
) -> list[tuple[str, list[uuid.UUID]]]:
    """Group the non-null FK ids of ``rows`` by target table."""
    grouped: dict[str, list[uuid.UUID]] = {}
    for local, target_table in fk_edges(model):
        for row in rows:
            target_id = getattr(row, local)
            if target_id is not None:
                grouped.setdefault(target_table, []).append(target_id)
    return list(grouped.items())


async def _collection_targets(
    spec: TableSpec, parent_ids: list[uuid.UUID]
) -> list[tuple[str, list[uuid.UUID]]]:
    """Return the capped child ids for each declared collection, grouped by child table."""
    frontier: list[tuple[str, list[uuid.UUID]]] = []
    for coll in spec.collections:
        child_ids = await _child_ids(coll, parent_ids)
        if child_ids:
            frontier.append((coll.via_table, child_ids))
    return frontier


async def _child_ids(coll: Collection, parent_ids: list[uuid.UUID]) -> list[uuid.UUID]:
    """Return a collection's child ids (capped per parent) in one ``IN`` query."""
    db = get_session()
    model = REGISTRY[coll.via_table].model
    table = table_of(model)
    pk = table.c["id"]
    fk_col = table.c[coll.via_fk]
    result = await db.execute(
        select(fk_col, pk).where(fk_col.in_(parent_ids)).order_by(table.c["created_at"])
    )
    grouped: dict[uuid.UUID, list[uuid.UUID]] = {}
    for parent_id, child_id in result.all():
        bucket = grouped.setdefault(parent_id, [])
        if len(bucket) < coll.cap:
            bucket.append(child_id)
    return [child_id for bucket in grouped.values() for child_id in bucket]
