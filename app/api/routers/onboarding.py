import csv
import io
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.dataset_column import DatasetColumn
from app.models.dataset_definition import DatasetDefinition
from app.models.onboarding import UploadColumnMapping, UploadReviewComment, UploadReviewConfirmation, WarehouseUpload
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import DatasetRequirementType, WarehouseDataset
from app.models.warehouse_dataset_mapping import WarehouseDatasetMapping

router = APIRouter(prefix="/onboarding", tags=["warehouse onboarding"])
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
SAMPLE_ROWS = 5
UPLOAD_DIRECTORY = Path("data/uploads")


class DatasetSelection(BaseModel):
    dataset_id: UUID
    confirm_clear: bool = False


class ColumnMapping(BaseModel):
    source_column_name: str
    logical_column_id: UUID | None = None


class MappingUpdate(BaseModel):
    mappings: list[ColumnMapping]

class ReviewAction(BaseModel):
    author: str
    role: str
    comment: str | None = None


def mapping_status(upload: WarehouseUpload) -> str:
    return "mapped" if upload.dataset_id is not None else "not_mapped"


def upload_payload(upload: WarehouseUpload) -> dict:
    return {"id": upload.id, "warehouse_id": upload.warehouse_id, "dataset_id": upload.dataset_id, "original_filename": upload.original_filename, "source_headers": upload.source_headers, "sample_rows": upload.sample_rows, "row_count": upload.row_count, "status": upload.status, "mappings": [{"source_column_name": item.source_column_name, "logical_column_id": item.logical_column_id} for item in upload.column_mappings]}


def parse_csv(content: bytes) -> tuple[list[str], list[dict[str, str]], int]:
    """Parse a UTF-8 CSV without normalising customer headers or values."""
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The CSV is empty or exceeds the 5 MB upload limit.")
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    headers = reader.fieldnames or []
    if not headers or any(not header or not header.strip() for header in headers) or len(set(headers)) != len(headers):
        raise ValueError("CSV headers must be present, non-blank, and unique.")
    rows = list(reader)
    return headers, rows[:SAMPLE_ROWS], len(rows)


@router.get("/warehouses/{warehouse_id}/uploads")
def list_uploads(warehouse_id: UUID, db: Annotated[Session, Depends(get_db)]):
    if db.get(Warehouse, warehouse_id) is None:
        raise HTTPException(404, "Warehouse not found.")
    uploads = db.scalars(
        select(WarehouseUpload)
        .where(WarehouseUpload.warehouse_id == warehouse_id)
        .order_by(WarehouseUpload.created_at.desc())
    ).all()
    datasets = {
        dataset.id: dataset
        for dataset in db.scalars(select(DatasetDefinition).where(DatasetDefinition.id.in_([item.dataset_id for item in uploads if item.dataset_id is not None]))).all()
    }
    return [
        {
            **upload_payload(upload),
            "logical_dataset_name": datasets[upload.dataset_id].name if upload.dataset_id else None,
            "mapping_status": mapping_status(upload),
        }
        for upload in uploads
    ]


@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def create_upload(warehouse_id: Annotated[UUID, Form()], file: Annotated[UploadFile, File()], db: Annotated[Session, Depends(get_db)]):
    if db.get(Warehouse, warehouse_id) is None:
        raise HTTPException(404, "Warehouse not found.")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(422, "Only CSV files are supported.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        headers, sample_rows, row_count = parse_csv(content)
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        raise HTTPException(422, f"Unreadable CSV: {error}") from error
    normalized_filename = (file.filename or "upload.csv").strip().lower()
    existing = db.scalar(
        select(WarehouseUpload).where(
            WarehouseUpload.warehouse_id == warehouse_id,
            func.lower(func.btrim(WarehouseUpload.original_filename)) == normalized_filename,
        )
    )
    if existing is not None:
        if existing.dataset_id is None:
            detail = "This dataset is already uploaded but has not been mapped yet."
        else:
            dataset = db.get(DatasetDefinition, existing.dataset_id)
            detail = f"This dataset is already uploaded and mapped to {dataset.name if dataset else 'the selected logical dataset'}. Use Reupload to replace it."
        raise HTTPException(409, detail)
    storage_key = f"{uuid4()}.csv"
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIRECTORY / storage_key).write_bytes(content)
    upload = WarehouseUpload(warehouse_id=warehouse_id, original_filename=file.filename or "upload.csv", storage_key=storage_key, source_headers=headers, sample_rows=sample_rows, row_count=row_count)
    db.add(upload)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        (UPLOAD_DIRECTORY / storage_key).unlink(missing_ok=True)
        raise HTTPException(409, "This dataset is already uploaded for this warehouse.") from error
    db.refresh(upload)
    return upload_payload(upload)


