from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from stitch.apps.lite.app import create_app
from stitch.core.queries import QueryResult


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_index_page(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "Stitch" in resp.text


@pytest.mark.asyncio
async def test_static_css(client):
    resp = await client.get("/static/style.css")
    assert resp.status_code == 200
    assert "var(--bg)" in resp.text


# --- Device pages ---

MOCK_DEVICES = [
    {
        "id": "dev_01",
        "name": "sw-core-01",
        "type": "SWITCH",
        "model": "USW-Pro-48",
        "management_ip": "192.168.254.2",
    },
    {
        "id": "dev_02",
        "name": "fw-main",
        "type": "FIREWALL",
        "model": "OPNsense",
        "management_ip": "192.168.254.1",
    },
]


@pytest.fixture
def mock_app():
    """App with a mocked SDK client."""
    app = create_app()
    mock_client = MagicMock()
    mock_client.query = AsyncMock()
    mock_client.command = AsyncMock()
    app.state.client = mock_client
    return app


@pytest.fixture
async def mock_client(mock_app):
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_device_list_page(mock_app, mock_client):
    mock_app.state.client.query.return_value = QueryResult(items=MOCK_DEVICES, total=2)
    resp = await mock_client.get("/devices")
    assert resp.status_code == 200
    assert "sw-core-01" in resp.text
    assert "fw-main" in resp.text


@pytest.mark.asyncio
async def test_device_list_empty(mock_app, mock_client):
    mock_app.state.client.query.return_value = QueryResult(items=[], total=0)
    resp = await mock_client.get("/devices")
    assert resp.status_code == 200
    assert "No devices found." in resp.text


@pytest.mark.asyncio
async def test_device_detail_page(mock_app, mock_client):
    device = {
        **MOCK_DEVICES[0],
        "ports": [{"name": "sfp-0", "type": "SFP_PLUS", "speed": "10G"}],
    }
    mock_app.state.client.query.side_effect = [
        QueryResult(items=[device], total=1),
        QueryResult(
            items=[{"device": "fw-main", "local_port": "sfp-0", "remote_port": "igb0"}],
            total=1,
        ),
    ]
    resp = await mock_client.get("/devices/dev_01")
    assert resp.status_code == 200
    assert "sw-core-01" in resp.text
    assert "sfp-0" in resp.text
    assert "fw-main" in resp.text


# --- Preflight pages ---


@pytest.mark.asyncio
async def test_preflight_page(mock_app, mock_client):
    resp = await mock_client.get("/preflight")
    assert resp.status_code == 200
    assert "Run Preflight" in resp.text
    assert 'name="scope"' in resp.text


@pytest.mark.asyncio
async def test_preflight_run(mock_app, mock_client):
    mock_app.state.client.command.return_value = {
        "summary": {"total": 5, "pass": 3, "warning": 1, "fail": 1},
        "results": [
            {
                "link": "link-01",
                "status": "fail",
                "checks": [
                    {"check": "speed_match", "flag": "error", "message": "Speed mismatch"},
                ],
            },
        ],
    }
    resp = await mock_client.post("/preflight/run", data={"scope": ""})
    assert resp.status_code == 200
    assert "Preflight Result" in resp.text
    mock_app.state.client.command.assert_called_once_with(
        "preflight",
        "run",
        params=None,
    )


@pytest.mark.asyncio
async def test_preflight_run_with_scope(mock_app, mock_client):
    mock_app.state.client.command.return_value = {
        "summary": {"total": 2, "pass": 2, "warning": 0, "fail": 0},
        "results": [],
    }
    resp = await mock_client.post("/preflight/run", data={"scope": "sw-core-01"})
    assert resp.status_code == 200
    mock_app.state.client.command.assert_called_once_with(
        "preflight",
        "run",
        params={"scope": "sw-core-01"},
    )


# --- Run pages ---

MOCK_RUNS = [
    {"id": "run_01", "status": "completed", "description": "Full preflight"},
    {"id": "run_02", "status": "running", "description": "Partial check"},
]


@pytest.mark.asyncio
async def test_run_list_page(mock_app, mock_client):
    mock_app.state.client.query.return_value = QueryResult(items=MOCK_RUNS, total=2)
    resp = await mock_client.get("/runs")
    assert resp.status_code == 200
    assert "run_01" in resp.text
    assert "run_02" in resp.text
    assert "Full preflight" in resp.text


@pytest.mark.asyncio
async def test_run_list_empty(mock_app, mock_client):
    mock_app.state.client.query.return_value = QueryResult(items=[], total=0)
    resp = await mock_client.get("/runs")
    assert resp.status_code == 200
    assert "No runs found." in resp.text


@pytest.mark.asyncio
async def test_run_detail_page(mock_app, mock_client):
    run = {
        "id": "run_01",
        "status": "completed",
        "description": "Full preflight",
        "created_at": "2026-04-09T12:00:00",
        "tasks": [
            {"id": "t1", "description": "Check links", "status": "completed", "executor": "local"},
        ],
    }
    mock_app.state.client.query.return_value = QueryResult(items=[run], total=1)
    resp = await mock_client.get("/runs/run_01")
    assert resp.status_code == 200
    assert "run_01" in resp.text
    assert "Check links" in resp.text


# --- Review pages ---


# Reviews removed from first product slice — routes hidden until backend supports them


# --- Topology page ---


@pytest.mark.asyncio
async def test_topology_page(mock_app, mock_client):
    topo = {
        "name": "lab-topo",
        "device_count": 4,
        "link_count": 8,
        "vlan_count": 3,
    }
    mock_app.state.client.query.return_value = QueryResult(items=[topo], total=1)
    resp = await mock_client.get("/topology")
    assert resp.status_code == 200
    assert "Topology" in resp.text
    assert "4" in resp.text  # device_count
    assert "8" in resp.text  # link_count


@pytest.mark.asyncio
async def test_topology_page_empty(mock_app, mock_client):
    mock_app.state.client.query.return_value = QueryResult(items=[], total=0)
    resp = await mock_client.get("/topology")
    assert resp.status_code == 200
    assert "No topology data available." in resp.text


# --- System page ---


@pytest.mark.asyncio
async def test_system_page(mock_app, mock_client):
    resp = await mock_client.get("/system")
    assert resp.status_code == 200
    assert "System" in resp.text
    assert "Stitch Lite" in resp.text
