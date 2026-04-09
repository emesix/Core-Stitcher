from __future__ import annotations

import pytest

from stitch.modelkit.enums import PortType, VlanMode
from stitch.modelkit.port import ExpectedNeighbor, Port, VlanMembership


def test_vlan_membership_minimal():
    vm = VlanMembership(mode=VlanMode.TRUNK, tagged=[10, 20])
    assert vm.mode == VlanMode.TRUNK
    assert vm.tagged == [10, 20]
    assert vm.native is None
    assert vm.access_vlan is None


def test_vlan_membership_full():
    vm = VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=[10, 20, 30], access_vlan=None)
    assert vm.native == 1
    assert len(vm.tagged) == 3


def test_vlan_membership_access():
    vm = VlanMembership(mode=VlanMode.ACCESS, tagged=[], access_vlan=42)
    assert vm.mode == VlanMode.ACCESS
    assert vm.access_vlan == 42


def test_vlan_membership_frozen():
    vm = VlanMembership(mode=VlanMode.TRUNK, tagged=[])
    with pytest.raises(Exception):
        vm.mode = VlanMode.ACCESS  # type: ignore[misc]


def test_expected_neighbor_minimal():
    en = ExpectedNeighbor(device="switch-a", port="eth0")
    assert en.device == "switch-a"
    assert en.port == "eth0"
    assert en.mac is None


def test_expected_neighbor_full():
    en = ExpectedNeighbor(device="switch-a", port="eth0", mac="aa:bb:cc:dd:ee:ff")
    assert en.mac == "aa:bb:cc:dd:ee:ff"


def test_expected_neighbor_frozen():
    en = ExpectedNeighbor(device="switch-a", port="eth0")
    with pytest.raises(Exception):
        en.device = "switch-b"  # type: ignore[misc]


def test_port_minimal():
    p = Port(type=PortType.ETHERNET)
    assert p.type == PortType.ETHERNET
    assert p.device_name is None
    assert p.vlans is None
    assert p.expected_neighbor is None


def test_port_full():
    vm = VlanMembership(mode=VlanMode.TRUNK, tagged=[10])
    en = ExpectedNeighbor(device="switch-a", port="eth0")
    p = Port(
        type=PortType.SFP_PLUS,
        device_name="ge-0/0/1",
        speed="10G",
        mac="aa:bb:cc:00:11:22",
        description="Uplink to core",
        vlans=vm,
        expected_neighbor=en,
    )
    assert p.speed == "10G"
    assert p.vlans is not None
    assert p.expected_neighbor is not None
