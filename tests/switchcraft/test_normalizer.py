"""Tests for switchcraft normalizer — MCP response → Observation conversion.

Uses fixture data matching the shape returned by switchcraft MCP tools
for an ONTI OGF 8-port SFP+ switch.
"""

from __future__ import annotations

import json
from pathlib import Path

from vos.modelkit.enums import ObservationSource
from vos.switchcraft.normalizer import (
    _port_alias,
    normalize_ports,
    normalize_status,
    normalize_vlans,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "switchcraft_onti_backend.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


# --- Port alias conversion ---


def test_port_alias_onti():
    assert _port_alias("Ethernet1/0/1") == "eth1"
    assert _port_alias("Ethernet1/0/8") == "eth8"


def test_port_alias_brocade():
    assert _port_alias("1/1/5") == "ge5"
    assert _port_alias("1/1/24") == "ge24"


def test_port_alias_jtcom():
    assert _port_alias("Port1") == "port1"
    assert _port_alias("Port9") == "port9"


def test_port_alias_passthrough():
    assert _port_alias("ge1") == "ge1"
    assert _port_alias("eth0") == "eth0"


# --- normalize_ports ---


def test_normalize_ports_count():
    fixture = _load_fixture()
    obs = normalize_ports("onti-be", fixture["get_ports"])
    # 8 ports × (type + device_name + enabled + status) = 32
    # plus speed for ports that have it (4 UP ports) = 36
    assert len(obs) >= 32


def test_normalize_ports_aliases():
    fixture = _load_fixture()
    obs = normalize_ports("onti-be", fixture["get_ports"])
    port_aliases = {o.port for o in obs if o.port is not None}
    assert "eth1" in port_aliases
    assert "eth8" in port_aliases


def test_normalize_ports_device_name():
    fixture = _load_fixture()
    obs = normalize_ports("onti-be", fixture["get_ports"])
    name_obs = [o for o in obs if o.field == "device_name" and o.port == "eth1"]
    assert len(name_obs) == 1
    assert name_obs[0].value == "Ethernet1/0/1"


def test_normalize_ports_speed():
    fixture = _load_fixture()
    obs = normalize_ports("onti-be", fixture["get_ports"])
    speed_obs = [o for o in obs if o.field == "speed" and o.port == "eth1"]
    assert len(speed_obs) == 1
    assert speed_obs[0].value == "10G"


def test_normalize_ports_no_speed_when_down():
    fixture = _load_fixture()
    obs = normalize_ports("onti-be", fixture["get_ports"])
    speed_obs = [o for o in obs if o.field == "speed" and o.port == "eth5"]
    assert len(speed_obs) == 0  # no speed observation for down ports


def test_normalize_ports_status():
    fixture = _load_fixture()
    obs = normalize_ports("onti-be", fixture["get_ports"])
    up = [o for o in obs if o.field == "status" and o.port == "eth1"]
    down = [o for o in obs if o.field == "status" and o.port == "eth5"]
    assert up[0].value == "up"
    assert down[0].value == "down"


def test_normalize_ports_source():
    fixture = _load_fixture()
    obs = normalize_ports("onti-be", fixture["get_ports"])
    assert all(o.source == ObservationSource.MCP_LIVE for o in obs)
    assert all(o.adapter == "switchcraft" for o in obs)


# --- normalize_vlans ---


def test_normalize_vlans_per_port():
    fixture = _load_fixture()
    obs = normalize_vlans("onti-be", fixture["get_vlans"])
    # eth1-eth4 are in VLANs 25 and 254 (untagged both), eth5-eth8 in VLAN 1
    assert len(obs) == 8  # one VLAN observation per port


def test_normalize_vlans_multi_membership():
    """Ports in multiple untagged VLANs get trunk-like membership."""
    fixture = _load_fixture()
    obs = normalize_vlans("onti-be", fixture["get_vlans"])
    eth1_vlans = [o for o in obs if o.port == "eth1"]
    assert len(eth1_vlans) == 1
    vlans_data = eth1_vlans[0].value
    # eth1 is in VLANs 25 and 254 (both untagged for ONTI)
    assert vlans_data["mode"] == "trunk"
    assert vlans_data["native"] == 25  # first untagged VLAN seen


def test_normalize_vlans_single_membership():
    """Ports in only one VLAN get access membership."""
    fixture = _load_fixture()
    obs = normalize_vlans("onti-be", fixture["get_vlans"])
    eth5_vlans = [o for o in obs if o.port == "eth5"]
    assert len(eth5_vlans) == 1
    vlans_data = eth5_vlans[0].value
    assert vlans_data["mode"] == "access"
    assert vlans_data["access_vlan"] == 1


# --- normalize_status ---


def test_normalize_status_device_type():
    fixture = _load_fixture()
    obs = normalize_status("onti-be", fixture["device_status"], device_name="ONTI-BE")
    type_obs = [o for o in obs if o.field == "type"]
    assert len(type_obs) == 1
    assert type_obs[0].value == "switch"
    assert type_obs[0].port is None


def test_normalize_status_device_name():
    fixture = _load_fixture()
    obs = normalize_status("onti-be", fixture["device_status"], device_name="ONTI-BE")
    name_obs = [o for o in obs if o.field == "name"]
    assert len(name_obs) == 1
    assert name_obs[0].value == "ONTI-BE"


def test_normalize_status_firmware():
    fixture = _load_fixture()
    obs = normalize_status("onti-be", fixture["device_status"])
    model_obs = [o for o in obs if o.field == "model"]
    assert len(model_obs) == 1
    assert model_obs[0].value == "V300SP10250704"


def test_normalize_status_reachable():
    fixture = _load_fixture()
    obs = normalize_status("onti-be", fixture["device_status"])
    reach_obs = [o for o in obs if o.field == "reachable"]
    assert len(reach_obs) == 1
    assert reach_obs[0].value is True


# --- Edge cases ---


def test_normalize_ports_empty():
    obs = normalize_ports("x", {"device_id": "x", "ports": []})
    assert obs == []


def test_normalize_vlans_empty():
    obs = normalize_vlans("x", {"device_id": "x", "vlans": []})
    assert obs == []


def test_normalize_status_unreachable():
    obs = normalize_status(
        "dead-switch",
        {"device_id": "dead", "reachable": False, "error": "timeout"},
    )
    reach_obs = [o for o in obs if o.field == "reachable"]
    assert reach_obs[0].value is False
