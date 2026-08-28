"""RBAC service tests (repositories mocked)."""

import uuid
from unittest.mock import AsyncMock, patch

from app.services import rbac_service


async def test_permissions_for_admin_expands_write_to_read() -> None:
    admin_id = uuid.uuid4()
    with patch.object(
        rbac_service.rbac_repository,
        "screen_permissions_for_admin",
        new=AsyncMock(return_value={("S1", True, True), ("S2", True, False)}),
    ):
        result = await rbac_service.permissions_for_admin(admin_id)
    assert result == {"S1.R", "S1.W", "S2.R"}
