"""RBAC repository tests (mocked session)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories import rbac_repository


async def test_screen_permissions_for_admin() -> None:
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.execute.return_value.all.return_value = [
        ("S1", True, False),
        ("S2", True, False),
    ]
    with patch.object(rbac_repository, "get_session", return_value=db):
        result = await rbac_repository.screen_permissions_for_admin(uuid.uuid4())
    assert result == {("S1", True, False), ("S2", True, False)}
