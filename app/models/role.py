"""Role table — a named set of Permissions assigned to a Platform Admin."""

import uuid
from datetime import datetime

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH
from app.utils.time import utcnow


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=NAME_MAX_LENGTH, unique=True, index=True)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    created_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
