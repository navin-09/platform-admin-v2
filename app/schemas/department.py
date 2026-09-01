"""Department API DTOs — a leaf master-data table (no foreign keys)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Status
from app.utils.limits import BUILDING_MAX_LENGTH, DEPARTMENT_NAME_MAX_LENGTH


class DepartmentCreate(BaseModel):
    department_name: str = Field(min_length=1, max_length=DEPARTMENT_NAME_MAX_LENGTH)
    building: str | None = Field(default=None, max_length=BUILDING_MAX_LENGTH)
    status: Status = Status.ACTIVE


class DepartmentUpdate(BaseModel):
    """Partial update (PATCH) — only provided fields are applied."""

    department_name: str | None = Field(
        default=None, min_length=1, max_length=DEPARTMENT_NAME_MAX_LENGTH
    )
    building: str | None = Field(default=None, max_length=BUILDING_MAX_LENGTH)
    status: Status | None = None


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    department_name: str
    building: str | None
    status: Status
    created_at: datetime
    updated_at: datetime
