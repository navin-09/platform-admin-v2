"""Health repository tests (mocked session)."""

from unittest.mock import AsyncMock, MagicMock, patch

from app.repositories import health_repository


async def test_ping_executes_a_query() -> None:
    db = MagicMock()
    db.execute = AsyncMock()
    with patch.object(health_repository, "get_session", return_value=db):
        await health_repository.ping()
    db.execute.assert_awaited_once()
