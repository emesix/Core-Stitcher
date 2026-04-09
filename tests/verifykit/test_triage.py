"""Tests for report triage ordering — presentation without behavior change.

Verifies that VerificationReport results are sorted by importance,
checks within links are sorted by severity, each link carries
highest_severity, and the report has an actionable highlights list.
"""

from __future__ import annotations

from stitch.modelkit.device import Device
from stitch.modelkit.enums import DeviceType, LinkType, PortType, VlanMode
from stitch.modelkit.link import Link, LinkEndpoint
from stitch.modelkit.port import Port, VlanMembership
from stitch.modelkit.topology import TopologyMeta, TopologySnapshot
from stitch.verifykit.engine import verify_topology

META = TopologyMeta(version="1.0", name="test")


def _trunk_port(tagged: list[int]) -> Port:
    return Port(
        type=PortType.SFP_PLUS,
        vlans=VlanMembership(mode=VlanMode.TRUNK, native=1, tagged=tagged),
    )


def _snap(devices: dict[str, Device], links: list[Link] | None = None) -> TopologySnapshot:
    return TopologySnapshot(meta=META, devices=devices, links=links or [])


def _mixed_report():
    """Create a report with pass, fail, and warning links."""
    devices = {
        "sw1": Device(
            id="sw1",
            name="SW1",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([25, 254]), "e2": _trunk_port([25])},
        ),
        "fw1": Device(
            id="fw1",
            name="FW1",
            type=DeviceType.FIREWALL,
            ports={"ix1": _trunk_port([25, 254])},
        ),
        "sw2": Device(
            id="sw2",
            name="SW2",
            type=DeviceType.SWITCH,
            ports={"e1": _trunk_port([254])},
        ),
    }
    links = [
        # This will pass (matching VLANs)
        Link(
            id="link-ok",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="e1"),
                LinkEndpoint(device="fw1", port="ix1"),
            ),
        ),
        # This will fail (ghost device missing)
        Link(
            id="link-fail",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="e1"),
                LinkEndpoint(device="ghost", port="e1"),
            ),
        ),
        # This will warn (no shared VLANs)
        Link(
            id="link-warn",
            type=LinkType.PHYSICAL_CABLE,
            endpoints=(
                LinkEndpoint(device="sw1", port="e2"),
                LinkEndpoint(device="sw2", port="e1"),
            ),
        ),
    ]
    declared = _snap(devices, links)
    observed = _snap(devices)
    return verify_topology(declared, observed)


# --- Result ordering ---


def test_results_ordered_fail_first():
    """Failed links appear before warning and passing links."""
    report = _mixed_report()
    statuses = [r.status for r in report.results]
    assert statuses[0] == "fail"
    # warning before pass
    assert statuses.index("pass") > statuses.index("warning") or "warning" not in statuses


def test_results_fail_before_warning_before_pass():
    report = _mixed_report()
    statuses = [r.status for r in report.results]
    assert statuses == ["fail", "warning", "pass"]


# --- Per-link highest_severity ---


def test_failing_link_has_error_severity():
    report = _mixed_report()
    fail_link = next(r for r in report.results if r.status == "fail")
    assert fail_link.highest_severity == "error"


def test_passing_link_has_info_severity():
    report = _mixed_report()
    pass_link = next(r for r in report.results if r.status == "pass")
    assert pass_link.highest_severity == "info"


def test_warning_link_has_warning_severity():
    report = _mixed_report()
    warn_link = next(r for r in report.results if r.status == "warning")
    assert warn_link.highest_severity == "warning"


# --- Check ordering within links ---


def test_checks_sorted_by_severity():
    """Within a link, error checks come before info checks."""
    report = _mixed_report()
    fail_link = next(r for r in report.results if r.status == "fail")
    severities = [c.severity for c in fail_link.checks]
    # error checks should come before info checks
    severity_order = {"error": 0, "warning": 1, "info": 2}
    ordered = sorted(severities, key=lambda s: severity_order.get(s, 9))
    assert severities == ordered


# --- Highlights ---


def test_report_has_highlights():
    report = _mixed_report()
    assert "highlights" in report.summary
    highlights = report.summary["highlights"]
    assert isinstance(highlights, list)
    assert len(highlights) > 0


def test_highlights_mention_categories():
    report = _mixed_report()
    highlights = report.summary["highlights"]
    text = " ".join(highlights)
    assert "endpoint_missing" in text or "missing" in text.lower()


def test_all_pass_has_clean_highlight():
    """When everything passes, highlights should reflect that."""
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
    highlights = report.summary["highlights"]
    assert len(highlights) == 1
    assert "pass" in highlights[0].lower() or "ok" in highlights[0].lower()


def test_empty_topology_highlights():
    report = verify_topology(_snap({}), _snap({}))
    highlights = report.summary["highlights"]
    assert len(highlights) >= 1
