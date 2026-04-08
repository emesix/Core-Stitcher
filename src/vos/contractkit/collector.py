from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vos.modelkit.observation import Observation


@runtime_checkable
class CollectorProtocol(Protocol):
    async def collect(self) -> list[Observation]: ...
