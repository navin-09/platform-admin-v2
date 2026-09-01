"""Screen CRUD routes."""

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
from app.schemas.screen import (
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
    ScreenCreate,
    ScreenRead,
    ScreenUpdate,
)
from app.services import screen_service
from app.utils.limits import SEARCH_MAX_LENGTH

router = APIRouter(tags=["Screens"])


@router.post("", response_model=ApiResponse[ScreenRead], status_code=201, summary="Create a screen")
async def create_screen(
    data: ScreenCreate,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.SCREENS_WRITE)),
) -> ApiResponse[ScreenRead]:
    """Create a new screen; the code is auto-generated when omitted."""
    screen = await screen_service.create_screen(data, actor_id=admin.id)
    return ApiResponse(code=CODE_CREATED, message=MSG_CREATED, data=screen)


@router.get("", response_model=ApiResponse[ListData[ScreenRead]], summary="List screens")
async def list_screens(
    page: int = Query(DEFAULT_PAGE, ge=MIN_PAGE),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    search: str | None = Query(
        None, max_length=SEARCH_MAX_LENGTH, description="Search by name or code"
    ),
    status: StatusFilter = Query(StatusFilter.ALL, description="Filter by status"),
    _: None = Depends(require_permission(PermissionName.SCREENS_READ)),
) -> ApiResponse[ListData[ScreenRead]]:
    """List screens, paginated and optionally filtered by search text or status."""
    screens, total = await screen_service.list_screens(
        page=page,
        limit=limit,
        search=search,
        status=resolve_filter(status, Status),
    )
    return ApiResponse(
        code=CODE_LISTED,
        message=MSG_LISTED,
        data=build_list_data(ScreenRead, screens, page=page, limit=limit, total=total),
    )


@router.get("/{screen_id}", response_model=ApiResponse[ScreenRead], summary="Get a screen")
async def get_screen(
    screen_id: uuid.UUID,
    _: None = Depends(require_permission(PermissionName.SCREENS_READ)),
) -> ApiResponse[ScreenRead]:
    """Fetch a single screen by id."""
    screen = await screen_service.get_screen(screen_id)
    return ApiResponse(code=CODE_FETCHED, message=MSG_FETCHED, data=screen)


@router.patch(
    "/{screen_id}", response_model=ApiResponse[ScreenRead], summary="Partially update a screen"
)
async def update_screen(
    screen_id: uuid.UUID,
    data: ScreenUpdate,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.SCREENS_WRITE)),
) -> ApiResponse[ScreenRead]:
    """Partially update a screen's name, sort order, or status; the code is immutable."""
    screen = await screen_service.update_screen(screen_id=screen_id, data=data, actor_id=admin.id)
    return ApiResponse(code=CODE_UPDATED, message=MSG_UPDATED, data=screen)


@router.delete("/{screen_id}", response_model=ApiResponse[None], summary="Delete a screen")
async def delete_screen(
    screen_id: uuid.UUID,
    admin: PlatformAdmin = Depends(get_current_admin),
    _: None = Depends(require_permission(PermissionName.SCREENS_WRITE)),
) -> ApiResponse[None]:
    """Soft-delete a screen by id (marks it inactive)."""
    await screen_service.delete_screen(screen_id, actor_id=admin.id)
    return ApiResponse(code=CODE_DELETED, message=MSG_DELETED, data=None)
