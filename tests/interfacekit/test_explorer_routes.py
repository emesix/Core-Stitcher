"""Tests for Explorer HTTP routes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stitch.apps.explorer.workflow import ExplorerWorkflow
from stitch.interfacekit.explorer_routes import create_explorer_router


@pytest.fixture()
def topology_file(tmp_path: Path) -> Path:
    data = {
        "meta": {"version": "1.0", "name": "test-topology"},
        "devices": {
            "sw1": {
                "id": "sw1",
                "name": "SW1",
                "type": "switch",
                "ports": {
                    "e1": {
                        "type": "sfp+",
                        "vlans": {"mode": "trunk", "native": 1, "tagged": [25, 254]},
                    },
                    "e2": {"type": "sfp+"},
                },
            },
            "fw1": {
                "id": "fw1",
                "name": "FW1",
                "type": "firewall",
                "ports": {
                    "ix1": {
                        "type": "sfp+",
                        "vlans": {"mode": "trunk", "native": 1, "tagged": [25, 254]},
                    },
                },
            },
        },
        "links": [
            {
                "id": "link-sw1-fw1",
                "type": "physical_cable",
                "endpoints": [
                    {"device": "sw1", "port": "e1"},
                    {"device": "fw1", "port": "ix1"},
                ],
            },
        ],
        "vlans": {},
    }
    path = tmp_path / "topology.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture()
def client(topology_file: Path) -> TestClient:
    workflow = ExplorerWorkflow(topology_file)
    router = create_explorer_router(workflow)
    app = FastAPI()
    app.include_router(router, prefix="/explorer")
    return TestClient(app)


def test_get_topology(client: TestClient):
    resp = client.get("/explorer/topology")
    assert resp.status_code == 200
    data = resp.json()
    assert "sw1" in data["devices"]
    assert "fw1" in data["devices"]


def test_list_devices(client: TestClient):
    resp = client.get("/explorer/devices")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    by_id = {d["id"]: d for d in data}
    assert "sw1" in by_id
    assert by_id["sw1"]["type"] == "switch"
    assert by_id["sw1"]["port_count"] == 2


def test_get_device(client: TestClient):
    resp = client.get("/explorer/devices/sw1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "SW1"
    assert "e1" in data["ports"]


def test_get_device_not_found(client: TestClient):
    resp = client.get("/explorer/devices/nonexistent")
    assert resp.status_code == 404


def test_get_neighbors(client: TestClient):
    resp = client.get("/explorer/devices/sw1/neighbors")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["device"] == "fw1"


def test_get_neighbors_not_found(client: TestClient):
    resp = client.get("/explorer/devices/nonexistent/neighbors")
    assert resp.status_code == 404


def test_get_vlan_ports(client: TestClient):
    resp = client.get("/explorer/vlans/25")
    assert resp.status_code == 200
    data = resp.json()
    devices = {e["device"] for e in data}
    assert devices == {"sw1", "fw1"}


def test_get_diagnostics(client: TestClient):
    resp = client.get("/explorer/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_devices"] == 2
    assert data["total_links"] == 1
    assert len(data["dangling_ports"]) == 1


def test_trace(client: TestClient):
    resp = client.post("/explorer/trace", json={"vlan": 25, "source": "sw1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"


def test_impact(client: TestClient):
    resp = client.post(
        "/explorer/impact",
        json={"action": "remove_link", "device": "sw1", "parameters": {"link_id": "link-sw1-fw1"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["safe_to_apply"] is False


def test_ui_returns_html(client: TestClient):
    resp = client.get("/explorer/ui")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "VOS Explorer" in resp.text
    assert "/explorer" in resp.text
