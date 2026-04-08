"""Tests for graphkit VLAN port queries."""

from __future__ import annotations

from vos.graphkit.vlan import vlan_ports
from vos.modelkit.device import Device
from vos.modelkit.enums import DeviceType, PortType, VlanMode
from vos.modelkit.port import Port, VlanMembership
from vos.modelkit.topology import TopologyMeta, TopologySnapshot

META = TopologyMeta(version="1.0", name="test")


def _trunk_port(tagged: list[int]) -> Port:
    return Port(
        type=PortType.SFP_PLUS,
        vlans=VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=tagged),
    )


def _access_port(vlan_id: int) -> Port:
    return Port(
        type=PortType.ETHERNET,
        vlans=VlanMembership(mode=VlanMode.ACCESS, access_vlan=vlan_id),
    )


def _snap(devices: dict[str, Device]) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=[])


def test_vlan_ports_finds_trunk():
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25, 254]), "e2": _trunk_port([254])},
            ),
        }
    )
    result = vlan_ports(snap, 25)
    assert len(result) == 1
    assert result[0].device == "sw1"
    assert result[0].port == "e1"
    assert result[0].mode == VlanMode.TRUNK


def test_vlan_ports_finds_access():
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _access_port(25), "e2": _access_port(254)},
            ),
        }
    )
    result = vlan_ports(snap, 25)
    assert len(result) == 1
    assert result[0].port == "e1"
    assert result[0].mode == VlanMode.ACCESS


def test_vlan_ports_across_devices():
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25, 254])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([25, 254])},
            ),
        }
    )
    result = vlan_ports(snap, 25)
    devices = {e.device for e in result}
    assert devices == {"sw1", "fw1"}


def test_vlan_ports_not_found():
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25])},
            ),
        }
    )
    result = vlan_ports(snap, 999)
    assert result == []


def test_vlan_ports_skips_no_vlans():
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": Port(type=PortType.SFP_PLUS)},
            ),
        }
    )
    result = vlan_ports(snap, 25)
    assert result == []


def test_vlan_ports_sorted_output():
    """Results are sorted by device, then port."""
    snap = _snap(
        {
            "zz": Device(
                id="zz",
                name="ZZ",
                type=DeviceType.SWITCH,
                ports={"b": _trunk_port([25]), "a": _trunk_port([25])},
            ),
            "aa": Device(
                id="aa",
                name="AA",
                type=DeviceType.SWITCH,
                ports={"x": _trunk_port([25])},
            ),
        }
    )
    result = vlan_ports(snap, 25)
    keys = [(e.device, e.port) for e in result]
    assert keys == [("aa", "x"), ("zz", "a"), ("zz", "b")]
