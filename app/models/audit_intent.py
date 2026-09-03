"""Durable Pending Audit Intent: the outbox row written before evidence is forged."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.utils.time import utcnow


class AuditIntent(SQLModel, table=True):
    __tablename__ = "audit_intents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Redacted event fields; the forwarder materializes them into an Audit Entry.
    payload: dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(index=True, default_factory=utcnow)
