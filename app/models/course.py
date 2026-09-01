"""Course table — a department reference."""

import uuid
from datetime import datetime

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import COURSE_NAME_MAX_LENGTH, CREDITS_MAX, CREDITS_MIN
from app.utils.time import utcnow


class Course(SQLModel, table=True):
    __tablename__ = "courses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    course_name: str = Field(max_length=COURSE_NAME_MAX_LENGTH)
    credits: int = Field(ge=CREDITS_MIN, le=CREDITS_MAX)
    department_id: uuid.UUID | None = Field(default=None, foreign_key="departments.id")
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
