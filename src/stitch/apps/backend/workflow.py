"""Workflow facade -- connects interfacekit routes to real domain engine.

Implements both ExplorerWorkflowProtocol and PreflightWorkflowProtocol
by delegating to graphkit, tracekit, and verifykit pure functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from stitch.graphkit.diagnostics import diagnostics
from stitch.graphkit.neighbors import neighbors
from stitch.graphkit.vlan import vlan_ports
from stitch.tracekit.impact import preview_impact
from stitch.tracekit.tracer import trace_vlan_path
from stitch.verifykit.engine import verify_topology

if TYPE_CHECKING:
    from pathlib import Path

    from stitch.modelkit.explorer import Neighbor, TopologyDiagnostics, VlanPortEntry
    from stitch.modelkit.impact import ImpactRequest, ImpactResult
    from stitch.modelkit.topology import TopologySnapshot
    from stitch.modelkit.trace import TraceRequest, TraceResult
    from stitch.modelkit.verification import VerificationReport


class BackendWorkflow:
    """Implements PreflightWorkflowProtocol and ExplorerWorkflowProtocol."""

    def __init__(self, topology: TopologySnapshot, topology_path: Path) -> None:
        self._topology = topology
        self._topology_path = topology_path

    # -- ExplorerWorkflowProtocol --

    @property
    def topology(self) -> TopologySnapshot:
        return self._topology

    def get_neighbors(self, device_id: str) -> list[Neighbor]:
        return neighbors(self._topology, device_id)

    def get_vlan_ports(self, vlan_id: int) -> list[VlanPortEntry]:
        return vlan_ports(self._topology, vlan_id)

    def get_diagnostics(self) -> TopologyDiagnostics:
        return diagnostics(self._topology)

    def trace(self, request: TraceRequest) -> TraceResult:
        return trace_vlan_path(self._topology, request)

    def impact(self, request: ImpactRequest) -> ImpactResult:
        return preview_impact(self._topology, request)

    # -- PreflightWorkflowProtocol --

    @property
    def declared_topology(self) -> TopologySnapshot:
        return self._topology

    async def run_verification(self) -> VerificationReport:
        # Without live collectors, verify declared against itself (baseline check)
        return verify_topology(self._topology, self._topology)

    async def run_trace(self, request: TraceRequest) -> TraceResult:
        return trace_vlan_path(self._topology, request)

    async def run_impact_preview(self, request: ImpactRequest) -> ImpactResult:
        return preview_impact(self._topology, request)

    # -- Health --

    async def health(self) -> dict[str, Any]:
        return {"status": "ok", "topology": str(self._topology_path)}
