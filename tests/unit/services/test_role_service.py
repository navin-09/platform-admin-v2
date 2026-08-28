"""Role service tests (repositories mocked)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.exceptions import AppError
from app.models.enums import AuditAction, AuditResourceType, Status
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from app.services import role_service


def _role(name: str = "support-agent") -> Role:
    return Role(id=uuid.uuid4(), name=name, description=None, status=Status.ACTIVE)


def test_normalize_permissions_write_implies_read() -> None:
    assert role_service._normalize_permissions(["S1.R", "S1.W", "S2.W"]) == {
        "S1": (True, True),
        "S2": (True, True),
    }


def test_normalize_permissions_read_only() -> None:
    assert role_service._normalize_permissions(["S1.R"]) == {"S1": (True, False)}


def test_normalize_permissions_deduplicates() -> None:
    assert role_service._normalize_permissions(["S1.R", "S1.R"]) == {"S1": (True, False)}


def test_expand_permissions_orders_by_sort_order_then_numeric_code() -> None:
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


async def test_create_role() -> None:
    record = AsyncMock()
    with (
        patch.object(
            role_service.role_repository, "get_role_by_name", new=AsyncMock(return_value=None)
        ),
        patch.object(
            role_service.role_repository,
            "create_role",
            new=AsyncMock(side_effect=lambda role, permissions: role),
        ),
        patch.object(
            role_service.role_repository,
            "permissions_for_role",
            new=AsyncMock(return_value=[]),
        ),
        patch.object(role_service.audit_service, "record", new=record),
    ):
        created = await role_service.create_role(RoleCreate(name="support-agent"))
    assert created.name == "support-agent"
    assert created.permissions == []
    record.assert_awaited_once_with(
        action=AuditAction.ROLE_CREATE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(created.id),
        details={"name": "support-agent", "permissions": []},
    )


async def test_create_role_normalizes_permissions() -> None:
    captured: dict[str, list] = {}

    async def _create(role, permissions):
        captured["permissions"] = permissions
        return role

    with (
        patch.object(
            role_service.role_repository, "get_role_by_name", new=AsyncMock(return_value=None)
        ),
        patch.object(
            role_service.screen_repository,
            "active_screen_codes",
            new=AsyncMock(return_value={"S1", "S2"}),
        ),
        patch.object(role_service.role_repository, "create_role", new=_create),
        patch.object(
            role_service.role_repository,
            "permissions_for_role",
            new=AsyncMock(return_value=[]),
        ),
        patch.object(role_service.audit_service, "record", new=AsyncMock()),
    ):
        await role_service.create_role(
            RoleCreate(name="support-agent", permissions=["S1.R", "S1.W", "S2.W"])
        )
    assert {(r.screen_code, r.read, r.write) for r in captured["permissions"]} == {
        ("S1", True, True),
        ("S2", True, True),
    }


async def test_create_role_rejects_unknown_screen() -> None:
    with (
        patch.object(
            role_service.role_repository, "get_role_by_name", new=AsyncMock(return_value=None)
        ),
        patch.object(
            role_service.screen_repository,
            "active_screen_codes",
            new=AsyncMock(return_value={"S1"}),
        ),
    ):
        with pytest.raises(AppError):
            await role_service.create_role(RoleCreate(name="support-agent", permissions=["S9.R"]))


async def test_create_role_duplicate_name() -> None:
    with patch.object(
        role_service.role_repository, "get_role_by_name", new=AsyncMock(return_value=_role())
    ):
        with pytest.raises(AppError):
            await role_service.create_role(RoleCreate(name="support-agent"))


async def test_get_role_not_found() -> None:
    with patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=None)):
        with pytest.raises(AppError):
            await role_service.get_role(uuid.uuid4())


async def test_get_role_found() -> None:
    role = _role()
    with (
        patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)),
        patch.object(
            role_service.role_repository,
            "permissions_for_role",
            new=AsyncMock(return_value=[]),
        ),
    ):
        result = await role_service.get_role(role.id)
    assert result.id == role.id
    assert result.permissions == []


async def test_list_roles() -> None:
    with (
        patch.object(
            role_service.role_repository, "list_roles", new=AsyncMock(return_value=([], 0))
        ),
        patch.object(
            role_service.role_repository, "permissions_for_roles", new=AsyncMock(return_value={})
        ),
    ):
        roles, total = await role_service.list_roles(page=1, limit=20)
    assert roles == []
    assert total == 0


async def test_update_role() -> None:
    role = _role()
    record = AsyncMock()

    async def _apply(role, data, permissions=None):
        for key, value in data.items():
            setattr(role, key, value)
        return role

    with (
        patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)),
        patch.object(
            role_service.role_repository, "get_role_by_name", new=AsyncMock(return_value=None)
        ),
        patch.object(role_service.role_repository, "update_role", new=_apply),
        patch.object(
            role_service.role_repository,
            "permissions_for_role",
            new=AsyncMock(return_value=[]),
        ),
        patch.object(role_service.audit_service, "record", new=record),
    ):
        result = await role_service.update_role(
            role_id=role.id, data=RoleUpdate(description="desc")
        )
    assert result.description == "desc"
    assert result.permissions == []
    record.assert_awaited_once_with(
        action=AuditAction.ROLE_UPDATE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(role.id),
        details={"description": "desc"},
    )


async def test_update_role_replaces_permissions() -> None:
    role = _role()
    captured: dict[str, list] = {}

    async def _update(role, data, permissions=None):
        captured["permissions"] = permissions
        return role

    with (
        patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)),
        patch.object(
            role_service.screen_repository,
            "active_screen_codes",
            new=AsyncMock(return_value={"S1", "S2"}),
        ),
        patch.object(role_service.role_repository, "update_role", new=_update),
        patch.object(
            role_service.role_repository,
            "permissions_for_role",
            new=AsyncMock(return_value=[("S1", 1, True, True), ("S2", 2, True, False)]),
        ),
        patch.object(role_service.audit_service, "record", new=AsyncMock()),
    ):
        result = await role_service.update_role(
            role_id=role.id, data=RoleUpdate(permissions=["S2.R", "S1.W"])
        )
    assert {(r.screen_code, r.read, r.write) for r in captured["permissions"]} == {
        ("S1", True, True),
        ("S2", True, False),
    }
    assert result.permissions == ["S1.R", "S1.W", "S2.R"]


async def test_update_role_rejects_unknown_screen() -> None:
    role = _role()
    with (
        patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)),
        patch.object(
            role_service.screen_repository,
            "active_screen_codes",
            new=AsyncMock(return_value={"S1"}),
        ),
    ):
        with pytest.raises(AppError):
            await role_service.update_role(role_id=role.id, data=RoleUpdate(permissions=["S9.R"]))


async def test_update_super_admin_name_protected() -> None:
    role = _role(name="super_admin")
    with patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)):
        with pytest.raises(AppError):
            await role_service.update_role(role_id=role.id, data=RoleUpdate(name="renamed"))


async def test_update_super_admin_deactivate_protected() -> None:
    role = _role(name="super_admin")
    with patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)):
        with pytest.raises(AppError):
            await role_service.update_role(role_id=role.id, data=RoleUpdate(status=Status.INACTIVE))


async def test_update_super_admin_permissions_protected() -> None:
    role = _role(name="super_admin")
    with patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)):
        with pytest.raises(AppError):
            await role_service.update_role(role_id=role.id, data=RoleUpdate(permissions=["S1.R"]))


async def test_delete_role() -> None:
    role = _role()
    record = AsyncMock()
    with (
        patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)),
        patch.object(role_service.role_repository, "delete_role", new=AsyncMock(return_value=None)),
        patch.object(role_service.audit_service, "record", new=record),
    ):
        await role_service.delete_role(role.id)
    record.assert_awaited_once_with(
        action=AuditAction.ROLE_DELETE,
        resource_type=AuditResourceType.ROLE,
        resource_id=str(role.id),
    )


async def test_delete_super_admin_protected() -> None:
    role = _role(name="super_admin")
    with patch.object(role_service.role_repository, "get_role", new=AsyncMock(return_value=role)):
        with pytest.raises(AppError):
            await role_service.delete_role(role.id)
