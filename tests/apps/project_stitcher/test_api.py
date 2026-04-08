"""Tests for HTTP API — full run lifecycle over REST."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vos.agentcore.executorkit.mock import MockExecutor
from vos.agentcore.registry import ExecutorRegistry
from vos.agentcore.storekit import JsonRunStore
from vos.apps.project_stitcher.api import create_router

if TYPE_CHECKING:
    from pathlib import Path

import pytest


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    store = JsonRunStore(tmp_path / "runs")
    registry = ExecutorRegistry()
    registry.register(MockExecutor("mock-1"))
    app = FastAPI()
    app.include_router(create_router(store, registry))
    return TestClient(app)


@pytest.fixture()
def client_no_executor(tmp_path: Path) -> TestClient:
    store = JsonRunStore(tmp_path / "runs")
    registry = ExecutorRegistry()
    app = FastAPI()
    app.include_router(create_router(store, registry))
    return TestClient(app)


# --- Health ---


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["executors"] == 1


# --- Create run ---


def test_create_run(client: TestClient):
    resp = client.post("/runs", json={"description": "verify topology"})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "planned"
    assert data["tasks"] == 1


def test_create_run_with_subtasks(client: TestClient):
    resp = client.post(
        "/runs",
        json={
            "description": "full check",
            "domain": "topology",
            "subtasks": [
                {"description": "collect"},
                {"description": "verify"},
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["tasks"] == 3


# --- List runs ---


def test_list_empty(client: TestClient):
    resp = client.get("/runs")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_after_create(client: TestClient):
    client.post("/runs", json={"description": "task 1"})
    client.post("/runs", json={"description": "task 2"})
    resp = client.get("/runs")
    assert len(resp.json()) == 2


# --- Get run ---


def test_get_run(client: TestClient):
    create_resp = client.post("/runs", json={"description": "test"})
    run_id = create_resp.json()["run_id"]

    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["run_id"] == run_id
    assert data["request"]["description"] == "test"
    assert data["plan"] is not None


def test_get_run_not_found(client: TestClient):
    resp = client.get("/runs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# --- Execute ---


def test_execute_run(client: TestClient):
    create_resp = client.post("/runs", json={"description": "do work"})
    run_id = create_resp.json()["run_id"]

    resp = client.post(f"/runs/{run_id}/execute")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["executed"] == 1


def test_execute_multi_task(client: TestClient):
    create_resp = client.post(
        "/runs",
        json={
            "description": "pipeline",
            "subtasks": [{"description": "a"}, {"description": "b"}],
        },
    )
    run_id = create_resp.json()["run_id"]

    resp = client.post(f"/runs/{run_id}/execute")
    assert resp.status_code == 200
    assert resp.json()["executed"] == 3


def test_execute_not_found(client: TestClient):
    resp = client.post("/runs/00000000-0000-0000-0000-000000000000/execute")
    assert resp.status_code == 404


def test_execute_no_executor(client_no_executor: TestClient):
    create_resp = client_no_executor.post(
        "/runs",
        json={"description": "x", "domain": "topology"},
    )
    run_id = create_resp.json()["run_id"]
    resp = client_no_executor.post(f"/runs/{run_id}/execute")
    assert resp.status_code == 200
    # Tasks executed but with no outcomes (skipped)
    assert resp.json()["skipped"] > 0


# --- Review ---


def test_review_run(client: TestClient):
    create_resp = client.post("/runs", json={"description": "work"})
    run_id = create_resp.json()["run_id"]
    client.post(f"/runs/{run_id}/execute")

    resp = client.post(f"/runs/{run_id}/review")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] in ("approve", "request_changes", "reject")
    assert "findings" in data
    assert "summary" in data


def test_review_not_found(client: TestClient):
    resp = client.post("/runs/00000000-0000-0000-0000-000000000000/review")
    assert resp.status_code == 404


def test_review_no_executor(client_no_executor: TestClient):
    create_resp = client_no_executor.post("/runs", json={"description": "x"})
    run_id = create_resp.json()["run_id"]
    resp = client_no_executor.post(f"/runs/{run_id}/review")
    assert resp.status_code == 503


# --- Full lifecycle ---


# --- Orchestrate ---


def test_orchestrate_run(client: TestClient):
    create_resp = client.post(
        "/runs",
        json={"description": "verify topology", "domain": "topology"},
    )
    run_id = create_resp.json()["run_id"]

    resp = client.post(f"/runs/{run_id}/orchestrate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["executed"] >= 1
    assert data["summary"] is not None
    assert data["review_verdict"] is not None


def test_orchestrate_not_found(client: TestClient):
    resp = client.post("/runs/00000000-0000-0000-0000-000000000000/orchestrate")
    assert resp.status_code == 400


# --- Full lifecycle ---


def test_full_lifecycle(client: TestClient):
    # Create
    create_resp = client.post(
        "/runs",
        json={
            "description": "end to end",
            "subtasks": [{"description": "step 1"}],
        },
    )
    run_id = create_resp.json()["run_id"]

    # Execute
    exec_resp = client.post(f"/runs/{run_id}/execute")
    assert exec_resp.json()["status"] == "completed"

    # Review
    review_resp = client.post(f"/runs/{run_id}/review")
    assert review_resp.status_code == 200

    # Inspect final state
    run_resp = client.get(f"/runs/{run_id}")
    data = run_resp.json()
    assert len(data["executions"]) == 2  # root + 1 subtask
    assert len(data["reviews"]) == 1
