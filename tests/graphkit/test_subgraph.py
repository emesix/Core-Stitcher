"""Tests for graphkit subgraph extraction."""

from __future__ import annotations

from vos.graphkit.subgraph import subgraph
from vos.modelkit.device import Device
from vos.modelkit.enums import DeviceType, LinkType, PortType
from vos.modelkit.link import Link, LinkEndpoint
from vos.modelkit.port import Port
from vos.modelkit.topology import TopologyMeta, TopologySnapshot
from vos.modelkit.vlan import VlanMetadata

META = TopologyMeta(version="1.0", name="test")


def _port() -> Port:
    return Port(type=PortType.SFP_PLUS)


def _three_device_topology() -> TopologySnapshot:
    return TopologySnapshot(
        meta=META,
        devices={
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _port(), "e2": _port()},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _port()},
            ),
            "pve": Device(
                id="pve",
                name="PVE",
                type=DeviceType.PROXMOX,
                ports={"enp2s0": _port()},
            ),
        },
        links=[
            Link(
                id="link-sw1-fw1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            ),
            Link(
                id="link-sw1-pve",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e2"),
                    LinkEndpoint(device="pve", port="enp2s0"),
                ),
            ),
        ],
        vlans={"25": VlanMetadata(name="Management", color="#ff0")},
    )


def test_subgraph_filters_devices():
    snap = _three_device_topology()
    result = subgraph(snap, {"sw1", "fw1"})
    assert set(result.devices.keys()) == {"sw1", "fw1"}
    assert "pve" not in result.devices


def test_subgraph_filters_links():
    snap = _three_device_topology()
    result = subgraph(snap, {"sw1", "fw1"})
    assert len(result.links) == 1
    assert result.links[0].id == "link-sw1-fw1"


def test_subgraph_preserves_vlans():
    snap = _three_device_topology()
    result = subgraph(snap, {"sw1"})
    assert result.vlans == snap.vlans


def test_subgraph_empty_set():
    snap = _three_device_topology()
    result = subgraph(snap, set())
    assert result.devices == {}
    assert result.links == []


def test_subgraph_all_devices():
    snap = _three_device_topology()
    result = subgraph(snap, {"sw1", "fw1", "pve"})
    assert set(result.devices.keys()) == {"sw1", "fw1", "pve"}
    assert len(result.links) == 2


def test_subgraph_meta_tagged():
    snap = _three_device_topology()
    result = subgraph(snap, {"sw1"})
    assert result.meta.version == snap.meta.version
    assert "(subgraph)" in result.meta.name
