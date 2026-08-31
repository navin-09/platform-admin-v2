"""Export request/response schemas (uniform flow: create → poll → download)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models.enums import (
    AuditActionFilter,
    AuditActorTypeFilter,
    AuditResourceTypeFilter,
    StatusFilter,
)
from app.utils.limits import (
    ACTOR_FILTER_MAX_LENGTH,
    EXPORT_REASON_MAX_LENGTH,
    SEARCH_MAX_LENGTH,
)

CODE_CREATED = "S_201_EXPORT_CREATE_OK"
MSG_CREATED = "Export created successfully"
CODE_FETCHED = "S_200_EXPORT_FETCH_OK"
MSG_FETCHED = "Export fetched successfully"
CODE_DOWNLOADED = "S_200_EXPORT_DOWNLOAD_OK"
MSG_DOWNLOADED = "Export downloaded successfully"


class AuditExportFilters(BaseModel):
    """Mirror of the audit-logs list endpoint filters; retained for the export.

    ``extra="forbid"``: a filters payload must match exactly one module's shape.
    Silently ignoring unknown fields would drop filters (e.g. a users payload
    parsed as audit filters) — invariant ③: no guessing, no silent degradation.
    """

    model_config = ConfigDict(extra="forbid")

    actor: str | None = Field(default=None, max_length=ACTOR_FILTER_MAX_LENGTH)
    action: AuditActionFilter = AuditActionFilter.ALL
    resource_type: AuditResourceTypeFilter = AuditResourceTypeFilter.ALL
    actor_type: AuditActorTypeFilter = AuditActorTypeFilter.ALL


class UsersExportFilters(BaseModel):
    """Mirror of the users list endpoint filters; retained for the export."""

    model_config = ConfigDict(extra="forbid")

    search: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    status: StatusFilter = StatusFilter.ALL


class ExportCreate(BaseModel):
    module: Literal["audit", "users"]
    # BRD §6.6: Export Reason is mandatory. StringConstraints strips whitespace
    # BEFORE the length check, so "   " fails min_length (Field-level
    # str_strip_whitespace is silently ignored by pydantic 2.13).
    reason: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=EXPORT_REASON_MAX_LENGTH),
    ]
    format: Literal["xlsx"] = "xlsx"
    # Omitted filters = export everything for the module; the service resolves
    # the per-module default and rejects a shape that doesn't match ``module``.
    filters: AuditExportFilters | UsersExportFilters | None = None


class ExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module: str
    reason: str
    classification: str
    status: str
    row_count: int | None
    expires_at: datetime | None
    created_at: datetime
