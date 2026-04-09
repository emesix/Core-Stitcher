"""Tests for graphkit BFS traversal."""

from __future__ import annotations

from stitch.graphkit.traversal import bfs
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


def _chain_topology() -> TopologySnapshot:
    """Linear chain: sw1 -- fw1 -- pve."""
    return _snap(
        {
            "sw1": Device(id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _port()}),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _port(), "ix2": _port()},
            ),
            "pve": Device(id="pve", name="PVE", type=DeviceType.PROXMOX, ports={"enp2s0": _port()}),
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
                id="link-fw1-pve",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="fw1", port="ix2"),
                    LinkEndpoint(device="pve", port="enp2s0"),
                ),
            ),
        ],
    )


def test_bfs_visits_all_reachable():
    snap = _chain_topology()
    result = bfs(snap, "sw1")
    assert set(result) == {"sw1", "fw1", "pve"}


def test_bfs_order_is_breadth_first():
    snap = _chain_topology()
    result = bfs(snap, "sw1")
    assert result[0] == "sw1"
    assert result[1] == "fw1"
    assert result[2] == "pve"


def test_bfs_from_middle():
    snap = _chain_topology()
    result = bfs(snap, "fw1")
    assert result[0] == "fw1"
    assert set(result) == {"sw1", "fw1", "pve"}


def test_bfs_nonexistent_start():
    snap = _chain_topology()
    result = bfs(snap, "nonexistent")
    assert result == []


def test_bfs_isolated_device():
    snap = _snap(
        {
            "sw1": Device(id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _port()}),
            "ap1": Device(
                id="ap1", name="AP1", type=DeviceType.ACCESSPOINT, ports={"wlan0": _port()}
            ),
        },
        [],
    )
    result = bfs(snap, "sw1")
    assert result == ["sw1"]


def test_bfs_with_predicate():
    snap = _chain_topology()
    result = bfs(snap, "sw1", predicate=lambda d: d != "pve")
    assert "sw1" in result
    assert "fw1" in result
    assert "pve" not in result


def test_bfs_cycle():
    """BFS should not revisit devices even with cycles."""
    snap = _snap(
        {
            "a": Device(
                id="a", name="A", type=DeviceType.SWITCH, ports={"p1": _port(), "p2": _port()}
            ),
            "b": Device(
                id="b", name="B", type=DeviceType.SWITCH, ports={"p1": _port(), "p2": _port()}
            ),
            "c": Device(
                id="c", name="C", type=DeviceType.SWITCH, ports={"p1": _port(), "p2": _port()}
            ),
        },
        [
            Link(
                id="ab",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="a", port="p1"),
                    LinkEndpoint(device="b", port="p1"),
                ),
            ),
            Link(
                id="bc",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="b", port="p2"),
                    LinkEndpoint(device="c", port="p1"),
                ),
            ),
            Link(
                id="ca",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="c", port="p2"),
                    LinkEndpoint(device="a", port="p2"),
                ),
            ),
        ],
    )
    result = bfs(snap, "a")
    assert len(result) == 3
    assert len(set(result)) == 3  # no duplicates
