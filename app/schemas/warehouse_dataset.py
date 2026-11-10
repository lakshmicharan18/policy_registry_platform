from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.warehouse_dataset import DatasetRequirementType


class WarehouseDatasetCreate(BaseModel):
    """Payload for associating a dataset definition with a warehouse."""

    dataset_id: UUID
    requirement_type: DatasetRequirementType
    condition_config: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_condition_config(self) -> "WarehouseDatasetCreate":
        if self.requirement_type is DatasetRequirementType.CONDITIONAL:
            if not self.condition_config:
                raise ValueError(
                    "condition_config must be a non-empty object for conditional requirements"
                )
        elif self.condition_config is not None:
            raise ValueError(
                "condition_config must be null for mandatory or optional requirements"
            )
        return self


class WarehouseDatasetRead(BaseModel):
    """Warehouse-dataset association data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_id: UUID
    dataset_id: UUID
    requirement_type: DatasetRequirementType
    condition_config: dict[str, Any] | None
