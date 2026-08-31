"""Platform Admin (Users API) service tests (repositories mocked)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.exceptions import AppError, LastAdminError
from app.models.enums import AuditAction, AuditResourceType, Status
from app.models.platform_admin import PlatformAdmin
from app.schemas.user import UserCreate, UserReplace, UserUpdate
from app.services import user_service


def _user(email: str = "alice@example.com") -> PlatformAdmin:
    return PlatformAdmin(
        id=uuid.uuid4(),
        email=email,
        username="Alice",
        status=Status.ACTIVE,
        hashed_password="hash",
    )


async def test_create_user() -> None:
    record = AsyncMock()
    assign = AsyncMock()
    with (
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_service.user_repository,
            "create_user",
            new=AsyncMock(side_effect=lambda user: user),
        ),
        patch.object(user_service.rbac_repository, "assign_super_admin", new=assign),
        patch.object(user_service, "hash_password", return_value="hashed"),
        patch.object(user_service.audit_service, "record", new=record),
    ):
        created = await user_service.create_user(
            UserCreate(name="Alice", email="alice@example.com", password="S3cureP@ss")
        )
    assert created.email == "alice@example.com"
    assert created.username == "Alice"
    assert created.hashed_password == "hashed"
    assign.assert_awaited_once_with(created.id)
    record.assert_awaited_once_with(
        action=AuditAction.USER_CREATE,
        resource_type=AuditResourceType.USER,
        resource_id=str(created.id),
        details={"email": "alice@example.com", "name": "Alice"},
    )


async def test_create_user_duplicate_email() -> None:
    with patch.object(
        user_service.user_repository,
        "get_user_by_email",
        new=AsyncMock(return_value=_user()),
    ):
        with pytest.raises(AppError):
            await user_service.create_user(
                UserCreate(name="Alice", email="alice@example.com", password="S3cureP@ss")
            )


async def test_get_user_not_found() -> None:
    with patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=None)):
        with pytest.raises(AppError):
            await user_service.get_user(uuid.uuid4())


async def test_get_user_found() -> None:
    user = _user()
    with patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)):
        result = await user_service.get_user(user.id)
    assert result.id == user.id


async def test_list_users() -> None:
    with patch.object(
        user_service.user_repository, "list_users", new=AsyncMock(return_value=([], 0))
    ):
        users, total = await user_service.list_users(page=1, limit=20)
    assert users == []
    assert total == 0


async def test_list_users_with_date_filters() -> None:
    from datetime import date

    from_date = date(2026, 8, 1)
    to_date = date(2026, 8, 31)
    with patch.object(
        user_service.user_repository, "list_users", new=AsyncMock(return_value=([], 0))
    ) as mock_list:
        users, total = await user_service.list_users(
            page=1, limit=20, from_date=from_date, to_date=to_date
        )
    assert users == []
    assert total == 0
    mock_list.assert_awaited_once_with(
        page=1,
        limit=20,
        search=None,
        status=None,
        from_date=from_date,
        to_date=to_date,
    )


async def test_update_user_applies_fields() -> None:
    user = _user()
    record = AsyncMock()

    async def _apply(user, data):
        for key, value in data.items():
            setattr(user, key, value)
        return user

    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_service.user_repository, "update_user", new=AsyncMock(side_effect=_apply)
        ),
        patch.object(user_service.audit_service, "record", new=record),
    ):
        result = await user_service.update_user(user_id=user.id, data=UserUpdate(name="Bob"))
    assert result.username == "Bob"
    record.assert_awaited_once_with(
        action=AuditAction.USER_UPDATE,
        resource_type=AuditResourceType.USER,
        resource_id=str(user.id),
        details={"name": "Bob"},
    )


async def test_update_user_email_change() -> None:
    user = _user()
    record = AsyncMock()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            user_service.user_repository,
            "update_user",
            new=AsyncMock(side_effect=lambda user, data: user),
        ),
        patch.object(user_service.audit_service, "record", new=record),
    ):
        result = await user_service.update_user(
            user_id=user.id, data=UserUpdate(email="new@example.com")
        )
    assert result is user


async def test_update_user_deactivate_last_active_raises() -> None:
    user = _user()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "count_active_admins",
            new=AsyncMock(return_value=0),
        ),
    ):
        with pytest.raises(LastAdminError):
            await user_service.update_user(user_id=user.id, data=UserUpdate(status=Status.INACTIVE))


async def test_update_user_deactivate_clears_session() -> None:
    user = _user()
    captured = {}

    async def _apply(user, data):
        captured.update(data)
        return user

    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "count_active_admins",
            new=AsyncMock(return_value=1),
        ),
        patch.object(
            user_service.user_repository, "update_user", new=AsyncMock(side_effect=_apply)
        ),
        patch.object(user_service.audit_service, "record", new=AsyncMock()),
    ):
        await user_service.update_user(user_id=user.id, data=UserUpdate(status=Status.INACTIVE))
    assert captured["status"] is Status.INACTIVE
    assert captured["current_refresh_jti"] is None


async def test_replace_user() -> None:
    user = _user()
    record = AsyncMock()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(user_service, "hash_password", return_value="hashed"),
        patch.object(
            user_service.user_repository,
            "update_user",
            new=AsyncMock(side_effect=lambda user, data: user),
        ),
        patch.object(user_service.audit_service, "record", new=record),
    ):
        result = await user_service.replace_user(
            user_id=user.id,
            data=UserReplace(name="Alice", email="alice@example.com", password="S3cureP@ss"),
        )
    assert result is user
    record.assert_awaited_once_with(
        action=AuditAction.USER_REPLACE,
        resource_type=AuditResourceType.USER,
        resource_id=str(user.id),
        details={"email": "alice@example.com", "name": "Alice"},
    )


async def test_replace_user_clears_lockout() -> None:
    user = _user()
    captured = {}

    async def _apply(user, data):
        captured.update(data)
        return user

    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "get_user_by_email",
            new=AsyncMock(return_value=None),
        ),
        patch.object(user_service, "hash_password", return_value="hashed"),
        patch.object(
            user_service.user_repository, "update_user", new=AsyncMock(side_effect=_apply)
        ),
        patch.object(user_service.audit_service, "record", new=AsyncMock()),
    ):
        await user_service.replace_user(
            user_id=user.id,
            data=UserReplace(name="Alice", email="alice@example.com", password="S3cureP@ss"),
        )
    assert captured["username"] == "Alice"
    assert captured["failed_login_attempts"] == 0
    assert captured["locked_until"] is None


async def test_delete_user() -> None:
    user = _user()
    record = AsyncMock()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "count_active_admins",
            new=AsyncMock(return_value=1),
        ),
        patch.object(user_service.user_repository, "delete_user", new=AsyncMock(return_value=None)),
        patch.object(user_service.audit_service, "record", new=record),
    ):
        await user_service.delete_user(user.id)
    record.assert_awaited_once_with(
        action=AuditAction.USER_DELETE,
        resource_type=AuditResourceType.USER,
        resource_id=str(user.id),
    )


async def test_delete_user_last_active_raises() -> None:
    user = _user()
    with (
        patch.object(user_service.user_repository, "get_user", new=AsyncMock(return_value=user)),
        patch.object(
            user_service.user_repository,
            "count_active_admins",
            new=AsyncMock(return_value=0),
        ),
    ):
        with pytest.raises(LastAdminError):
            await user_service.delete_user(user.id)
