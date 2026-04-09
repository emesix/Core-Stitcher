"""Tests for enriched verification reporting — categories, severity, and summary.

Verifies that every check result gets the correct category and severity,
and that the VerificationReport summary includes by_category and by_severity
breakdowns. Does NOT test pass/fail behavior — that's in test_engine.py.
"""

from __future__ import annotations

from stitch.modelkit.device import Device
from stitch.modelkit.enums import DeviceType, LinkType, PortType, VlanMode
from stitch.modelkit.link import Link, LinkEndpoint
from stitch.modelkit.port import ExpectedNeighbor, Port, VlanMembership
from stitch.modelkit.topology import TopologyMeta, TopologySnapshot
from stitch.verifykit.engine import verify_topology

META = TopologyMeta(version="1.0", name="test")


def _trunk_port(tagged: list[int], *, neighbor: ExpectedNeighbor | None = None) -> Port:
    return Port(
        type=PortType.SFP_PLUS,
        vlans=VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=tagged),
        expected_neighbor=neighbor,
    )


def _snap(devices: dict[str, Device], links: list[Link] | None = None) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=links or [])


# --- Category mapping ---


def test_missing_device_category():
    declared = _snap(
        {
            "sw1": Device(
                id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _trunk_port([])}
            )
        },
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="ghost", port="e1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap({"sw1": declared.devices["sw1"]}))
    missing = [c for c in report.results[0].checks if c.flag == "missing"]
    assert len(missing) >= 1
    assert all(c.category == "endpoint_missing" for c in missing)


def test_missing_port_category():
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([]), "e2": _trunk_port([])},
        ),
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.BRIDGE_MEMBER,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="sw1", port="e2"),
                ),
            )
        ],
    )
    observed = _snap(
        {
            "sw1": Device(
                id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _trunk_port([])}
            ),
        }
    )
    report = verify_topology(declared, observed)
    missing = [
        c for c in report.results[0].checks if c.check == "port_exists" and c.flag == "missing"
    ]
    assert len(missing) == 1
    assert missing[0].category == "endpoint_missing"


def test_neighbor_mismatch_category():
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([25], neighbor=ExpectedNeighbor(device="fw1", port="ix1"))},
        ),
        "sw2": Device(
            id="sw2",
            name="SW2",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([25])},
        ),
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="sw2", port="e1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap(devices))
    neighbor = [c for c in report.results[0].checks if c.check == "neighbor_match"]
    assert neighbor[0].category == "neighbor_mismatch"


def test_vlan_warning_category():
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([25])},
        ),
        "sw2": Device(
            id="sw2",
            name="SW2",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([254])},
        ),
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="sw2", port="e1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap(devices))
    vlan = [c for c in report.results[0].checks if c.check == "vlan_compatibility"]
    assert vlan[0].category == "vlan_mismatch"
    assert vlan[0].flag == "warning"


def test_ok_checks_have_no_category():
    devices = {
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
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap(devices))
    ok_checks = [c for c in report.results[0].checks if c.flag == "ok"]
    assert len(ok_checks) > 0
    assert all(c.category is None for c in ok_checks)


# --- Severity mapping ---


def test_ok_check_severity_info():
    devices = {
        "pve": Device(
            id="pve",
            name="PVE",
            type=DeviceType.PROXMOX,
            ports={"e1": Port(type=PortType.SFP_PLUS), "vmbr0": Port(type=PortType.BRIDGE)},
        ),
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.BRIDGE_MEMBER,
                endpoints=(
                    LinkEndpoint(device="pve", port="e1"),
                    LinkEndpoint(device="pve", port="vmbr0"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap(devices))
    ok_checks = [c for c in report.results[0].checks if c.flag == "ok"]
    assert all(c.severity == "info" for c in ok_checks)


def test_missing_check_severity_error():
    declared = _snap(
        {
            "sw1": Device(
                id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _trunk_port([])}
            )
        },
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="ghost", port="e1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap({"sw1": declared.devices["sw1"]}))
    missing = [c for c in report.results[0].checks if c.flag == "missing"]
    assert all(c.severity == "error" for c in missing)


def test_warning_check_severity_warning():
    devices = {
        "sw1": Device(
            id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _trunk_port([25])}
        ),
        "sw2": Device(
            id="sw2", name="SW2", type=DeviceType.SWITCH, ports={"e1": _trunk_port([254])}
        ),
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="sw2", port="e1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap(devices))
    warnings = [c for c in report.results[0].checks if c.flag == "warning"]
    assert all(c.severity == "warning" for c in warnings)


# --- Summary by_category and by_severity ---


def test_summary_has_by_category():
    declared = _snap(
        {
            "sw1": Device(
                id="sw1", name="SW1", type=DeviceType.SWITCH, ports={"e1": _trunk_port([])}
            )
        },
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="ghost", port="e1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap({"sw1": declared.devices["sw1"]}))
    assert "by_category" in report.summary
    assert report.summary["by_category"]["endpoint_missing"] >= 1


def test_summary_has_by_severity():
    devices = {
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
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap(devices))
    assert "by_severity" in report.summary
    assert report.summary["by_severity"]["info"] > 0


def test_summary_mixed_results():
    """Report with both passing and failing links has correct counts."""
    devices = {
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
    }
    links = [
        Link(
            id="ok-link",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="e1"),
                LinkEndpoint(device="fw1", port="ix1"),
            ),
        ),
        Link(
            id="bad-link",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="e1"),
                LinkEndpoint(device="ghost", port="e1"),
            ),
        ),
    ]
    declared = _snap(devices, links)
    report = verify_topology(declared, _snap(devices))

    assert report.summary["total"] == 2
    assert report.summary["pass"] == 1
    assert report.summary["fail"] == 1
    assert report.summary["by_category"]["endpoint_missing"] >= 1
    assert report.summary["by_severity"]["info"] > 0
    assert report.summary["by_severity"]["error"] >= 1


def test_summary_empty_categories_when_all_pass():
    """When all checks pass, by_category should be empty."""
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([25])},
        ),
        "fw1": Device(
            id="fw1",
            name="FW1",
            type=DeviceType.FIREWALL,
            ports={"ix1": _trunk_port([25])},
        ),
    }
    declared = _snap(
        devices,
        [
            Link(
                id="l1",
                type=LinkType.PHYSICAL_CABLE,
                endpoints=(
                    LinkEndpoint(device="sw1", port="e1"),
                    LinkEndpoint(device="fw1", port="ix1"),
                ),
            )
        ],
    )
    report = verify_topology(declared, _snap(devices))
    assert report.summary["by_category"] == {}
    assert report.summary["by_severity"]["info"] > 0
