from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routers import onboarding
from app.db.dependencies import get_db
from app.db.session import engine
from app.main import app
from app.models.dataset_definition import DatasetDefinition
from app.models.dataset_column import DatasetColumn, DatasetDataType
from app.models.onboarding import UploadColumnMapping, WarehouseUpload
from app.models.warehouse import Warehouse
from app.models.warehouse_dataset import DatasetRequirementType, WarehouseDataset
from app.models.warehouse_dataset_mapping import WarehouseDatasetMapping


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.upload_uniqueness_session = session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.upload_uniqueness_session
    session.close()
    transaction.rollback()
    connection.close()


def make_upload(warehouse_id, filename: str, dataset_id=None) -> WarehouseUpload:
    return WarehouseUpload(
        warehouse_id=warehouse_id,
        dataset_id=dataset_id,
        original_filename=filename,
        storage_key=f"{uuid4()}.csv",
        source_headers=["source"],
        sample_rows=[{"source": "value"}],
        row_count=1,
    )


def test_normalized_filename_is_unique_per_warehouse_but_not_globally(client: TestClient) -> None:
    session = app.state.upload_uniqueness_session
    first = Warehouse(warehouse_code=f"TEST-{uuid4().hex[:10]}", name="First")
    second = Warehouse(warehouse_code=f"TEST-{uuid4().hex[:10]}", name="Second")
    session.add_all([first, second])
    session.flush()
    session.add(make_upload(first.id, " Orders.CSV "))
    session.add(make_upload(second.id, "orders.csv"))
    session.flush()

    with pytest.raises(IntegrityError), session.begin_nested():
        session.add(make_upload(first.id, "orders.csv"))
        session.flush()


def test_logical_dataset_is_reserved_per_warehouse_not_globally(client: TestClient) -> None:
    session = app.state.upload_uniqueness_session
    first = Warehouse(warehouse_code=f"TEST-{uuid4().hex[:10]}", name="First")
    second = Warehouse(warehouse_code=f"TEST-{uuid4().hex[:10]}", name="Second")
    dataset = DatasetDefinition(dataset_code=f"TEST-{uuid4().hex[:10]}", name="Logical")
    session.add_all([first, second, dataset])
    session.flush()
    first_upload = make_upload(first.id, "first.csv")
    competing_upload = make_upload(first.id, "second.csv")
    other_warehouse_upload = make_upload(second.id, "third.csv")
    session.add_all([first_upload, competing_upload, other_warehouse_upload])
    session.flush()

    assert client.put(f"/onboarding/uploads/{first_upload.id}/dataset", json={"dataset_id": str(dataset.id)}).status_code == 200
    assert client.put(f"/onboarding/uploads/{competing_upload.id}/dataset", json={"dataset_id": str(dataset.id)}).status_code == 409
    assert client.put(f"/onboarding/uploads/{other_warehouse_upload.id}/dataset", json={"dataset_id": str(dataset.id)}).status_code == 200


def test_reupload_releases_only_its_dataset_selection(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(onboarding, "UPLOAD_DIRECTORY", tmp_path)
    session = app.state.upload_uniqueness_session
    warehouse = Warehouse(warehouse_code=f"TEST-{uuid4().hex[:10]}", name="Warehouse")
    dataset = DatasetDefinition(dataset_code=f"TEST-{uuid4().hex[:10]}", name="Logical")
    session.add_all([warehouse, dataset])
    session.flush()
    upload = make_upload(warehouse.id, "old.csv", dataset.id)
    other_upload = make_upload(warehouse.id, "other.csv")
    column = DatasetColumn(dataset_id=dataset.id, column_name="logical", data_type=DatasetDataType.STRING)
    association = WarehouseDataset(warehouse_id=warehouse.id, dataset_id=dataset.id, requirement_type=DatasetRequirementType.OPTIONAL)
    session.add_all([upload, other_upload, column, association])
    session.flush()
    session.add_all([
        UploadColumnMapping(upload_id=upload.id, warehouse_id=warehouse.id, dataset_id=dataset.id, source_column_name="source", logical_column_id=column.id),
        WarehouseDatasetMapping(warehouse_dataset_id=association.id, warehouse_id=warehouse.id, dataset_id=dataset.id, warehouse_code=warehouse.warehouse_code, warehouse_name=warehouse.name, customer_dataset_name="old.csv"),
    ])
    session.flush()

    response = client.put(
        f"/onboarding/uploads/{upload.id}/reupload",
        data={"confirm": "true"},
        files={"file": ("new.csv", b"replacement\nvalue\n", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["dataset_id"] is None
    assert client.put(f"/onboarding/uploads/{other_upload.id}/dataset", json={"dataset_id": str(dataset.id)}).status_code == 200
