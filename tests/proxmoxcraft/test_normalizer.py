"""Tests for proxmoxcraft normalizer — Proxmox network data → Observations."""

from __future__ import annotations

import json
from pathlib import Path

from vos.modelkit.enums import ObservationSource, PortType
from vos.proxmoxcraft.normalizer import (
    _classify_port,
    normalize_network,
    normalize_node_identity,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "proxmox_pve_hx310_db.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# --- Port classification ---


def test_classify_bridge():
    assert _classify_port("bridge", "vmbr0") == PortType.BRIDGE


def test_classify_eth():
    assert _classify_port("eth", "enp2s0") == PortType.SFP_PLUS


def test_classify_vlan():
    assert _classify_port("vlan", "enp2s0.25") == PortType.VLAN


def test_classify_virtual():
    assert _classify_port("eth", "tap100i0") == PortType.VIRTUAL


# --- normalize_network ---


def test_network_ports_present():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    ports = {o.port for o in obs if o.port is not None}
    assert "enp2s0" in ports
    assert "vmbr0" in ports
    assert "vmbr1" in ports
    assert "enp2s0.25" in ports
    # loopback excluded
    assert "lo" not in ports


def test_bridge_type():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    vmbr0_type = [o for o in obs if o.port == "vmbr0" and o.field == "type"]
    assert vmbr0_type[0].value == "bridge"


def test_bridge_members():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    vmbr0_members = [o for o in obs if o.port == "vmbr0" and o.field == "bridge_members"]
    assert len(vmbr0_members) == 1
    assert vmbr0_members[0].value == ["enp2s0"]


def test_bridge_ip():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    vmbr0_ip = [o for o in obs if o.port == "vmbr0" and o.field == "addr4"]
    assert len(vmbr0_ip) == 1
    assert vmbr0_ip[0].value == "192.168.254.20/24"


def test_vlan_tag():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    vlan_obs = [o for o in obs if o.port == "enp2s0.25" and o.field == "vlans"]
    assert len(vlan_obs) == 1
    assert vlan_obs[0].value == {"mode": "access", "access_vlan": 25}


def test_vlan_parent():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    parent = [o for o in obs if o.port == "enp2s0.25" and o.field == "vlan_parent"]
    assert len(parent) == 1
    assert parent[0].value == "enp2s0"


def test_physical_nic_status():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    status = [o for o in obs if o.port == "enp2s0" and o.field == "status"]
    assert status[0].value == "up"


def test_all_observations_source():
    fixture = _load_fixture()
    obs = normalize_network("pve-hx310-db", fixture["network"])
    assert all(o.source == ObservationSource.MCP_LIVE for o in obs)
    assert all(o.adapter == "proxmoxcraft" for o in obs)


# --- normalize_node_identity ---


def test_node_identity():
    fixture = _load_fixture()
    obs = normalize_node_identity(
        "pve-hx310-db",
        fixture["node_status"],
        device_name="PVE-HX310-DB",
        management_ip="192.168.254.20",
    )
    type_obs = [o for o in obs if o.field == "type"]
    assert type_obs[0].value == "proxmox"
    name_obs = [o for o in obs if o.field == "name"]
    assert name_obs[0].value == "PVE-HX310-DB"
    model_obs = [o for o in obs if o.field == "model"]
    assert "pve-manager" in model_obs[0].value


# --- Edge cases ---


def test_empty_network():
    obs = normalize_network("x", [])
    assert obs == []
