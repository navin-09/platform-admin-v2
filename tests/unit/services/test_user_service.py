"""Platform Admin (Users API) service unit tests — faked collaborators."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.exceptions.exceptions import EmailExistsError, LastAdminError, UserNotFoundError
from app.models.enums import AuditAction, AuditResourceType, Status
from app.schemas.user import UserCreate, UserReplace, UserUpdate
from app.services import user_service
from tests.unit.fakes import FakeRbacRepository, FakeUserRepository, active_admin


@pytest.fixture()
def fakes(monkeypatch) -> FakeUserRepository:
    repo = FakeUserRepository(user=active_admin())
    audit = AsyncMock()
    monkeypatch.setattr(user_service, "user_repository", repo)
    monkeypatch.setattr(user_service, "rbac_repository", FakeRbacRepository())
    monkeypatch.setattr(user_service, "hash_password", lambda _plain: "hashed")
    monkeypatch.setattr(user_service.audit_service, "record", audit)
    repo.audit = audit
    return repo


def _user(email: str = "alice@example.com"):
    return active_admin(email=email, username="Alice")


# --------------------------------------------------------------------------- #
# create_user
# --------------------------------------------------------------------------- #


async def test_create_user_success(fakes) -> None:
    created = await user_service.create_user(
        UserCreate(name="Alice", email="alice@example.com", password="S3cureP@ss")
    )

    assert created.email == "alice@example.com"
    assert created.username == "Alice"
    assert created.hashed_password == "hashed"
    assert fakes.created == [created]
    fakes.audit.assert_awaited_once_with(
        action=AuditAction.USER_CREATE,
        resource_type=AuditResourceType.USER,
        resource_id=str(created.id),
        details={"email": "alice@example.com", "name": "Alice"},
    )


async def test_create_user_success_assigns_super_admin(fakes, monkeypatch) -> None:
    rbac = FakeRbacRepository()
    monkeypatch.setattr(user_service, "rbac_repository", rbac)

    created = await user_service.create_user(
        UserCreate(name="Alice", email="alice@example.com", password="S3cureP@ss")
    )

    assert rbac.assigned == [created.id]


async def test_create_user_failure_duplicate_email(fakes) -> None:
    fakes.email_owner = _user()

    with pytest.raises(EmailExistsError):
        await user_service.create_user(
            UserCreate(name="Alice", email="alice@example.com", password="S3cureP@ss")
        )


# --------------------------------------------------------------------------- #
# get_user / list_users
# --------------------------------------------------------------------------- #


async def test_get_user_success(fakes) -> None:
    result = await user_service.get_user(fakes.user.id)
    assert result is fakes.user


async def test_get_user_failure_not_found(fakes) -> None:
    fakes.user = None

    with pytest.raises(UserNotFoundError):
        await user_service.get_user(uuid.uuid4())


async def test_list_users_success_empty(fakes) -> None:
    users, total = await user_service.list_users(page=1, limit=20)
    assert users == []
    assert total == 0


async def test_list_users_with_date_filters(fakes) -> None:
    from datetime import date

    from_date = date(2026, 8, 1)
    to_date = date(2026, 8, 31)

    users, total = await user_service.list_users(
        page=1, limit=20, from_date=from_date, to_date=to_date
    )

    assert users == []
    assert total == 0
    assert fakes.list_calls == [
        {
            "page": 1,
            "limit": 20,
            "search": None,
            "status": None,
            "from_date": from_date,
            "to_date": to_date,
        }
    ]


# --------------------------------------------------------------------------- #
# update_user
# --------------------------------------------------------------------------- #


async def test_update_user_success_applies_fields(fakes) -> None:
    result = await user_service.update_user(user_id=fakes.user.id, data=UserUpdate(name="Bob"))

    assert result.username == "Bob"
    fakes.audit.assert_awaited_once_with(
        action=AuditAction.USER_UPDATE,
        resource_type=AuditResourceType.USER,
        resource_id=str(fakes.user.id),
        details={"name": "Bob"},
    )


async def test_update_user_success_email_change(fakes) -> None:
    result = await user_service.update_user(
        user_id=fakes.user.id, data=UserUpdate(email="new@example.com")
    )
    assert result is fakes.user
    assert result.email == "new@example.com"


async def test_update_user_failure_email_taken(fakes) -> None:
    fakes.email_owner = _user(email="other@example.com")

    with pytest.raises(EmailExistsError):
        await user_service.update_user(
            user_id=fakes.user.id, data=UserUpdate(email="other@example.com")
        )


async def test_update_user_failure_deactivate_last_active(fakes) -> None:
    fakes.active_count = 0

    with pytest.raises(LastAdminError):
        await user_service.update_user(
            user_id=fakes.user.id, data=UserUpdate(status=Status.INACTIVE)
        )


async def test_update_user_success_deactivate_clears_session(fakes) -> None:
    await user_service.update_user(user_id=fakes.user.id, data=UserUpdate(status=Status.INACTIVE))

    updated, data = fakes.updated[-1]
    assert updated is fakes.user
    assert data["status"] is Status.INACTIVE
    assert data["current_refresh_jti"] is None


# --------------------------------------------------------------------------- #
# replace_user
# --------------------------------------------------------------------------- #


async def test_replace_user_success(fakes) -> None:
    result = await user_service.replace_user(
        user_id=fakes.user.id,
        data=UserReplace(name="Alice", email="alice@example.com", password="S3cureP@ss"),
    )

    assert result is fakes.user
    assert result.username == "Alice"
    assert result.hashed_password == "hashed"
    fakes.audit.assert_awaited_once_with(
        action=AuditAction.USER_REPLACE,
        resource_type=AuditResourceType.USER,
        resource_id=str(fakes.user.id),
        details={"email": "alice@example.com", "name": "Alice"},
    )


async def test_replace_user_success_clears_lockout(fakes) -> None:
    fakes.user.failed_login_attempts = 4
    fakes.user.locked_until = None

    await user_service.replace_user(
        user_id=fakes.user.id,
        data=UserReplace(name="Alice", email="alice@example.com", password="S3cureP@ss"),
    )

    updated, data = fakes.updated[-1]
    assert data["username"] == "Alice"
    assert data["failed_login_attempts"] == 0
    assert data["locked_until"] is None


# --------------------------------------------------------------------------- #
# delete_user
# --------------------------------------------------------------------------- #


async def test_delete_user_success(fakes) -> None:
    await user_service.delete_user(fakes.user.id)

    assert fakes.deleted == [fakes.user]
    fakes.audit.assert_awaited_once_with(
        action=AuditAction.USER_DELETE,
        resource_type=AuditResourceType.USER,
        resource_id=str(fakes.user.id),
    )


async def test_delete_user_failure_last_active(fakes) -> None:
    fakes.active_count = 0

    with pytest.raises(LastAdminError):
        await user_service.delete_user(fakes.user.id)
