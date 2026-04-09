"""Tests for ExplorerWorkflow — composition of graphkit + tracekit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stitch.apps.explorer.workflow import ExplorerWorkflow
from stitch.contractkit.explorer import ExplorerWorkflowProtocol
from stitch.modelkit.impact import ImpactRequest
from stitch.modelkit.trace import TraceRequest


@pytest.fixture()
def topology_file(tmp_path: Path) -> Path:
    data = {
        "meta": {"version": "1.0", "name": "test-topology"},
        "devices": {
            "sw1": {
                "id": "sw1",
                "name": "SW1",
                "type": "switch",
                "ports": {
                    "e1": {
                        "type": "sfp+",
                        "vlans": {"mode": "trunk", "native": 1, "tagged": [25, 254]},
                    },
                    "e2": {
                        "type": "sfp+",
                        "vlans": {"mode": "trunk", "native": 1, "tagged": [25, 254]},
                    },
                    "e3": {"type": "sfp+"},
                },
            },
            "fw1": {
                "id": "fw1",
                "name": "FW1",
                "type": "firewall",
                "ports": {
                    "ix1": {
                        "type": "sfp+",
                        "vlans": {"mode": "trunk", "native": 1, "tagged": [25, 254]},
                    },
                },
            },
            "pve": {
                "id": "pve",
                "name": "PVE",
                "type": "proxmox",
                "ports": {
                    "enp2s0": {
                        "type": "sfp+",
                        "vlans": {"mode": "trunk", "native": 1, "tagged": [25, 254]},
                    },
                },
            },
        },
        "links": [
            {
                "id": "link-sw1-fw1",
                "type": "physical_cable",
                "endpoints": [
                    {"device": "sw1", "port": "e1"},
                    {"device": "fw1", "port": "ix1"},
                ],
            },
            {
                "id": "link-sw1-pve",
                "type": "physical_cable",
                "endpoints": [
                    {"device": "sw1", "port": "e2"},
                    {"device": "pve", "port": "enp2s0"},
                ],
            },
        ],
        "vlans": {},
    }
    path = tmp_path / "topology.json"
    path.write_text(json.dumps(data))
    return path


def test_implements_protocol(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    assert isinstance(wf, ExplorerWorkflowProtocol)


def test_topology_returns_snapshot(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    snap = wf.topology
    assert "sw1" in snap.devices
    assert "fw1" in snap.devices
    assert len(snap.links) == 2


def test_get_neighbors(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    nbrs = wf.get_neighbors("sw1")
    devices = {n.device for n in nbrs}
    assert devices == {"fw1", "pve"}


def test_get_neighbors_unknown_device(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    nbrs = wf.get_neighbors("nonexistent")
    assert nbrs == []


def test_get_vlan_ports(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    entries = wf.get_vlan_ports(25)
    devices = {e.device for e in entries}
    assert devices == {"sw1", "fw1", "pve"}


def test_get_vlan_ports_not_found(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    entries = wf.get_vlan_ports(999)
    assert entries == []


def test_get_diagnostics(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    diag = wf.get_diagnostics()
    assert diag.total_devices == 3
    assert diag.total_links == 2
    # sw1/e3 is dangling (no link)
    dangling_keys = [(d.device, d.port) for d in diag.dangling_ports]
    assert ("sw1", "e3") in dangling_keys


def test_trace(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    result = wf.trace(TraceRequest(vlan=25, source="sw1"))
    assert result.status == "complete"
    assert len(result.hops) > 0


def test_topology_is_cached(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    snap1 = wf.topology
    snap2 = wf.topology
    assert snap1 is snap2


def test_reload_picks_up_changes(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    assert "sw1" in wf.topology.devices

    # Rewrite file with different content
    data = json.loads(topology_file.read_text())
    del data["devices"]["sw1"]
    topology_file.write_text(json.dumps(data))

    # Still cached
    assert "sw1" in wf.topology.devices

    # After reload, picks up the change
    wf.reload()
    assert "sw1" not in wf.topology.devices


def test_impact(topology_file: Path):
    wf = ExplorerWorkflow(topology_file)
    result = wf.impact(
        ImpactRequest(action="remove_link", device="sw1", parameters={"link_id": "link-sw1-fw1"})
    )
    assert result.safe_to_apply is False
    affected = {e.device for e in result.impact}
    assert "fw1" in affected
