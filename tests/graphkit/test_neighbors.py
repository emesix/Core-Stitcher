"""Tests for graphkit neighbor queries."""

from __future__ import annotations

from stitch.graphkit.neighbors import neighbors
from stitch.modelkit.device import Device
from stitch.modelkit.enums import DeviceType, LinkType, PortType
from stitch.modelkit.link import Link, LinkEndpoint
from stitch.modelkit.port import Port
from stitch.modelkit.topology import TopologyMeta, TopologySnapshot

META = TopologyMeta(version="1.0", name="test")


def _port() -> Port:
    return Port(type=PortType.SFP_PLUS)


def _snap(devices: dict[str, Device], links: list[Link]) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=links)


def _triangle_topology() -> TopologySnapshot:
    """Three devices in a triangle: sw1 -- fw1, sw1 -- pve, fw1 -- pve."""
    return _snap(
        {
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
                ports={"ix1": _port(), "ix2": _port()},
            ),
            "pve": Device(
                id="pve",
                name="PVE",
                type=DeviceType.PROXMOX,
                ports={"enp2s0": _port(), "enp3s0": _port()},
            ),
        },
        [
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
            Link(
                id="link-fw1-pve",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="fw1", port="ix2"),
                    LinkEndpoint(device="pve", port="enp3s0"),
                ),
            ),
        ],
    )


def test_neighbors_returns_adjacent_devices():
    snap = _triangle_topology()
    nbrs = neighbors(snap, "sw1")
    devices = {n.device for n in nbrs}
    assert devices == {"fw1", "pve"}


def test_neighbors_includes_port_info():
    snap = _triangle_topology()
    nbrs = neighbors(snap, "sw1")
    fw_neighbor = next(n for n in nbrs if n.device == "fw1")
    assert fw_neighbor.local_port == "e1"
    assert fw_neighbor.remote_port == "ix1"
    assert fw_neighbor.link_id == "link-sw1-fw1"
    assert fw_neighbor.link_type == LinkType.PHYSICAL_CABLE


def test_neighbors_unknown_device():
    snap = _triangle_topology()
    nbrs = neighbors(snap, "nonexistent")
    assert nbrs == []


def test_neighbors_isolated_device():
    snap = _snap(
        {
            "ap1": Device(
                id="ap1", name="AP1", type=DeviceType.ACCESSPOINT, ports={"wlan0": _port()}
            )
        },
        [],
    )
    nbrs = neighbors(snap, "ap1")
    assert nbrs == []


def test_neighbors_multiple_links_same_pair():
    """Two links between the same devices return two neighbor entries."""
    snap = _snap(
        {
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
                ports={"ix1": _port(), "ix2": _port()},
            ),
        },
        [
            Link(
                id="link-a",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            ),
            Link(
                id="link-b",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e2"),
                    LinkEndpoint(device="fw1", port="ix2"),
                ),
            ),
        ],
    )
    nbrs = neighbors(snap, "sw1")
    assert len(nbrs) == 2
    link_ids = {n.link_id for n in nbrs}
    assert link_ids == {"link-a", "link-b"}
