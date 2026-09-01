"""Country API DTOs — a leaf lookup table (background reference)."""

import uuid

from pydantic import BaseModel, ConfigDict


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    country_name: str
    country_code: str
