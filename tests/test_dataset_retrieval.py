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


def create_dataset(client: TestClient, suffix: str) -> dict[str, object]:
    response = client.post(
        "/datasets",
        json={
            "dataset_code": f"TEST-{suffix}-{uuid4().hex[:8]}",
            "name": f"Test Dataset {suffix}",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_list_dataset_definitions_is_ordered(client: TestClient) -> None:
    first = create_dataset(client, "B")
    second = create_dataset(client, "A")

    response = client.get("/datasets")

    assert response.status_code == 200
    payload = response.json()
    dataset_codes = [dataset["dataset_code"] for dataset in payload]
    assert dataset_codes == sorted(dataset_codes)
    assert {first["id"], second["id"]}.issubset(
        {dataset["id"] for dataset in payload}
    )


def test_get_dataset_definition_includes_ordered_columns(client: TestClient) -> None:
    dataset = create_dataset(client, "DETAIL")

    for column_name, data_type in (("zeta", "string"), ("alpha", "integer")):
        response = client.post(
            f"/datasets/{dataset['id']}/columns",
            json={"column_name": column_name, "data_type": data_type},
        )
        assert response.status_code == 201

    response = client.get(f"/datasets/{dataset['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == dataset["id"]
    assert payload["dataset_code"] == dataset["dataset_code"]
    assert [column["column_name"] for column in payload["columns"]] == [
        "alpha",
        "zeta",
    ]
    assert payload["columns"][0]["data_type"] == "integer"
    assert payload["columns"][0]["dataset_id"] == dataset["id"]


def test_get_dataset_definition_returns_not_found_for_unknown_id(client: TestClient) -> None:
    response = client.get(f"/datasets/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset definition not found."


def test_get_dataset_definition_rejects_invalid_uuid(client: TestClient) -> None:
    response = client.get("/datasets/not-a-uuid")

    assert response.status_code == 422


def test_list_dataset_definitions_returns_empty_list_when_no_rows() -> None:
    class EmptyScalarResult:
        def all(self) -> list[object]:
            return []

    class EmptySession:
        def scalars(self, statement: object) -> EmptyScalarResult:
            return EmptyScalarResult()

    def override_get_db() -> Generator[EmptySession, None, None]:
        yield EmptySession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/datasets")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
