from __future__ import annotations

import pytest
from pydantic import ValidationError

from vos.modelkit.device import Device, Position
from vos.modelkit.enums import DeviceType


def test_position_minimal():
    p = Position(x=1.0, y=2.0)
    assert p.x == 1.0
    assert p.y == 2.0


def test_position_frozen():
    p = Position(x=0.0, y=0.0)
    with pytest.raises(Exception):
        p.x = 5.0  # type: ignore[misc]


def test_device_minimal():
    d = Device(id="my-switch", name="My Switch", type=DeviceType.SWITCH)
    assert d.id == "my-switch"
    assert d.name == "My Switch"
    assert d.type == DeviceType.SWITCH
    assert d.ports == {}
    assert d.children == []


def test_device_full():
    d = Device(
        id="pve-node1",
        name="Proxmox Node 1",
        type=DeviceType.PROXMOX,
        model="Dell R720",
        management_ip="192.168.254.10",
        mcp_source="proxmox",
        position=Position(x=100.0, y=200.0),
        ports={},
        children=["vm-101", "vm-102"],
    )
    assert d.management_ip == "192.168.254.10"
    assert d.mcp_source == "proxmox"
    assert d.position is not None
    assert d.position.x == 100.0
    assert len(d.children) == 2


def test_device_id_slug_valid():
    d = Device(id="abc-123.def_ghi", name="Test", type=DeviceType.OTHER)
    assert d.id == "abc-123.def_ghi"


def test_device_id_slug_invalid_start():
    with pytest.raises(ValidationError):
        Device(id="-bad-start", name="Test", type=DeviceType.OTHER)


def test_device_id_slug_invalid_uppercase():
    with pytest.raises(ValidationError):
        Device(id="BadDevice", name="Test", type=DeviceType.OTHER)


def test_device_id_slug_invalid_space():
    with pytest.raises(ValidationError):
        Device(id="has space", name="Test", type=DeviceType.OTHER)
