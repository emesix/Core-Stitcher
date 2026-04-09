"""Tests for SwitchcraftCollector — collector with mocked MCP gateway.

Verifies the collector calls the right MCP tools, handles errors gracefully,
and produces the correct Observation stream.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

from stitch.switchcraft.collector import SwitchcraftCollector

FIXTURE = Path(__file__).parent.parent / "fixtures" / "switchcraft_onti_backend.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _mock_call_tool(fixture: dict) -> AsyncMock:
    """Create an AsyncMock for McpGatewayClient.call_tool that returns fixture data."""

    async def call_tool(tool_name: str, arguments: dict | None = None, **kwargs):
        if tool_name == "switchcraft-device-status":
            return fixture["device_status"]
        if tool_name == "switchcraft-get-ports":
            return fixture["get_ports"]
        if tool_name == "switchcraft-get-vlans":
            return fixture["get_vlans"]
        return None

    mock = AsyncMock(side_effect=call_tool)
    return mock


async def test_collector_produces_observations():
    fixture = _load_fixture()
    collector = SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
        device_name="ONTI-BE",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

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
    collector._gw.call_tool = _mock_call_tool(fixture)

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
    collector._gw.call_tool = _mock_call_tool(fixture)

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
    collector._gw.call_tool = _mock_call_tool(fixture)

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

    async def failing_call_tool(tool_name: str, arguments=None, **kwargs):
        return None

    collector._gw.call_tool = AsyncMock(side_effect=failing_call_tool)

    obs = await collector.collect()

    assert obs == []


async def test_collector_all_observations_are_mcp_live():
    """All observations should have source=mcp_live and adapter=switchcraft."""
    fixture = _load_fixture()
    collector = SwitchcraftCollector(
        device_slug="onti-be",
        mcp_device_id="onti-backend",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    assert all(o.source == "mcp_live" for o in obs)
    assert all(o.adapter == "switchcraft" for o in obs)
