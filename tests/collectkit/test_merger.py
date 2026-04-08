from __future__ import annotations

from vos.collectkit.merger import merge_observations
from vos.modelkit.enums import DeviceType, ObservationSource, PortType
from vos.modelkit.observation import Observation


def _obs(
    device: str,
    field: str,
    value: object,
    *,
    port: str | None = None,
    source: ObservationSource = ObservationSource.MCP_LIVE,
    adapter: str | None = None,
) -> Observation:
    return Observation(
        device=device,
        port=port,
        field=field,
        value=value,
        source=source,
        adapter=adapter,
    )


def test_empty_observations():
    snap, conflicts = merge_observations([])
    assert len(snap.devices) == 0
    assert len(conflicts) == 0


def test_single_device_observation():
    obs = [
        _obs("onti-be", "type", "switch"),
        _obs("onti-be", "name", "ONTI-BE"),
        _obs("onti-be", "management_ip", "192.168.254.10"),
    ]
    snap, conflicts = merge_observations(obs)
    assert len(conflicts) == 0
    assert "onti-be" in snap.devices
    dev = snap.devices["onti-be"]
    assert dev.type == DeviceType.SWITCH
    assert dev.name == "ONTI-BE"
    assert dev.management_ip == "192.168.254.10"


def test_port_observations():
    obs = [
        _obs("onti-be", "type", "switch"),
        _obs("onti-be", "type", "sfp+", port="eth1"),
        _obs("onti-be", "device_name", "ge1", port="eth1"),
        _obs("onti-be", "mac", "aa:bb:cc:dd:ee:01", port="eth1"),
    ]
    snap, conflicts = merge_observations(obs)
    dev = snap.devices["onti-be"]
    assert "eth1" in dev.ports
    port = dev.ports["eth1"]
    assert port.type == PortType.SFP_PLUS
    assert port.device_name == "ge1"
    assert port.mac == "aa:bb:cc:dd:ee:01"


def test_conflict_detection():
    obs = [
        _obs("onti-be", "type", "switch"),
        _obs("onti-be", "status", "up", port="eth1", adapter="switchcraft"),
        _obs("onti-be", "status", "down", port="eth1", adapter="other-adapter"),
    ]
    snap, conflicts = merge_observations(obs)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.device == "onti-be"
    assert c.port == "eth1"
    assert c.field == "status"
    assert "up" in c.values
    assert "down" in c.values


def test_mcp_live_wins_over_declared():
    obs = [
        _obs("onti-be", "type", "switch"),
        _obs(
            "onti-be",
            "status",
            "down",
            port="eth1",
            source=ObservationSource.DECLARED,
            adapter="topology",
        ),
        _obs(
            "onti-be",
            "status",
            "up",
            port="eth1",
            source=ObservationSource.MCP_LIVE,
            adapter="switchcraft",
        ),
    ]
    snap, conflicts = merge_observations(obs)
    # mcp_live should win
    assert snap.devices["onti-be"].ports["eth1"].description == "up"


def test_no_conflict_when_values_agree():
    obs = [
        _obs("onti-be", "type", "switch"),
        _obs("onti-be", "status", "up", port="eth1", adapter="a"),
        _obs("onti-be", "status", "up", port="eth1", adapter="b"),
    ]
    snap, conflicts = merge_observations(obs)
    assert len(conflicts) == 0


def test_multiple_devices():
    obs = [
        _obs("onti-be", "type", "switch"),
        _obs("onti-be", "name", "ONTI-BE"),
        _obs("opnsense", "type", "firewall"),
        _obs("opnsense", "name", "OPNsense"),
    ]
    snap, conflicts = merge_observations(obs)
    assert len(snap.devices) == 2
    assert snap.devices["onti-be"].type == DeviceType.SWITCH
    assert snap.devices["opnsense"].type == DeviceType.FIREWALL


def test_vlan_membership_observation():
    vlans_data = {"mode": "trunk", "native": 1, "tagged": [25, 254]}
    obs = [
        _obs("onti-be", "type", "switch"),
        _obs("onti-be", "type", "sfp+", port="eth1"),
        _obs("onti-be", "vlans", vlans_data, port="eth1"),
    ]
    snap, conflicts = merge_observations(obs)
    port = snap.devices["onti-be"].ports["eth1"]
    assert port.vlans is not None
    assert port.vlans.native == 1
    assert 25 in port.vlans.tagged


def test_snapshot_meta():
    snap, _ = merge_observations([_obs("x", "type", "other")])
    assert snap.meta.version == "1.0"
    assert snap.meta.name == "observed"
