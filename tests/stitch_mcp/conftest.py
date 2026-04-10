"""Shared fixtures for stitch-mcp tests."""

import json

import pytest

from stitch.mcp.engine import StitchEngine

SAMPLE_TOPO = {
    "meta": {"version": "1.0", "name": "test-lab", "updated": "2026-01-01", "updated_by": "test"},
    "devices": {
        "sw01": {
            "id": "sw01",
            "name": "Lab Switch",
            "type": "switch",
            "model": "Mikrotik CRS309",
            "management_ip": "192.168.254.3",
            "ports": {
                "sfp-sfpplus1": {"type": "sfp+", "speed": "10G"},
                "sfp-sfpplus2": {"type": "sfp+", "speed": "10G"},
                "ether1": {"type": "ethernet", "speed": "1G"},
            },
        },
        "fw01": {
            "id": "fw01",
            "name": "OPNsense",
            "type": "firewall",
            "model": "Protectli VP2420",
            "management_ip": "192.168.254.1",
            "ports": {
                "ix0": {"type": "sfp+", "speed": "10G"},
                "ix1": {"type": "sfp+", "speed": "10G"},
            },
        },
        "pve01": {
            "id": "pve01",
            "name": "Proxmox Node",
            "type": "proxmox",
            "model": "Intel A770",
            "management_ip": "192.168.254.2",
            "ports": {
                "enp2s0": {"type": "ethernet", "speed": "2.5G"},
            },
        },
    },
    "links": [
        {
            "id": "link-sw01-fw01",
            "type": "physical_cable",
            "endpoints": [
                {"device": "sw01", "port": "sfp-sfpplus1"},
                {"device": "fw01", "port": "ix0"},
            ],
        },
        {
            "id": "link-sw01-pve01",
            "type": "physical_cable",
            "endpoints": [
                {"device": "sw01", "port": "ether1"},
                {"device": "pve01", "port": "enp2s0"},
            ],
        },
    ],
    "vlans": {
        "100": {"name": "management", "subnet": "192.168.254.0/24"},
        "200": {"name": "servers", "subnet": "192.168.200.0/24"},
    },
}


@pytest.fixture
def topology_file(tmp_path):
    p = tmp_path / "test-topo.json"
    p.write_text(json.dumps(SAMPLE_TOPO))
    return str(p)


@pytest.fixture
def engine(topology_file):
    return StitchEngine(topology_path=topology_file, gateway_url="http://localhost:4444")
