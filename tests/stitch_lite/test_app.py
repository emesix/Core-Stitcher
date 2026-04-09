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
