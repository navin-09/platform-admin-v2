"""Teacher table — a department reference."""

import uuid
from datetime import datetime

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import OFFICE_ROOM_MAX_LENGTH, TEACHER_NAME_MAX_LENGTH
from app.utils.time import utcnow


class Teacher(SQLModel, table=True):
    __tablename__ = "teachers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    teacher_name: str = Field(max_length=TEACHER_NAME_MAX_LENGTH)
    office_room: str | None = Field(default=None, max_length=OFFICE_ROOM_MAX_LENGTH)
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
