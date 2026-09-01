"""Student API DTOs — the hub: many FKs, a self-reference, and an enrollments collection."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Status
from app.schemas.address import AddressRead
from app.schemas.department import DepartmentRead
from app.schemas.enrollment import EnrollmentRead
from app.schemas.program import ProgramRead
from app.schemas.teacher import TeacherRead
from app.utils.limits import (
    FIRST_NAME_MAX_LENGTH,
    GPA_DECIMAL_PLACES,
    GPA_MAX,
    GPA_MAX_DIGITS,
    LAST_NAME_MAX_LENGTH,
    STUDENT_EMAIL_MAX_LENGTH,
)


class StudentCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=FIRST_NAME_MAX_LENGTH)
    last_name: str = Field(min_length=1, max_length=LAST_NAME_MAX_LENGTH)
    email: str = Field(min_length=1, max_length=STUDENT_EMAIL_MAX_LENGTH)
    enrollment_date: date
    gpa: Decimal | None = Field(
        default=None,
        max_digits=GPA_MAX_DIGITS,
        decimal_places=GPA_DECIMAL_PLACES,
        ge=0,
        le=GPA_MAX,
    )
    address_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    program_id: uuid.UUID | None = None
    mentor_id: uuid.UUID | None = None
    status: Status = Status.ACTIVE


class StudentUpdate(BaseModel):
    """Partial update (PATCH) — only provided fields are applied."""

    first_name: str | None = Field(default=None, min_length=1, max_length=FIRST_NAME_MAX_LENGTH)
    last_name: str | None = Field(default=None, min_length=1, max_length=LAST_NAME_MAX_LENGTH)
    email: str | None = Field(default=None, min_length=1, max_length=STUDENT_EMAIL_MAX_LENGTH)
    enrollment_date: date | None = None
    gpa: Decimal | None = Field(
        default=None,
        max_digits=GPA_MAX_DIGITS,
        decimal_places=GPA_DECIMAL_PLACES,
        ge=0,
        le=GPA_MAX,
    )
    address_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    teacher_id: uuid.UUID | None = None
    program_id: uuid.UUID | None = None
    mentor_id: uuid.UUID | None = None
    status: Status | None = None


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    enrollment_date: date
    gpa: Decimal | None
    department: DepartmentRead | None
    teacher: TeacherRead | None
    program: ProgramRead | None
    address: AddressRead | None
    mentor: "StudentRead | None"
    enrollments: list[EnrollmentRead]
    status: Status
    created_at: datetime
    updated_at: datetime


StudentRead.model_rebuild()
