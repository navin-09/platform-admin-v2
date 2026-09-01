"""Country table — top-level lookup with no foreign keys."""

import uuid
from datetime import datetime

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import COUNTRY_CODE_MAX_LENGTH, COUNTRY_NAME_MAX_LENGTH
from app.utils.time import utcnow


class Country(SQLModel, table=True):
    __tablename__ = "countries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    country_name: str = Field(max_length=COUNTRY_NAME_MAX_LENGTH)
    country_code: str = Field(max_length=COUNTRY_CODE_MAX_LENGTH, unique=True, index=True)
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