@router.put("/uploads/{upload_id}/reupload")
async def reupload(
    upload_id: UUID,
    confirm: Annotated[bool, Form()],
    file: Annotated[UploadFile, File()],
    db: Annotated[Session, Depends(get_db)],
):
    """Replace one upload only after its replacement CSV is valid."""
    if not confirm:
        raise HTTPException(422, "Reupload confirmation is required.")
    upload = db.get(WarehouseUpload, upload_id)
    if upload is None:
        raise HTTPException(404, "Upload not found.")
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(422, "Only CSV files are supported.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        headers, sample_rows, row_count = parse_csv(content)
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        raise HTTPException(422, f"Unreadable CSV: {error}") from error

    replacement_name = file.filename or "upload.csv"
    duplicate = db.scalar(
        select(WarehouseUpload.id).where(
            WarehouseUpload.warehouse_id == upload.warehouse_id,
            func.lower(func.btrim(WarehouseUpload.original_filename)) == replacement_name.strip().lower(),
            WarehouseUpload.id != upload.id,
        )
    )
    if duplicate is not None:
        raise HTTPException(409, "This dataset is already uploaded for this warehouse.")

    old_storage_key = upload.storage_key
    new_storage_key = f"{uuid4()}.csv"
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIRECTORY / new_storage_key).write_bytes(content)
    try:
        if upload.dataset_id is not None:
            association = db.scalar(select(WarehouseDataset).where(WarehouseDataset.warehouse_id == upload.warehouse_id, WarehouseDataset.dataset_id == upload.dataset_id))
            if association is not None:
                mapping = db.scalar(select(WarehouseDatasetMapping).where(WarehouseDatasetMapping.warehouse_dataset_id == association.id))
                if mapping is not None:
                    db.delete(mapping)
        upload.column_mappings.clear()
        upload.comments.clear()
        upload.confirmations.clear()
        # The column mappings reference the upload's warehouse/dataset
        # identity as a composite FK. Delete those children before releasing
        # the dataset reservation on the parent upload.
        db.flush()
        upload.dataset_id = None
        upload.original_filename = replacement_name
        upload.storage_key = new_storage_key
        upload.source_headers = headers
        upload.sample_rows = sample_rows
        upload.row_count = row_count
        upload.status = "draft"
        db.commit()
    except IntegrityError as error:
        db.rollback()
        (UPLOAD_DIRECTORY / new_storage_key).unlink(missing_ok=True)
        raise HTTPException(409, "Unable to replace this upload.") from error
    (UPLOAD_DIRECTORY / old_storage_key).unlink(missing_ok=True)
    db.refresh(upload)
    return upload_payload(upload)


@router.get("/uploads/{upload_id}")
def get_upload(upload_id: UUID, db: Annotated[Session, Depends(get_db)]):
    upload = db.scalar(select(WarehouseUpload).where(WarehouseUpload.id == upload_id))
    if upload is None: raise HTTPException(404, "Upload not found.")
    return upload_payload(upload)


@router.put("/uploads/{upload_id}/dataset")
def select_dataset(upload_id: UUID, body: DatasetSelection, db: Annotated[Session, Depends(get_db)]):
    upload = db.get(WarehouseUpload, upload_id)
    if upload is None: raise HTTPException(404, "Upload not found.")
    if db.get(DatasetDefinition, body.dataset_id) is None: raise HTTPException(404, "Dataset definition not found.")
    selected_by_other = db.scalar(
        select(WarehouseUpload.id).where(
            WarehouseUpload.warehouse_id == upload.warehouse_id,
            WarehouseUpload.dataset_id == body.dataset_id,
            WarehouseUpload.id != upload.id,
        )
    )
    if selected_by_other is not None:
        raise HTTPException(409, "This logical dataset is already assigned to another upload for this warehouse.")
    existing_mapping = None
    if upload.dataset_id is not None:
        association = db.scalar(select(WarehouseDataset).where(WarehouseDataset.warehouse_id == upload.warehouse_id, WarehouseDataset.dataset_id == upload.dataset_id))
        if association is not None:
            existing_mapping = db.scalar(select(WarehouseDatasetMapping).where(WarehouseDatasetMapping.warehouse_dataset_id == association.id))
    if upload.dataset_id != body.dataset_id and (upload.column_mappings or existing_mapping is not None) and not body.confirm_clear:
        raise HTTPException(409, "Changing the logical dataset clears existing column mappings; confirm_clear is required.")
    if upload.dataset_id != body.dataset_id:
        upload.column_mappings.clear()
        if existing_mapping is not None:
            db.delete(existing_mapping)
        upload.dataset_id = body.dataset_id
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "This logical dataset is already assigned to another upload for this warehouse.") from error
    db.refresh(upload)
    return upload_payload(upload)


