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
from unittest.mock import AsyncMock

from stitch.apps.preflight import PreflightWorkflow
from stitch.switchcraft import SwitchcraftConfig, SwitchcraftModule

SWITCH_FIXTURE = Path(__file__).parent.parent / "fixtures" / "switchcraft_onti_backend.json"
TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"


def _load_switch_fixture() -> dict:
    return json.loads(SWITCH_FIXTURE.read_text())


def _mock_call_tool(fixture: dict) -> AsyncMock:
    async def call_tool(tool_name: str, arguments: dict | None = None, **kwargs):
        lookup = {
            "switchcraft-device-status": fixture["device_status"],
            "switchcraft-get-ports": fixture["get_ports"],
            "switchcraft-get-vlans": fixture["get_vlans"],
        }
        return lookup.get(tool_name)

    return AsyncMock(side_effect=call_tool)


def _patch_module_gateway(module: SwitchcraftModule, fixture: dict) -> None:
    """Patch the gateway client on a module's collector."""
    if module._collector is not None:
        module._collector._gw.call_tool = _mock_call_tool(fixture)


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
    _patch_module_gateway(module, fixture)

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
    _patch_module_gateway(module, fixture)

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
    _patch_module_gateway(module, unreachable_fixture)

    result = await module.health()

    assert result["status"] == "degraded"
    assert result["reachable"] is False
    assert "not responding" in result.get("message", "").lower()


async def test_health_gateway_down():
    """If the MCP gateway itself is unreachable, health returns error."""
    config = SwitchcraftConfig(
        mcp_device_id="any",
        device_slug="any",
    )
    module = SwitchcraftModule()
    await module.start(_make_context(config))

    async def failing_call_tool(tool_name: str, arguments=None, **kwargs):
        return None

    module._collector._gw.call_tool = AsyncMock(side_effect=failing_call_tool)

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
    _patch_module_gateway(module, fixture)

    workflow = PreflightWorkflow(TOPO_FIXTURE, collectors=[module])

    report = await workflow.run_verification()

    # Should produce a real VerificationReport
    assert report.summary["total"] == 3
    # onti-be ports are observed, so links involving onti-be should have checks
    assert len(report.results) == 3
    for result in report.results:
        assert len(result.checks) > 0
