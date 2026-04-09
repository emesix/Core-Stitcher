"""Tests for verification diff engine."""

from __future__ import annotations

from datetime import UTC, datetime

from stitch.modelkit.diff import VerificationDiff
from stitch.modelkit.enums import ObservationSource
from stitch.modelkit.verification import CheckResult, LinkVerification, VerificationReport
from stitch.verifykit.diff import diff_reports


def _check(
    check: str = "port_type",
    port: str = "eth1",
    flag: str = "pass",
    expected: str = "sfp+",
    observed: str = "sfp+",
) -> CheckResult:
    return CheckResult(
        check=check,
        port=port,
        expected=expected,
        observed=observed,
        source=ObservationSource.MCP_LIVE,
        flag=flag,
    )


def _link(
    link: str = "link-1",
    status: str = "pass",
    checks: list[CheckResult] | None = None,
) -> LinkVerification:
    return LinkVerification(
        link=link,
        link_type="physical_cable",
        status=status,
        checks=checks or [],
    )


def _report(
    results: list[LinkVerification] | None = None,
    ts: datetime | None = None,
) -> VerificationReport:
    return VerificationReport(
        timestamp=ts or datetime(2026, 4, 8, 10, 0, 0, tzinfo=UTC),
        results=results or [],
    )


# --- No change ---


def test_identical_reports():
    checks = [_check()]
    r = _report([_link(checks=checks)])
    diff = diff_reports(r, r)
    assert diff.summary.unchanged == 1
    assert diff.summary.added == 0
    assert diff.summary.removed == 0
    assert diff.summary.changed == 0


def test_both_empty():
    diff = diff_reports(_report(), _report())
    assert diff.links == []
    assert diff.summary.unchanged == 0


# --- Added ---


def test_link_added():
    before = _report([])
    after = _report([_link("new-link")])
    diff = diff_reports(before, after)
    assert diff.summary.added == 1
    assert diff.links[0].link == "new-link"
    assert diff.links[0].change == "added"


def test_check_added_within_link():
    before = _report([_link("link-1", checks=[_check(check="type", port="eth1")])])
    after = _report(
        [
            _link(
                "link-1",
                checks=[
                    _check(check="type", port="eth1"),
                    _check(check="speed", port="eth1", flag="mismatch"),
                ],
            )
        ]
    )
    diff = diff_reports(before, after)
    assert diff.summary.changed == 1
    link_diff = diff.links[0]
    assert len(link_diff.check_diffs) == 1
    assert link_diff.check_diffs[0].change == "added"
    assert link_diff.check_diffs[0].check == "speed"


# --- Removed ---


def test_link_removed():
    before = _report([_link("old-link")])
    after = _report([])
    diff = diff_reports(before, after)
    assert diff.summary.removed == 1
    assert diff.links[0].change == "removed"


def test_check_removed_within_link():
    before = _report(
        [_link("link-1", checks=[_check(check="type"), _check(check="speed")])]
    )
    after = _report([_link("link-1", checks=[_check(check="type")])])
    diff = diff_reports(before, after)
    assert diff.summary.changed == 1
    assert diff.links[0].check_diffs[0].change == "removed"
    assert diff.links[0].check_diffs[0].check == "speed"


# --- Changed ---


def test_check_flag_changed():
    before = _report([_link("link-1", checks=[_check(flag="pass")])])
    after = _report([_link("link-1", checks=[_check(flag="mismatch")])])
    diff = diff_reports(before, after)
    assert diff.summary.changed == 1
    cd = diff.links[0].check_diffs[0]
    assert cd.change == "changed"
    assert cd.before_flag == "pass"
    assert cd.after_flag == "mismatch"


# --- Mixed ---


def test_mixed_changes():
    before = _report([_link("link-a"), _link("link-b")])
    after = _report([_link("link-b"), _link("link-c")])
    diff = diff_reports(before, after)
    assert diff.summary.removed == 1  # link-a
    assert diff.summary.unchanged == 1  # link-b
    assert diff.summary.added == 1  # link-c


# --- Timestamps ---


def test_timestamps_preserved():
    t1 = datetime(2026, 4, 1, tzinfo=UTC)
    t2 = datetime(2026, 4, 8, tzinfo=UTC)
    diff = diff_reports(_report(ts=t1), _report(ts=t2))
    assert diff.before_timestamp == t1
    assert diff.after_timestamp == t2


# --- Serialization ---


def test_diff_is_serializable():
    before = _report([_link("link-1", checks=[_check(flag="pass")])])
    after = _report([_link("link-1", checks=[_check(flag="mismatch")])])
    diff = diff_reports(before, after)
    data = diff.model_dump(mode="json")
    assert isinstance(data, dict)
    roundtrip = VerificationDiff.model_validate(data)
    assert roundtrip.summary.changed == 1
