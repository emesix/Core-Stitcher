from __future__ import annotations

import json
from pathlib import Path

import pytest

from vos.modelkit.enums import DeviceType, LinkType, PortType, VlanMode
from vos.storekit import load_topology, save_topology
from vos.storekit.loader import TopologyVersionError

FIXTURE = Path(__file__).parent.parent / "fixtures" / "topology_sample.json"


def test_load_sample_topology():
    snap = load_topology(FIXTURE)
    assert snap.meta.name == "homelab-sample"
    assert snap.meta.version == "1.0"
    assert len(snap.devices) == 3
    assert len(snap.links) == 3
    assert len(snap.vlans) == 2


def test_load_devices():
    snap = load_topology(FIXTURE)
    onti = snap.devices["onti-be"]
    assert onti.type == DeviceType.SWITCH
    assert onti.management_ip == "192.168.254.10"
    assert len(onti.ports) == 2

    fw = snap.devices["opnsense"]
    assert fw.type == DeviceType.FIREWALL

    pve = snap.devices["pve-hx310-db"]
    assert pve.type == DeviceType.PROXMOX


def test_load_ports_and_vlans():
    snap = load_topology(FIXTURE)
    eth1 = snap.devices["onti-be"].ports["eth1"]
    assert eth1.type == PortType.SFP_PLUS
    assert eth1.vlans is not None
    assert eth1.vlans.mode == VlanMode.TRUNK
    assert 25 in eth1.vlans.tagged
    assert 254 in eth1.vlans.tagged
    assert eth1.expected_neighbor is not None
    assert eth1.expected_neighbor.device == "opnsense"


def test_load_links():
    snap = load_topology(FIXTURE)
    phys_link = snap.links[0]
    assert phys_link.type == LinkType.PHYSICAL_CABLE
    assert phys_link.endpoints[0].device == "opnsense"

    bridge_link = snap.links[2]
    assert bridge_link.type == LinkType.BRIDGE_MEMBER


def test_load_vlan_metadata():
    snap = load_topology(FIXTURE)
    assert snap.vlans["25"].name == "IoT"
    assert snap.vlans["254"].subnet == "192.168.254.0/24"


def test_roundtrip(tmp_path: Path):
    snap = load_topology(FIXTURE)
    out = tmp_path / "topology_out.json"
    save_topology(snap, out)

    reloaded = load_topology(out)
    assert reloaded.meta.name == snap.meta.name
    assert len(reloaded.devices) == len(snap.devices)
    assert len(reloaded.links) == len(snap.links)
    assert len(reloaded.vlans) == len(snap.vlans)


def test_unsupported_version(tmp_path: Path):
    data = {
        "meta": {"version": "99.0", "name": "bad"},
        "devices": {},
        "links": [],
        "vlans": {},
    }
    path = tmp_path / "bad_version.json"
    path.write_text(json.dumps(data))

    with pytest.raises(TopologyVersionError, match="99.0"):
        load_topology(path)


def test_missing_version(tmp_path: Path):
    data = {"meta": {"name": "no-version"}, "devices": {}, "links": [], "vlans": {}}
    path = tmp_path / "no_version.json"
    path.write_text(json.dumps(data))

    with pytest.raises(TopologyVersionError, match="missing"):
        load_topology(path)


def test_invalid_json(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("not json at all")

    with pytest.raises(json.JSONDecodeError):
        load_topology(path)


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_topology("/nonexistent/topology.json")
