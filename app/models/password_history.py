"""Previous hashed passwords, kept to reject password reuse."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils.limits import PASSWORD_HASH_LENGTH
from app.utils.time import utcnow


class PasswordHistory(SQLModel, table=True):
    __tablename__ = "password_history"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    platform_admin_id: uuid.UUID = Field(foreign_key="platform_admins.id", index=True)
    hashed_password: str = Field(max_length=PASSWORD_HASH_LENGTH)
    # Not populated: this row is appended internally on password change, never
    # through an actor-bearing CRUD endpoint.
    created_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    created_at: datetime = Field(default_factory=utcnow)
