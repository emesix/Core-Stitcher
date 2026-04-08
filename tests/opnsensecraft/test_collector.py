"""Tests for OpnsensecraftCollector with mocked MCP gateway."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import httpx

from vos.opnsensecraft.collector import OpnsensecraftCollector

FIXTURE = Path(__file__).parent.parent / "fixtures" / "opnsense_interfaces.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def _make_mcp_response(data: dict) -> dict:
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
            return httpx.Response(
                200,
                json=_make_mcp_response(fixture),
                request=httpx.Request("POST", url),
            )

    return patch("httpx.AsyncClient", PatchedClient)


async def test_collector_produces_observations():
    fixture = _load_fixture()
    collector = OpnsensecraftCollector(
        device_slug="opnsense",
        device_name="OPNsense",
        management_ip="192.168.254.1",
    )

    with _patch_httpx(fixture):
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

    with _patch_httpx(fixture):
        obs = await collector.collect()

    type_obs = [o for o in obs if o.field == "type" and o.port is None]
    assert type_obs[0].value == "firewall"


async def test_collector_has_port_observations():
    fixture = _load_fixture()
    collector = OpnsensecraftCollector(device_slug="opnsense")

    with _patch_httpx(fixture):
        obs = await collector.collect()

    ports = {o.port for o in obs if o.port is not None}
    assert "ix1" in ports
    assert "bridge0" in ports


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
        collector = OpnsensecraftCollector(device_slug="dead")
        obs = await collector.collect()

    # Should still have device identity obs (those don't need MCP)
    type_obs = [o for o in obs if o.field == "type" and o.port is None]
    assert type_obs[0].value == "firewall"
    # But no interface observations
    port_obs = [o for o in obs if o.port is not None]
    assert len(port_obs) == 0
