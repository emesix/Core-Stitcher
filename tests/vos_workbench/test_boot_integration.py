"""Integration test: runtime boot → module start → router mount → HTTP.

Proves the full host-side composition path without manual wiring:
1. Runtime loads config and discovers module types
2. boot_modules() instantiates and starts interfacekit
3. interfacekit resolves PreflightWorkflowProtocol via CapabilityResolver
4. Router is built and exposed via module.router
5. collect_routers() discovers it
6. Mounted router serves POST /verify → VerificationReport
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vos.apps.explorer.workflow import ExplorerWorkflow
from vos.apps.preflight import PreflightWorkflow
from vos.modelkit.enums import ObservationSource
from vos.modelkit.observation import Observation
from vos_workbench.runtime.runtime import Runtime

TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"


class FakeCollector:
    async def collect(self) -> list[Observation]:
        obs: list[Observation] = []
        devices = [("onti-be", "switch"), ("opnsense", "firewall"), ("pve-hx310-db", "proxmox")]
        for device, dtype in devices:
            obs.append(
                Observation(
                    device=device,
                    field="type",
                    value=dtype,
                    source=ObservationSource.MCP_LIVE,
                    adapter="fake",
                )
            )
        ports = [
            ("onti-be", "eth1"),
            ("onti-be", "eth2"),
            ("opnsense", "ix1"),
            ("pve-hx310-db", "enp2s0"),
            ("pve-hx310-db", "vmbr0"),
        ]
        for device, port in ports:
            obs.append(
                Observation(
                    device=device,
                    port=port,
                    field="type",
                    value="sfp+",
                    source=ObservationSource.MCP_LIVE,
                    adapter="fake",
                )
            )
        return obs


def _create_project(tmp_path: Path) -> Path:
    """Create a minimal project with interfacekit module config."""
    workbench = {
        "schema_version": 1,
        "project": {"id": "preflight-integration", "name": "Preflight Integration Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    # interfacekit module
    ikit_dir = tmp_path / "modules" / "interfacekit-1"
    ikit_dir.mkdir(parents=True)
    ikit_config = {
        "uuid": str(uuid4()),
        "name": "interfacekit-1",
        "type": "integration.interfacekit",
        "config": {"api_prefix": "/api/v1"},
    }
    (ikit_dir / "module.yaml").write_text(yaml.dump(ikit_config))

    return tmp_path


async def test_boot_modules_starts_interfacekit(tmp_path: Path):
    """boot_modules() instantiates and starts interfacekit from config."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    # Register the preflight workflow as a capability BEFORE booting
    # (in production, the app shell would register itself during bootstrap)
    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")

    results = await rt.boot_modules()

    assert results["interfacekit-1"] == "started"
    instance = rt.get_instance("interfacekit-1")
    assert instance is not None
    assert hasattr(instance, "router")
    assert instance.router is not None


async def test_collect_routers_finds_interfacekit(tmp_path: Path):
    """collect_routers() discovers the router from started interfacekit."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")

    await rt.boot_modules()
    routers = rt.collect_routers()

    assert len(routers) == 1


async def test_full_boot_to_http(tmp_path: Path):
    """Full path: runtime boot → module start → router mount → POST /verify → report."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    # Register workflow capability
    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")

    # Boot modules — interfacekit resolves workflow via resolver
    await rt.boot_modules()

    # Collect and mount routers — no manual wiring
    app = FastAPI()
    for router in rt.collect_routers():
        app.include_router(router)

    # Hit the endpoint
    client = TestClient(app)
    resp = client.post("/verify")

    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "summary" in data
    assert data["summary"]["total"] == 3
    assert data["summary"]["pass"] == 3


