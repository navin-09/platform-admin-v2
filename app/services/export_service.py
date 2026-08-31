"""Export engine: create (uniform flow), background generate, status, download.

BRD §6.6 / §17.7 / §19.2: every export needs a mandatory reason, carries only
authorized fields, retains filters and metadata, is classified, is audited on
generation and download, and is served through a 24-hour single-user link.
Generation runs as an in-process task; if the process died before finishing,
the download endpoint lazily regenerates the file (idempotent).
"""

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.export_config import EXPORT_SPECS, ExportSpec
from app.database.database import db_session
from app.exceptions.exceptions import (
    ExportExpiredError,
    ExportNotFoundError,
    ExportTooLargeError,
    PermissionDeniedError,
    ValidationError,
    field_errors,
)
from app.models.enums import (
    ActorType,
    AuditAction,
    AuditResourceType,
    ExportStatus,
    Status,
)
from app.models.export import Export
from app.repositories import export_repository
from app.schemas.export import AuditExportFilters, ExportCreate, UsersExportFilters
from app.services import audit_service, xlsx_writer
from app.utils.time import utcnow

logger = logging.getLogger("app.services.export")

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def create_export(*, admin_email: str, data: ExportCreate) -> Export:
    """Validate, count, persist, and kick off background generation."""
    spec = _spec(data.module)
    filters_model = _filters_for_module(data)
    filters = filters_model.model_dump(mode="json")

    row_count = await _count_rows(spec, filters)
    if row_count > settings.export_max_rows:
        raise ExportTooLargeError(
            data={"row_count": row_count, "max_rows": settings.export_max_rows}
        )

    export = await export_repository.create_export(
        module=data.module,
        reason=data.reason,
        file_format=data.format,
        classification=spec.classification,
        filters=filters,
        created_by=admin_email,
    )
    _spawn_generation(export.id)

    await audit_service.record(
        actor=admin_email,
        actor_type=ActorType.ADMIN.value,
        action=AuditAction.EXPORT_GENERATED,
        resource_type=AuditResourceType.EXPORT,
        resource_id=str(export.id),
        details={
            "module": data.module,
            "reason": data.reason,
            "row_count": row_count,
            "filters": filters,
        },
    )
    return export


async def get_export_status(*, export_id: uuid.UUID, admin_email: str) -> Export:
    """Status of one export, owner-checked (single-user links, BRD §6.6)."""
    return await _owned_export(export_id, admin_email)


async def download_export(*, export_id: uuid.UUID, admin_email: str) -> FileResponse:
    """Serve the file: owner check, 24h expiry, lazy regeneration, audited."""
    export = await _owned_export(export_id, admin_email)

    if export.expires_at is not None and export.expires_at <= utcnow():
        export.status = ExportStatus.EXPIRED.value
        await export_repository.update_export(export)
        raise ExportExpiredError()

    if export.status != ExportStatus.READY.value or not _file_exists(export):
        export = await _generate(export_id)  # lazy regeneration (idempotent)

    path = Path(export.file_path or "")
    if not path.is_file():
        raise ExportNotFoundError()

    await audit_service.record(
        actor=admin_email,
        actor_type=ActorType.ADMIN.value,
        action=AuditAction.EXPORT_DOWNLOADED,
        resource_type=AuditResourceType.EXPORT,
        resource_id=str(export.id),
        details={
            "module": export.module,
            "reason": export.reason,
            "row_count": export.row_count,
            "classification": export.classification,
        },
    )
    return FileResponse(path, media_type=XLSX_MEDIA_TYPE, filename=path.name)


def _spawn_generation(export_id: uuid.UUID) -> None:
    """Fire-and-forget generation. Wrapped so tests can patch it."""
    asyncio.create_task(_generate_task(export_id))


async def _generate_task(export_id: uuid.UUID) -> None:
    """Background generation with failure marking. If the process dies before
    completion, the download endpoint regenerates lazily (idempotent)."""
    try:
        async with db_session():
            await _generate(export_id)
    except Exception:
        logger.exception("export generation failed; export_id=%s", export_id)
        try:
            async with db_session():
                export = await export_repository.get_export(export_id)
                if export is not None and export.status == ExportStatus.PENDING.value:
                    export.status = ExportStatus.FAILED.value
                    export.generation_error = "Generation failed; retry the download."
                    await export_repository.update_export(export)
        except Exception:
            logger.exception("failed to mark export failed; export_id=%s", export_id)


