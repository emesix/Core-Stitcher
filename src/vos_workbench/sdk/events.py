from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventPublisher(Protocol):
    async def publish(self, event: Any) -> None: ...
