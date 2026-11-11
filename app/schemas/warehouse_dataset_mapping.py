from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WarehouseDatasetMappingCreate(BaseModel):
    warehouse_dataset_id: UUID
    customer_dataset_name: str = Field(min_length=1, max_length=255)


class WarehouseDatasetMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_dataset_id: UUID
    warehouse_id: UUID
    dataset_id: UUID
    warehouse_code: str
    warehouse_name: str
    customer_dataset_name: str
