import asyncio

import pytest

from vos_workbench.events.models import VosEvent


def _event(type_: str = "test.event", source: str = "module://name/test") -> VosEvent:
    return VosEvent(type=type_, source=source, project_id="test")


@pytest.fixture
def bus():
    from vos_workbench.events.bus import EventBus

    return EventBus()


async def test_publish_and_receive(bus):
    received = []

    async def collect():
        async for event in bus.subscribe("sub1"):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)  # yield so collect() can register the subscriber
    await bus.publish(_event("a"))
    await bus.publish(_event("b"))
    await asyncio.wait_for(task, timeout=2.0)
    assert len(received) == 2
    assert received[0].type == "a"
    assert received[1].type == "b"


async def test_subscribe_with_type_filter(bus):
    received = []

    async def collect():
        async for event in bus.subscribe("sub1", event_types=["wanted"]):
            received.append(event)
            break

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)  # yield so collect() can register the subscriber
    await bus.publish(_event("unwanted"))
    await bus.publish(_event("wanted"))
    await asyncio.wait_for(task, timeout=2.0)
    assert len(received) == 1
    assert received[0].type == "wanted"


async def test_multiple_subscribers(bus):
    received_a = []
    received_b = []

    async def collect_a():
        async for event in bus.subscribe("a"):
            received_a.append(event)
            break

    async def collect_b():
        async for event in bus.subscribe("b"):
            received_b.append(event)
            break

    task_a = asyncio.create_task(collect_a())
    task_b = asyncio.create_task(collect_b())
    await asyncio.sleep(0)  # yield so both collectors can register
    await bus.publish(_event("shared"))
    await asyncio.wait_for(asyncio.gather(task_a, task_b), timeout=2.0)
    assert len(received_a) == 1
    assert len(received_b) == 1


async def test_unsubscribe(bus):
    bus.subscribe("sub1")
    bus.unsubscribe("sub1")
    assert "sub1" not in bus._subscribers


async def test_event_history(bus):
    await bus.publish(_event("first"))
    await bus.publish(_event("second"))
    history = bus.get_history()
    assert len(history) == 2
    assert history[0].type == "first"


async def test_event_history_filtered(bus):
    await bus.publish(_event("a", source="module://name/mod1"))
    await bus.publish(_event("b", source="module://name/mod2"))
    history = bus.get_history(event_types=["a"])
    assert len(history) == 1
    assert history[0].type == "a"
