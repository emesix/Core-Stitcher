from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from stitch.modelkit.explorer import Neighbor, TopologyDiagnostics, VlanPortEntry
    from stitch.modelkit.impact import ImpactRequest, ImpactResult
    from stitch.modelkit.topology import TopologySnapshot
    from stitch.modelkit.trace import TraceRequest, TraceResult


@runtime_checkable
class ExplorerWorkflowProtocol(Protocol):
    @property
    def topology(self) -> TopologySnapshot: ...

    def get_neighbors(self, device_id: str) -> list[Neighbor]: ...

    def get_vlan_ports(self, vlan_id: int) -> list[VlanPortEntry]: ...

    def get_diagnostics(self) -> TopologyDiagnostics: ...

    def trace(self, request: TraceRequest) -> TraceResult: ...

    def impact(self, request: ImpactRequest) -> ImpactResult: ...
