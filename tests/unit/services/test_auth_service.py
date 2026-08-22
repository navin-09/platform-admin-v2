"""Auth service tests (repositories mocked)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from jose import JWTError

from app.exceptions.errors import ApiError
from app.models.enums import AdminStatus
from app.models.platform_admin import PlatformAdmin
from app.schemas.auth import LoginRequest, RefreshRequest
from app.services import auth_service


async def test_login_success() -> None:
    admin = PlatformAdmin(
        id=uuid.uuid4(),
        username="admin",
        email="admin@example.com",
        hashed_password="hash",
        status=AdminStatus.ACTIVE,
    )
    with (
        patch.object(
            auth_service.auth_repository,
            "get_admin_by_email",
            new=AsyncMock(return_value=admin),
        ),
        patch.object(auth_service, "verify_password", return_value=True),
        patch.object(auth_service, "create_access_token", return_value="access"),
        patch.object(auth_service, "create_refresh_token", return_value="refresh"),
    ):
        token = await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))
    assert token.access_token == "access"
    assert token.refresh_token == "refresh"


async def test_login_invalid_credentials() -> None:
    with patch.object(
        auth_service.auth_repository,
        "get_admin_by_email",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ApiError):
            await auth_service.login(LoginRequest(email="nope@example.com", password="pw"))


async def test_login_inactive_account() -> None:
    admin = PlatformAdmin(
        id=uuid.uuid4(),
        username="admin",
        email="admin@example.com",
        hashed_password="hash",
        status=AdminStatus.INACTIVE,
    )
    with (
        patch.object(
            auth_service.auth_repository,
            "get_admin_by_email",
            new=AsyncMock(return_value=admin),
        ),
        patch.object(auth_service, "verify_password", return_value=True),
    ):
        with pytest.raises(ApiError):
            await auth_service.login(LoginRequest(email="admin@example.com", password="pw"))


async def test_refresh_success() -> None:
    admin_id = uuid.uuid4()
    admin = PlatformAdmin(
        id=admin_id, username="admin", email="admin@example.com", hashed_password="hash"
    )
    with (
        patch.object(
            auth_service, "decode_token", return_value={"type": "refresh", "sub": str(admin_id)}
        ),
        patch.object(
            auth_service.auth_repository,
            "get_admin_by_id",
            new=AsyncMock(return_value=admin),
        ),
        patch.object(auth_service, "create_access_token", return_value="access"),
        patch.object(auth_service, "create_refresh_token", return_value="refresh"),
    ):
        token = await auth_service.refresh(RefreshRequest(refresh_token="r"))
    assert token.access_token == "access"
    assert token.refresh_token == "refresh"


async def test_refresh_rejects_malformed_subject() -> None:
    with patch.object(
        auth_service, "decode_token", return_value={"type": "refresh", "sub": "not-a-uuid"}
    ):
        with pytest.raises(ApiError):
            await auth_service.refresh(RefreshRequest(refresh_token="r"))


async def test_refresh_rejects_wrong_token_type() -> None:
    with patch.object(
        auth_service, "decode_token", return_value={"type": "access", "sub": str(uuid.uuid4())}
    ):
        with pytest.raises(ApiError):
            await auth_service.refresh(RefreshRequest(refresh_token="r"))


async def test_refresh_rejects_invalid_token() -> None:
    with patch.object(auth_service, "decode_token", side_effect=JWTError("bad token")):
        with pytest.raises(ApiError):
            await auth_service.refresh(RefreshRequest(refresh_token="r"))


async def test_refresh_rejects_unknown_admin() -> None:
    with (
        patch.object(
            auth_service,
            "decode_token",
            return_value={"type": "refresh", "sub": str(uuid.uuid4())},
        ),
        patch.object(
            auth_service.auth_repository,
            "get_admin_by_id",
            new=AsyncMock(return_value=None),
        ),
    ):
        with pytest.raises(ApiError):
            await auth_service.refresh(RefreshRequest(refresh_token="r"))


async def test_get_admin_by_id_returns_admin() -> None:
    admin = PlatformAdmin(
        id=uuid.uuid4(), username="admin", email="admin@example.com", hashed_password="hash"
    )
    with patch.object(
        auth_service.auth_repository,
        "get_admin_by_id",
        new=AsyncMock(return_value=admin),
    ):
        result = await auth_service.get_admin_by_id(admin.id)
    assert result is admin


async def test_get_admin_by_id_unknown_raises() -> None:
    with patch.object(
        auth_service.auth_repository,
        "get_admin_by_id",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(ApiError):
            await auth_service.get_admin_by_id(uuid.uuid4())
