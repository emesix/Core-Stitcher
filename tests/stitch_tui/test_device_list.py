"""Tests for the device list screen."""

from __future__ import annotations

from stitch.apps.tui.screens.device_list import DeviceListScreen


def test_device_list_screen_creation():
    items = [
        {
            "name": "sw-core-01",
            "type": "SWITCH",
            "model": "USW-Pro-48",
            "management_ip": "192.168.254.2",
        },
        {
            "name": "fw-main",
            "type": "FIREWALL",
            "model": "OPNsense",
            "management_ip": "192.168.254.1",
        },
    ]
    screen = DeviceListScreen(items=items)
    assert screen.items == items
    assert len(screen.items) == 2


def test_device_list_empty():
    screen = DeviceListScreen(items=[])
    assert screen.items == []
