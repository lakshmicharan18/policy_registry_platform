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


def test_register_dataset_definition(client: TestClient) -> None:
    dataset_code = f"TEST-{uuid4().hex[:12]}"

    response = client.post(
        "/datasets",
        json={
            "dataset_code": dataset_code,
            "name": "Test Dataset",
            "description": "A test-only dataset definition.",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["dataset_code"] == dataset_code
    assert payload["name"] == "Test Dataset"
    assert payload["description"] == "A test-only dataset definition."
    assert payload["id"]
    assert payload["created_at"]


def test_register_dataset_definition_rejects_duplicate_code(client: TestClient) -> None:
    dataset_code = f"TEST-{uuid4().hex[:12]}"
    payload = {"dataset_code": dataset_code, "name": "Test Dataset"}

    assert client.post("/datasets", json=payload).status_code == 201

    response = client.post("/datasets", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "A dataset with this dataset_code already exists."


@pytest.mark.parametrize(
    "payload",
    [
        {"dataset_code": "", "name": "Test Dataset"},
        {"dataset_code": "   ", "name": "Test Dataset"},
        {"dataset_code": "D" * 101, "name": "Test Dataset"},
        {"dataset_code": "DS001", "name": ""},
        {"dataset_code": "DS001", "name": "   "},
        {"dataset_code": "DS001", "name": "N" * 256},
    ],
)
def test_register_dataset_definition_validates_input(
    client: TestClient,
    payload: dict[str, str],
) -> None:
    response = client.post("/datasets", json=payload)

    assert response.status_code == 422
