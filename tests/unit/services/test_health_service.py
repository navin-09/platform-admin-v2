"""Health service tests (repository mocked)."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.errors import ApiError
from app.services import health_service


async def test_check_passes_when_database_is_up() -> None:
    with patch.object(health_service.health_repository, "ping", new=AsyncMock()):
        await health_service.check()


async def test_check_raises_when_database_is_down() -> None:
    with patch.object(
        health_service.health_repository,
        "ping",
        new=AsyncMock(side_effect=SQLAlchemyError("db down")),
    ):
        with pytest.raises(ApiError):
            await health_service.check()


async def test_check_raises_on_driver_connection_error() -> None:
    # asyncpg surfaces connection failures as OSError (e.g. ConnectionRefusedError).
    with patch.object(
        health_service.health_repository,
        "ping",
        new=AsyncMock(side_effect=ConnectionRefusedError("refused")),
    ):
        with pytest.raises(ApiError):
            await health_service.check()
