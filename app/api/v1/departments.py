"""Department routes: generic engine CRUD + custom endpoints."""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Query

from app.api.master_data_routes import build_router
from app.core.master_data import DEPARTMENT_SPEC
from app.schemas.common import ApiResponse, ListData, build_list_data
from app.schemas.master_data import CODE_LISTED, MSG_LISTED
from app.schemas.student import StudentRead
from app.services import department_service

router: APIRouter = build_router(DEPARTMENT_SPEC)


@router.get("/{department_id}/students", response_model=ApiResponse[ListData[StudentRead]])
async def department_students(
    department_id: uuid.UUID,
    min_gpa: Decimal | None = Query(None, ge=0, le=4.0),
    limit: int = Query(20, ge=1, le=100),
) -> ApiResponse[ListData[StudentRead]]:
    """Students in a department, optionally above a GPA floor — fully nested."""
    students, total = await department_service.students_of(
        department_id=department_id,
        min_gpa=min_gpa,
        limit=limit,
    )
    return ApiResponse(
        code=CODE_LISTED,
        message=MSG_LISTED,
        data=build_list_data(StudentRead, students, page=1, limit=limit, total=total),
    )
