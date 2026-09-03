"""Immutable audit evidence: one hashed, hash-chained row per consequential action."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Column
from sqlmodel import Field, SQLModel

from app.utils.audit_chain import entry_digest
from app.utils.limits import (
    ACTION_MAX_LENGTH,
    ACTOR_TYPE_MAX_LENGTH,
    AUDIT_HASH_MAX_LENGTH,
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
    created_at: datetime = Field(index=True, default_factory=utcnow)
    # Tamper-evident chain: seq fixes append order; entry_hash seals the fields,
    # prev_hash links to the sealed predecessor (BRD immutable evidence, ASVS 7.3.3).
    seq: int | None = Field(default=None, sa_column=Column(BigInteger, index=True))
    prev_hash: str | None = Field(default=None, max_length=AUDIT_HASH_MAX_LENGTH)
    entry_hash: str | None = Field(default=None, max_length=AUDIT_HASH_MAX_LENGTH)

    def chain_fields(self) -> dict[str, Any]:
        """The evidence fields sealed by the hash chain (canonical-JSON input)."""
        return {
            "seq": self.seq,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "url": self.url,
            "payload": self.payload,
            "response": self.response,
            "request_id": self.request_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at,
        }

    def compute_entry_hash(self, prev_hash: str | None) -> str:
        """The entry hash sealing this row's fields onto the chain."""
        return entry_digest(prev_hash, self.chain_fields())
