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


def create_warehouse(client: TestClient) -> str:
    response = client.post(
        "/warehouses",
        json={
            "warehouse_code": f"TEST-{uuid4().hex[:12]}",
            "name": "Test Warehouse",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


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


def test_register_conditional_warehouse_dataset_association(client: TestClient) -> None:
    warehouse_id = create_warehouse(client)
    dataset_id = create_dataset(client)

    response = client.post(
        f"/warehouses/{warehouse_id}/datasets",
        json={
            "dataset_id": dataset_id,
            "requirement_type": "conditional",
            "condition_config": {"when": "warehouse_enabled"},
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["warehouse_id"] == warehouse_id
    assert payload["dataset_id"] == dataset_id
    assert payload["requirement_type"] == "conditional"
    assert payload["condition_config"] == {"when": "warehouse_enabled"}
    assert payload["id"]


def test_register_warehouse_dataset_rejects_duplicate_association(client: TestClient) -> None:
    warehouse_id = create_warehouse(client)
    dataset_id = create_dataset(client)
    payload = {"dataset_id": dataset_id, "requirement_type": "mandatory"}

    assert client.post(f"/warehouses/{warehouse_id}/datasets", json=payload).status_code == 201

    response = client.post(f"/warehouses/{warehouse_id}/datasets", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "This dataset is already associated with this warehouse."


def test_register_warehouse_dataset_rejects_unknown_warehouse(client: TestClient) -> None:
    response = client.post(
        f"/warehouses/{uuid4()}/datasets",
        json={"dataset_id": create_dataset(client), "requirement_type": "mandatory"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Warehouse not found."


def test_register_warehouse_dataset_rejects_unknown_dataset(client: TestClient) -> None:
    response = client.post(
        f"/warehouses/{create_warehouse(client)}/datasets",
        json={"dataset_id": str(uuid4()), "requirement_type": "mandatory"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset definition not found."


@pytest.mark.parametrize(
    "path, payload",
    [
        (
            "/warehouses/not-a-uuid/datasets",
            {"dataset_id": str(uuid4()), "requirement_type": "mandatory"},
        ),
        (
            "/warehouses/{warehouse_id}/datasets",
            {"dataset_id": "not-a-uuid", "requirement_type": "mandatory"},
        ),
        (
            "/warehouses/{warehouse_id}/datasets",
            {"dataset_id": str(uuid4()), "requirement_type": "unsupported"},
        ),
    ],
)
def test_register_warehouse_dataset_validates_identifiers_and_requirement_type(
    client: TestClient,
    path: str,
    payload: dict[str, str],
) -> None:
    response = client.post(path.format(warehouse_id=create_warehouse(client)), json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"requirement_type": "conditional"},
        {"requirement_type": "conditional", "condition_config": {}},
        {"requirement_type": "mandatory", "condition_config": {"when": "x"}},
        {"requirement_type": "optional", "condition_config": {"when": "x"}},
        {"requirement_type": "conditional", "condition_config": []},
    ],
)
def test_register_warehouse_dataset_validates_condition_config(
    client: TestClient,
    payload: dict[str, object],
) -> None:
    response = client.post(
        f"/warehouses/{create_warehouse(client)}/datasets",
        json={"dataset_id": create_dataset(client), **payload},
    )

    assert response.status_code == 422


def test_register_warehouse_dataset_allows_same_dataset_for_different_warehouses(
    client: TestClient,
) -> None:
    dataset_id = create_dataset(client)
    payload = {"dataset_id": dataset_id, "requirement_type": "optional"}

    first = client.post(f"/warehouses/{create_warehouse(client)}/datasets", json=payload)
    second = client.post(f"/warehouses/{create_warehouse(client)}/datasets", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["warehouse_id"] != second.json()["warehouse_id"]
