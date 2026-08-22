"""Request-scoped session holder (no engine; safe to import anywhere)."""

from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession

current_session: ContextVar[AsyncSession | None] = ContextVar("db_session", default=None)


def get_session() -> AsyncSession:
    """Return the request-scoped session (set by the ``get_db`` dependency)."""
    session = current_session.get()
    if session is None:
        raise RuntimeError("No request-scoped database session; is get_db registered?")
    return session
