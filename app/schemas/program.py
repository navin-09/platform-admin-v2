"""Program API DTOs — references a department (background reference)."""

import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.department import DepartmentRead


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_name: str
    degree_type: str | None
    department: DepartmentRead | None
