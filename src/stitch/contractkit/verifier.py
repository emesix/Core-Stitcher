from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from stitch.modelkit.topology import TopologySnapshot
    from stitch.modelkit.verification import VerificationReport


@runtime_checkable
class VerifierProtocol(Protocol):
    async def verify(
        self,
        declared: TopologySnapshot,
        observed: TopologySnapshot,
    ) -> VerificationReport: ...
