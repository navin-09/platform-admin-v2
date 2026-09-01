"""Platform Admin → Role assignment table — which Roles an admin holds."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.utils.time import utcnow


class PlatformAdminRole(SQLModel, table=True):
    __tablename__ = "platform_admin_roles"

    platform_admin_id: uuid.UUID = Field(foreign_key="platform_admins.id", primary_key=True)
    role_id: uuid.UUID = Field(foreign_key="roles.id", primary_key=True)
    created_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="platform_admins.id")
    created_at: datetime = Field(default_factory=utcnow)
