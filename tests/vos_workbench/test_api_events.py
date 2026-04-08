"""Tests for /events endpoint with pagination and filtering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from vos_workbench.events.models import VosEvent


def _create_project(tmp_path: Path) -> Path:
    workbench = {
        "schema_version": 1,
        "project": {"id": "test-project", "name": "Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))
    (tmp_path / "modules").mkdir()
    return tmp_path


@pytest.fixture
def project_path(tmp_path):
    return _create_project(tmp_path)


@pytest.fixture
def app(project_path, tmp_path):
    from vos_workbench.api.app import create_app

    db_url = f"sqlite:///{tmp_path / 'events.db'}"
    return create_app(project_root=project_path, db_url=db_url)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_get_events_empty(client):
    response = await client.get("/api/v1/events")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["offset"] == 0
    assert body["meta"]["limit"] == 100


async def test_get_events_with_data(client, app):
    runtime = app.state.runtime
    await runtime.event_bus.publish(
        VosEvent(type="test.a", source="module://name/test", project_id="test")
    )
    await runtime.event_bus.publish(
        VosEvent(type="test.b", source="module://name/test", project_id="test")
    )
    response = await client.get("/api/v1/events?type=test.a")
    body = response.json()
    assert body["meta"]["count"] == 1
    assert body["data"][0]["type"] == "test.a"


async def test_get_events_filtered_by_type(client, app):
    runtime = app.state.runtime
    await runtime.event_bus.publish(
        VosEvent(type="wanted", source="module://name/test", project_id="test")
    )
    await runtime.event_bus.publish(
        VosEvent(type="unwanted", source="module://name/test", project_id="test")
    )
    response = await client.get("/api/v1/events?type=wanted")
    body = response.json()
    assert body["meta"]["count"] == 1
    assert body["data"][0]["type"] == "wanted"


async def test_events_pagination_offset_limit(client, app):
    runtime = app.state.runtime
    for i in range(10):
        await runtime.event_bus.publish(
            VosEvent(
                type=f"evt.{i}",
                source="module://name/test",
                project_id="test",
                time=datetime(2026, 6, 1, tzinfo=UTC) + timedelta(seconds=i),
            )
        )
    # Page 1
    resp1 = await client.get("/api/v1/events?offset=0&limit=3&since=2026-06-01T00:00:00Z")
    body1 = resp1.json()
    assert body1["meta"]["count"] == 3
    assert body1["meta"]["has_more"] is True
    assert body1["meta"]["offset"] == 0
    # Page 2
    resp2 = await client.get("/api/v1/events?offset=3&limit=3&since=2026-06-01T00:00:00Z")
    body2 = resp2.json()
    assert body2["meta"]["count"] == 3
    assert body2["meta"]["offset"] == 3
    # No overlap
    ids1 = {e["id"] for e in body1["data"]}
    ids2 = {e["id"] for e in body2["data"]}
    assert ids1.isdisjoint(ids2)


async def test_events_since_filter(client, app):
    runtime = app.state.runtime
    t1 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 6, 1, 14, 0, 0, tzinfo=UTC)
    await runtime.event_bus.publish(VosEvent(type="old", source="s", project_id="p", time=t1))
    await runtime.event_bus.publish(VosEvent(type="new", source="s", project_id="p", time=t2))
    response = await client.get("/api/v1/events?since=2026-06-01T13:00:00Z")
    body = response.json()
    assert body["meta"]["count"] == 1
    assert body["data"][0]["type"] == "new"


async def test_events_until_filter(client, app):
    runtime = app.state.runtime
    t1 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 6, 1, 14, 0, 0, tzinfo=UTC)
    await runtime.event_bus.publish(VosEvent(type="old", source="s", project_id="p", time=t1))
    await runtime.event_bus.publish(VosEvent(type="new", source="s", project_id="p", time=t2))
    response = await client.get("/api/v1/events?until=2026-06-01T13:00:00Z")
    body = response.json()
    types = [e["type"] for e in body["data"]]
    assert "old" in types
    assert "new" not in types


async def test_events_source_glob_filter(client, app):
    runtime = app.state.runtime
    await runtime.event_bus.publish(VosEvent(type="a", source="system://eventbus", project_id="p"))
    await runtime.event_bus.publish(
        VosEvent(type="b", source="module://name/router", project_id="p")
    )
    response = await client.get("/api/v1/events?source=system://*")
    body = response.json()
    for event in body["data"]:
        assert event["source"].startswith("system://")


async def test_events_severity_filter(client, app):
    runtime = app.state.runtime
    await runtime.event_bus.publish(VosEvent(type="a", source="s", project_id="p", severity="info"))
    await runtime.event_bus.publish(
        VosEvent(type="b", source="s", project_id="p", severity="warning")
    )
    response = await client.get("/api/v1/events?severity=warning")
    body = response.json()
    for event in body["data"]:
        assert event["severity"] == "warning"


async def test_events_time_asc_ordering(client, app):
    runtime = app.state.runtime
    t1 = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 6, 1, 8, 0, 0, tzinfo=UTC)
    t3 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    await runtime.event_bus.publish(VosEvent(type="mid", source="s", project_id="p", time=t1))
    await runtime.event_bus.publish(VosEvent(type="early", source="s", project_id="p", time=t2))
    await runtime.event_bus.publish(VosEvent(type="late", source="s", project_id="p", time=t3))
    response = await client.get("/api/v1/events?since=2026-06-01T00:00:00Z")
    body = response.json()
    types = [e["type"] for e in body["data"]]
    assert types == ["early", "mid", "late"]


async def test_events_max_limit_enforced(client):
    response = await client.get("/api/v1/events?limit=2000")
    assert response.status_code == 422


async def test_events_has_more_flag(client, app):
    runtime = app.state.runtime
    for i in range(5):
        await runtime.event_bus.publish(
            VosEvent(
                type=f"e.{i}",
                source="s",
                project_id="p",
                time=datetime(2026, 6, 1, tzinfo=UTC) + timedelta(seconds=i),
            )
        )
    resp = await client.get("/api/v1/events?limit=3&since=2026-06-01T00:00:00Z")
    assert resp.json()["meta"]["has_more"] is True
    resp = await client.get("/api/v1/events?limit=5&since=2026-06-01T00:00:00Z")
    assert resp.json()["meta"]["has_more"] is False
    resp = await client.get("/api/v1/events?limit=10&since=2026-06-01T00:00:00Z")
    assert resp.json()["meta"]["has_more"] is False
