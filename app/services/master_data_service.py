"""Generic master-data CRUD service: list/get/create/update/delete with FK validation and audit."""

import uuid
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy import Column, ColumnElement, func, select
from sqlmodel import SQLModel

from app.core.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.core.master_data import REGISTRY, TableSpec, fk_edges, nested_name, record_id, table_of
from app.database.session import get_session
from app.exceptions.exceptions import MasterDataNotFoundError, ValidationError, field_errors
from app.models.enums import AuditAction, Status
from app.repositories import master_data_resolver
from app.services import audit_service


async def list_rows(
    spec: TableSpec,
    *,
    page: int = DEFAULT_PAGE,
    limit: int = DEFAULT_PAGE_SIZE,
    search: str | None = None,
    status: Status | None = None,
) -> tuple[list[BaseModel], int]:
    """List a page of rows, fully nested."""
    db = get_session()
    filters: list[ColumnElement[bool]] = []
    if search and spec.search_field:
        filters.append(_column(spec, spec.search_field).ilike(f"%{search}%"))
    if status is not None:
        filters.append(_column(spec, "status") == status)
    total = await db.scalar(select(func.count()).select_from(spec.model).where(*filters))
    result = await db.execute(
        select(spec.model)
        .where(*filters)
        .order_by(_column(spec, "created_at"))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = list(result.scalars().all())
    nodes = await master_data_resolver.resolve_graph(spec, [record_id(row) for row in rows])
    return [serialize(spec, row, nodes) for row in rows], total or 0


async def get_row(spec: TableSpec, record_id: uuid.UUID) -> BaseModel:
    """Fetch one row, fully nested."""
    row = await _get_or_404(spec, record_id)
    nodes = await master_data_resolver.resolve_graph(spec, [record_id])
    return serialize(spec, row, nodes)


async def create_row(spec: TableSpec, data: BaseModel) -> BaseModel:
    """Validate FKs, insert the row, audit, and return it fully nested."""
    db = get_session()
    payload = data.model_dump()
    await _validate_fks(spec, payload)
    row = spec.model(**payload)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await audit_service.record(
        action=AuditAction.MASTER_DATA_CREATE,
        resource_type=spec.table,
        resource_id=str(record_id(row)),
        details=_json_safe(_scalar_fields(spec, row)),
    )
    return await _read_one(spec, record_id(row))


async def update_row(spec: TableSpec, record_id: uuid.UUID, data: BaseModel) -> BaseModel:
    """Validate changed FKs, apply the diff, audit before/after, and return nested."""
    db = get_session()
    row = await _get_or_404(spec, record_id)
    payload = data.model_dump(exclude_unset=True, exclude_none=True)
    await _validate_fks(spec, payload)
    before = _json_safe(_scalar_fields(spec, row))
    for field, value in payload.items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    after = _json_safe(_scalar_fields(spec, row))
    diff = {key: {"from": before.get(key), "to": after.get(key)} for key in payload}
    await audit_service.record(
        action=AuditAction.MASTER_DATA_UPDATE,
        resource_type=spec.table,
        resource_id=str(record_id),
        details=diff,
    )
    return await _read_one(spec, record_id)


async def delete_row(spec: TableSpec, record_id: uuid.UUID) -> None:
    """Soft-delete the row (status -> inactive) and audit."""
    db = get_session()
    row = await _get_or_404(spec, record_id)
    cast(Any, row).status = Status.INACTIVE
    await db.commit()
    await audit_service.record(
        action=AuditAction.MASTER_DATA_DELETE,
        resource_type=spec.table,
        resource_id=str(record_id),
    )


def serialize(
    spec: TableSpec,
    row: SQLModel,
    nodes: dict[tuple[str, uuid.UUID], SQLModel],
) -> BaseModel:
    """Render one row (and its resolved graph) into the typed Read DTO."""
    return _serialize(spec, row, nodes, frozenset())


async def _read_one(spec: TableSpec, record_id: uuid.UUID) -> BaseModel:
    row = await _get_or_404(spec, record_id)
    nodes = await master_data_resolver.resolve_graph(spec, [record_id])
    return serialize(spec, row, nodes)


async def _get_or_404(spec: TableSpec, record_id: uuid.UUID) -> SQLModel:
    db = get_session()
    row = await db.get(spec.model, record_id)
    if row is None:
        raise MasterDataNotFoundError()
    return row


async def _validate_fks(spec: TableSpec, payload: dict[str, Any]) -> None:
    """Ensure every provided FK id exists; raise a field error on any missing target."""
    db = get_session()
    for local, target_table in fk_edges(spec.model):
        target_id = payload.get(local)
        if target_id is None:
            continue
        pk = table_of(REGISTRY[target_table].model).c["id"]
        exists = await db.scalar(select(pk).where(pk == target_id))
        if exists is None:
            raise ValidationError(
                data=field_errors([(local, f"Referenced {target_table} record not found")])
            )


def _serialize(
    spec: TableSpec,
    row: SQLModel,
    nodes: dict[tuple[str, uuid.UUID], SQLModel],
    ancestors: frozenset[tuple[str, uuid.UUID]],
) -> BaseModel:
    """Build the Read DTO, resolving FKs into nested objects (cycle-safe)."""
    fields: dict[str, Any] = {
        column.name: getattr(row, column.name) for column in table_of(spec.model).columns
    }
    for local, target_table in fk_edges(spec.model):
        field_name = nested_name(local)
        target_id = getattr(row, local)
        key = (target_table, target_id) if target_id is not None else None
        if key is None or key in ancestors:
            fields[field_name] = None
            continue
        target = nodes.get(key)
        if target is None:
            fields[field_name] = None
            continue
        fields[field_name] = _serialize(REGISTRY[target_table], target, nodes, ancestors | {key})
    for coll in spec.collections:
        fields[coll.via_table] = [
            _serialize(
                REGISTRY[coll.via_table], child, nodes, ancestors | {(spec.table, record_id(row))}
            )
            for child in _children(nodes, coll.via_table, coll.via_fk, record_id(row))
        ]
    return spec.read_model(**fields)


def _children(
    nodes: dict[tuple[str, uuid.UUID], SQLModel],
    via_table: str,
    via_fk: str,
    parent_id: uuid.UUID,
) -> list[SQLModel]:
    """Return the child rows in ``nodes`` whose ``via_fk`` points at ``parent_id``."""
    return [
        node
        for (table, _), node in nodes.items()
        if table == via_table and getattr(node, via_fk) == parent_id
    ]


def _scalar_fields(spec: TableSpec, row: SQLModel) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in table_of(spec.model).columns}


def _column(spec: TableSpec, name: str) -> Column[Any]:
    return table_of(spec.model).columns[name]


def _json_safe(data: dict[str, Any]) -> dict[str, Any]:
    return {key: _to_json(value) for key, value in data.items()}


def _to_json(value: Any) -> Any:
    """Convert values the audit JSON column cannot natively serialize."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, date):  # also covers datetime (a date subclass)
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    return value
