"""Password-reset OTP issuance state (expiry window + request throttle)."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils.limits import EMAIL_MAX_LENGTH
from app.utils.time import utcnow


class PasswordResetOtp(SQLModel, table=True):
    __tablename__ = "password_reset_otps"

    email: str = Field(primary_key=True, max_length=EMAIL_MAX_LENGTH)
    expires_at: datetime
    request_count: int = Field(default=0)
    window_started_at: datetime = Field(default_factory=utcnow)
    verified: bool = Field(default=False)
    # Not populated: this row is unauthenticated system state (forgot-password
    # flow), not written through an actor-bearing CRUD endpoint.
    created_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
