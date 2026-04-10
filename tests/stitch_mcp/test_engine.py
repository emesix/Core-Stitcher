import json
import os
import time

import pytest

from stitch.mcp.engine import StitchEngine

SAMPLE_TOPO = {
    "meta": {"version": "1.0", "name": "test", "updated": "2026-01-01", "updated_by": "test"},
    "devices": {
        "dev1": {"id": "dev1", "name": "Device 1", "type": "switch", "ports": {}},
        "dev2": {"id": "dev2", "name": "Device 2", "type": "firewall", "ports": {}},
    },
    "links": [],
    "vlans": {},
}


@pytest.fixture
def topology_file(tmp_path):
    p = tmp_path / "test-topo.json"
    p.write_text(json.dumps(SAMPLE_TOPO))
    return str(p)


def test_engine_lazy_load(topology_file):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    assert engine._cached_topology is None
    topo = engine.get_topology()
    assert len(topo.devices) == 2
    assert engine._cached_topology is not None


def test_engine_caches_by_mtime(topology_file):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    topo1 = engine.get_topology()
    topo2 = engine.get_topology()
    assert topo1 is topo2


def test_engine_reloads_on_mtime_change(topology_file):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    topo1 = engine.get_topology()
    time.sleep(0.1)
    new_topo = {
        **SAMPLE_TOPO,
        "devices": {"dev1": {"id": "dev1", "name": "Device 1", "type": "switch", "ports": {}}},
    }
    new_topo["meta"] = {**SAMPLE_TOPO["meta"], "name": "updated"}
    with open(topology_file, "w") as f:
        json.dump(new_topo, f)
    os.utime(topology_file, (time.time() + 1, time.time() + 1))
    topo2 = engine.get_topology()
    assert topo2 is not topo1
    assert len(topo2.devices) == 1


def test_engine_override_path(topology_file, tmp_path):
    other = tmp_path / "other.json"
    other.write_text(
        json.dumps(
            {
                "meta": {
                    "version": "1.0",
                    "name": "other",
                    "updated": "2026-01-01",
                    "updated_by": "test",
                },
                "devices": {},
                "links": [],
                "vlans": {},
            }
        )
    )
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    topo = engine.get_topology(override_path=str(other))
    assert len(topo.devices) == 0


def test_engine_get_explorer(topology_file):
    engine = StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
    explorer = engine.get_explorer()
    diag = explorer.get_diagnostics()
    assert diag.total_devices == 2
