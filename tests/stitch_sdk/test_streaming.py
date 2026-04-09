import json

from stitch.core.streams import StreamTopic
from stitch.sdk.streaming import StreamClient


class FakeWebSocket:
    def __init__(self, messages: list[dict]):
        self._messages = [json.dumps(m) for m in messages]
        self._index = 0
        self.closed = False

    async def recv(self) -> str:
        if self._index >= len(self._messages):
            raise Exception("connection closed")
        msg = self._messages[self._index]
        self._index += 1
        return msg

    async def send(self, data: str) -> None:
        pass

    async def close(self) -> None:
        self.closed = True


async def test_stream_client_receives_events():
    messages = [
        {
            "event_id": "evt_001",
            "sequence": 1,
            "topic": "run.progress",
            "resource": "stitch:/run/run_18f2/task/tsk_001",
            "payload": {"status": "succeeded"},
            "timestamp": "2026-04-09T12:04:01Z",
        },
        {
            "event_id": "evt_002",
            "sequence": 2,
            "topic": "run.progress",
            "resource": "stitch:/run/run_18f2/task/tsk_002",
            "payload": {"status": "running"},
            "timestamp": "2026-04-09T12:04:03Z",
        },
    ]
    ws = FakeWebSocket(messages)
    client = StreamClient(ws)
    events = []
    async for event in client.events():
        events.append(event)
        if len(events) >= 2:
            break
    assert len(events) == 2
    assert events[0].event_id == "evt_001"
    assert events[0].topic == StreamTopic.RUN_PROGRESS
    assert events[1].payload["status"] == "running"


async def test_stream_client_tracks_last_event_id():
    messages = [
        {
            "event_id": "evt_001",
            "sequence": 1,
            "topic": "run.progress",
            "resource": "r",
            "payload": {},
            "timestamp": "2026-04-09T12:00:00Z",
        },
    ]
    ws = FakeWebSocket(messages)
    client = StreamClient(ws)
    async for _event in client.events():
        break
    assert client.last_event_id == "evt_001"


async def test_stream_client_handles_disconnect():
    ws = FakeWebSocket([])  # empty = immediate disconnect
    client = StreamClient(ws)
    events = []
    async for event in client.events():
        events.append(event)
    assert events == []


async def test_stream_client_close():
    ws = FakeWebSocket([])
    client = StreamClient(ws)
    await client.close()
    assert ws.closed is True
