from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vos.modelkit.impact import ImpactRequest, ImpactResult
    from vos.modelkit.trace import TraceRequest, TraceResult
    from vos.modelkit.verification import VerificationReport


@runtime_checkable
class PreflightWorkflowProtocol(Protocol):
    async def run_verification(self) -> VerificationReport: ...

    async def run_trace(self, request: TraceRequest) -> TraceResult: ...

    async def run_impact_preview(self, request: ImpactRequest) -> ImpactResult: ...
