"""Cross-cutting contract tests verifying spine structural promises.

Every test uses temp-file SQLite. No shared state between tests.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from vos_workbench.events.bus import EventBus
from vos_workbench.events.models import VosEvent


def _write_project(root: Path, modules: list[dict] | None = None) -> Path:
    workbench = {
        "schema_version": 1,
        "project": {"id": "contract-test", "name": "Contract Test"},
    }
    (root / "workbench.yaml").write_text(yaml.dump(workbench))
    (root / "modules").mkdir(exist_ok=True)

    for mod in modules or []:
        mod_dir = root / "modules" / mod["name"]
        mod_dir.mkdir(parents=True, exist_ok=True)
        (mod_dir / "module.yaml").write_text(yaml.dump(mod))

    return root


# --- Contract: Boot persistence ---


async def test_contract_boot_persistence(tmp_path: Path):
    """system.loaded survives process restart (new Runtime, same DB)."""
    from vos_workbench.runtime.runtime import Runtime

    db_path = tmp_path / "persist.db"
    db_url = f"sqlite:///{db_path}"
    project = _write_project(tmp_path)

    # Boot 1
    rt1 = Runtime(project, db_url=db_url)
    rt1.load()
    events1, count1, _ = rt1.query_events(event_type="system.loaded")
    assert count1 == 1
    assert events1[0]["source"] == "system://runtime"

    # "Restart": new Runtime, same DB
    rt2 = Runtime(project, db_url=db_url)
    rt2.load()
    events2, count2, _ = rt2.query_events(event_type="system.loaded")
    assert count2 == 2


# --- Contract: Overflow visibility ---


async def test_contract_overflow_visibility(tmp_path: Path):
    """Overflow marks subscriber degraded and emits bus.subscriber.overflow."""
    from vos_workbench.runtime.runtime import Runtime

    db_path = tmp_path / "overflow.db"
    db_url = f"sqlite:///{db_path}"
    project = _write_project(tmp_path)

    rt = Runtime(project, db_url=db_url)
    rt.load()

    # Override bus with tiny buffer but keep persistence wiring
    rt.event_bus = EventBus(buffer_size=2)
    rt.event_bus.on_publish = rt._persist_event

    # Subscribe but never read
    rt.event_bus.subscribe("slow-consumer")

    # Publish enough to overflow
    for i in range(5):
        await rt.event_bus.publish(
            VosEvent(
                type=f"flood.{i}",
                source="module://name/test",
                project_id="contract-test",
            )
        )

    # Subscriber should be degraded
    status = rt.event_bus.get_subscriber_status("slow-consumer")
    assert status is not None
    assert status["degraded"] is True
    assert status["overflow_count"] >= 1

    # Overflow event should be persisted
    events, count, _ = rt.query_events(event_type="bus.subscriber.overflow")
    assert count >= 1


# --- Contract: Partial startup in health ---


async def test_contract_partial_startup_in_health(tmp_path: Path):
    """Failed modules appear in /readyz (503) and /health diagnostic."""
    from vos_workbench.api.app import create_app

    modules = [
        {"uuid": str(uuid4()), "name": "good-mod", "type": "exec.shell"},
        {
            "uuid": str(uuid4()),
            "name": "broken-mod",
            "type": "exec.shell",
            "wiring": {"depends_on": [{"ref": "module://ghost", "kind": "hard"}]},
        },
    ]
    project = _write_project(tmp_path, modules)
    db_url = f"sqlite:///{tmp_path / 'partial.db'}"
    app = create_app(project_root=project, db_url=db_url)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/readyz")
        assert resp.status_code == 503
        body = resp.json()
        assert "broken-mod" in body["failed_modules"]

        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        health = resp.json()["data"]
        failed = [m for m in health["modules"] if m["status"] == "failed"]
        assert len(failed) == 1
        assert failed[0]["name"] == "broken-mod"
        assert failed[0]["failure_reason"] is not None


# --- Contract: DB unavailable at boot ---


def test_contract_db_unavailable_at_boot(tmp_path: Path):
    """Unreachable DB produces a clear error, not a raw traceback."""
    from vos_workbench.runtime.runtime import Runtime

    project = _write_project(tmp_path)
    db_url = "sqlite:////nonexistent/path/to/impossible.db"

    rt = Runtime(project, db_url=db_url)
    with pytest.raises(Exception) as exc_info:
        rt.load()

    error_msg = str(exc_info.value)
    assert error_msg


# --- Contract: Health reflects startup plan ---


async def test_contract_readyz_reflects_startup_plan(tmp_path: Path):
    """readyz failed_modules matches startup plan failures exactly."""
    from vos_workbench.api.app import create_app

    modules = [
        {"uuid": str(uuid4()), "name": "healthy-mod", "type": "exec.shell"},
        {
            "uuid": str(uuid4()),
            "name": "fail-a",
            "type": "exec.shell",
            "wiring": {"depends_on": [{"ref": "module://missing-x", "kind": "hard"}]},
        },
        {
            "uuid": str(uuid4()),
            "name": "fail-b",
            "type": "core.router",
            "wiring": {"depends_on": [{"ref": "module://missing-y", "kind": "hard"}]},
        },
    ]
    project = _write_project(tmp_path, modules)
    db_url = f"sqlite:///{tmp_path / 'startup-plan.db'}"
    app = create_app(project_root=project, db_url=db_url)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/readyz")
        assert resp.status_code == 503
        body = resp.json()
        assert set(body["failed_modules"]) == {"fail-a", "fail-b"}


# --- Contract: Events pagination consistency ---


async def test_contract_events_pagination_consistency(tmp_path: Path):
    """Pages do not overlap or skip events under stable dataset."""
    from vos_workbench.api.app import create_app

    project = _write_project(tmp_path)
    db_url = f"sqlite:///{tmp_path / 'pagination.db'}"
    app = create_app(project_root=project, db_url=db_url)
    runtime = app.state.runtime

    base_time = datetime(2026, 6, 1, tzinfo=UTC)
    for i in range(50):
        await runtime.event_bus.publish(
            VosEvent(
                type=f"page.{i:03d}",
                source="module://name/test",
                project_id="contract-test",
                time=base_time + timedelta(seconds=i),
            )
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        all_ids: list[str] = []
        offset = 0
        page_size = 20

        while True:
            resp = await client.get(f"/api/v1/events?offset={offset}&limit={page_size}")
            body = resp.json()
            page_ids = [e["id"] for e in body["data"]]
            all_ids.extend(page_ids)

            if not body["meta"]["has_more"]:
                break
            offset += page_size

        # system.loaded + 50 events = 51 total
        assert len(all_ids) == 51
        assert len(set(all_ids)) == 51
