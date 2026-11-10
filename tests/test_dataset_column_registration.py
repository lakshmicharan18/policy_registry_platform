from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.db.session import engine
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    connection: Connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    session.close()
    transaction.rollback()
    connection.close()


def create_dataset(client: TestClient) -> str:
    response = client.post(
        "/datasets",
        json={
            "dataset_code": f"TEST-{uuid4().hex[:12]}",
            "name": "Test Dataset",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_register_dataset_column(client: TestClient) -> None:
    dataset_id = create_dataset(client)

    response = client.post(
        f"/datasets/{dataset_id}/columns",
        json={
            "column_name": "quantity",
            "data_type": "integer",
            "is_required": False,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["dataset_id"] == dataset_id
    assert payload["column_name"] == "quantity"
    assert payload["data_type"] == "integer"
    assert payload["is_required"] is False
    assert payload["id"]


def test_register_dataset_column_rejects_duplicate_column_name(client: TestClient) -> None:
    dataset_id = create_dataset(client)
    payload = {"column_name": "sku", "data_type": "string"}

    assert client.post(f"/datasets/{dataset_id}/columns", json=payload).status_code == 201

    response = client.post(f"/datasets/{dataset_id}/columns", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A column with this column_name already exists in this dataset."
    )


def test_register_dataset_column_rejects_unknown_dataset(client: TestClient) -> None:
    response = client.post(
        f"/datasets/{uuid4()}/columns",
        json={"column_name": "sku", "data_type": "string"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset definition not found."


@pytest.mark.parametrize(
    "payload",
    [
        {"column_name": "", "data_type": "string"},
        {"column_name": "   ", "data_type": "string"},
        {"column_name": "C" * 101, "data_type": "string"},
        {"column_name": "sku", "data_type": "unsupported"},
        {"column_name": "sku", "data_type": "string", "is_required": "invalid"},
    ],
)
def test_register_dataset_column_validates_input(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    dataset_id = create_dataset(client)

    response = client.post(f"/datasets/{dataset_id}/columns", json=payload)

    assert response.status_code == 422
