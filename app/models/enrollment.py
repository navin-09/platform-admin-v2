"""Enrollment table — many-to-many junction between students and courses."""

import uuid
from datetime import datetime

from sqlalchemy import Column, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import GRADE_MAX_LENGTH, SEMESTER_MAX_LENGTH
from app.utils.time import utcnow


class Enrollment(SQLModel, table=True):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "semester", name="uq_enrollment"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    student_id: uuid.UUID = Field(foreign_key="students.id")
    course_id: uuid.UUID = Field(foreign_key="courses.id")
    semester: str = Field(max_length=SEMESTER_MAX_LENGTH)
    grade: str | None = Field(default=None, max_length=GRADE_MAX_LENGTH)
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