async def _generate(export_id: uuid.UUID) -> Export:
    """Stream matching rows into an xlsx file and mark the export READY."""
    export = await export_repository.get_export(export_id)
    if export is None:
        raise ExportNotFoundError()
    spec = _spec(export.module)

    path = settings.export_dir_path / _filename(spec, export)
    metadata = {
        "Export ID": str(export.id),
        "Module": spec.label,
        "Exported By": export.created_by,
        "Reason": export.reason,
        "Classification": spec.classification,
        "Applied Filters": json.dumps(export.filters, default=str),
        "Generated At (UTC)": utcnow().isoformat(),
        "Time Zone": "UTC (the UI displays IST)",
        "Max Records Per File": settings.export_max_rows,
    }

    row_count = await xlsx_writer.write_export_xlsx(
        path,
        metadata=metadata,
        metadata_sheet="Metadata",
        data_sheet=spec.sheet_name,
        headers=[header for _, header in spec.columns],
        rows=_row_stream(spec, export.filters),
    )

    export.status = ExportStatus.READY.value
    export.row_count = row_count
    export.file_path = str(path)
    export.expires_at = utcnow() + timedelta(hours=settings.export_link_ttl_hours)
    await export_repository.update_export(export)
    return export


def _row_stream(
    spec: ExportSpec,
    filters: dict[str, object] | None,
) -> AsyncIterator[list[Any]]:
    """Map each model row to the spec's ordered column values, per module."""

    async def _iter() -> AsyncIterator[list[Any]]:
        if spec.module == "audit":
            actor, action, resource_type, actor_type = _audit_filters_from_dict(filters)
            async for audit_entry in export_repository.stream_audit_logs(
                actor=actor, action=action, resource_type=resource_type, actor_type=actor_type
            ):
                yield _extract_row(audit_entry, spec)
        elif spec.module == "users":
            search, status = _users_filters_from_dict(filters)
            async for admin_entry in export_repository.stream_platform_admins(
                search=search, status=status
            ):
                yield _extract_row(admin_entry, spec)
        else:
            raise ValidationError(
                data=field_errors([("module", f"unsupported export module: {spec.module}")])
            )

    return _iter()


async def _count_rows(spec: ExportSpec, filters: dict[str, object] | None) -> int:
    """Count matching rows for the spec's module (drives the 100k cap)."""
    if spec.module == "audit":
        actor, action, resource_type, actor_type = _audit_filters_from_dict(filters)
        return await export_repository.count_audit_logs(
            actor=actor, action=action, resource_type=resource_type, actor_type=actor_type
        )
    if spec.module == "users":
        search, status = _users_filters_from_dict(filters)
        return await export_repository.count_platform_admins(search=search, status=status)
    raise ValidationError(
        data=field_errors([("module", f"unsupported export module: {spec.module}")])
    )


def _extract_row(entry: object, spec: ExportSpec) -> list[Any]:
    return [getattr(entry, field) for field, _ in spec.columns]


def _filename(spec: ExportSpec, export: Export) -> str:
    stamp = export.created_at.strftime("%Y%m%d_%H%M%S")
    return f"{spec.filename_prefix}_{stamp}_{export.id.hex[:8]}.xlsx"


def _filters_for_module(data: ExportCreate) -> AuditExportFilters | UsersExportFilters:
    """Resolve the per-module filter shape; reject a mismatched shape outright.

    The union alone cannot see ``module`` (pydantic validates fields in
    isolation), so a users-shaped filter on an audit export would otherwise
    parse and silently export *everything*. Invariant ③: no silent degradation.
    """
    if data.filters is None:
        if data.module == "audit":
            return AuditExportFilters()
        if data.module == "users":
            return UsersExportFilters()
    if data.module == "audit" and isinstance(data.filters, AuditExportFilters):
        return data.filters
    if data.module == "users" and isinstance(data.filters, UsersExportFilters):
        return data.filters
    raise ValidationError(
        data=field_errors([("filters", f"filters shape does not match module '{data.module}'")])
    )


def _spec(module: str) -> ExportSpec:
    spec = EXPORT_SPECS.get(module)
    if spec is None:
        raise ValidationError(
            data=field_errors([("module", f"unsupported export module: {module}")])
        )
    return spec


async def _owned_export(export_id: uuid.UUID, admin_email: str) -> Export:
    export = await export_repository.get_export(export_id)
    if export is None:
        raise ExportNotFoundError()
    if export.created_by != admin_email:
        raise PermissionDeniedError()
    return export


def _file_exists(export: Export) -> bool:
    return export.file_path is not None and Path(export.file_path).is_file()


def _audit_filters_from_dict(
    filters: dict[str, object] | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    if not filters:
        return (None, None, None, None)
    actor = filters.get("actor")
    return (
        actor if isinstance(actor, str) else None,
        _resolve_stored(filters.get("action"), AuditAction),
        _resolve_stored(filters.get("resource_type"), AuditResourceType),
        _resolve_stored(filters.get("actor_type"), ActorType),
    )


def _users_filters_from_dict(filters: dict[str, object] | None) -> tuple[str | None, str | None]:
    if not filters:
        return (None, None)
    search = filters.get("search")
    return (
        search if isinstance(search, str) and search else None,
        _resolve_stored(filters.get("status"), Status),
    )


def _resolve_stored(
    value: object,
    enum_cls: type[AuditAction] | type[AuditResourceType] | type[ActorType] | type[Status],
) -> str | None:
    if not isinstance(value, str) or value == "All":
        return None
    try:
        return str(enum_cls(value))
    except ValueError:
        return None
