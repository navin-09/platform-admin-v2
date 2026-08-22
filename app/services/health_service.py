"""Service health business logic."""

import logging

from app.exceptions.errors import service_unavailable
from app.repositories import health_repository

logger = logging.getLogger("app.services.health")


async def check() -> None:
    """Verify the database is reachable; raise a typed error when it is not.

    ``ping`` does nothing but ``SELECT 1``, so any exception (driver connection
    errors raise ``OSError``, not just ``SQLAlchemyError``) means the database
    is unreachable.
    """
    try:
        await health_repository.ping()
    except Exception:
        logger.exception("database health check failed")
        raise service_unavailable() from None
