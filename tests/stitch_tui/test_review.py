"""Tests for the review screen."""

from __future__ import annotations

from stitch.apps.tui.screens.review import ReviewScreen


def test_review_creation():
    review = {
        "run_id": "run_4f8a",
        "verdict": "request_changes",
        "reviewer": "ai",
        "findings": [
            {"description": "VLAN 42 break", "severity": "ERROR"},
            {"description": "port mismatch", "severity": "WARNING"},
        ],
    }
    screen = ReviewScreen(review=review)
    assert len(screen.review["findings"]) == 2


def test_review_no_findings():
    review = {"run_id": "run_x", "verdict": "approve", "reviewer": "human", "findings": []}
    screen = ReviewScreen(review=review)
    assert screen.review["verdict"] == "approve"
