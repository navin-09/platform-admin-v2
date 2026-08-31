"""Health service unit tests — repository faked (see tests/unit/fakes.py)."""

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions.exceptions import AppError
from app.services import health_service
from tests.unit.fakes import FakeHealthRepository


async def test_check_success_when_database_is_up() -> None:
    health_service.health_repository = FakeHealthRepository()

    await health_service.check()


async def test_check_failure_when_database_is_down() -> None:
    health_service.health_repository = FakeHealthRepository(error=SQLAlchemyError("db down"))

    with pytest.raises(AppError):
        await health_service.check()


async def test_check_failure_on_driver_connection_error() -> None:
    # asyncpg surfaces connection failures as OSError (e.g. ConnectionRefusedError).
    health_service.health_repository = FakeHealthRepository(error=ConnectionRefusedError("refused"))

    with pytest.raises(AppError):
        await health_service.check()
