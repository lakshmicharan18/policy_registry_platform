from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.dataset_column import DatasetColumnRead


class DatasetDefinitionCreate(BaseModel):
    """Payload for registering a dataset definition."""

    dataset_code: str = Field(max_length=100)
    name: str = Field(max_length=255)
    description: str | None = None

    @field_validator("dataset_code", "name")
    @classmethod
    def validate_non_empty_string(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class DatasetDefinitionRead(BaseModel):
    """Dataset definition data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_code: str
    name: str
    description: str | None
    created_at: datetime


class DatasetDefinitionDetail(DatasetDefinitionRead):
    """Dataset definition data including its registered columns."""

    columns: list[DatasetColumnRead]
