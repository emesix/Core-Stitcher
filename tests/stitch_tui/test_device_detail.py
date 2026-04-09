"""Tests for the device detail screen."""

from __future__ import annotations

from stitch.apps.tui.screens.device_detail import DeviceDetailScreen


def test_device_detail_creation():
    device = {
        "name": "sw-core-01",
        "type": "SWITCH",
        "model": "USW-Pro-48",
        "management_ip": "192.168.254.2",
        "mcp_source": "switchcraft",
        "ports": [{"name": "sfp-0", "type": "SFP_PLUS", "speed": "10G"}],
    }
    screen = DeviceDetailScreen(device=device)
    assert screen.device["name"] == "sw-core-01"


def test_device_detail_with_neighbors():
    device = {"name": "sw-core-01", "type": "SWITCH", "ports": []}
    neighbors = [{"device": "fw-main", "local_port": "sfp-0", "remote_port": "igb0"}]
    screen = DeviceDetailScreen(device=device, neighbors=neighbors)
    assert len(screen.neighbors) == 1
