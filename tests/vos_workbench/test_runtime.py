from pathlib import Path
from uuid import uuid4

import yaml


def _create_project(tmp_path: Path) -> Path:
    workbench = {
        "schema_version": 1,
        "project": {"id": "test-project", "name": "Test"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    for name, type_ in [("mod-a", "exec.shell"), ("mod-b", "exec.shell")]:
        mod_dir = tmp_path / "modules" / name
        mod_dir.mkdir(parents=True)
        module = {
            "uuid": str(uuid4()),
            "name": name,
            "type": type_,
        }
        (mod_dir / "module.yaml").write_text(yaml.dump(module))

    return tmp_path


def _runtime(tmp_path: Path):
    from vos_workbench.runtime.runtime import Runtime

    project_root = _create_project(tmp_path)
    db_path = tmp_path / "runtime.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()
    return rt


def test_runtime_load(tmp_path):
    rt = _runtime(tmp_path)
    assert rt.workbench_config.project.id == "test-project"
    assert len(rt.module_configs) == 2


def test_runtime_is_booted(tmp_path):
    rt = _runtime(tmp_path)
    assert rt.is_booted is True


def test_runtime_startup_plan(tmp_path):
    rt = _runtime(tmp_path)
    plan = rt.compute_startup()
    assert len(plan.failed) == 0
    assert len(plan.order) >= 1


def test_runtime_module_lookup(tmp_path):
    rt = _runtime(tmp_path)
    mod = rt.get_module("mod-a")
    assert mod is not None
    assert mod.name == "mod-a"
    assert rt.get_module("nonexistent") is None


def test_runtime_module_lookup_by_uuid(tmp_path):
    rt = _runtime(tmp_path)
    mod = rt.get_module("mod-a")
    assert mod is not None
    found = rt.get_module_by_uuid(str(mod.uuid))
    assert found is not None
    assert found.name == "mod-a"


def test_runtime_health(tmp_path):
    rt = _runtime(tmp_path)
    health = rt.get_health()
    assert health["system_status"] == "ok"
    assert health["booted"] is True
    assert health["module_count"] == 2
    assert health["failed_count"] == 0
    assert len(health["modules"]) == 2


async def test_runtime_event_persistence(tmp_path):
    from vos_workbench.events.models import VosEvent

    rt = _runtime(tmp_path)
    await rt.event_bus.publish(
        VosEvent(type="test.persisted", source="module://name/test", project_id="test")
    )

    events, count, _ = rt.query_events()
    assert count >= 1
    assert any(e["type"] == "test.persisted" for e in events)


async def test_runtime_event_query_filtered(tmp_path):
    from vos_workbench.events.models import VosEvent

    rt = _runtime(tmp_path)
    await rt.event_bus.publish(VosEvent(type="a", source="module://name/test", project_id="test"))
    await rt.event_bus.publish(VosEvent(type="b", source="module://name/test", project_id="test"))

    events, count, _ = rt.query_events(event_type="a")
    assert count == 1


async def test_runtime_emits_system_loaded_event(tmp_path):
    """Runtime.load() emits system.loaded after persistence is wired."""
    from vos_workbench.runtime.runtime import Runtime

    project_root = _create_project(tmp_path)
    db_path = tmp_path / "loaded.db"
    rt = Runtime(project_root, db_url=f"sqlite:///{db_path}")
    rt.load()

    events, count, _ = rt.query_events(event_type="system.loaded")
    assert count == 1
    assert events[0]["source"] == "system://runtime"


async def test_runtime_event_bus_subscribe(tmp_path):
    import asyncio

    from vos_workbench.events.models import VosEvent

    rt = _runtime(tmp_path)
    received = []

    async def collect():
        async for event in rt.event_bus.subscribe("test"):
            received.append(event)
            break

    task = asyncio.create_task(collect())
    await asyncio.sleep(0)
    await rt.event_bus.publish(
        VosEvent(type="test", source="module://name/test", project_id="test")
    )
    await asyncio.wait_for(task, timeout=2.0)
    assert len(received) == 1
