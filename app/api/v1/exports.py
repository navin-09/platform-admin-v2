"""Export routes: create, poll status, download (24h single-user links)."""

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.deps import get_current_admin, require_permission
from app.models.enums import PermissionName
from app.models.platform_admin import PlatformAdmin
from app.schemas.common import ApiResponse
from app.schemas.export import (
    CODE_CREATED,
    CODE_FETCHED,
    MSG_CREATED,
    MSG_FETCHED,
    ExportCreate,
    ExportRead,
)
from app.services import export_service

router = APIRouter(tags=["Exports"])


@router.post(
    "/exports",
    response_model=ApiResponse[ExportRead],
    status_code=201,
    summary="Create an export",
)
async def create_export(
    data: ExportCreate,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.AUDIT_READ)),
) -> ApiResponse[ExportRead]:
    """Create an export of audit logs matching the given filters (reason mandatory)."""
    export = await export_service.create_export(admin_email=admin.email, data=data)
    return ApiResponse(
        code=CODE_CREATED,
        message=MSG_CREATED,
        data=ExportRead.model_validate(export),
    )


@router.get(
    "/exports/{export_id}",
    response_model=ApiResponse[ExportRead],
    summary="Get export status",
)
async def get_export(
    export_id: uuid.UUID,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.AUDIT_READ)),
) -> ApiResponse[ExportRead]:
    """Poll the export status (pending → ready; ready carries row count + expiry)."""
    export = await export_service.get_export_status(export_id=export_id, admin_email=admin.email)
    return ApiResponse(
        code=CODE_FETCHED,
        message=MSG_FETCHED,
        data=ExportRead.model_validate(export),
    )


@router.get(
    "/exports/{export_id}/download",
    response_model=None,
    summary="Download an export (.xlsx, 24-hour single-user link)",
)
async def download_export(
    export_id: uuid.UUID,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.AUDIT_READ)),
) -> FileResponse:
    """Serve the generated xlsx (owner-only, expires 24h after generation)."""
    return await export_service.download_export(export_id=export_id, admin_email=admin.email)
