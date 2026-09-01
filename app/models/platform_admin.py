import uuid
from datetime import datetime

from sqlalchemy import Column, func
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.models.enums import Status, enum_values
from app.utils.limits import (
    DISPLAY_NAME_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    JTI_MAX_LENGTH,
    PASSWORD_HASH_LENGTH,
)
from app.utils.time import utcnow


class PlatformAdmin(SQLModel, table=True):
    __tablename__ = "platform_admins"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=EMAIL_MAX_LENGTH, unique=True, index=True)
    username: str = Field(max_length=DISPLAY_NAME_MAX_LENGTH, unique=True, index=True)
    hashed_password: str = Field(max_length=PASSWORD_HASH_LENGTH)
    status: Status = Field(
        default=Status.ACTIVE,
        sa_column=Column(
            SAEnum(Status, name="status", values_callable=enum_values),
            nullable=False,
        ),
    )
    failed_login_attempts: int = Field(default=0)
    locked_until: datetime | None = Field(default=None)
    current_refresh_jti: str | None = Field(default=None, max_length=JTI_MAX_LENGTH)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": func.now()})
