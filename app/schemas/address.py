"""Address API DTOs — references a country (background reference)."""

import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.country import CountryRead


class AddressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    street_address: str
    city: str
    state_province: str | None
    postal_code: str | None
    country: CountryRead | None
