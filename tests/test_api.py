import pytest
from fastapi.testclient import TestClient
from collections.abc import Iterator

from app.config import Settings
from app.database import Base
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    application = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            redis_url=None,
            redis_cache_ttl_seconds=30,
        )
    )
    Base.metadata.create_all(application.state.engine)
    with TestClient(application) as test_client:
        yield test_client


def test_liveness_and_readiness(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    readiness = client.get("/ready")
    assert readiness.status_code == 200
    assert readiness.json()["dependencies"]["database"] == "ok"
    assert readiness.json()["dependencies"]["redis"] == "unavailable"


def test_create_get_and_list_tasks(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "  Ship the API  ", "description": "MVP"})

    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "Ship the API"
    assert task["status"] == "pending"
    assert client.get(f"/tasks/{task['id']}").json()["description"] == "MVP"
    assert len(client.get("/tasks").json()) == 1


def test_filter_and_paginate_tasks(client: TestClient) -> None:
    first = client.post("/tasks", json={"title": "First"}).json()
    client.patch(f"/tasks/{first['id']}", json={"status": "completed"})
    client.post("/tasks", json={"title": "Second"})

    completed = client.get("/tasks", params={"status": "completed"}).json()
    page = client.get("/tasks", params={"limit": 1, "offset": 1}).json()
    assert len(completed) == 1
    assert completed[0]["title"] == "First"
    assert len(page) == 1


def test_update_invalidates_cached_task_and_delete_removes_it(client: TestClient) -> None:
    task_id = client.post("/tasks", json={"title": "Initial"}).json()["id"]
    assert client.get(f"/tasks/{task_id}").json()["title"] == "Initial"

    updated = client.patch(f"/tasks/{task_id}", json={"title": "Updated"})
    assert updated.status_code == 200
    assert client.get(f"/tasks/{task_id}").json()["title"] == "Updated"

    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": "x" * 201},
        {"title": "Valid", "unexpected": "field"},
    ],
)
def test_rejects_invalid_create_payloads(client: TestClient, payload: dict[str, str]) -> None:
    assert client.post("/tasks", json=payload).status_code == 422


def test_rejects_empty_or_invalid_updates(client: TestClient) -> None:
    task_id = client.post("/tasks", json={"title": "Task"}).json()["id"]

    assert client.patch(f"/tasks/{task_id}", json={}).status_code == 422
    assert client.patch(f"/tasks/{task_id}", json={"status": "unknown"}).status_code == 422


def test_missing_tasks_return_not_found(client: TestClient) -> None:
    assert client.get("/tasks/999").status_code == 404
    assert client.patch("/tasks/999", json={"title": "Missing"}).status_code == 404
    assert client.delete("/tasks/999").status_code == 404
