"""Address table — a simple one-table reference to a country."""

import uuid
from datetime import datetime

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import (
    CITY_MAX_LENGTH,
    POSTAL_CODE_MAX_LENGTH,
    STATE_PROVINCE_MAX_LENGTH,
    STREET_ADDRESS_MAX_LENGTH,
)
from app.utils.time import utcnow


class Address(SQLModel, table=True):
    __tablename__ = "addresses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    street_address: str = Field(max_length=STREET_ADDRESS_MAX_LENGTH)
    city: str = Field(max_length=CITY_MAX_LENGTH)
    state_province: str | None = Field(default=None, max_length=STATE_PROVINCE_MAX_LENGTH)
    postal_code: str | None = Field(default=None, max_length=POSTAL_CODE_MAX_LENGTH)
    country_id: uuid.UUID = Field(foreign_key="countries.id")
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
