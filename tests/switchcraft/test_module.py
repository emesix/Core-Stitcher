"""Tests for SwitchcraftModule — verifies the module lifecycle wires up correctly.

Proves that start() constructs a real collector from config, and collect()
produces observations. Also tests workflow-level integration: a real
SwitchcraftModule feeding PreflightWorkflow, not a FakeCollector.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx

from vos.apps.preflight import PreflightWorkflow
from vos.switchcraft import SwitchcraftConfig, SwitchcraftModule

SWITCH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "switchcraft_onti_backend.json"
TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"


def _load_switch_fixture() -> dict:
    return json.loads(SWITCH_FIXTURE.read_text())


def _make_mcp_response(data: dict) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps(data)}]},
    }


def _mock_post(fixture: dict):
    async def mock_post(url: str, *, json: dict, **kwargs):
        tool_name = json["params"]["name"]
        lookup = {
            "switchcraft-device-status": fixture["device_status"],
            "switchcraft-get-ports": fixture["get_ports"],
            "switchcraft-get-vlans": fixture["get_vlans"],
        }
        data = lookup.get(tool_name)
        if data is None:
            return httpx.Response(404, request=httpx.Request("POST", url))
        return httpx.Response(
            200,
            json=_make_mcp_response(data),
            request=httpx.Request("POST", url),
        )

    return mock_post


@dataclass
class FakeModuleContext:
    module_name: str
    module_uuid: str
    publisher: Any
    config: Any
    capabilities: Any


def _make_context(config: SwitchcraftConfig) -> FakeModuleContext:
    return FakeModuleContext(
        module_name="switchcraft-onti-be",
        module_uuid="test-uuid",
        publisher=None,
        config=config,
        capabilities=None,
    )


def _patch_httpx(fixture: dict):
    """Context manager that patches httpx.AsyncClient to return fixture data."""

    class PatchedClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url: str, *, json: dict, **kwargs):
            return await _mock_post(fixture)(url, json=json, **kwargs)

    return patch("httpx.AsyncClient", PatchedClient)


# --- Module lifecycle ---


async def test_start_constructs_collector():
    config = SwitchcraftConfig(
        mcp_device_id="onti-backend",
        device_slug="onti-be",
        device_name="ONTI-BE",
    )
    module = SwitchcraftModule()
    assert module._collector is None

    await module.start(_make_context(config))
    assert module._collector is not None


async def test_stop_clears_collector():
    config = SwitchcraftConfig(
        mcp_device_id="onti-backend",
        device_slug="onti-be",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))
    assert module._collector is not None

    await module.stop()
    assert module._collector is None


async def test_collect_before_start_returns_empty():
    module = SwitchcraftModule()
    obs = await module.collect()
    assert obs == []


async def test_collect_after_start_produces_observations():
    fixture = _load_switch_fixture()
    config = SwitchcraftConfig(
        mcp_device_id="onti-backend",
        device_slug="onti-be",
        device_name="ONTI-BE",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))

    with _patch_httpx(fixture):
        obs = await module.collect()

    assert len(obs) > 0
    assert all(o.device == "onti-be" for o in obs)


async def test_port_type_mapping():
    config = SwitchcraftConfig(
        mcp_device_id="test",
        device_slug="test",
        port_type="ethernet",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))
    assert module._collector is not None
    assert module._collector._port_type.value == "ethernet"


# --- Health checks ---


async def test_health_before_start():
    module = SwitchcraftModule()
    result = await module.health()
    assert result["status"] == "error"
    assert "not started" in result["message"].lower()


async def test_health_reachable():
    fixture = _load_switch_fixture()
    config = SwitchcraftConfig(
        mcp_device_id="onti-backend",
        device_slug="onti-be",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))

    with _patch_httpx(fixture):
        result = await module.health()

    assert result["status"] == "ok"
    assert result["reachable"] is True
    assert result["device_id"] == "onti-backend"
    assert "uptime" in result
    assert "firmware" in result


async def test_health_unreachable():
    unreachable_fixture = {
        "device_status": {
            "device_id": "dead",
            "reachable": False,
            "uptime": None,
            "firmware": None,
            "error": "Device not responding to ping",
        },
        "get_ports": {"device_id": "dead", "ports": []},
        "get_vlans": {"device_id": "dead", "vlans": []},
    }
    config = SwitchcraftConfig(
        mcp_device_id="dead-switch",
        device_slug="dead",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))

    with _patch_httpx(unreachable_fixture):
        result = await module.health()

    assert result["status"] == "degraded"
    assert result["reachable"] is False
    assert "not responding" in result.get("message", "").lower()


async def test_health_gateway_down():
    """If the MCP gateway itself is unreachable, health returns error."""

    def _patch_httpx_error():
        class FailingClient:
            def __init__(self, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def post(self, url: str, *, json: dict, **kwargs):
                raise httpx.ConnectError("Connection refused")

        return patch("httpx.AsyncClient", FailingClient)

    config = SwitchcraftConfig(
        mcp_device_id="any",
        device_slug="any",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))

    with _patch_httpx_error():
        result = await module.health()

    assert result["status"] == "error"


# --- Workflow integration ---


async def test_workflow_with_real_module():
    """PreflightWorkflow using a real SwitchcraftModule, not a FakeCollector."""
    fixture = _load_switch_fixture()
    config = SwitchcraftConfig(
        mcp_device_id="onti-backend",
        device_slug="onti-be",
        device_name="ONTI-BE",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[module])

    with _patch_httpx(fixture):
        report = await workflow.run_verification()

    # Should produce a real VerificationReport
    assert report.summary["total"] == 3
    # onti-be ports are observed, so links involving onti-be should have checks
    assert len(report.results) == 3
    for result in report.results:
        assert len(result.checks) > 0
