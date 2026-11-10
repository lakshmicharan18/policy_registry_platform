from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.dataset_column import DatasetDataType


class DatasetColumnCreate(BaseModel):
    """Payload for registering a column in a dataset definition."""

    column_name: str = Field(max_length=100)
    data_type: DatasetDataType
    is_required: bool = True

    @field_validator("column_name")
    @classmethod
    def validate_column_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class DatasetColumnRead(BaseModel):
    """Dataset column data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    column_name: str
    data_type: DatasetDataType
    is_required: bool
