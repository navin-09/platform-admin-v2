import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_permission
from app.core.constants import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE,
    MIN_PAGE_SIZE,
)
from app.models.enums import (
    PermissionName,
    Status,
    StatusFilter,
    resolve_filter,
)
from app.schemas.common import ApiResponse, ListData, build_list_data
from app.schemas.user import (
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
    UserCreate,
    UserRead,
    UserReplace,
    UserUpdate,
)
from app.services import user_service
from app.utils.limits import SEARCH_MAX_LENGTH

router = APIRouter(tags=["Users"])


@router.post("", response_model=ApiResponse[UserRead], status_code=201, summary="Create a user")
async def create_user(
    data: UserCreate,
    _: None = Depends(require_permission(PermissionName.USERS_WRITE)),
) -> ApiResponse[UserRead]:
    """Create a new user with a name, email, and password."""
    user = await user_service.create_user(data)
    return ApiResponse(code=CODE_CREATED, message=MSG_CREATED, data=user)


@router.get("", response_model=ApiResponse[ListData[UserRead]], summary="List users")
async def list_users(
    page: int = Query(DEFAULT_PAGE, ge=MIN_PAGE),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE),
    search: str | None = Query(
        None, max_length=SEARCH_MAX_LENGTH, description="Search by name or email"
    ),
    status: StatusFilter = Query(StatusFilter.ALL, description="Filter by user status"),
    from_date: date | None = Query(
        None, description="Filter users created on or after this date (YYYY-MM-DD)"
    ),
    to_date: date | None = Query(
        None, description="Filter users created on or before this date (YYYY-MM-DD)"
    ),
    _: None = Depends(require_permission(PermissionName.USERS_READ)),
) -> ApiResponse[ListData[UserRead]]:
    """List users, paginated and optionally filtered by search text, status, or date range."""
    users, total = await user_service.list_users(
        page=page,
        limit=limit,
        search=search,
        status=resolve_filter(status, Status),
        from_date=from_date,
        to_date=to_date,
    )
    return ApiResponse(
        code=CODE_LISTED,
        message=MSG_LISTED,
        data=build_list_data(UserRead, users, page=page, limit=limit, total=total),
    )


@router.get("/{user_id}", response_model=ApiResponse[UserRead], summary="Get a user")
async def get_user(
    user_id: uuid.UUID,
    _: None = Depends(require_permission(PermissionName.USERS_READ)),
) -> ApiResponse[UserRead]:
    """Fetch a single user by id."""
    user = await user_service.get_user(user_id)
    return ApiResponse(code=CODE_FETCHED, message=MSG_FETCHED, data=user)


@router.put("/{user_id}", response_model=ApiResponse[UserRead], summary="Fully replace a user")
async def replace_user(
    user_id: uuid.UUID,
    data: UserReplace,
    _: None = Depends(require_permission(PermissionName.USERS_WRITE)),
) -> ApiResponse[UserRead]:
    """Replace a user's name, email, and password; status is left unchanged."""
    user = await user_service.replace_user(user_id=user_id, data=data)
    return ApiResponse(code=CODE_UPDATED, message=MSG_UPDATED, data=user)


@router.patch("/{user_id}", response_model=ApiResponse[UserRead], summary="Partially update a user")
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    _: None = Depends(require_permission(PermissionName.USERS_WRITE)),
) -> ApiResponse[UserRead]:
    """Partially update a user's name, email, or status."""
    user = await user_service.update_user(user_id=user_id, data=data)
    return ApiResponse(code=CODE_UPDATED, message=MSG_UPDATED, data=user)


@router.delete("/{user_id}", response_model=ApiResponse[None], summary="Delete a user")
async def delete_user(
    user_id: uuid.UUID,
    _: None = Depends(require_permission(PermissionName.USERS_WRITE)),
) -> ApiResponse[None]:
    """Delete a user by id."""
    await user_service.delete_user(user_id)
    return ApiResponse(code=CODE_DELETED, message=MSG_DELETED, data=None)
