from pathlib import Path
from uuid import uuid4

import yaml
from httpx import ASGITransport, AsyncClient


def _create_project(tmp_path: Path) -> Path:
    workbench = {
        "schema_version": 1,
        "project": {"id": "test-health", "name": "Health Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    mod_dir = tmp_path / "modules" / "test-mod"
    mod_dir.mkdir(parents=True)
    module = {"uuid": str(uuid4()), "name": "test-mod", "type": "exec.shell"}
    (mod_dir / "module.yaml").write_text(yaml.dump(module))
    return tmp_path


async def test_health_minimal_no_project():
    """Health without project_root returns minimal status."""
    from vos_workbench.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["booted"] is False


async def test_health_with_project(tmp_path):
    """Health with project_root returns full system status."""
    from vos_workbench.api.app import create_app

    project_root = _create_project(tmp_path)
    app = create_app(project_root=project_root, db_url=f"sqlite:///{tmp_path / 'health.db'}")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        data = body["data"]
        assert data["system_status"] == "ok"
        assert data["booted"] is True
        assert data["module_count"] == 1
        assert data["failed_count"] == 0
        assert len(data["modules"]) == 1
        assert data["modules"][0]["name"] == "test-mod"
        assert data["modules"][0]["status"] == "enabled"


async def test_health_response_format(tmp_path):
    from vos_workbench.api.app import create_app

    project_root = _create_project(tmp_path)
    app = create_app(project_root=project_root, db_url=f"sqlite:///{tmp_path / 'health.db'}")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        body = response.json()
        assert "request_id" in body["meta"]
        assert "timestamp" in body["meta"]


async def test_livez_always_200():
    """livez returns 200 even without a runtime."""
    from vos_workbench.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/livez")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


async def test_livez_with_runtime(tmp_path):
    """livez still returns 200 with a runtime loaded."""
    from vos_workbench.api.app import create_app

    project_root = _create_project(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'livez.db'}"
    app = create_app(project_root=project_root, db_url=db_url)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/livez")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


async def test_readyz_503_without_runtime():
    """readyz returns 503 when no runtime is loaded."""
    from vos_workbench.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/readyz")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert body["booted"] is False


async def test_readyz_200_with_healthy_runtime(tmp_path):
    """readyz returns 200 when runtime is booted and healthy."""
    from vos_workbench.api.app import create_app

    project_root = _create_project(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'readyz.db'}"
    app = create_app(project_root=project_root, db_url=db_url)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/readyz")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["booted"] is True
        assert body["startup_plan_complete"] is True
        assert body["db_reachable"] is True
        assert body["failed_modules"] == []


async def test_readyz_503_with_failed_modules(tmp_path):
    """readyz returns 503 when hard dependencies are unsatisfied."""
    from vos_workbench.api.app import create_app

    workbench = {
        "schema_version": 1,
        "project": {"id": "test-readyz", "name": "Readyz Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))
    mod_dir = tmp_path / "modules" / "broken-mod"
    mod_dir.mkdir(parents=True)
    module = {
        "uuid": str(uuid4()),
        "name": "broken-mod",
        "type": "exec.shell",
        "wiring": {
            "depends_on": [{"ref": "module://nonexistent", "kind": "hard"}],
        },
    }
    (mod_dir / "module.yaml").write_text(yaml.dump(module))
    db_url = f"sqlite:///{tmp_path / 'readyz-fail.db'}"
    app = create_app(project_root=tmp_path, db_url=db_url)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/readyz")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "not_ready"
        assert "broken-mod" in body["failed_modules"]


async def test_readyz_soft_degradation_does_not_affect_status(tmp_path):
    """Modules with missing soft dependencies do NOT cause 503."""
    from vos_workbench.api.app import create_app

    workbench = {
        "schema_version": 1,
        "project": {"id": "test-soft", "name": "Soft Dep Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))
    mod_dir = tmp_path / "modules" / "soft-mod"
    mod_dir.mkdir(parents=True)
    module = {
        "uuid": str(uuid4()),
        "name": "soft-mod",
        "type": "exec.shell",
        "wiring": {
            "depends_on": [{"ref": "module://optional-thing", "kind": "soft"}],
        },
    }
    (mod_dir / "module.yaml").write_text(yaml.dump(module))
    db_url = f"sqlite:///{tmp_path / 'soft.db'}"
    app = create_app(project_root=tmp_path, db_url=db_url)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/readyz")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["failed_modules"] == []
