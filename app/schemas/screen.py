import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Status
from app.schemas.fields import ScreenCodeStr
from app.utils.limits import NAME_MAX_LENGTH, SORT_ORDER_MAX

CODE_CREATED = "S_201_SCR_CREATED"
MSG_CREATED = "Screen created successfully"
CODE_LISTED = "S_200_SCR_LIST_OK"
MSG_LISTED = "Screens fetched successfully"
CODE_FETCHED = "S_200_SCR_FETCH_OK"
MSG_FETCHED = "Screen fetched successfully"
CODE_UPDATED = "S_200_SCR_UPDATED"
MSG_UPDATED = "Screen updated successfully"
CODE_DELETED = "S_200_SCR_DELETED"
MSG_DELETED = "Screen deleted successfully"


class ScreenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH, examples=["Reports"])
    code: ScreenCodeStr | None = Field(
        default=None, description="Optional; auto-generated as the next S{n} when omitted."
    )
    sort_order: int = Field(default=0, ge=0, le=SORT_ORDER_MAX)
    status: Status = Status.ACTIVE


class ScreenUpdate(BaseModel):
    """Partial update (PATCH) — the code is immutable and cannot be changed."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    sort_order: int | None = Field(default=None, ge=0, le=SORT_ORDER_MAX)
    status: Status | None = None


class ScreenRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    sort_order: int
    status: Status
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