@router.put("/uploads/{upload_id}/mappings")
def save_mappings(upload_id: UUID, body: MappingUpdate, db: Annotated[Session, Depends(get_db)]):
    upload = db.get(WarehouseUpload, upload_id)
    if upload is None: raise HTTPException(404, "Upload not found.")
    if upload.dataset_id is None: raise HTTPException(422, "Select a logical dataset before mapping columns.")
    source_names = [item.source_column_name for item in body.mappings]
    logical_ids = [item.logical_column_id for item in body.mappings if item.logical_column_id]
    if set(source_names) != set(upload.source_headers) or len(logical_ids) != len(upload.source_headers):
        raise HTTPException(422, "Please map all columns before saving the mapping.")
    if len(source_names) != len(set(source_names)) or len(logical_ids) != len(set(logical_ids)) or any(name not in upload.source_headers for name in source_names):
        raise HTTPException(422, "Mappings must use unique upload headers and logical columns.")
    allowed = set(db.scalars(select(DatasetColumn.id).where(DatasetColumn.dataset_id == upload.dataset_id)).all())
    if not set(logical_ids).issubset(allowed): raise HTTPException(422, "Logical columns must belong to the selected dataset.")
    warehouse = db.get(Warehouse, upload.warehouse_id)
    if warehouse is None:
        raise HTTPException(404, "Warehouse not found.")

    # The onboarding flow has no requirement-rule selector.  An association
    # created here is therefore an optional draft association; it can be
    # managed through the existing warehouse-dataset API later.
    association = db.scalar(
        select(WarehouseDataset).where(
            WarehouseDataset.warehouse_id == upload.warehouse_id,
            WarehouseDataset.dataset_id == upload.dataset_id,
        )
    )
    if association is None:
        association = WarehouseDataset(
            id=uuid4(),
            warehouse_id=upload.warehouse_id,
            dataset_id=upload.dataset_id,
            requirement_type=DatasetRequirementType.OPTIONAL,
        )
        db.add(association)

    mapping = db.scalar(
        select(WarehouseDatasetMapping).where(
            WarehouseDatasetMapping.warehouse_dataset_id == association.id
        )
    )
    if mapping is None:
        mapping = WarehouseDatasetMapping(
            warehouse_dataset_id=association.id,
            warehouse_id=warehouse.id,
            dataset_id=upload.dataset_id,
            warehouse_code=warehouse.warehouse_code,
            warehouse_name=warehouse.name,
            customer_dataset_name=upload.original_filename,
        )
        db.add(mapping)
    else:
        # Repeated saves update the draft snapshot instead of creating one.
        mapping.warehouse_id = warehouse.id
        mapping.dataset_id = upload.dataset_id
        mapping.warehouse_code = warehouse.warehouse_code
        mapping.warehouse_name = warehouse.name
        mapping.customer_dataset_name = upload.original_filename

    try:
        # Flush removals before re-inserting the same logical column so the
        # database's per-upload uniqueness constraint also permits re-saves.
        upload.column_mappings.clear()
        db.flush()
        upload.column_mappings.extend(UploadColumnMapping(upload_id=upload.id, warehouse_id=upload.warehouse_id, dataset_id=upload.dataset_id, source_column_name=item.source_column_name, logical_column_id=item.logical_column_id) for item in body.mappings if item.logical_column_id)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(409, "Unable to save a consistent mapping.") from error
    db.refresh(upload)
    return upload_payload(upload)

@router.post("/uploads/{upload_id}/submit")
def submit_for_review(upload_id: UUID, db: Annotated[Session, Depends(get_db)]):
    upload = db.get(WarehouseUpload, upload_id)
    if upload is None: raise HTTPException(404, "Upload not found.")
    upload.status = "in_review"; db.commit(); return upload_payload(upload)

@router.post("/uploads/{upload_id}/comments", status_code=status.HTTP_201_CREATED)
def add_comment(upload_id: UUID, body: ReviewAction, db: Annotated[Session, Depends(get_db)]):
    if db.get(WarehouseUpload, upload_id) is None: raise HTTPException(404, "Upload not found.")
    if not body.comment or not body.comment.strip(): raise HTTPException(422, "A comment is required.")
    item = UploadReviewComment(upload_id=upload_id, author=body.author, role=body.role, comment=body.comment.strip()); db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "author": item.author, "role": item.role, "comment": item.comment, "created_at": item.created_at}

@router.post("/uploads/{upload_id}/confirmations", status_code=status.HTTP_201_CREATED)
def add_confirmation(upload_id: UUID, body: ReviewAction, db: Annotated[Session, Depends(get_db)]):
    if db.get(WarehouseUpload, upload_id) is None: raise HTTPException(404, "Upload not found.")
    item = UploadReviewConfirmation(upload_id=upload_id, author=body.author, role=body.role); db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "author": item.author, "role": item.role, "confirmed_at": item.confirmed_at}
