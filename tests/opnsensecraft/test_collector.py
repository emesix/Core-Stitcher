"""Tests for OpnsensecraftCollector with mocked MCP gateway."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

from stitch.opnsensecraft.collector import OpnsensecraftCollector

FIXTURE = Path(__file__).parent.parent / "fixtures" / "opnsense_interfaces.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _mock_call_tool(fixture: dict) -> AsyncMock:
    async def call_tool(tool_name: str, arguments: dict | None = None, **kwargs):
        if tool_name == "opnsense-get-interfaces":
            return fixture
        return None

    return AsyncMock(side_effect=call_tool)


async def test_collector_produces_observations():
    fixture = _load_fixture()
    collector = OpnsensecraftCollector(
        device_slug="opnsense",
        device_name="OPNsense",
        management_ip="192.168.254.1",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    assert len(obs) > 0
    devices = {o.device for o in obs}
    assert devices == {"opnsense"}


async def test_collector_has_device_identity():
    fixture = _load_fixture()
    collector = OpnsensecraftCollector(
        device_slug="opnsense",
        device_name="OPNsense",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    type_obs = [o for o in obs if o.field == "type" and o.port is None]
    assert type_obs[0].value == "firewall"


async def test_collector_has_port_observations():
    fixture = _load_fixture()
    collector = OpnsensecraftCollector(device_slug="opnsense")
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    ports = {o.port for o in obs if o.port is not None}
    assert "ix1" in ports
    assert "bridge0" in ports


async def test_collector_handles_mcp_error():
    collector = OpnsensecraftCollector(device_slug="dead")

    async def failing_call_tool(tool_name: str, arguments=None, **kwargs):
        return None

    collector._gw.call_tool = AsyncMock(side_effect=failing_call_tool)

    obs = await collector.collect()

    # Should still have device identity obs (those don't need MCP)
    type_obs = [o for o in obs if o.field == "type" and o.port is None]
    assert type_obs[0].value == "firewall"
    # But no interface observations
    port_obs = [o for o in obs if o.port is not None]
    assert len(port_obs) == 0
