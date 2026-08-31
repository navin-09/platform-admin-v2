"""Export request/response schemas (uniform flow: create → poll → download)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    """Mirror of the audit-logs list endpoint filters; retained for the export."""

    actor: str | None = Field(default=None, max_length=ACTOR_FILTER_MAX_LENGTH)
    action: AuditActionFilter = AuditActionFilter.ALL
    resource_type: AuditResourceTypeFilter = AuditResourceTypeFilter.ALL
    actor_type: AuditActorTypeFilter = AuditActorTypeFilter.ALL


class UsersExportFilters(BaseModel):
    """Mirror of the users list endpoint filters; retained for the export."""

    search: str | None = Field(default=None, max_length=SEARCH_MAX_LENGTH)
    status: StatusFilter = StatusFilter.ALL


class ExportCreate(BaseModel):
    module: Literal["audit", "users"]
    reason: str = Field(min_length=1, max_length=EXPORT_REASON_MAX_LENGTH)
    format: Literal["xlsx"] = "xlsx"
    filters: AuditExportFilters | UsersExportFilters = Field(default_factory=AuditExportFilters)


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
