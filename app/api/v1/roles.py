"""Role CRUD routes."""

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin, require_permission
from app.core.constants import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
)
from app.models.enums import PermissionName, Status, StatusFilter, resolve_filter
from app.models.platform_admin import PlatformAdmin
from app.schemas.common import ApiResponse, ListData, build_list_data
from app.schemas.role import (
    CODE_CREATED,
    CODE_DELETED,
    CODE_FETCHED,
    CODE_LISTED,
    CODE_UPDATED,
    MSG_CREATED,
    MSG_DELETED,
    MSG_FETCHED,
    MSG_LISTED,
    MSG_UPDATED,
    RoleCreate,
    RoleRead,
    RoleUpdate,
)
from app.services import role_service
from app.utils.limits import SEARCH_MAX_LENGTH

router = APIRouter(tags=["Roles"])


@router.post("", response_model=ApiResponse[RoleRead], status_code=201, summary="Create a role")
async def create_role(
    data: RoleCreate,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.ROLES_WRITE)),
) -> ApiResponse[RoleRead]:
    """Create a new role with a name, description, status, and permissions."""
    role = await role_service.create_role(data, actor_id=admin.id)
    return ApiResponse(code=CODE_CREATED, message=MSG_CREATED, data=role)


@router.get("", response_model=ApiResponse[ListData[RoleRead]], summary="List roles")
async def list_roles(
    page: int = Query(DEFAULT_PAGE, ge=MIN_PAGE),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    search: str | None = Query(None, max_length=SEARCH_MAX_LENGTH, description="Search by name"),
    status: StatusFilter = Query(StatusFilter.ALL, description="Filter by status"),
    _: None = Depends(require_permission(PermissionName.ROLES_READ)),
) -> ApiResponse[ListData[RoleRead]]:
    """List roles, paginated and optionally filtered by search text or status."""
    roles, total = await role_service.list_roles(
        page=page,
        limit=limit,
        search=search,
        status=resolve_filter(status, Status),
    )
    return ApiResponse(
        code=CODE_LISTED,
        message=MSG_LISTED,
        data=build_list_data(RoleRead, roles, page=page, limit=limit, total=total),
    )


@router.get("/{role_id}", response_model=ApiResponse[RoleRead], summary="Get a role")
async def get_role(
    role_id: uuid.UUID,
    _: None = Depends(require_permission(PermissionName.ROLES_READ)),
) -> ApiResponse[RoleRead]:
    """Fetch a single role by id, including its permissions."""
    role = await role_service.get_role(role_id)
    return ApiResponse(code=CODE_FETCHED, message=MSG_FETCHED, data=role)


@router.patch("/{role_id}", response_model=ApiResponse[RoleRead], summary="Partially update a role")
async def update_role(
    role_id: uuid.UUID,
    data: RoleUpdate,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.ROLES_WRITE)),
) -> ApiResponse[RoleRead]:
    """Partially update a role's name, description, status, or permissions."""
    role = await role_service.update_role(role_id=role_id, data=data, actor_id=admin.id)
    return ApiResponse(code=CODE_UPDATED, message=MSG_UPDATED, data=role)


@router.delete("/{role_id}", response_model=ApiResponse[None], summary="Delete a role")
async def delete_role(
    role_id: uuid.UUID,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.ROLES_WRITE)),
) -> ApiResponse[None]:
    """Soft-delete a role by id (marks it inactive)."""
    await role_service.delete_role(role_id, actor_id=admin.id)
    return ApiResponse(code=CODE_DELETED, message=MSG_DELETED, data=None)
