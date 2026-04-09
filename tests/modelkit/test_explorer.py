"""Tests for explorer-specific modelkit types."""

from __future__ import annotations

from stitch.modelkit.explorer import (
    DanglingPort,
    Neighbor,
    TopologyDiagnostics,
    VlanPortEntry,
)


def test_neighbor_frozen():
    n = Neighbor(
        device="fw1",
        local_port="e1",
        remote_port="ix1",
        link_id="phys-sw1-fw1",
        link_type="physical_cable",
    )
    assert n.device == "fw1"
    assert n.link_type == "physical_cable"


def test_dangling_port_frozen():
    dp = DanglingPort(device="sw1", port="e3", reason="No links attached")
    assert dp.reason == "No links attached"


def test_vlan_port_entry_frozen():
    vpe = VlanPortEntry(device="sw1", port="e1", mode="trunk")
    assert vpe.mode == "trunk"


def test_diagnostics_defaults():
    diag = TopologyDiagnostics()
    assert diag.dangling_ports == []
    assert diag.orphan_devices == []
    assert diag.missing_endpoints == []
    assert diag.total_devices == 0
    assert diag.total_ports == 0
    assert diag.total_links == 0


def test_diagnostics_with_data():
    diag = TopologyDiagnostics(
        dangling_ports=[DanglingPort(device="sw1", port="e3", reason="No links attached")],
        orphan_devices=["ap1"],
        missing_endpoints=["link-x: device 'gone' not found"],
        total_devices=5,
        total_ports=20,
        total_links=8,
    )
    assert len(diag.dangling_ports) == 1
    assert diag.total_devices == 5
