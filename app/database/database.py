"""Async engine, session factory, and the ``get_db`` request dependency."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.tracing import configure_tracing
from app.database.session import current_session

# SQLAlchemy must be instrumented before the first engine is created.
configure_tracing()

engine = create_async_engine(settings.database_url)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[None]:
    """Establish the request-scoped session, then close it after the request."""
    async with async_session_factory() as session:
        token = current_session.set(session)
        try:
            yield
        finally:
            current_session.reset(token)
