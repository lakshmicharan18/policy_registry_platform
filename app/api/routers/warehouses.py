from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.dataset_definition import DatasetDefinition
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import WarehouseDataset
from app.schemas.warehouse_dataset import WarehouseDatasetCreate, WarehouseDatasetRead
from app.schemas.warehouse import WarehouseCreate, WarehouseRead


router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseRead])
def list_warehouses(db: Annotated[Session, Depends(get_db)]) -> list[Warehouse]:
    """List registered warehouses for onboarding selection."""
    return list(db.scalars(select(Warehouse).order_by(Warehouse.warehouse_code)).all())


@router.post("", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
def register_warehouse(
    warehouse_in: WarehouseCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Warehouse:
    """Register a warehouse in the policy registry."""
    warehouse = Warehouse(**warehouse_in.model_dump())
    db.add(warehouse)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A warehouse with this warehouse_code already exists.",
        ) from error

    db.refresh(warehouse)
    return warehouse


@router.post(
    "/{warehouse_id}/datasets",
    response_model=WarehouseDatasetRead,
    status_code=status.HTTP_201_CREATED,
)
def register_warehouse_dataset(
    warehouse_id: UUID,
    association_in: WarehouseDatasetCreate,
    db: Annotated[Session, Depends(get_db)],
) -> WarehouseDataset:
    """Associate an existing dataset definition with a warehouse."""
    if db.get(Warehouse, warehouse_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found.",
        )
    if db.get(DatasetDefinition, association_in.dataset_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset definition not found.",
        )

    association = WarehouseDataset(
        warehouse_id=warehouse_id,
        **association_in.model_dump(),
    )
    db.add(association)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dataset is already associated with this warehouse.",
        ) from error

    db.refresh(association)
    return association
