"""Export request/response schemas (uniform flow: create → poll → download)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

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
    """Audit-logs list filters retained for the export (extra=forbid: no silent drops)."""

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
    # Reason is optional; StringConstraints strips whitespace BEFORE the length check.
    reason: (
        Annotated[
            str,
            StringConstraints(strip_whitespace=True, max_length=EXPORT_REASON_MAX_LENGTH),
        ]
        | None
    ) = None
    format: Literal["csv", "xlsx"] = "xlsx"
    # Omitted filters = export everything for the module; the service resolves
    # the per-module default and rejects a shape that doesn't match ``module``.
    filters: AuditExportFilters | UsersExportFilters | None = None

    @field_validator("reason")
    @classmethod
    def _blank_reason_is_none(cls, value: str | None) -> str | None:
        """A blank or whitespace-only reason (after stripping) means "none given"."""
        return value or None


class ExportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module: str
    reason: str | None
    format: str = Field(validation_alias="file_format")
    classification: str
    status: str
    row_count: int | None
    expires_at: datetime | None
    created_at: datetime
