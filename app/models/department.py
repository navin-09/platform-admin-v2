"""Department table — top-level academic entity with no foreign keys."""

import uuid
from datetime import datetime

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import BUILDING_MAX_LENGTH, DEPARTMENT_NAME_MAX_LENGTH
from app.utils.time import utcnow


class Department(SQLModel, table=True):
    __tablename__ = "departments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    department_name: str = Field(max_length=DEPARTMENT_NAME_MAX_LENGTH)
    building: str | None = Field(default=None, max_length=BUILDING_MAX_LENGTH)
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
