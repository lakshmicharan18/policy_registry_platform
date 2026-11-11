from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.session import engine
from app.main import app
from app.models.dataset_column import DatasetColumn, DatasetDataType
from app.models.dataset_definition import DatasetDefinition
from app.models.onboarding import UploadColumnMapping, WarehouseUpload
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import WarehouseDataset
from app.models.warehouse_dataset_mapping import WarehouseDatasetMapping


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    connection: Connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.onboarding_test_session = session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.onboarding_test_session
    session.close()
    transaction.rollback()
    connection.close()


def test_mapping_save_persists_a_consistent_single_mapping(client: TestClient) -> None:
    mapping_columns = {
        column["name"]
        for column in inspect(engine).get_columns("warehouse_dataset_mappings")
    }
    if not {"warehouse_id", "dataset_id"}.issubset(mapping_columns):
        pytest.skip("Run Alembic through d4e5f6a7b8c9 to exercise mapping persistence.")

    warehouse = Warehouse(warehouse_code=f"TEST-{uuid4().hex[:12]}", name="Test Warehouse")
    dataset = DatasetDefinition(dataset_code=f"TEST-{uuid4().hex[:12]}", name="Test Dataset")
    session = app.state.onboarding_test_session
    session.add_all([warehouse, dataset])
    session.flush()
    column = DatasetColumn(dataset_id=dataset.id, column_name="sku", data_type=DatasetDataType.STRING)
    upload = WarehouseUpload(
        warehouse_id=warehouse.id,
        dataset_id=dataset.id,
        original_filename="customer.csv",
        storage_key=f"{uuid4()}.csv",
        source_headers=["customer_sku"],
        sample_rows=[{"customer_sku": "ABC"}],
        row_count=1,
    )
    session.add_all([column, upload])
    session.flush()

    unmapped = client.put(
        f"/onboarding/uploads/{upload.id}/mappings",
        json={"mappings": [{"source_column_name": "customer_sku", "logical_column_id": None}]},
    )
    assert unmapped.status_code == 422
    assert unmapped.json()["detail"] == "Please map all columns before saving the mapping."

    payload = {"mappings": [{"source_column_name": "customer_sku", "logical_column_id": str(column.id)}]}
    first = client.put(f"/onboarding/uploads/{upload.id}/mappings", json=payload)
    second = client.put(f"/onboarding/uploads/{upload.id}/mappings", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    association = session.scalar(select(WarehouseDataset).where(WarehouseDataset.warehouse_id == warehouse.id, WarehouseDataset.dataset_id == dataset.id))
    mapping = session.scalar(select(WarehouseDatasetMapping).where(WarehouseDatasetMapping.warehouse_dataset_id == association.id))
    assert association is not None
    assert mapping is not None
    assert mapping.warehouse_dataset_id == association.id
    assert mapping.warehouse_id == warehouse.id
    assert mapping.dataset_id == dataset.id
    assert mapping.customer_dataset_name == "customer.csv"
    assert len(session.scalars(select(WarehouseDatasetMapping).where(WarehouseDatasetMapping.warehouse_dataset_id == association.id)).all()) == 1
    assert len(session.scalars(select(UploadColumnMapping).where(UploadColumnMapping.upload_id == upload.id)).all()) == 1
