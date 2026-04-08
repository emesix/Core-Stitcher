"""Integration test: boot the full stack from a project directory
and verify the system is healthy via the API."""

from pathlib import Path
from uuid import uuid4

import yaml
from httpx import ASGITransport, AsyncClient

from vos_workbench.events.models import VosEvent


def _create_full_project(tmp_path: Path) -> Path:
    workbench = {
        "schema_version": 1,
        "project": {"id": "vos-integration", "name": "Integration Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    _write_module(tmp_path, "policy-main", "core.policy")
    _write_module(tmp_path, "memory-main", "memory.file")
    _write_module(
        tmp_path,
        "router-main",
        "core.router",
        depends=[
            {"ref": "module://policy-main", "kind": "hard"},
            {"ref": "module://memory-main", "kind": "soft"},
        ],
    )

    return tmp_path


def _write_module(
    root: Path,
    name: str,
    type_: str,
    depends: list | None = None,
) -> None:
    mod_dir = root / "modules" / name
    mod_dir.mkdir(parents=True)
    module: dict = {
        "uuid": str(uuid4()),
        "name": name,
        "type": type_,
    }
    if depends:
        module["wiring"] = {"depends_on": depends}
    (mod_dir / "module.yaml").write_text(yaml.dump(module))


async def test_full_boot_to_health(tmp_path):
    from vos_workbench.api.app import create_app

    project_root = _create_full_project(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'integration.db'}"
    app = create_app(project_root=project_root, db_url=db_url)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Health check
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        health = resp.json()["data"]
        assert health["system_status"] == "ok"
        assert health["booted"] is True
        assert health["module_count"] == 3

        # Project info
        resp = await client.get("/api/v1/project")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == "vos-integration"

        # Module list
        resp = await client.get("/api/v1/modules")
        assert resp.status_code == 200
        modules = resp.json()["data"]
        assert len(modules) == 3
        names = {m["name"] for m in modules}
        assert names == {"policy-main", "memory-main", "router-main"}

        # Config tree
        resp = await client.get("/api/v1/tree/config")
        assert resp.status_code == 200
        assert len(resp.json()["data"]["modules"]) == 3

        # Publish an event and query it
        runtime = app.state.runtime
        await runtime.event_bus.publish(
            VosEvent(
                type="system.booted",
                source="module://name/router-main",
                project_id="vos-integration",
            )
        )

        resp = await client.get("/api/v1/events")
        assert resp.status_code == 200
        body = resp.json()
        assert "meta" in body
        types = [e["type"] for e in body["data"]]
        assert "system.booted" in types
