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


def test_register_warehouse(client: TestClient) -> None:
    warehouse_code = f"TEST-{uuid4().hex[:12]}"

    response = client.post(
        "/warehouses",
        json={"warehouse_code": warehouse_code, "name": "Test Warehouse"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["warehouse_code"] == warehouse_code
    assert payload["name"] == "Test Warehouse"
    assert payload["id"]
    assert payload["created_at"]


def test_register_warehouse_rejects_duplicate_code(client: TestClient) -> None:
    warehouse_code = f"TEST-{uuid4().hex[:12]}"
    payload = {"warehouse_code": warehouse_code, "name": "Test Warehouse"}

    assert client.post("/warehouses", json=payload).status_code == 201

    response = client.post("/warehouses", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "A warehouse with this warehouse_code already exists."


@pytest.mark.parametrize(
    "payload",
    [
        {"warehouse_code": "", "name": "Test Warehouse"},
        {"warehouse_code": "   ", "name": "Test Warehouse"},
        {"warehouse_code": "W" * 51, "name": "Test Warehouse"},
        {"warehouse_code": "WH001", "name": ""},
        {"warehouse_code": "WH001", "name": "N" * 256},
    ],
)
def test_register_warehouse_validates_input(client: TestClient, payload: dict[str, str]) -> None:
    response = client.post("/warehouses", json=payload)

    assert response.status_code == 422
