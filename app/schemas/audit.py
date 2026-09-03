import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

CODE_LISTED = "S_200_AUDIT_LIST_OK"
MSG_LISTED = "Audit logs fetched successfully"


class AuditLogFilter(BaseModel):
    """Audit-log list filters, resolved: None means no filter (never the All sentinel)."""

    actor: str | None = None
    action: str | None = None
    resource_type: str | None = None
    actor_type: str | None = None
    from_date: date | None = None
    to_date: date | None = None


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor: str | None
    actor_type: str | None
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict[str, Any] | None
    url: str | None
    payload: dict[str, Any] | None
    response: dict[str, Any] | None
    request_id: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
