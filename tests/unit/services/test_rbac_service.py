"""RBAC service unit tests — repository faked (see tests/unit/fakes.py).

Covers both public methods (permissions_for_admin, roles_for_admin) and the
pure _expand helper's edge cases.
"""

import uuid

from app.services import rbac_service
from tests.unit.fakes import FakeRbacRepository


async def test_permissions_for_admin_success_expands_write_to_read() -> None:
    repo = FakeRbacRepository(screen_perms={("S1", True, True), ("S2", True, False)})
    rbac_service.rbac_repository = repo

    result = await rbac_service.permissions_for_admin(uuid.uuid4())

    assert result == {"S1.R", "S1.W", "S2.R"}


async def test_permissions_for_admin_success_empty_rows() -> None:
    rbac_service.rbac_repository = FakeRbacRepository(screen_perms=set())

    result = await rbac_service.permissions_for_admin(uuid.uuid4())

    assert result == set()


async def test_roles_for_admin_success() -> None:
    repo = FakeRbacRepository(role_names={"super_admin"})
    rbac_service.rbac_repository = repo

    result = await rbac_service.roles_for_admin(uuid.uuid4())

    assert result == {"super_admin"}


async def test_roles_for_admin_success_empty() -> None:
    rbac_service.rbac_repository = FakeRbacRepository(role_names=set())

    result = await rbac_service.roles_for_admin(uuid.uuid4())

    assert result == set()


def test_expand_skips_rows_without_read_or_write() -> None:
    assert rbac_service._expand({("S9", False, False)}) == set()


def test_expand_write_only_grants_both() -> None:
    assert rbac_service._expand({("S1", False, True)}) == {"S1.R", "S1.W"}
