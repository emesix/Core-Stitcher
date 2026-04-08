"""Tests for SwitchcraftCollector — collector with mocked MCP gateway.

Verifies the collector calls the right MCP tools, handles errors gracefully,
and produces the correct Observation stream.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from vos.switchcraft.collector import SwitchcraftCollector

FIXTURE = Path(__file__).parent.parent / "fixtures" / "switchcraft_onti_backend.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _make_mcp_response(data: dict) -> dict:
    """Wrap data in the MCP JSON-RPC response envelope."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [{"type": "text", "text": json.dumps(data)}],
        },
    }


def _mock_post(fixture: dict):
    """Create an AsyncMock for httpx.AsyncClient.post that returns fixture data."""

    async def mock_post(url: str, *, json: dict, **kwargs):
        tool_name = json["params"]["name"]
        if tool_name == "switchcraft-device-status":
            data = fixture["device_status"]
        elif tool_name == "switchcraft-get-ports":
            data = fixture["get_ports"]
        elif tool_name == "switchcraft-get-vlans":
            data = fixture["get_vlans"]
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        resp = httpx.Response(
            200,
            json=_make_mcp_response(data),
            request=httpx.Request("POST", url),
        )
        return resp

    return mock_post


async def test_collector_produces_observations():
    fixture = _load_fixture()
    collector = SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
        device_name="ONTI-BE",
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        client.post = _mock_post(fixture)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client

        obs = await collector.collect()

    assert len(obs) > 0
    devices = {o.device for o in obs}
    assert devices == {"onti-be"}


async def test_collector_has_port_observations():
    fixture = _load_fixture()
    collector = SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
        device_name="ONTI-BE",
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        client.post = _mock_post(fixture)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client

        obs = await collector.collect()

    ports = {o.port for o in obs if o.port is not None}
    assert "eth1" in ports
    assert "eth8" in ports


async def test_collector_has_vlan_observations():
    fixture = _load_fixture()
    collector = SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
        device_name="ONTI-BE",
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        client.post = _mock_post(fixture)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client

        obs = await collector.collect()

    vlan_obs = [o for o in obs if o.field == "vlans"]
    assert len(vlan_obs) == 8  # one per port


async def test_collector_has_device_level_observations():
    fixture = _load_fixture()
    collector = SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
        device_name="ONTI-BE",
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        client.post = _mock_post(fixture)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client

        obs = await collector.collect()

    type_obs = [o for o in obs if o.field == "type" and o.port is None]
    assert len(type_obs) == 1
    assert type_obs[0].value == "switch"

    name_obs = [o for o in obs if o.field == "name"]
    assert name_obs[0].value == "ONTI-BE"


async def test_collector_handles_mcp_error():
    """If MCP tools fail, collector returns empty list gracefully."""
    collector = SwitchcraftCollector(
        device_slug="dead-switch",
        mcp_device_id="nonexistent",
    )

    async def failing_post(url: str, *, json: dict, **kwargs):
        raise httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        client.post = failing_post
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client

        obs = await collector.collect()

    assert obs == []


async def test_collector_all_observations_are_mcp_live():
    """All observations should have source=mcp_live and adapter=switchcraft."""
    fixture = _load_fixture()
    collector = SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        client = AsyncMock()
        client.post = _mock_post(fixture)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = client

        obs = await collector.collect()

    assert all(o.source == "mcp_live" for o in obs)
    assert all(o.adapter == "switchcraft" for o in obs)
