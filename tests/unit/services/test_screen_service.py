"""Screen service unit tests — faked collaborators (see tests/unit/fakes.py)."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.exceptions.exceptions import (
    ProtectedResourceError,
    ScreenCodeExistsError,
    ScreenNotFoundError,
)
from app.models.enums import AuditAction, AuditResourceType, Status
from app.models.role import Role
from app.models.screen import Screen
from app.schemas.screen import ScreenCreate, ScreenUpdate
from app.services import screen_service
from tests.unit.fakes import FakeRoleRepository, FakeScreenRepository


@pytest.fixture()
def fakes(monkeypatch) -> FakeScreenRepository:
    repo = FakeScreenRepository(
        screen=_screen(),
        screen_by_code=None,
        next_code="S5",
    )
    audit = AsyncMock()
    monkeypatch.setattr(screen_service, "screen_repository", repo)
    monkeypatch.setattr(
        screen_service, "role_repository", FakeRoleRepository(role_by_name=_super_admin())
    )
    monkeypatch.setattr(screen_service.audit_service, "record", audit)
    repo.audit = audit
    return repo


def _screen(code: str = "S5", name: str = "Reports") -> Screen:
    return Screen(id=uuid.uuid4(), code=code, name=name, sort_order=0, status=Status.ACTIVE)


def _super_admin() -> Role:
    return Role(id=uuid.uuid4(), name="super_admin", status=Status.ACTIVE)


# --------------------------------------------------------------------------- #
# create_screen
# --------------------------------------------------------------------------- #


async def test_create_screen_success_auto_generates_code(fakes) -> None:
    created = await screen_service.create_screen(ScreenCreate(name="Reports"))

    assert created.code == "S5"
    fakes.audit.assert_awaited_once()
    event = fakes.audit.await_args.args[0]
    assert event.action == AuditAction.SCREEN_CREATE
    assert event.resource_type == AuditResourceType.SCREEN
    assert event.resource_id == "S5"
    assert event.details == {"code": "S5", "name": "Reports"}


async def test_create_screen_success_grants_super_admin(fakes) -> None:
    await screen_service.create_screen(ScreenCreate(name="Reports", code="S5"))

    assert len(fakes.created) == 1
    assert fakes.created_kwargs["super_admin_role_id"] is not None


async def test_create_screen_failure_duplicate_code(fakes) -> None:
    fakes.screen_by_code = _screen()

    with pytest.raises(ScreenCodeExistsError):
        await screen_service.create_screen(ScreenCreate(name="Reports", code="S5"))


# --------------------------------------------------------------------------- #
# get_screen / list_screens
# --------------------------------------------------------------------------- #


async def test_get_screen_success(fakes) -> None:
    result = await screen_service.get_screen(fakes.screen.id)
    assert result is fakes.screen


async def test_get_screen_failure_not_found(fakes) -> None:
    fakes.screen = None

    with pytest.raises(ScreenNotFoundError):
        await screen_service.get_screen(uuid.uuid4())


async def test_list_screens_success_empty(fakes) -> None:
    screens, total = await screen_service.list_screens(page=1, limit=20)
    assert screens == []
    assert total == 0


# --------------------------------------------------------------------------- #
# update_screen
# --------------------------------------------------------------------------- #


async def test_update_screen_success(fakes) -> None:
    result = await screen_service.update_screen(
        screen_id=fakes.screen.id, data=ScreenUpdate(name="New")
    )

    assert result.name == "New"
    fakes.audit.assert_awaited_once()
    event = fakes.audit.await_args.args[0]
    assert event.action == AuditAction.SCREEN_UPDATE
    assert event.resource_type == AuditResourceType.SCREEN
    assert event.resource_id == "S5"
    assert event.details == {"name": "New"}


async def test_update_screen_failure_not_found(fakes) -> None:
    fakes.screen = None

    with pytest.raises(ScreenNotFoundError):
        await screen_service.update_screen(screen_id=uuid.uuid4(), data=ScreenUpdate(name="New"))


async def test_update_protected_screen_failure_deactivate(fakes) -> None:
    fakes.screen = _screen(code="S1")

    with pytest.raises(ProtectedResourceError):
        await screen_service.update_screen(
            screen_id=fakes.screen.id, data=ScreenUpdate(status=Status.INACTIVE)
        )


# --------------------------------------------------------------------------- #
# delete_screen
# --------------------------------------------------------------------------- #


async def test_delete_screen_success(fakes) -> None:
    await screen_service.delete_screen(fakes.screen.id)

    assert fakes.deleted == [fakes.screen]
    fakes.audit.assert_awaited_once()
    event = fakes.audit.await_args.args[0]
    assert event.action == AuditAction.SCREEN_DELETE
    assert event.resource_type == AuditResourceType.SCREEN
    assert event.resource_id == "S5"


async def test_delete_screen_failure_not_found(fakes) -> None:
    fakes.screen = None

    with pytest.raises(ScreenNotFoundError):
        await screen_service.delete_screen(uuid.uuid4())


async def test_delete_protected_screen_failure(fakes) -> None:
    fakes.screen = _screen(code="S4")

    with pytest.raises(ProtectedResourceError):
        await screen_service.delete_screen(fakes.screen.id)
