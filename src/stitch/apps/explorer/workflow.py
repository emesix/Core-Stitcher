"""ExplorerWorkflow — read-only topology browser.

Composes graphkit pure functions and tracekit engines over a declared
TopologySnapshot loaded via storekit. No adapters, no collection, no
verification — just navigation and query.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from stitch.graphkit.diagnostics import diagnostics
from stitch.graphkit.neighbors import neighbors
from stitch.graphkit.vlan import vlan_ports
from stitch.storekit import load_topology
from stitch.tracekit.impact import preview_impact
from stitch.tracekit.tracer import trace_vlan_path

if TYPE_CHECKING:
    from stitch.modelkit.explorer import Neighbor, TopologyDiagnostics, VlanPortEntry
    from stitch.modelkit.impact import ImpactRequest, ImpactResult
    from stitch.modelkit.topology import TopologySnapshot
    from stitch.modelkit.trace import TraceRequest, TraceResult


class ExplorerWorkflow:
    def __init__(self, topology_path: str | Path) -> None:
        self._topology_path = Path(topology_path)
        self._topology: TopologySnapshot = load_topology(self._topology_path)

    @property
    def topology(self) -> TopologySnapshot:
        return self._topology

    def reload(self) -> None:
        """Re-read topology from disk."""
        self._topology = load_topology(self._topology_path)

    def get_neighbors(self, device_id: str) -> list[Neighbor]:
        return neighbors(self.topology, device_id)

    def get_vlan_ports(self, vlan_id: int) -> list[VlanPortEntry]:
        return vlan_ports(self.topology, vlan_id)

    def get_diagnostics(self) -> TopologyDiagnostics:
        return diagnostics(self.topology)

    def trace(self, request: TraceRequest) -> TraceResult:
        return trace_vlan_path(self.topology, request)

    def impact(self, request: ImpactRequest) -> ImpactResult:
        return preview_impact(self.topology, request)
