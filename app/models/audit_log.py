import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.utils.limits import (
    ACTION_MAX_LENGTH,
    ACTOR_TYPE_MAX_LENGTH,
    EMAIL_MAX_LENGTH,
    IP_ADDRESS_MAX_LENGTH,
    REQUEST_ID_MAX_LENGTH,
    RESOURCE_ID_MAX_LENGTH,
    RESOURCE_TYPE_MAX_LENGTH,
    URL_MAX_LENGTH,
    USER_AGENT_MAX_LENGTH,
)
from app.utils.time import utcnow


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # The actor is the admin's login email (ADR-0011) or a short system-actor name.
    actor: str | None = Field(default=None, max_length=EMAIL_MAX_LENGTH)
    actor_type: str | None = Field(default=None, max_length=ACTOR_TYPE_MAX_LENGTH)
    action: str = Field(index=True, max_length=ACTION_MAX_LENGTH)
    resource_type: str | None = Field(default=None, max_length=RESOURCE_TYPE_MAX_LENGTH)
    resource_id: str | None = Field(default=None, max_length=RESOURCE_ID_MAX_LENGTH)
    details: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    url: str | None = Field(default=None, max_length=URL_MAX_LENGTH)
    payload: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    response: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    request_id: str | None = Field(default=None, max_length=REQUEST_ID_MAX_LENGTH)
    ip_address: str | None = Field(default=None, max_length=IP_ADDRESS_MAX_LENGTH)
    user_agent: str | None = Field(default=None, max_length=USER_AGENT_MAX_LENGTH)
    # Not populated: ``actor`` above already records who performed the action.
    created_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    created_at: datetime = Field(index=True, default_factory=utcnow)
