"""Tests for ProxmoxcraftCollector with mocked MCP gateway."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import httpx

from vos.proxmoxcraft.collector import ProxmoxcraftCollector

FIXTURE = Path(__file__).parent.parent / "fixtures" / "proxmox_pve_hx310_db.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _make_mcp_response(data: object) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(data)}]},
    }


def _patch_httpx(fixture: dict):
    class PatchedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, *, json: dict, **kwargs):
            tool_name = json["params"]["name"]
            if tool_name == "proxmox-node-status":
                data = fixture["node_status"]
            elif tool_name == "proxmox-list-bridges":
                data = fixture["bridges"]
            else:
                return httpx.Response(404, request=httpx.Request("POST", url))
            return httpx.Response(
                200,
                json=_make_mcp_response(data),
                request=httpx.Request("POST", url),
            )

    return patch("httpx.AsyncClient", PatchedClient)


async def test_collector_produces_observations():
    fixture = _load_fixture()
    collector = ProxmoxcraftCollector(
        device_slug="pve-hx310-db",
        node_name="pve-hx310-db",
        device_name="PVE-HX310-DB",
        management_ip="192.168.254.20",
    )

    with _patch_httpx(fixture):
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

    with _patch_httpx(fixture):
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

    with _patch_httpx(fixture):
        obs = await collector.collect()

    ports = {o.port for o in obs if o.port is not None}
    assert "vmbr0" in ports

    bridge_members = [o for o in obs if o.port == "vmbr0" and o.field == "bridge_members"]
    assert len(bridge_members) == 1
    assert bridge_members[0].value == ["enp2s0"]


async def test_collector_handles_mcp_error():
    class FailingClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, *, json: dict, **kwargs):
            raise httpx.ConnectError("Connection refused")

    with patch("httpx.AsyncClient", FailingClient):
        collector = ProxmoxcraftCollector(
            device_slug="dead",
            node_name="dead",
        )
        obs = await collector.collect()

    # No observations when MCP is down (node identity requires node-status)
    assert len(obs) == 0


async def test_collector_all_observations_source():
    fixture = _load_fixture()
    collector = ProxmoxcraftCollector(
        device_slug="pve-hx310-db",
        node_name="pve-hx310-db",
    )

    with _patch_httpx(fixture):
        obs = await collector.collect()

    assert all(o.source == "mcp_live" for o in obs)
    assert all(o.adapter == "proxmoxcraft" for o in obs)
