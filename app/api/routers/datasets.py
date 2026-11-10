from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.dependencies import get_db
from app.models.dataset_column import DatasetColumn
from app.models.dataset_definition import DatasetDefinition
from app.schemas.dataset_column import DatasetColumnCreate, DatasetColumnRead
from app.schemas.dataset_definition import (
    DatasetDefinitionCreate,
    DatasetDefinitionDetail,
    DatasetDefinitionRead,
)


router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetDefinitionRead])
def list_dataset_definitions(
    db: Annotated[Session, Depends(get_db)],
) -> list[DatasetDefinition]:
    """List dataset definitions ordered by dataset code."""
    statement = select(DatasetDefinition).order_by(DatasetDefinition.dataset_code)
    return list(db.scalars(statement).all())


@router.get("/{dataset_id}", response_model=DatasetDefinitionDetail)
def get_dataset_definition(
    dataset_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetDefinition:
    """Return a dataset definition and its columns."""
    statement = (
        select(DatasetDefinition)
        .where(DatasetDefinition.id == dataset_id)
        .options(selectinload(DatasetDefinition.columns))
    )
    dataset_definition = db.scalar(statement)
    if dataset_definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset definition not found.",
        )
    return dataset_definition


@router.post("", response_model=DatasetDefinitionRead, status_code=status.HTTP_201_CREATED)
def register_dataset_definition(
    dataset_in: DatasetDefinitionCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetDefinition:
    """Register a reusable dataset definition."""
    dataset_definition = DatasetDefinition(**dataset_in.model_dump())
    db.add(dataset_definition)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dataset with this dataset_code already exists.",
        ) from error

    db.refresh(dataset_definition)
    return dataset_definition


@router.post(
    "/{dataset_id}/columns",
    response_model=DatasetColumnRead,
    status_code=status.HTTP_201_CREATED,
)
def register_dataset_column(
    dataset_id: UUID,
    column_in: DatasetColumnCreate,
    db: Annotated[Session, Depends(get_db)],
) -> DatasetColumn:
    """Register a column in an existing dataset definition."""
    if db.get(DatasetDefinition, dataset_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset definition not found.",
        )

    dataset_column = DatasetColumn(dataset_id=dataset_id, **column_in.model_dump())
    db.add(dataset_column)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A column with this column_name already exists in this dataset.",
        ) from error

    db.refresh(dataset_column)
    return dataset_column
