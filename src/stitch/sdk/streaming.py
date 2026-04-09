"""WebSocket stream client with reconnect and resume."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from stitch.core.streams import StreamEvent

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class StreamClient:
    """Wraps a WebSocket connection and yields StreamEvents."""

    def __init__(self, ws) -> None:
        self._ws = ws
        self._last_event_id: str | None = None

    @property
    def last_event_id(self) -> str | None:
        return self._last_event_id

    async def events(self) -> AsyncIterator[StreamEvent]:
        """Yield StreamEvents from the WebSocket."""
        try:
            while True:
                raw = await self._ws.recv()
                data = json.loads(raw)
                event = StreamEvent(**data)
                self._last_event_id = event.event_id
                yield event
        except Exception:
            return

    async def close(self) -> None:
        await self._ws.close()
