import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, settings
from app.core.logging import configure_logging
from app.core.tracing import instrument_app
from app.database.database import get_db
from app.exceptions.exception_handlers import register_exception_handlers
from app.middleware.logging import AccessLogMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.services import audit_service

configure_logging()


async def _audit_forwarder() -> None:
    """Promote Pending Audit Intents into chained Audit Entries until shutdown."""
    while True:
        try:
            await audit_service.promote_intents()
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.getLogger("app.forwarder").exception("audit forwarder pass failed")
        await asyncio.sleep(1.0)


def create_app(app_settings: Settings = settings) -> FastAPI:
    """Build and configure the FastAPI application."""

    # ``get_db`` runs for every route, so a request-scoped session is available to
    # the repository layer before any endpoint or dependency executes.
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        forwarder = asyncio.create_task(_audit_forwarder())
        try:
            yield
        finally:
            forwarder.cancel()
            try:
                await forwarder
            except asyncio.CancelledError:
                pass

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        dependencies=[Depends(get_db)],
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    # Starlette runs the *last* added middleware first (outermost). Add the access
    # log first so RequestContextMiddleware runs before it and sets request_id.
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=app_settings.api_v1_prefix)

    instrument_app(app)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        # Bind all interfaces so colleagues on the LAN can reach it.
        host="0.0.0.0",  # noqa: S104  # nosec B104
        port=8000,
        reload=True,
        reload_dirs=["app"],
        app_dir=".",
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
