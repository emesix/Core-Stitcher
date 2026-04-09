"""Tests for InterfacekitModule lifecycle — spine context → resolved workflow → router.

Proves that InterfacekitModule.start() uses the capability resolver to find
PreflightWorkflowProtocol, builds a real router from it, and exposes it via
the .router property. This is the first module to exercise capability resolution.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stitch.apps.preflight import PreflightWorkflow
from stitch.contractkit.workflow import PreflightWorkflowProtocol
from stitch.interfacekit import InterfacekitConfig, InterfacekitModule
from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.observation import Observation

TOPO_FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"


class FakeCollector:
    def __init__(self, observations: list[Observation]) -> None:
        self._observations = observations

    async def collect(self) -> list[Observation]:
        return self._observations


def _minimal_observations() -> list[Observation]:
    obs: list[Observation] = []
    devices = [("onti-be", "switch"), ("opnsense", "firewall"), ("pve-hx310-db", "proxmox")]
    for device, dtype in devices:
        obs.append(
            Observation(
                device=device,
                field="type",
                value=dtype,
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            )
        )
    for device, port in [
        ("onti-be", "eth1"),
        ("onti-be", "eth2"),
        ("opnsense", "ix1"),
        ("pve-hx310-db", "enp2s0"),
        ("pve-hx310-db", "vmbr0"),
    ]:
        obs.append(
            Observation(
                device=device,
                port=port,
                field="type",
                value="sfp+",
                source=ObservationSource.MCP_LIVE,
                adapter="fake",
            )
        )
    return obs


class FakeCapabilityResolver:
    """Minimal resolver that returns a single PreflightWorkflow."""

    def __init__(self, workflow: PreflightWorkflow) -> None:
        self._workflow = workflow

    def resolve_one(self, protocol: type, *, selector: str | None = None) -> Any:
        if protocol is PreflightWorkflowProtocol:
            return self._workflow
        raise LookupError(f"No capability for {protocol}")

    def resolve_all(self, protocol: type) -> list:
        if protocol is PreflightWorkflowProtocol:
            return [self._workflow]
        return []

    def resolve_named(self, protocol: type, instance_id: Any) -> Any:
        raise LookupError(f"No named capability for {protocol}")


@dataclass
class FakeModuleContext:
    module_name: str
    module_uuid: str
    publisher: Any
    config: Any
    capabilities: Any


def _make_context(
    config: InterfacekitConfig,
    workflow: PreflightWorkflow,
) -> FakeModuleContext:
    return FakeModuleContext(
        module_name="interfacekit-1",
        module_uuid="test-uuid",
        publisher=None,
        config=config,
        capabilities=FakeCapabilityResolver(workflow),
    )


# --- Module lifecycle ---


async def test_start_resolves_workflow_and_builds_router():
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[FakeCollector(_minimal_observations())],
    )
    config = InterfacekitConfig()
    module = InterfacekitModule()

    assert module.router is None

    await module.start(_make_context(config, workflow))

    assert module.router is not None


async def test_stop_clears_router():
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[FakeCollector([])],
    )
    module = InterfacekitModule()
    await module.start(_make_context(InterfacekitConfig(), workflow))
    assert module.router is not None

    await module.stop()
    assert module.router is None


async def test_health_before_start():
    module = InterfacekitModule()
    result = await module.health()
    assert result["status"] == "error"


async def test_health_after_start():
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[FakeCollector([])],
    )
    module = InterfacekitModule()
    await module.start(_make_context(InterfacekitConfig(), workflow))
    result = await module.health()
    assert result["status"] == "ok"


async def test_router_serves_verify_endpoint():
    """Full proof: spine context → resolve workflow → build router → HTTP works."""
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[FakeCollector(_minimal_observations())],
    )
    module = InterfacekitModule()
    await module.start(_make_context(InterfacekitConfig(), workflow))

    app = FastAPI()
    app.include_router(module.router)
    client = TestClient(app)

    resp = client.post("/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total"] == 3
    assert data["summary"]["pass"] == 3


async def test_resolve_wrong_protocol_raises():
    """Resolver should raise if asked for a protocol it doesn't have."""
    workflow = PreflightWorkflow(
        TOPO_FIXTURE,
        collectors=[FakeCollector([])],
    )
    resolver = FakeCapabilityResolver(workflow)

    # Should raise for unknown protocol
    try:
        resolver.resolve_one(object)
        raise AssertionError("Should have raised LookupError")
    except LookupError:
        pass
