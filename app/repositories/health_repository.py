"""Database liveness probe (all SQL)."""

from sqlalchemy import text

from app.database.session import get_session


async def ping() -> None:
    """Run ``SELECT 1`` to confirm the database is reachable."""
    await get_session().execute(text("SELECT 1"))
