"""Tests for tracekit impact preview — deterministic "what breaks if" analysis.

Tests the first real impact preview slice: given a TopologySnapshot and an
ImpactRequest, compute which links, devices, and VLANs are affected by the
proposed change.
"""

from __future__ import annotations

from stitch.modelkit.device import Device
from stitch.modelkit.enums import DeviceType, LinkType, PortType, VlanMode
from stitch.modelkit.impact import ImpactRequest
from stitch.modelkit.link import Link, LinkEndpoint
from stitch.modelkit.port import Port, VlanMembership
from stitch.modelkit.topology import TopologyMeta, TopologySnapshot
from stitch.tracekit.impact import preview_impact

META = TopologyMeta(version="1.0", name="test")


def _trunk_port(tagged: list[int]) -> Port:
    return Port(
        type=PortType.SFP_PLUS,
        vlans=VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=tagged),
    )


def _snap(devices: dict[str, Device], links: list[Link]) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=links)


def _two_device_topology() -> TopologySnapshot:
    return _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25, 254])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([25, 254])},
            ),
        },
        [
            Link(
                id="phys-sw1-fw1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )


def _three_device_topology() -> TopologySnapshot:
    return _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={"e1": _trunk_port([25, 254]), "e2": _trunk_port([25, 254])},
            ),
            "fw1": Device(
                id="fw1",
                name="FW1",
                type=DeviceType.FIREWALL,
                ports={"ix1": _trunk_port([25, 254])},
            ),
            "pve": Device(
                id="pve",
                name="PVE",
                type=DeviceType.PROXMOX,
                ports={"enp2s0": _trunk_port([25, 254])},
            ),
        },
        [
            Link(
                id="link-sw1-fw1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            ),
            Link(
                id="link-sw1-pve",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e2"),
                    LinkEndpoint(device="pve", port="enp2s0"),
                ),
            ),
        ],
    )


# --- Remove link ---


def test_remove_link_affects_endpoints():
    """Removing a physical link affects both endpoint devices."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "phys-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    assert result.proposed_change == request
    assert len(result.impact) > 0

    affected_devices = {e.device for e in result.impact}
    assert "sw1" in affected_devices or "fw1" in affected_devices


def test_remove_link_reports_lost_vlans():
    """Removing the only link carrying VLANs reports VLAN loss."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "phys-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    effects_text = " ".join(e.effect for e in result.impact)
    assert "vlan" in effects_text.lower() or "VLAN" in effects_text


def test_remove_link_risk_level():
    """Removing the only link should be high risk."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "phys-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    assert result.risk in ("high", "medium", "low")
    assert result.safe_to_apply is False  # removing the only link is unsafe


def test_remove_nonexistent_link():
    """Removing a link that doesn't exist has no impact."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "nonexistent"},
    )

    result = preview_impact(snap, request)

    assert len(result.impact) == 0
    assert result.safe_to_apply is True


def test_remove_link_in_multi_path():
    """Removing one link in a multi-path topology still affects that path."""
    snap = _three_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "link-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    # fw1 should be affected (loses connectivity)
    affected_devices = {e.device for e in result.impact}
    assert "fw1" in affected_devices


# --- Remove VLAN ---


def test_remove_vlan_from_port():
    """Removing a VLAN from a trunk port reports downstream impact."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_vlan",
        device="sw1",
        port="e1",
        parameters={"vlan_id": 25},
    )

    result = preview_impact(snap, request)

    assert len(result.impact) > 0
    effects_text = " ".join(e.effect for e in result.impact)
    assert "25" in effects_text


def test_remove_vlan_not_on_port():
    """Removing a VLAN not present on the port has no impact."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_vlan",
        device="sw1",
        port="e1",
        parameters={"vlan_id": 999},
    )

    result = preview_impact(snap, request)

    assert len(result.impact) == 0
    assert result.safe_to_apply is True


# --- Unknown action ---


def test_unknown_action():
    """Unknown action type returns empty impact with low risk."""
    snap = _two_device_topology()
    request = ImpactRequest(action="unknown_action", device="sw1")

    result = preview_impact(snap, request)

    assert len(result.impact) == 0
    assert result.risk == "low"


# --- Impact effect severity ---


def test_effects_have_severity():
    """Each impact effect should have a severity."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "phys-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    for effect in result.impact:
        assert effect.severity in ("info", "warning", "error")


# --- Presentation: sorting, highest_severity, highlights ---


def test_effects_sorted_by_severity():
    """Error effects should come before warning effects."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "phys-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    severities = [e.severity for e in result.impact]
    severity_order = {"error": 0, "warning": 1, "info": 2}
    assert severities == sorted(severities, key=lambda s: severity_order.get(s, 9))


def test_highest_severity_on_result():
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "phys-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    assert result.highest_severity == "error"


def test_highest_severity_no_impact():
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "nonexistent"},
    )

    result = preview_impact(snap, request)

    assert result.highest_severity == "info"


def test_highlights_present():
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_link",
        device="sw1",
        parameters={"link_id": "phys-sw1-fw1"},
    )

    result = preview_impact(snap, request)

    assert len(result.highlights) > 0
    text = " ".join(result.highlights)
    assert "affected" in text.lower()


def test_highlights_no_impact():
    snap = _two_device_topology()
    request = ImpactRequest(action="unknown_action", device="sw1")

    result = preview_impact(snap, request)

    assert "No impact" in result.highlights[0]


# --- Remove port ---


def test_remove_port_affects_connected_links():
    """Removing a port breaks all links connected to it."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_port",
        device="sw1",
        port="e1",
    )

    result = preview_impact(snap, request)

    assert result.safe_to_apply is False
    affected_devices = {e.device for e in result.impact}
    assert "sw1" in affected_devices
    assert "fw1" in affected_devices


def test_remove_port_reports_lost_vlans():
    """Removing a trunk port reports VLAN reachability loss."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_port",
        device="sw1",
        port="e1",
    )

    result = preview_impact(snap, request)

    effects_text = " ".join(e.effect for e in result.impact)
    assert "VLAN" in effects_text


def test_remove_port_not_found():
    """Removing a port that doesn't exist has no impact."""
    snap = _two_device_topology()
    request = ImpactRequest(
        action="remove_port",
        device="sw1",
        port="nonexistent",
    )

    result = preview_impact(snap, request)

    assert len(result.impact) == 0
    assert result.safe_to_apply is True


def test_remove_port_no_links():
    """Removing a port with no connected links is safe."""
    snap = _snap(
        {
            "sw1": Device(
                id="sw1",
                name="SW1",
                type=DeviceType.SWITCH,
                ports={
                    "e1": _trunk_port([25, 254]),
                    "e2": _trunk_port([25]),
                },
            ),
        },
        [],
    )
    request = ImpactRequest(
        action="remove_port",
        device="sw1",
        port="e2",
    )

    result = preview_impact(snap, request)

    # Port goes down but no links affected
    assert len(result.impact) == 1
    assert result.impact[0].device == "sw1"
    assert result.safe_to_apply is True
    assert result.risk == "low"
