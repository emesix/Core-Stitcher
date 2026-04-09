from __future__ import annotations

from datetime import UTC, datetime

from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.verification import CheckResult, LinkVerification, VerificationReport


def test_check_result_minimal():
    cr = CheckResult(
        check="vlan_membership",
        port="eth0",
        expected=10,
        observed=10,
        source=ObservationSource.MCP_LIVE,
        flag="ok",
    )
    assert cr.check == "vlan_membership"
    assert cr.port == "eth0"
    assert cr.flag == "ok"
    assert cr.message is None


def test_check_result_full():
    cr = CheckResult(
        check="speed_match",
        port="sfp1",
        expected="10G",
        observed="1G",
        source=ObservationSource.DECLARED,
        flag="mismatch",
        message="Speed lower than expected",
    )
    assert cr.flag == "mismatch"
    assert cr.message == "Speed lower than expected"


def test_link_verification_minimal():
    cr = CheckResult(
        check="vlan",
        port="eth0",
        expected=10,
        observed=10,
        source=ObservationSource.MCP_LIVE,
        flag="ok",
    )
    lv = LinkVerification(link="link-001", link_type="physical_cable", status="ok", checks=[cr])
    assert lv.link == "link-001"
    assert lv.status == "ok"
    assert len(lv.checks) == 1


def test_link_verification_empty_checks():
    lv = LinkVerification(link="link-002", link_type="bridge_member", status="unknown", checks=[])
    assert lv.checks == []


def test_verification_report_minimal():
    report = VerificationReport(results=[], summary={})
    assert report.results == []
    assert report.summary == {}
    assert isinstance(report.timestamp, datetime)


def test_verification_report_full():
    cr = CheckResult(
        check="vlan",
        port="eth0",
        expected=10,
        observed=20,
        source=ObservationSource.MCP_LIVE,
        flag="mismatch",
    )
    lv = LinkVerification(
        link="link-001", link_type="physical_cable", status="mismatch", checks=[cr]
    )
    now = datetime.now(UTC)
    report = VerificationReport(
        timestamp=now,
        results=[lv],
        summary={"ok": 0, "mismatch": 1},
    )
    assert len(report.results) == 1
    assert report.summary["mismatch"] == 1
    assert report.timestamp == now
