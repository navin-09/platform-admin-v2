"""Enrollment API DTOs — the student/course junction (background reference)."""

import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.course import CourseRead


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    semester: str
    grade: str | None
    course: CourseRead | None
