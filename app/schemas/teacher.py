"""Teacher API DTOs — a department reference, resolved as a nested object."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Status
from app.schemas.department import DepartmentRead
from app.utils.limits import OFFICE_ROOM_MAX_LENGTH, TEACHER_NAME_MAX_LENGTH


class TeacherCreate(BaseModel):
    teacher_name: str = Field(min_length=1, max_length=TEACHER_NAME_MAX_LENGTH)
    office_room: str | None = Field(default=None, max_length=OFFICE_ROOM_MAX_LENGTH)
    department_id: uuid.UUID | None = None
    status: Status = Status.ACTIVE


class TeacherUpdate(BaseModel):
    """Partial update (PATCH) — only provided fields are applied."""

    teacher_name: str | None = Field(default=None, min_length=1, max_length=TEACHER_NAME_MAX_LENGTH)
    office_room: str | None = Field(default=None, max_length=OFFICE_ROOM_MAX_LENGTH)
    department_id: uuid.UUID | None = None
    status: Status | None = None


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    teacher_name: str
    office_room: str | None
    department_id: uuid.UUID | None
    department: DepartmentRead | None
    status: Status
    created_at: datetime
    updated_at: datetime
