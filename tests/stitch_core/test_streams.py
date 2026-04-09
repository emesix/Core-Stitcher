from datetime import UTC, datetime

from stitch.core.streams import StreamEvent, StreamSubscription, StreamTopic


def test_stream_subscription():
    sub = StreamSubscription(
        topic=StreamTopic.RUN_PROGRESS,
        target="stitch:/run/run_18f2",
    )
    assert sub.topic == "run.progress"
    assert sub.filters == []


def test_stream_event():
    evt = StreamEvent(
        event_id="evt_001",
        sequence=1,
        topic=StreamTopic.RUN_PROGRESS,
        resource="stitch:/run/run_18f2/task/tsk_001",
        payload={"status": "succeeded"},
        timestamp=datetime.now(UTC),
    )
    assert evt.sequence == 1
    assert evt.payload["status"] == "succeeded"
