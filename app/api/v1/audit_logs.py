"""Audit log listing routes."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin
from app.core.constants import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
)
from app.models.audit_log import AuditLog
from app.models.enums import (
    AuditAction,
    AuditActionFilter,
    AuditResourceType,
    AuditResourceTypeFilter,
    resolve_filter,
)
from app.models.platform_admin import PlatformAdmin
from app.schemas.audit import CODE_LISTED, MSG_LISTED, AuditLogListData, AuditLogRead
from app.schemas.common import ApiResponse, Pagination
from app.services import audit_service
from app.utils.pagination import total_pages

router = APIRouter(tags=["Audit"])


@router.get("/audit-logs", response_model=ApiResponse[AuditLogListData], summary="List audit logs")
async def list_audit_logs(
    page: int = Query(DEFAULT_PAGE, ge=MIN_PAGE),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    actor: str | None = Query(None, description="Filter by actor (username)"),
    action: AuditActionFilter = Query(AuditActionFilter.ALL, description="Filter by audit action"),
    resource_type: AuditResourceTypeFilter = Query(
        AuditResourceTypeFilter.ALL, description="Filter by resource type"
    ),
    _admin: PlatformAdmin = Depends(get_current_admin),
) -> ApiResponse[AuditLogListData]:
    """List audit log entries, paginated and filterable by actor, action, or resource type."""
    action_value = resolve_filter(value=action, base=AuditAction)
    resource_type_value = resolve_filter(value=resource_type, base=AuditResourceType)
    entries, total = await audit_service.list_audit_logs(
        page=page,
        limit=limit,
        actor=actor,
        action=action_value,
        resource_type=resource_type_value,
    )
    body = _to_audit_log_list_data(entries=entries, page=page, limit=limit, total=total)
    return ApiResponse(code=CODE_LISTED, message=MSG_LISTED, data=body)


def _to_audit_log_list_data(
    entries: list[AuditLog], page: int, limit: int, total: int
) -> AuditLogListData:
    return AuditLogListData(
        data=[AuditLogRead.model_validate(e) for e in entries],
        pagination=Pagination(
            page=page,
            limit=limit,
            total_items=total,
            total_pages=total_pages(total_items=total, limit=limit),
        ),
    )
