"""Department-specific queries not covered by the generic engine."""

import uuid
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import ColumnElement, func, select
from sqlmodel import col

from app.core.master_data import STUDENT_SPEC, record_id
from app.database.session import get_session
from app.models.student import Student
from app.repositories import master_data_resolver
from app.services import master_data_service


async def students_of(
    department_id: uuid.UUID,
    *,
    min_gpa: Decimal | None = None,
    limit: int = 20,
) -> tuple[list[BaseModel], int]:
    """List a department's students (optionally above a GPA floor), fully nested."""
    db = get_session()
    filters: list[ColumnElement[bool]] = [col(Student.department_id) == department_id]
    if min_gpa is not None:
        filters.append(col(Student.gpa) >= min_gpa)
    total = await db.scalar(select(func.count()).select_from(Student).where(*filters))
    result = await db.execute(
        select(Student).where(*filters).order_by(col(Student.gpa).desc()).limit(limit)
    )
    rows = list(result.scalars().all())
    nodes = await master_data_resolver.resolve_graph(STUDENT_SPEC, [record_id(row) for row in rows])
    return [master_data_service.serialize(STUDENT_SPEC, row, nodes) for row in rows], total or 0
