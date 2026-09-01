"""Aggregate router that mounts every v1 route (prefix set at include time)."""

from fastapi import APIRouter

from app.api.v1 import (
    audit_logs,
    auth,
    departments,
    exports,
    health,
    roles,
    screens,
    students,
    teachers,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router, prefix="/users")
api_router.include_router(roles.router, prefix="/roles")
api_router.include_router(screens.router, prefix="/screens")
api_router.include_router(audit_logs.router)
api_router.include_router(exports.router)
api_router.include_router(departments.router, prefix="/departments")
api_router.include_router(teachers.router, prefix="/teachers")
api_router.include_router(students.router, prefix="/students")
