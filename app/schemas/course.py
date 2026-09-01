"""Course API DTOs — references a department (background reference)."""

import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.department import DepartmentRead


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_name: str
    credits: int
    department: DepartmentRead | None
