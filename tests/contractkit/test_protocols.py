from __future__ import annotations

from typing import Any

from stitch.contractkit import (
    CollectorProtocol,
    ExplorerWorkflowProtocol,
    MergerProtocol,
    ModuleHealth,
    ModuleStatus,
    PreflightWorkflowProtocol,
    TracerProtocol,
    VerifierProtocol,
)


class FakeCollector:
    async def collect(self) -> list[Any]:
        return []


class FakeMerger:
    async def merge(self, observations: list[Any]) -> tuple[Any, list[Any]]:
        return {}, []


class FakeVerifier:
    async def verify(self, declared: Any, observed: Any) -> Any:
        return {}


class FakeTracer:
    async def trace(self, snapshot: Any, request: Any) -> Any:
        return {}

    async def preview(self, snapshot: Any, request: Any) -> Any:
        return {}


class FakeWorkflow:
    async def run_verification(self) -> Any:
        return {}

    async def run_trace(self, request: Any) -> Any:
        return {}

    async def run_impact_preview(self, request: Any) -> Any:
        return {}


def test_collector_protocol():
    assert isinstance(FakeCollector(), CollectorProtocol)


def test_merger_protocol():
    assert isinstance(FakeMerger(), MergerProtocol)


def test_verifier_protocol():
    assert isinstance(FakeVerifier(), VerifierProtocol)


def test_tracer_protocol():
    assert isinstance(FakeTracer(), TracerProtocol)


def test_workflow_protocol():
    assert isinstance(FakeWorkflow(), PreflightWorkflowProtocol)


def test_module_health():
    h = ModuleHealth(status="ok", message=None, details={})
    assert h.status == "ok"
    assert h.details == {}


def test_module_status():
    s = ModuleStatus(
        module_name="switchcraft-1",
        module_type="resource.switchcraft",
        health=ModuleHealth(status="degraded", message="timeout", details={}),
    )
    assert s.module_name == "switchcraft-1"
    assert s.health.status == "degraded"


class FakeExplorerWorkflow:
    @property
    def topology(self):
        return None

    def get_neighbors(self, device_id):
        return []

    def get_vlan_ports(self, vlan_id):
        return []

    def get_diagnostics(self):
        return None

    def trace(self, request):
        return None

    def impact(self, request):
        return None


def test_explorer_workflow_protocol():
    assert isinstance(FakeExplorerWorkflow(), ExplorerWorkflowProtocol)
