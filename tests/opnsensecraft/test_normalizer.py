"""Tests for opnsensecraft normalizer — OPNsense interfaces → Observations."""

from __future__ import annotations

import json
from pathlib import Path

from vos.modelkit.enums import ObservationSource, PortType
from vos.opnsensecraft.normalizer import (
    _classify_port,
    _parse_speed,
    normalize_device_identity,
    normalize_interfaces,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "opnsense_interfaces.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# --- Port classification ---


def test_classify_sfp_port():
    assert _classify_port({"device": "ix0", "is_physical": True}) == PortType.SFP_PLUS


def test_classify_virtual_port():
    assert _classify_port({"device": "vtnet0", "is_physical": True}) == PortType.VIRTUAL


def test_classify_vlan_port():
    assert _classify_port({"device": "vlan01", "vlan_tag": "25"}) == PortType.VLAN


def test_classify_bridge_port():
    assert _classify_port({"device": "bridge0", "members": {"a": {}}}) == PortType.BRIDGE


# --- Speed parsing ---


def test_parse_speed_10g():
    assert _parse_speed("10Gbase-Twinax <full-duplex>") == "10G"


def test_parse_speed_1g():
    assert _parse_speed("1000baseT <full-duplex>") == "1G"


def test_parse_speed_2_5g():
    assert _parse_speed("2500Base-T <full-duplex>") == "2.5G"


def test_parse_speed_none():
    assert _parse_speed("Ethernet autoselect") is None


# --- normalize_interfaces ---


def test_all_ports_present():
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    ports = {o.port for o in obs if o.port is not None}
    assert "ix0" in ports
    assert "ix1" in ports
    assert "vtnet0" in ports
    assert "vlan01" in ports
    assert "bridge0" in ports


def test_physical_port_observations():
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    ix1_type = [o for o in obs if o.port == "ix1" and o.field == "type"]
    assert len(ix1_type) == 1
    assert ix1_type[0].value == "sfp+"

    ix1_mac = [o for o in obs if o.port == "ix1" and o.field == "mac"]
    assert ix1_mac[0].value == "20:7c:14:f4:78:77"

    ix1_speed = [o for o in obs if o.port == "ix1" and o.field == "speed"]
    assert ix1_speed[0].value == "10G"


def test_vlan_tag_observation():
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    vlan01_vlans = [o for o in obs if o.port == "vlan01" and o.field == "vlans"]
    assert len(vlan01_vlans) == 1
    assert vlan01_vlans[0].value == {"mode": "access", "access_vlan": 25}


def test_vlan_parent_observation():
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    vlan01_parent = [o for o in obs if o.port == "vlan01" and o.field == "vlan_parent"]
    assert len(vlan01_parent) == 1
    assert vlan01_parent[0].value == "ix0"


def test_parent_gets_tagged_vlans():
    """Parent interface should get trunk VLAN membership from its children."""
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    ix0_vlans = [o for o in obs if o.port == "ix0" and o.field == "vlans"]
    assert len(ix0_vlans) == 1
    assert ix0_vlans[0].value["mode"] == "trunk"
    assert 25 in ix0_vlans[0].value["tagged"]
    assert 254 in ix0_vlans[0].value["tagged"]


def test_bridge_members_observation():
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    bridge_members = [o for o in obs if o.port == "bridge0" and o.field == "bridge_members"]
    assert len(bridge_members) == 1
    assert sorted(bridge_members[0].value) == ["vlan02", "vlan03", "vtnet0"]


def test_ip_address_observation():
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    bridge_ip = [o for o in obs if o.port == "bridge0" and o.field == "addr4"]
    assert len(bridge_ip) == 1
    assert bridge_ip[0].value == "192.168.254.1/24"


def test_all_observations_source():
    fixture = _load_fixture()
    obs = normalize_interfaces("opnsense", fixture)
    assert all(o.source == ObservationSource.MCP_LIVE for o in obs)
    assert all(o.adapter == "opnsensecraft" for o in obs)


# --- normalize_device_identity ---


def test_device_identity():
    obs = normalize_device_identity(
        "opnsense",
        device_name="OPNsense",
        management_ip="192.168.254.1",
    )
    type_obs = [o for o in obs if o.field == "type"]
    assert type_obs[0].value == "firewall"
    name_obs = [o for o in obs if o.field == "name"]
    assert name_obs[0].value == "OPNsense"
    ip_obs = [o for o in obs if o.field == "management_ip"]
    assert ip_obs[0].value == "192.168.254.1"


# --- Edge cases ---


def test_empty_rows():
    obs = normalize_interfaces("x", {"rows": []})
    assert obs == []
