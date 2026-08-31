"""Export service tests (repositories mocked)."""

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.exceptions import (
    ExportExpiredError,
    ExportNotFoundError,
    ExportTooLargeError,
    PermissionDeniedError,
)
from app.models.enums import ExportStatus
from app.models.export import Export
from app.schemas.export import AuditExportFilters, ExportCreate
from app.services import export_service


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _export(
    *,
    export_id: uuid.UUID | None = None,
    created_by: str = "admin@example.com",
    status: str = ExportStatus.READY.value,
    file_path: str | None = "exports/audit_export_test.xlsx",
    expires_at: datetime | None = None,
) -> Export:
    return Export(
        id=export_id or uuid.uuid4(),
        module="audit",
        reason="Regulatory request",
        file_format="xlsx",
        classification="Restricted",
        filters={"actor": None, "action": "All"},
        status=status,
        row_count=10,
        file_path=file_path,
        expires_at=expires_at or (_utcnow_naive() + timedelta(hours=1)),
        created_by=created_by,
    )


async def test_create_export_raises_when_over_max_rows() -> None:
    with patch.object(
        export_service.export_repository, "count_audit_logs", new=AsyncMock(return_value=100_001)
    ):
        with pytest.raises(ExportTooLargeError):
            await export_service.create_export(
                admin_email="admin@example.com",
                data=ExportCreate(module="audit", reason="Test", filters=AuditExportFilters()),
            )


async def test_create_export_persists_and_spawns_generation() -> None:
    created = _export(status=ExportStatus.PENDING.value, file_path=None)
    with (
        patch.object(
            export_service.export_repository, "count_audit_logs", new=AsyncMock(return_value=5)
        ),
        patch.object(
            export_service.export_repository, "create_export", new=AsyncMock(return_value=created)
        ),
        patch.object(export_service, "_spawn_generation") as spawn,
        patch.object(export_service.audit_service, "record", new=AsyncMock()),
    ):
        export = await export_service.create_export(
            admin_email="admin@example.com",
            data=ExportCreate(module="audit", reason="Test", filters=AuditExportFilters()),
        )
    assert export is created
    spawn.assert_called_once_with(created.id)


async def test_get_export_status_rejects_other_owner() -> None:
    export = _export(created_by="other@example.com")
    with patch.object(
        export_service.export_repository, "get_export", new=AsyncMock(return_value=export)
    ):
        with pytest.raises(PermissionDeniedError):
            await export_service.get_export_status(
                export_id=export.id, admin_email="admin@example.com"
            )


async def test_get_export_status_not_found() -> None:
    with patch.object(
        export_service.export_repository, "get_export", new=AsyncMock(return_value=None)
    ):
        with pytest.raises(ExportNotFoundError):
            await export_service.get_export_status(
                export_id=uuid.uuid4(), admin_email="admin@example.com"
            )


async def test_download_export_expired_raises_and_marks_expired() -> None:
    export = _export(expires_at=_utcnow_naive() - timedelta(minutes=1))
    with (
        patch.object(
            export_service.export_repository, "get_export", new=AsyncMock(return_value=export)
        ),
        patch.object(export_service.export_repository, "update_export", new=AsyncMock()),
    ):
        with pytest.raises(ExportExpiredError):
            await export_service.download_export(
                export_id=export.id, admin_email="admin@example.com"
            )
    assert export.status == ExportStatus.EXPIRED.value


async def test_download_export_regenerates_lazily_when_file_missing(tmp_path) -> None:
    export = _export(file_path=str(tmp_path / "missing.xlsx"))
    generated_path = tmp_path / "regenerated.xlsx"
    generated_path.write_bytes(b"PK fake xlsx")
    generated = _export(file_path=str(generated_path))
    with (
        patch.object(
            export_service.export_repository, "get_export", new=AsyncMock(return_value=export)
        ),
        patch.object(export_service, "_generate", new=AsyncMock(return_value=generated)),
        patch.object(export_service.audit_service, "record", new=AsyncMock()),
    ):
        response = await export_service.download_export(
            export_id=export.id, admin_email="admin@example.com"
        )
    assert response.path == Path(generated.file_path)


async def test_download_export_audits_and_serves(tmp_path) -> None:
    target = tmp_path / "real.xlsx"
    target.write_bytes(b"PK fake xlsx")
    export = _export(file_path=str(target))
    with (
        patch.object(
            export_service.export_repository, "get_export", new=AsyncMock(return_value=export)
        ),
        patch.object(export_service.audit_service, "record", new=AsyncMock()) as record,
    ):
        response = await export_service.download_export(
            export_id=export.id, admin_email="admin@example.com"
        )
    record.assert_awaited_once()
    details = record.await_args.kwargs["details"]
    assert details["module"] == "audit"
    assert response.path == target
