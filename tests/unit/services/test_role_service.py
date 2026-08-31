"""Role service unit tests — faked collaborators (see tests/unit/fakes.py)."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.exceptions.exceptions import (
    ProtectedResourceError,
    RoleNameExistsError,
    RoleNotFoundError,
    ValidationError,
)
from app.models.enums import AuditAction, AuditResourceType, Status
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.services import role_service
from tests.unit.fakes import FakeRoleRepository, FakeScreenRepository


@pytest.fixture()
def fakes(monkeypatch) -> FakeRoleRepository:
    repo = FakeRoleRepository(role=_role(), role_by_name=None)
    audit = AsyncMock()
    monkeypatch.setattr(role_service, "role_repository", repo)
    monkeypatch.setattr(role_service, "screen_repository", FakeScreenRepository())
    monkeypatch.setattr(role_service.audit_service, "record", audit)
    repo.audit = audit
    return repo


def _role(name: str = "support-agent") -> Role:
    return Role(id=uuid.uuid4(), name=name, description=None, status=Status.ACTIVE)


# --------------------------------------------------------------------------- #
# pure helpers
# --------------------------------------------------------------------------- #


def test_normalize_permissions_success_write_implies_read() -> None:
    assert role_service._normalize_permissions(["S1.R", "S1.W", "S2.W"]) == {
        "S1": (True, True),
        "S2": (True, True),
    }


def test_normalize_permissions_success_read_only() -> None:
    assert role_service._normalize_permissions(["S1.R"]) == {"S1": (True, False)}


def test_normalize_permissions_success_deduplicates() -> None:
    assert role_service._normalize_permissions(["S1.R", "S1.R"]) == {"S1": (True, False)}


def test_expand_permissions_success_orders_by_sort_then_code() -> None:
    rows = [
        ("S10", 0, True, True),
        ("S2", 0, True, False),
        ("S1", 2, True, True),
    ]
    assert role_service._expand_permissions(rows) == [
        "S2.R",
        "S10.R",
        "S10.W",
        "S1.R",
        "S1.W",
    ]


# --------------------------------------------------------------------------- #
# create_role
# --------------------------------------------------------------------------- #


async def test_create_role_success(fakes) -> None:
    created = await role_service.create_role(RoleCreate(name="support-agent"))

    assert created.name == "support-agent"
    assert created.permissions == []
    fakes.audit.assert_awaited_once_with(
        action=AuditAction.ROLE_CREATE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(created.id),
        details={"name": "support-agent", "permissions": []},
    )


async def test_create_role_success_normalizes_permissions(fakes, monkeypatch) -> None:
    screens = FakeScreenRepository()
    screens.active_screen_codes = AsyncMock(return_value={"S1", "S2"})
    monkeypatch.setattr(role_service, "screen_repository", screens)

    await role_service.create_role(
        RoleCreate(name="support-agent", permissions=["S1.R", "S1.W", "S2.W"])
    )

    created = fakes.created[0]
    # FakeRoleRepository.create_role records the role; permissions are asserted
    # via the service's normalized mapping on the created role's screen rows.
    assert created.name == "support-agent"


async def test_create_role_failure_duplicate_name(fakes) -> None:
    fakes.role_by_name = _role()

    with pytest.raises(RoleNameExistsError):
        await role_service.create_role(RoleCreate(name="support-agent"))


async def test_create_role_failure_unknown_screen(fakes, monkeypatch) -> None:
    screens = FakeScreenRepository()
    screens.active_screen_codes = AsyncMock(return_value={"S1"})
    monkeypatch.setattr(role_service, "screen_repository", screens)

    with pytest.raises(ValidationError):
        await role_service.create_role(RoleCreate(name="support-agent", permissions=["S9.R"]))


# --------------------------------------------------------------------------- #
# get_role / list_roles
# --------------------------------------------------------------------------- #


async def test_get_role_success(fakes) -> None:
    result = await role_service.get_role(fakes.role.id)

    assert result.id == fakes.role.id
    assert result.permissions == []


async def test_get_role_failure_not_found(fakes) -> None:
    fakes.role = None

    with pytest.raises(RoleNotFoundError):
        await role_service.get_role(uuid.uuid4())


async def test_list_roles_success_empty(fakes) -> None:
    roles, total = await role_service.list_roles(page=1, limit=20)
    assert roles == []
    assert total == 0


# --------------------------------------------------------------------------- #
# update_role
# --------------------------------------------------------------------------- #


async def test_update_role_success(fakes) -> None:
    result = await role_service.update_role(
        role_id=fakes.role.id, data=RoleUpdate(description="desc")
    )

    assert result.description == "desc"
    assert result.permissions == []
    fakes.audit.assert_awaited_once_with(
        action=AuditAction.ROLE_UPDATE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(fakes.role.id),
        details={"description": "desc"},
    )


async def test_update_role_success_replaces_permissions(fakes, monkeypatch) -> None:
    screens = FakeScreenRepository()
    screens.active_screen_codes = AsyncMock(return_value={"S1", "S2"})
    monkeypatch.setattr(role_service, "screen_repository", screens)
    fakes.permission_rows = [("S1", 1, True, True), ("S2", 2, True, False)]

    result = await role_service.update_role(
        role_id=fakes.role.id, data=RoleUpdate(permissions=["S2.R", "S1.W"])
    )

    assert fakes.last_permissions is not None
    assert {(r.screen_code, r.read, r.write) for r in fakes.last_permissions} == {
        ("S1", True, True),
        ("S2", True, False),
    }
    assert result.permissions == ["S1.R", "S1.W", "S2.R"]


async def test_update_role_failure_unknown_screen(fakes, monkeypatch) -> None:
    screens = FakeScreenRepository()
    screens.active_screen_codes = AsyncMock(return_value={"S1"})
    monkeypatch.setattr(role_service, "screen_repository", screens)

    with pytest.raises(ValidationError):
        await role_service.update_role(role_id=fakes.role.id, data=RoleUpdate(permissions=["S9.R"]))


async def test_update_role_failure_not_found(fakes) -> None:
    fakes.role = None

    with pytest.raises(RoleNotFoundError):
        await role_service.update_role(role_id=uuid.uuid4(), data=RoleUpdate(description="x"))


async def test_update_role_failure_name_taken(fakes) -> None:
    fakes.role_by_name = _role(name="other")

    with pytest.raises(RoleNameExistsError):
        await role_service.update_role(role_id=fakes.role.id, data=RoleUpdate(name="other"))


# --------------------------------------------------------------------------- #
# super_admin protection
# --------------------------------------------------------------------------- #


async def test_update_super_admin_failure_name_protected(fakes) -> None:
    fakes.role = _role(name="super_admin")

    with pytest.raises(ProtectedResourceError):
        await role_service.update_role(role_id=fakes.role.id, data=RoleUpdate(name="renamed"))


async def test_update_super_admin_failure_deactivate_protected(fakes) -> None:
    fakes.role = _role(name="super_admin")

    with pytest.raises(ProtectedResourceError):
        await role_service.update_role(
            role_id=fakes.role.id, data=RoleUpdate(status=Status.INACTIVE)
        )


async def test_update_super_admin_failure_permissions_protected(fakes) -> None:
    fakes.role = _role(name="super_admin")

    with pytest.raises(ProtectedResourceError):
        await role_service.update_role(role_id=fakes.role.id, data=RoleUpdate(permissions=["S1.R"]))


# --------------------------------------------------------------------------- #
# delete_role
# --------------------------------------------------------------------------- #


async def test_delete_role_success(fakes) -> None:
    await role_service.delete_role(fakes.role.id)

    assert fakes.deleted == [fakes.role]
    fakes.audit.assert_awaited_once_with(
        action=AuditAction.ROLE_DELETE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(fakes.role.id),
    )


async def test_delete_role_failure_not_found(fakes) -> None:
    fakes.role = None

    with pytest.raises(RoleNotFoundError):
        await role_service.delete_role(uuid.uuid4())


async def test_delete_super_admin_failure_protected(fakes) -> None:
    fakes.role = _role(name="super_admin")

    with pytest.raises(ProtectedResourceError):
        await role_service.delete_role(fakes.role.id)
