from fastapi import Depends, FastAPI

from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.users import router as users_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.tracing import instrument_app
from app.database.database import get_db
from app.exceptions.handlers import register_exception_handlers
from app.middleware.logging import AccessLogMiddleware
from app.middleware.request_context import RequestContextMiddleware

configure_logging()

# ``get_db`` runs for every route, so a request-scoped session is available to
# the repository layer before any endpoint or dependency executes.
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    dependencies=[Depends(get_db)],
)

register_exception_handlers(app)

# Starlette runs the *last* added middleware first (outermost). Add the access
# log first so RequestContextMiddleware runs before it and sets request_id.
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestContextMiddleware)

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1/users")
app.include_router(audit_logs_router, prefix="/api/v1")

instrument_app(app)


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", reload=True, app_dir=".", log_config=None, access_log=False)


if __name__ == "__main__":
    main()
