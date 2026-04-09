"""Tests for TUI application state."""

from stitch.apps.tui.state import AppState, Mode


def test_initial_state():
    s = AppState()
    assert s.mode == Mode.BROWSE
    assert s.scope is None
    assert s.selection == []
    assert s.history == []
    assert s.history_index == -1


def test_navigate_pushes_history():
    s = AppState()
    s.navigate("stitch:/device/dev_01")
    assert s.current_uri == "stitch:/device/dev_01"
    assert len(s.history) == 1
    s.navigate("stitch:/device/dev_02")
    assert s.current_uri == "stitch:/device/dev_02"
    assert len(s.history) == 2


def test_go_back():
    s = AppState()
    s.navigate("stitch:/device/dev_01")
    s.navigate("stitch:/device/dev_02")
    s.go_back()
    assert s.current_uri == "stitch:/device/dev_01"


def test_go_back_at_start():
    s = AppState()
    s.navigate("stitch:/device/dev_01")
    s.go_back()
    assert s.current_uri is None


def test_go_forward():
    s = AppState()
    s.navigate("stitch:/device/dev_01")
    s.navigate("stitch:/device/dev_02")
    s.go_back()
    s.go_forward()
    assert s.current_uri == "stitch:/device/dev_02"


def test_selection_toggle():
    s = AppState()
    s.toggle_selection("stitch:/device/dev_01")
    assert "stitch:/device/dev_01" in s.selection
    s.toggle_selection("stitch:/device/dev_01")
    assert "stitch:/device/dev_01" not in s.selection


def test_clear_selection():
    s = AppState()
    s.toggle_selection("stitch:/device/dev_01")
    s.toggle_selection("stitch:/device/dev_02")
    s.clear_selection()
    assert s.selection == []


def test_mode_switching():
    s = AppState()
    s.mode = Mode.WATCH
    assert s.mode == Mode.WATCH
    s.mode = Mode.REVIEW
    assert s.mode == Mode.REVIEW
