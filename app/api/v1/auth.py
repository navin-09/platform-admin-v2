"""Auth routes: login and token refresh."""

from fastapi import APIRouter, Request

from app.api.audit import record_audit
from app.exceptions.errors import ApiError
from app.models.enums import AuditAction, AuditResourceType
from app.schemas.auth import (
    CODE_LOGIN_OK,
    CODE_REFRESH_OK,
    MSG_LOGIN_OK,
    MSG_REFRESH_OK,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login", response_model=ApiResponse[TokenResponse], summary="Log in and obtain tokens"
)
async def login(
    credentials: LoginRequest,
    request: Request,
) -> ApiResponse[TokenResponse]:
    """Authenticate a platform admin and return access and refresh tokens."""
    try:
        token = await auth_service.login(credentials)
    except ApiError:
        await _audit_login(request=request, credentials=credentials, success=False)
        raise
    await _audit_login(request=request, credentials=credentials, success=True)
    return ApiResponse(code=CODE_LOGIN_OK, message=MSG_LOGIN_OK, data=token)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="Exchange a refresh token for new tokens",
)
async def refresh(payload: RefreshRequest) -> ApiResponse[TokenResponse]:
    """Exchange a valid refresh token for a new access and refresh token pair."""
    token = await auth_service.refresh(payload)
    return ApiResponse(code=CODE_REFRESH_OK, message=MSG_REFRESH_OK, data=token)


async def _audit_login(request: Request, credentials: LoginRequest, success: bool) -> None:
    await record_audit(
        request=request,
        actor=credentials.email,
        action=AuditAction.LOGIN_SUCCESS if success else AuditAction.LOGIN_FAILURE,
        resource_type=AuditResourceType.AUTH,
        resource_id=credentials.email,
    )
