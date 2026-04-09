from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vos.modelkit.observation import MergeConflict, Observation
    from vos.modelkit.topology import TopologySnapshot


@runtime_checkable
class MergerProtocol(Protocol):
    async def merge(
        self,
        observations: list[Observation],
    ) -> tuple[TopologySnapshot, list[MergeConflict]]: ...
