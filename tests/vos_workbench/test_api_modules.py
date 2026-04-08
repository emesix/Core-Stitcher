from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from httpx import ASGITransport, AsyncClient


def _create_project(tmp_path: Path) -> Path:
    workbench = {
        "schema_version": 1,
        "project": {"id": "test-project", "name": "Test Project"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    mod_dir = tmp_path / "modules" / "exec-shell"
    mod_dir.mkdir(parents=True)
    module = {
        "uuid": str(uuid4()),
        "name": "exec-shell",
        "type": "exec.shell",
        "config": {"command": "echo hello"},
    }
    (mod_dir / "module.yaml").write_text(yaml.dump(module))

    return tmp_path


@pytest.fixture
def project_path(tmp_path):
    return _create_project(tmp_path)


@pytest.fixture
def app(project_path):
    from vos_workbench.api.app import create_app

    return create_app(project_root=project_path, db_url="sqlite:///:memory:")


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_get_project(client):
    response = await client.get("/api/v1/project")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == "test-project"
    assert body["data"]["name"] == "Test Project"


async def test_list_modules(client):
    response = await client.get("/api/v1/modules")
    assert response.status_code == 200
    body = response.json()
    modules = body["data"]
    assert len(modules) == 1
    assert modules[0]["name"] == "exec-shell"


async def test_get_module_by_uuid(client):
    response = await client.get("/api/v1/modules")
    modules = response.json()["data"]
    module_uuid = modules[0]["uuid"]

    response = await client.get(f"/api/v1/modules/{module_uuid}")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["name"] == "exec-shell"


async def test_get_module_not_found(client):
    fake_uuid = str(uuid4())
    response = await client.get(f"/api/v1/modules/{fake_uuid}")
    assert response.status_code == 404


async def test_get_config_tree(client):
    response = await client.get("/api/v1/tree/config")
    assert response.status_code == 200
    body = response.json()
    assert "modules" in body["data"]
