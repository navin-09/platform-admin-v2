import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Status
from app.schemas.fields import PermissionStr
from app.utils.limits import DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH

CODE_CREATED = "S_201_ROL_CREATED"
MSG_CREATED = "Role created successfully"
CODE_LISTED = "S_200_ROL_LIST_OK"
MSG_LISTED = "Roles fetched successfully"
CODE_FETCHED = "S_200_ROL_FETCH_OK"
MSG_FETCHED = "Role fetched successfully"
CODE_UPDATED = "S_200_ROL_UPDATED"
MSG_UPDATED = "Role updated successfully"
CODE_DELETED = "S_200_ROL_DELETED"
MSG_DELETED = "Role deleted successfully"


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH, examples=["support-agent"])
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: Status = Status.ACTIVE
    permissions: list[PermissionStr] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Partial update (PATCH) — only provided fields are applied."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    status: Status | None = None
    permissions: list[PermissionStr] | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: Status
    permissions: list[str]
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