async def test_full_boot_to_impact(tmp_path: Path):
    """Runtime boot → interfacekit → POST /impact → ImpactResult."""
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

    client = TestClient(app)
    resp = client.post(
        "/impact",
        json={
            "action": "remove_link",
            "device": "onti-be",
            "parameters": {"link_id": "phys-opnsense-ix1-to-onti-be-eth1"},
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["proposed_change"]["action"] == "remove_link"
    assert len(data["impact"]) > 0
    assert data["risk"] in ("high", "medium", "low")


async def test_shutdown_stops_modules(tmp_path: Path):
    """shutdown_modules() stops all started modules."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")
    await rt.boot_modules()

    assert rt.get_instance("interfacekit-1") is not None

    await rt.shutdown_modules()

    assert rt.get_instance("interfacekit-1") is None
    assert rt.collect_routers() == []


async def test_explorer_routes_available_when_registered(tmp_path: Path):
    """Explorer routes are mounted when ExplorerWorkflow is registered as a capability."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    # Register both workflows
    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")

    explorer = ExplorerWorkflow(TOPO_FIXTURE)
    rt.register_capability(explorer, instance_id="explorer-workflow", name="explorer")

    await rt.boot_modules()

    app = FastAPI()
    for router in rt.collect_routers():
        app.include_router(router)

    client = TestClient(app)

    # Explorer endpoints work
    resp = client.get("/explorer/devices")
    assert resp.status_code == 200
    assert len(resp.json()) > 0

    resp = client.get("/explorer/diagnostics")
    assert resp.status_code == 200
    assert "total_devices" in resp.json()

    # Preflight endpoints still work
    resp = client.post("/verify")
    assert resp.status_code == 200


async def test_preflight_works_without_explorer(tmp_path: Path):
    """Preflight routes work even when Explorer is not registered."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    # Only register preflight — no explorer
    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")

    await rt.boot_modules()

    app = FastAPI()
    for router in rt.collect_routers():
        app.include_router(router)

    client = TestClient(app)

    # Preflight works
    resp = client.post("/verify")
    assert resp.status_code == 200

    # Explorer routes are not mounted
    resp = client.get("/explorer/devices")
    assert resp.status_code == 404


async def test_explorer_ui_served_through_spine(tmp_path: Path):
    """Explorer visual layer is reachable through the normal spine boot path."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")

    explorer = ExplorerWorkflow(TOPO_FIXTURE)
    rt.register_capability(explorer, instance_id="explorer-workflow", name="explorer")

    await rt.boot_modules()

    app = FastAPI()
    for router in rt.collect_routers():
        app.include_router(router)

    client = TestClient(app)
    resp = client.get("/explorer/ui")
    assert resp.status_code == 200
    assert "VOS Explorer" in resp.text


async def test_explorer_health_reports_status(tmp_path: Path):
    """Health endpoint reflects whether Explorer is wired."""
    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[FakeCollector()])
    rt.register_capability(workflow, instance_id="preflight-workflow", name="preflight")

    explorer = ExplorerWorkflow(TOPO_FIXTURE)
    rt.register_capability(explorer, instance_id="explorer-workflow", name="explorer")

    await rt.boot_modules()

    instance = rt.get_instance("interfacekit-1")
    health = await instance.health()
    assert health["status"] == "ok"
    assert health["explorer"] is True


async def test_disabled_module_not_started(tmp_path: Path):
    """Disabled modules should not be started."""
    workbench = {
        "schema_version": 1,
        "project": {"id": "test", "name": "Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    mod_dir = tmp_path / "modules" / "interfacekit-disabled"
    mod_dir.mkdir(parents=True)
    config = {
        "uuid": str(uuid4()),
        "name": "interfacekit-disabled",
        "type": "integration.interfacekit",
        "enabled": False,
    }
    (mod_dir / "module.yaml").write_text(yaml.dump(config))

    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root=tmp_path, db_url=f"sqlite:///{db_path}")
    rt.load()

    results = await rt.boot_modules()
    assert results["interfacekit-disabled"] == "disabled"
    assert rt.get_instance("interfacekit-disabled") is None
