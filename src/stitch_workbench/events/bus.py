from __future__ import annotations

import asyncio
import contextlib
from collections import deque
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from stitch_workbench.events.models import VosEvent

logger = structlog.get_logger()

DEFAULT_BUFFER_SIZE = 1000
DEFAULT_HISTORY_SIZE = 10000


@dataclass
class _Subscriber:
    queue: asyncio.Queue[VosEvent]
    event_types: list[str] | None = None
    source_filter: str | None = None
    overflow_count: int = 0
    degraded: bool = False


class EventBus:
    """In-process asyncio pub/sub event bus.

    Overflow contract: when a subscriber's buffer is full, the event is
    dropped, the subscriber is marked degraded, and a
    bus.subscriber.overflow event is emitted.
    """

    def __init__(
        self,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        history_size: int = DEFAULT_HISTORY_SIZE,
    ) -> None:
        self._subscribers: dict[str, _Subscriber] = {}
        self._buffer_size = buffer_size
        self._history: deque[VosEvent] = deque(maxlen=history_size)
        self._publishing = False  # guard against recursive overflow events
        self.on_publish: Callable[[VosEvent], None] | None = None  # persistence callback

    async def publish(self, event: VosEvent) -> None:
        """Publish an event to all matching subscribers."""
        self._history.append(event)

        # Persistence callback (e.g., write to SQLite)
        if self.on_publish is not None:
            self.on_publish(event)

        overflow_events: list[VosEvent] = []

        for sub_id, sub in self._subscribers.items():
            if not self._matches(event, sub):
                continue
            try:
                sub.queue.put_nowait(event)
            except asyncio.QueueFull:
                sub.overflow_count += 1
                sub.degraded = True
                logger.warning(
                    "subscriber_buffer_overflow",
                    subscriber=sub_id,
                    overflow_count=sub.overflow_count,
                    dropped_event_type=event.type,
                )
                # Collect overflow events to emit after this publish loop
                # (avoids modifying subscribers during iteration)
                if not self._publishing:
                    overflow_events.append(self._make_overflow_event(sub_id, sub, event))

        # Emit overflow events outside the main publish loop
        if overflow_events:
            self._publishing = True
            try:
                for oe in overflow_events:
                    self._history.append(oe)
                    if self.on_publish is not None:
                        self.on_publish(oe)
                    for _sid, s in self._subscribers.items():
                        if not self._matches(oe, s):
                            continue
                        with contextlib.suppress(asyncio.QueueFull):
                            s.queue.put_nowait(oe)
            finally:
                self._publishing = False

    def subscribe(
        self,
        subscriber_id: str,
        event_types: list[str] | None = None,
        source_filter: str | None = None,
    ) -> AsyncIterator[VosEvent]:
        sub = _Subscriber(
            queue=asyncio.Queue(maxsize=self._buffer_size),
            event_types=event_types,
            source_filter=source_filter,
        )
        self._subscribers[subscriber_id] = sub
        return self._iter_subscriber(subscriber_id)

    def unsubscribe(self, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)

    def get_subscriber_status(self, subscriber_id: str) -> dict | None:
        """Get subscriber status including degraded flag."""
        sub = self._subscribers.get(subscriber_id)
        if sub is None:
            return None
        return {
            "subscriber_id": subscriber_id,
            "degraded": sub.degraded,
            "overflow_count": sub.overflow_count,
            "queue_size": sub.queue.qsize(),
        }

    def get_history(
        self,
        event_types: list[str] | None = None,
        since: int | None = None,
        limit: int = 100,
    ) -> list[VosEvent]:
        events = list(self._history)
        if since is not None:
            events = events[since:]
        if event_types:
            type_set = set(event_types)
            events = [e for e in events if e.type in type_set]
        return events[:limit]

    @staticmethod
    def _matches(event: VosEvent, sub: _Subscriber) -> bool:
        if sub.event_types and event.type not in sub.event_types:
            return False
        return not sub.source_filter or fnmatch(event.source, sub.source_filter)

    @staticmethod
    def _make_overflow_event(
        subscriber_id: str,
        sub: _Subscriber,
        dropped_event: VosEvent,
    ) -> VosEvent:
        from stitch_workbench.events.models import VosEvent as VE

        return VE(
            type="bus.subscriber.overflow",
            source="system://eventbus",
            project_id=dropped_event.project_id,
            severity="warning",
            data={
                "subscriber_id": subscriber_id,
                "overflow_count": sub.overflow_count,
                "dropped_event_type": dropped_event.type,
            },
        )

    async def _iter_subscriber(self, subscriber_id: str) -> AsyncIterator[VosEvent]:
        sub = self._subscribers.get(subscriber_id)
        if sub is None:
            return
        try:
            while subscriber_id in self._subscribers:
                event = await sub.queue.get()
                yield event
        finally:
            self._subscribers.pop(subscriber_id, None)
