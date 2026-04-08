"""Tests for graphkit topology diagnostics."""

from __future__ import annotations

from vos.graphkit.diagnostics import (
    dangling_ports,
    diagnostics,
    missing_endpoints,
    orphan_devices,
)
from vos.modelkit.device import Device
from vos.modelkit.enums import DeviceType, LinkType, PortType
from vos.modelkit.link import Link, LinkEndpoint
from vos.modelkit.port import Port
from vos.modelkit.topology import TopologyMeta, TopologySnapshot

META = TopologyMeta(version="1.0", name="test")


def _port() -> Port:
    return Port(type=PortType.SFP_PLUS)


def _snap(devices: dict[str, Device], links: list[Link]) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=links)


def _connected_topology() -> TopologySnapshot:
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
                ports={"ix1": _port()},
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
        ],
    )


def test_dangling_ports_finds_unlinked():
    snap = _connected_topology()
    result = dangling_ports(snap)
    assert len(result) == 1
    assert result[0].device == "sw1"
    assert result[0].port == "e2"


def test_dangling_ports_none_when_all_linked():
    snap = _snap(
        {
            "sw1": Device(id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _port()}),
            "fw1": Device(id="fw1", name="FW1", type=DeviceType.FIREWALL, ports={"ix1": _port()}),
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
        ],
    )
    result = dangling_ports(snap)
    assert result == []


def test_orphan_devices_finds_isolated():
    snap = _snap(
        {
            "sw1": Device(id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _port()}),
            "ap1": Device(
                id="ap1", name="AP1", type=DeviceType.ACCESSPOINT, ports={"wlan0": _port()}
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
        ],
    )
    result = orphan_devices(snap)
    assert result == ["ap1"]


def test_orphan_devices_none_when_all_connected():
    snap = _connected_topology()
    result = orphan_devices(snap)
    assert result == []


def test_missing_endpoints_device_not_found():
    snap = _snap(
        {"sw1": Device(id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _port()})},
        [
            Link(
                id="link-a",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="gone", port="p1"),
                ),
            ),
        ],
    )
    result = missing_endpoints(snap)
    assert len(result) == 1
    assert "gone" in result[0]


def test_missing_endpoints_port_not_found():
    snap = _snap(
        {
            "sw1": Device(id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _port()}),
            "fw1": Device(id="fw1", name="FW1", type=DeviceType.FIREWALL, ports={"ix1": _port()}),
        },
        [
            Link(
                id="link-a",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="wrongport"),
                ),
            ),
        ],
    )
    result = missing_endpoints(snap)
    assert len(result) == 1
    assert "wrongport" in result[0]


def test_missing_endpoints_none_when_valid():
    snap = _connected_topology()
    result = missing_endpoints(snap)
    assert result == []


def test_diagnostics_totals():
    snap = _connected_topology()
    diag = diagnostics(snap)
    assert diag.total_devices == 2
    assert diag.total_ports == 3  # sw1 has 2, fw1 has 1
    assert diag.total_links == 1


def test_diagnostics_includes_dangling():
    snap = _connected_topology()
    diag = diagnostics(snap)
    assert len(diag.dangling_ports) == 1
    assert diag.dangling_ports[0].port == "e2"
