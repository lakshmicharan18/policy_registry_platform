from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import WarehouseDataset
from app.models.warehouse_dataset_mapping import WarehouseDatasetMapping
from app.schemas.warehouse_dataset_mapping import (
    WarehouseDatasetMappingCreate,
    WarehouseDatasetMappingRead,
)

router = APIRouter(prefix="/warehouse-dataset-mappings", tags=["warehouse dataset mappings"])


@router.post("", response_model=WarehouseDatasetMappingRead, status_code=status.HTTP_201_CREATED)
def create_warehouse_dataset_mapping(
    mapping_in: WarehouseDatasetMappingCreate,
    db: Annotated[Session, Depends(get_db)],
) -> WarehouseDatasetMapping:
    """Store a source dataset name with warehouse details copied from PostgreSQL."""
    association = db.get(WarehouseDataset, mapping_in.warehouse_dataset_id)
    if association is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse dataset association not found.")
    warehouse = db.get(Warehouse, association.warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found.")
    mapping = WarehouseDatasetMapping(
        warehouse_dataset_id=association.id,
        warehouse_id=warehouse.id,
        dataset_id=association.dataset_id,
        warehouse_code=warehouse.warehouse_code,
        warehouse_name=warehouse.name,
        customer_dataset_name=mapping_in.customer_dataset_name,
    )
    db.add(mapping)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A mapping already exists for this warehouse dataset association.") from error
    db.refresh(mapping)
    return mapping
