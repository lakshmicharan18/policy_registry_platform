from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.dataset_column import DatasetColumn, DatasetDataType
from app.models.dataset_definition import DatasetDefinition
from app.models.dataset_requirement_rule import DatasetRequirementRule
from app.models.onboarding import (
    UploadColumnMapping,
    UploadReviewComment,
    UploadReviewConfirmation,
    WarehouseUpload,
)
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import DatasetRequirementType, WarehouseDataset
from app.models.warehouse_dataset_mapping import WarehouseDatasetMapping


def add_graph(session: Session, suffix: str) -> dict[str, object]:
    warehouse = Warehouse(warehouse_code=f"CAS-{suffix}", name=f"Warehouse {suffix}")
    dataset = DatasetDefinition(dataset_code=f"CAS-{suffix}", name=f"Dataset {suffix}")
    session.add_all([warehouse, dataset])
    session.flush()
    column = DatasetColumn(dataset_id=dataset.id, column_name="sku", data_type=DatasetDataType.STRING)
    association = WarehouseDataset(
        warehouse_id=warehouse.id,
        dataset_id=dataset.id,
        requirement_type=DatasetRequirementType.OPTIONAL,
    )
    upload = WarehouseUpload(
        warehouse_id=warehouse.id,
        dataset_id=dataset.id,
        original_filename=f"{suffix}.csv",
        storage_key=f"cascade-{uuid4()}.csv",
        source_headers=["customer_sku"],
        sample_rows=[{"customer_sku": "ABC"}],
        row_count=1,
    )
    rule = DatasetRequirementRule(dataset_id=dataset.id, requirement_type=DatasetRequirementType.OPTIONAL)
    session.add_all([column, association, upload, rule])
    session.flush()
    mapping = WarehouseDatasetMapping(
        warehouse_dataset_id=association.id,
        warehouse_id=warehouse.id,
        dataset_id=dataset.id,
        warehouse_code=warehouse.warehouse_code,
        warehouse_name=warehouse.name,
        customer_dataset_name=f"{suffix}.csv",
    )
    column_mapping = UploadColumnMapping(
        upload_id=upload.id,
        warehouse_id=warehouse.id,
        dataset_id=dataset.id,
        source_column_name="customer_sku",
        logical_column_id=column.id,
    )
    comment = UploadReviewComment(upload_id=upload.id, author="test", role="tester", comment="temporary")
    confirmation = UploadReviewConfirmation(upload_id=upload.id, author="test", role="tester")
    session.add_all([mapping, column_mapping, comment, confirmation])
    session.flush()
    return {
        "warehouse": warehouse,
        "dataset": dataset,
        "column": column,
        "association": association,
        "upload": upload,
        "rule": rule,
        "mapping": mapping,
        "column_mapping": column_mapping,
        "comment": comment,
        "confirmation": confirmation,
    }


def test_database_foreign_key_cascades_are_parent_to_child_only() -> None:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        warehouse_graph = add_graph(session, uuid4().hex[:10])
        dataset_graph = add_graph(session, uuid4().hex[:10])
        child_graph = add_graph(session, uuid4().hex[:10])
        unrelated_graph = add_graph(session, uuid4().hex[:10])
        warehouse_ids = {key: item.id for key, item in warehouse_graph.items()}
        dataset_ids = {key: item.id for key, item in dataset_graph.items()}
        child_ids = {key: item.id for key, item in child_graph.items()}
        unrelated_ids = {key: item.id for key, item in unrelated_graph.items()}

        session.execute(delete(Warehouse).where(Warehouse.id == warehouse_ids["warehouse"]))
        session.flush()
        session.expire_all()
        for key in ("association", "mapping", "upload", "column_mapping", "comment", "confirmation"):
            assert session.get(type(warehouse_graph[key]), warehouse_ids[key]) is None
        assert session.get(DatasetDefinition, warehouse_ids["dataset"]) is not None

        session.execute(delete(DatasetDefinition).where(DatasetDefinition.id == dataset_ids["dataset"]))
        session.flush()
        session.expire_all()
        for key in ("dataset", "column", "rule", "association", "mapping", "upload", "column_mapping", "comment", "confirmation"):
            assert session.get(type(dataset_graph[key]), dataset_ids[key]) is None
        assert session.get(Warehouse, dataset_ids["warehouse"]) is not None

        session.execute(delete(WarehouseDatasetMapping).where(WarehouseDatasetMapping.id == child_ids["mapping"]))
        session.flush()
        session.expire_all()
        assert session.get(WarehouseDatasetMapping, child_ids["mapping"]) is None
        assert session.get(Warehouse, child_ids["warehouse"]) is not None
        assert session.get(DatasetDefinition, child_ids["dataset"]) is not None
        assert session.get(WarehouseDataset, child_ids["association"]) is not None

        assert session.get(Warehouse, unrelated_ids["warehouse"]) is not None
        assert session.get(DatasetDefinition, unrelated_ids["dataset"]) is not None
    finally:
        session.close()
        transaction.rollback()
        connection.close()
