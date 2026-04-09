"""Tests for the aggregated health endpoint — GET /health/modules.

Tests the route helper with canned health data, and an integration test
proving runtime → boot → health aggregation → HTTP response.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stitch.apps.preflight import PreflightWorkflow
from stitch.interfacekit.routes import create_health_router
from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.observation import Observation
from stitch_workbench.runtime.runtime import Runtime

TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"


# --- Route-level tests ---


async def _healthy_modules() -> dict:
    return {
        "status": "ok",
        "modules_total": 2,
        "modules_ok": 2,
        "modules_degraded": 0,
        "modules_error": 0,
        "modules": [
            {"name": "switchcraft-1", "type": "resource.switchcraft", "health": {"status": "ok"}},
            {
                "name": "interfacekit-1",
                "type": "integration.interfacekit",
                "health": {"status": "ok"},
            },
        ],
    }


async def _degraded_modules() -> dict:
    return {
        "status": "degraded",
        "modules_total": 2,
        "modules_ok": 1,
        "modules_degraded": 1,
        "modules_error": 0,
        "modules": [
            {"name": "switchcraft-1", "type": "resource.switchcraft", "health": {"status": "ok"}},
            {
                "name": "switchcraft-2",
                "type": "resource.switchcraft",
                "health": {"status": "degraded", "message": "unreachable"},
            },
        ],
    }


def test_health_route_all_ok():
    router = create_health_router(_healthy_modules)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/health/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["modules_total"] == 2
    assert data["modules_ok"] == 2
    assert len(data["modules"]) == 2


def test_health_route_degraded():
    router = create_health_router(_degraded_modules)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/health/modules")
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["modules_degraded"] == 1


# --- Runtime integration test ---


class FakeCollector:
    async def collect(self) -> list[Observation]:
        return [
            Observation(
                device="x",
                field="type",
                value="switch",
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            ),
        ]


def _create_project(tmp_path: Path) -> Path:
    workbench = {
        "schema_version": 1,
        "project": {"id": "health-test", "name": "Health Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    ikit_dir = tmp_path / "modules" / "interfacekit-1"
    ikit_dir.mkdir(parents=True)
    (ikit_dir / "module.yaml").write_text(
        yaml.dump(
            {
                "uuid": str(uuid4()),
                "name": "interfacekit-1",
                "type": "integration.interfacekit",
                "config": {"api_prefix": "/api/v1"},
            }
        )
    )

    return tmp_path


async def test_runtime_health_aggregation(tmp_path: Path):
    """Runtime aggregates health from started modules via get_module_health()."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")
    await rt.boot_modules()

    health = await rt.get_module_health()

    assert health["status"] == "ok"
    assert health["modules_total"] >= 1
    assert health["modules_ok"] >= 1

    ikit_health = next(m for m in health["modules"] if m["name"] == "interfacekit-1")
    assert ikit_health["type"] == "integration.interfacekit"
    assert ikit_health["health"]["status"] == "ok"


async def test_runtime_health_via_http(tmp_path: Path):
    """Full path: runtime → boot → health aggregation → health router → HTTP."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")
    await rt.boot_modules()

    app = FastAPI()
    for router in rt.collect_routers():
        app.include_router(router)
    app.include_router(create_health_router(rt.get_module_health))

    client = TestClient(app)

    # Health endpoint works
    resp = client.get("/health/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["modules_total"] >= 1

    # Preflight endpoint still works alongside
    resp = client.post("/verify")
    assert resp.status_code == 200
