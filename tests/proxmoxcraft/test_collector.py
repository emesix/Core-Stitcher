"""Tests for ProxmoxcraftCollector with mocked MCP gateway."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

from stitch.proxmoxcraft.collector import ProxmoxcraftCollector

FIXTURE = Path(__file__).parent.parent / "fixtures" / "proxmox_pve_hx310_db.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _mock_call_tool(fixture: dict) -> AsyncMock:
    async def call_tool(tool_name: str, arguments: dict | None = None, **kwargs):
        if tool_name == "proxmox-proxmox-node-status":
            return fixture["node_status"]
        if tool_name == "proxmox-proxmox-list-bridges":
            return fixture["bridges"]
        return None

    return AsyncMock(side_effect=call_tool)


async def test_collector_produces_observations():
    fixture = _load_fixture()
    collector = ProxmoxcraftCollector(
        device_slug="pve-hx310-db",
        node_name="pve-hx310-db",
        device_name="PVE-HX310-DB",
        management_ip="192.168.254.20",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    assert len(obs) > 0
    devices = {o.device for o in obs}
    assert devices == {"pve-hx310-db"}


async def test_collector_has_device_identity():
    fixture = _load_fixture()
    collector = ProxmoxcraftCollector(
        device_slug="pve-hx310-db",
        node_name="pve-hx310-db",
        device_name="PVE-HX310-DB",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    type_obs = [o for o in obs if o.field == "type" and o.port is None]
    assert type_obs[0].value == "proxmox"

    name_obs = [o for o in obs if o.field == "name"]
    assert name_obs[0].value == "PVE-HX310-DB"


async def test_collector_has_bridge_observations():
    fixture = _load_fixture()
    collector = ProxmoxcraftCollector(
        device_slug="pve-hx310-db",
        node_name="pve-hx310-db",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    ports = {o.port for o in obs if o.port is not None}
    assert "vmbr0" in ports

    bridge_members = [o for o in obs if o.port == "vmbr0" and o.field == "bridge_members"]
    assert len(bridge_members) == 1
    assert bridge_members[0].value == ["enp2s0"]


async def test_collector_handles_mcp_error():
    collector = ProxmoxcraftCollector(
        device_slug="dead",
        node_name="dead",
    )

    async def failing_call_tool(tool_name: str, arguments=None, **kwargs):
        return None

    collector._gw.call_tool = AsyncMock(side_effect=failing_call_tool)

    obs = await collector.collect()

    # No observations when MCP is down (node identity requires node-status)
    assert len(obs) == 0


async def test_collector_all_observations_source():
    fixture = _load_fixture()
    collector = ProxmoxcraftCollector(
        device_slug="pve-hx310-db",
        node_name="pve-hx310-db",
    )
    collector._gw.call_tool = _mock_call_tool(fixture)

    obs = await collector.collect()

    assert all(o.source == "mcp_live" for o in obs)
    assert all(o.adapter == "proxmoxcraft" for o in obs)
