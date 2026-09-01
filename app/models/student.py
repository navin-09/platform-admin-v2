"""Student table — the hub: five foreign keys including a self-referencing mentor."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import (
    FIRST_NAME_MAX_LENGTH,
    GPA_DECIMAL_PLACES,
    GPA_MAX,
    GPA_MAX_DIGITS,
    LAST_NAME_MAX_LENGTH,
    STUDENT_EMAIL_MAX_LENGTH,
)
from app.utils.time import utcnow


class Student(SQLModel, table=True):
    __tablename__ = "students"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    first_name: str = Field(max_length=FIRST_NAME_MAX_LENGTH)
    last_name: str = Field(max_length=LAST_NAME_MAX_LENGTH)
    email: str = Field(max_length=STUDENT_EMAIL_MAX_LENGTH, unique=True, index=True)
    enrollment_date: date
    gpa: Decimal | None = Field(
        default=None,
        max_digits=GPA_MAX_DIGITS,
        decimal_places=GPA_DECIMAL_PLACES,
        ge=0,
        le=GPA_MAX,
    )
    address_id: uuid.UUID | None = Field(default=None, foreign_key="addresses.id")
    department_id: uuid.UUID | None = Field(default=None, foreign_key="departments.id")
    advisor_id: uuid.UUID | None = Field(default=None, foreign_key="advisors.id")
    program_id: uuid.UUID | None = Field(default=None, foreign_key="programs.id")
    mentor_id: uuid.UUID | None = Field(default=None, foreign_key="students.id")
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
