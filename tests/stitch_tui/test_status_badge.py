"""Tests for status badge widget utilities."""

from stitch.apps.tui.widgets.status_badge import status_class, status_symbol


def test_status_symbol_succeeded():
    assert status_symbol("succeeded") == "\u2713"


def test_status_symbol_running():
    assert status_symbol("running") == "\u25cf"


def test_status_symbol_failed():
    assert status_symbol("failed") == "\u2717"


def test_status_symbol_pending():
    assert status_symbol("pending") == "\u25cb"


def test_status_symbol_cancelled():
    assert status_symbol("cancelled") == "\u2014"


def test_status_class_ok():
    assert status_class("succeeded") == "status-ok"


def test_status_class_error():
    assert status_class("failed") == "status-error"


def test_status_class_running():
    assert status_class("running") == "status-running"


def test_status_unknown():
    assert status_symbol("unknown") == "?"
    assert status_class("unknown") == "status-pending"
