from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vos.modelkit.impact import ImpactRequest, ImpactResult
    from vos.modelkit.topology import TopologySnapshot
    from vos.modelkit.trace import TraceRequest, TraceResult


@runtime_checkable
class TracerProtocol(Protocol):
    async def trace(self, snapshot: TopologySnapshot, request: TraceRequest) -> TraceResult: ...

    async def preview(
        self,
        snapshot: TopologySnapshot,
        request: ImpactRequest,
    ) -> ImpactResult: ...
