"""Export records: one row per export request, with status and 24h-link metadata."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import ExportStatus
from app.utils.limits import (
    EXPORT_CLASSIFICATION_MAX_LENGTH,
    EXPORT_FILENAME_MAX_LENGTH,
    EXPORT_FORMAT_MAX_LENGTH,
    EXPORT_MODULE_MAX_LENGTH,
    EXPORT_REASON_MAX_LENGTH,
)
from app.utils.time import utcnow


class Export(SQLModel, table=True):
    __tablename__ = "exports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    module: str = Field(index=True, max_length=EXPORT_MODULE_MAX_LENGTH)
    reason: str | None = Field(default=None, max_length=EXPORT_REASON_MAX_LENGTH)
    file_format: str = Field(default="xlsx", max_length=EXPORT_FORMAT_MAX_LENGTH)
    classification: str = Field(max_length=EXPORT_CLASSIFICATION_MAX_LENGTH)
    # The exact filters applied at creation, retained for metadata sheet and audit evidence.
    filters: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    status: str = Field(index=True, default=ExportStatus.PENDING.value)
    row_count: int | None = Field(default=None)
    file_path: str | None = Field(default=None, max_length=EXPORT_FILENAME_MAX_LENGTH)
    generation_error: str | None = Field(default=None, max_length=EXPORT_REASON_MAX_LENGTH)
    # The 24h single-user download window starts when the file is ready.
    expires_at: datetime | None = Field(default=None, index=True)
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="platform_admins.id", index=True
    )
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    created_at: datetime = Field(index=True, default_factory=utcnow)
