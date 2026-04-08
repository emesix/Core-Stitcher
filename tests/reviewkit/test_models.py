"""Tests for reviewkit models — findings, verdicts, review results."""

from __future__ import annotations

from uuid import uuid4

from vos.agentcore.reviewkit import (
    ReviewFinding,
    ReviewRequest,
    ReviewResult,
    ReviewVerdict,
    Severity,
)

# --- ReviewFinding ---


def test_finding_defaults():
    f = ReviewFinding(description="looks good")
    assert f.severity == Severity.INFO
    assert f.task_id is None
    assert f.category is None
    assert f.suggestion is None


def test_finding_with_all_fields():
    tid = uuid4()
    f = ReviewFinding(
        description="missing test",
        severity=Severity.ERROR,
        task_id=tid,
        category="testing",
        suggestion="add unit test for edge case",
    )
    assert f.severity == Severity.ERROR
    assert f.task_id == tid
    assert f.category == "testing"


# --- ReviewRequest ---


def test_request_defaults():
    r = ReviewRequest()
    assert r.plan_id is None
    assert r.task_id is None
    assert r.content is None
    assert r.criteria == []


def test_request_with_criteria():
    r = ReviewRequest(
        plan_id=uuid4(),
        criteria=["correctness", "completeness", "no side effects"],
    )
    assert len(r.criteria) == 3


# --- ReviewResult ---


def test_result_defaults():
    r = ReviewResult()
    assert r.verdict == ReviewVerdict.APPROVE
    assert r.findings == []
    assert r.summary == ""
    assert r.has_errors is False
    assert r.has_warnings is False


def test_result_with_findings():
    r = ReviewResult(
        verdict=ReviewVerdict.REQUEST_CHANGES,
        findings=[
            ReviewFinding(description="info note", severity=Severity.INFO),
            ReviewFinding(description="real issue", severity=Severity.ERROR),
        ],
        summary="One error found",
    )
    assert r.has_errors is True
    assert r.has_warnings is False
    assert len(r.findings) == 2


def test_result_has_warnings():
    r = ReviewResult(
        findings=[ReviewFinding(description="warn", severity=Severity.WARNING)],
    )
    assert r.has_warnings is True
    assert r.has_errors is False


def test_findings_by_severity():
    r = ReviewResult(
        findings=[
            ReviewFinding(description="a", severity=Severity.INFO),
            ReviewFinding(description="b", severity=Severity.ERROR),
            ReviewFinding(description="c", severity=Severity.ERROR),
            ReviewFinding(description="d", severity=Severity.WARNING),
        ],
    )
    errors = r.findings_by_severity(Severity.ERROR)
    assert len(errors) == 2
    assert all(f.severity == Severity.ERROR for f in errors)

    infos = r.findings_by_severity(Severity.INFO)
    assert len(infos) == 1


def test_findings_by_severity_empty():
    r = ReviewResult()
    assert r.findings_by_severity(Severity.CRITICAL) == []


# --- Verdicts ---


def test_verdict_values():
    assert ReviewVerdict.APPROVE == "approve"
    assert ReviewVerdict.REQUEST_CHANGES == "request_changes"
    assert ReviewVerdict.REJECT == "reject"


# --- Serialization ---


def test_result_serialization_roundtrip():
    r = ReviewResult(
        verdict=ReviewVerdict.REJECT,
        findings=[
            ReviewFinding(description="critical bug", severity=Severity.CRITICAL),
        ],
        summary="Rejected due to critical bug",
    )
    data = r.model_dump(mode="json")
    restored = ReviewResult.model_validate(data)
    assert restored.verdict == ReviewVerdict.REJECT
    assert len(restored.findings) == 1
    assert restored.findings[0].severity == Severity.CRITICAL


def test_request_serialization_roundtrip():
    pid = uuid4()
    r = ReviewRequest(plan_id=pid, criteria=["correctness"])
    data = r.model_dump(mode="json")
    restored = ReviewRequest.model_validate(data)
    assert restored.plan_id == pid
    assert restored.criteria == ["correctness"]
