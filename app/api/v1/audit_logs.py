from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin, require_permission
from app.core.constants import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
)
from app.models.enums import (
    ActorType,
    AuditAction,
    AuditActionFilter,
    AuditActorTypeFilter,
    AuditResourceType,
    AuditResourceTypeFilter,
    PermissionName,
    resolve_filter,
)
from app.models.platform_admin import PlatformAdmin
from app.schemas.audit import CODE_LISTED, MSG_LISTED, AuditLogRead
from app.schemas.common import ApiResponse, ListData, build_list_data
from app.services import audit_service
from app.utils.limits import ACTOR_FILTER_MAX_LENGTH

router = APIRouter(tags=["Audit"])


@router.get(
    "/audit-logs",
    response_model=ApiResponse[ListData[AuditLogRead]],
    summary="List audit logs",
)
async def list_audit_logs(
    page: int = Query(DEFAULT_PAGE, ge=MIN_PAGE),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    actor: str | None = Query(
        None, max_length=ACTOR_FILTER_MAX_LENGTH, description="Filter by actor (email)"
    ),
    action: AuditActionFilter = Query(AuditActionFilter.ALL, description="Filter by audit action"),
    resource_type: AuditResourceTypeFilter = Query(
        AuditResourceTypeFilter.ALL, description="Filter by resource type"
    ),
    actor_type: AuditActorTypeFilter = Query(
        AuditActorTypeFilter.ALL, description="Filter by actor type"
    ),
    from_date: date | None = Query(
        None, description="Filter audit logs created on or after this date (YYYY-MM-DD)"
    ),
    to_date: date | None = Query(
        None, description="Filter audit logs created on or before this date (YYYY-MM-DD)"
    ),
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.AUDIT_READ)),
) -> ApiResponse[ListData[AuditLogRead]]:
    """List audit log entries, paginated and filterable by actor, action,
    resource type, or date range.
    """
    entries, total = await audit_service.list_audit_logs(
        page=page,
        limit=limit,
        actor=actor,
        action=resolve_filter(action, AuditAction),
        resource_type=resolve_filter(resource_type, AuditResourceType),
        actor_type=resolve_filter(actor_type, ActorType),
        from_date=from_date,
        to_date=to_date,
    )
    response: ApiResponse[ListData[AuditLogRead]] = ApiResponse(
        code=CODE_LISTED,
        message=MSG_LISTED,
        data=build_list_data(AuditLogRead, entries, page=page, limit=limit, total=total),
    )
    await audit_service.record(
        actor=admin.email,
        actor_type=ActorType.ADMIN.value,
        action=AuditAction.AUDIT_READ,
        resource_type=AuditResourceType.AUDIT,
        details={"page": page, "limit": limit, "total": total},
    )
    return response
