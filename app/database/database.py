"""Async engine, session factory, and the ``get_db`` request dependency."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.tracing import configure_tracing
from app.database.session import current_session

# SQLAlchemy must be instrumented before the first engine is created.
configure_tracing()

# ``pool_pre_ping`` makes the engine verify a pooled connection is still alive
# before handing it out, so connections closed by Postgres (idle timeouts, server
# restarts, network resets) don't surface as "connection was closed in the middle
# of operation" errors on the next request.
engine = create_async_engine(settings.database_url, pool_pre_ping=True)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def db_session() -> AsyncGenerator[None, None]:
    """Standalone session context usable from requests AND background tasks.

    Background generation has no HTTP request, so it cannot rely on ``get_db``;
    it enters this context instead. Repositories are untouched: they keep reading
    the ambient session via ``get_session()``.
    """
    async with async_session_factory() as session:
        token = current_session.set(session)
        try:
            yield
        finally:
            current_session.reset(token)


async def get_db() -> AsyncGenerator[None, None]:
    """Establish the request-scoped session, then close it after the request."""
    async with db_session():
        yield
