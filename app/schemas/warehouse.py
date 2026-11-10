from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WarehouseCreate(BaseModel):
    """Payload for registering a warehouse."""

    warehouse_code: str = Field(max_length=50)
    name: str = Field(max_length=255)

    @field_validator("warehouse_code", "name")
    @classmethod
    def validate_non_empty_string(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class WarehouseRead(BaseModel):
    """Warehouse data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_code: str
    name: str
    created_at: datetime
