"""Tests for the Stitch TUI app shell."""

from __future__ import annotations

import pytest

from stitch.apps.tui.app import StitchTUI
from stitch.apps.tui.state import Mode


def test_app_creates():
    app = StitchTUI()
    assert app.TITLE == "Stitch TUI"


def test_app_has_bindings():
    app = StitchTUI()
    binding_keys = [b.key for b in app.BINDINGS]
    assert "ctrl+q" in binding_keys
    assert "ctrl+e" in binding_keys
    assert "ctrl+b" in binding_keys
    assert "tab" in binding_keys
    assert "shift+tab" in binding_keys


def test_app_default_state():
    app = StitchTUI()
    assert app.app_state.mode == Mode.BROWSE
    assert app.app_state.profile == "default"
    assert app.app_state.sidebar_visible is True
    assert app.app_state.bottom_visible is True


def test_app_custom_profile():
    app = StitchTUI(profile="lab")
    assert app.app_state.profile == "lab"


def test_app_theme_selection():
    app = StitchTUI(theme_name="light")
    assert app._theme_name == "light"


def test_app_client_initially_none():
    app = StitchTUI()
    assert app._client is None


def test_app_has_navigate_to():
    app = StitchTUI()
    assert hasattr(app, "navigate_to")
    assert callable(app.navigate_to)


@pytest.mark.asyncio
async def test_app_mounts_zones():
    app = StitchTUI()
    async with app.run_test() as _pilot:
        assert app.query_one("#top-bar") is not None
        assert app.query_one("#sidebar") is not None
        assert app.query_one("#center") is not None
        assert app.query_one("#bottom-panel") is not None
        assert app.query_one("#footer") is not None


@pytest.mark.asyncio
async def test_app_starts_without_server():
    """App should start gracefully when no server is configured."""
    app = StitchTUI()
    async with app.run_test() as _pilot:
        assert app._client is None
        assert app.app_state.connected is False
        # Welcome screen should still be visible
        assert app.query_one("#center") is not None


@pytest.mark.asyncio
async def test_navigate_to_updates_state():
    """navigate_to should update history even without a client."""
    app = StitchTUI()
    async with app.run_test() as _pilot:
        await app.navigate_to("device", "switch-01")
        assert app.app_state.current_uri == "stitch:/device/switch-01"


@pytest.mark.asyncio
async def test_toggle_sidebar():
    app = StitchTUI()
    async with app.run_test() as pilot:
        sidebar = app.query_one("#sidebar")
        assert sidebar.display is True
        await pilot.press("ctrl+e")
        assert sidebar.display is False
        assert app.app_state.sidebar_visible is False
        await pilot.press("ctrl+e")
        assert sidebar.display is True
        assert app.app_state.sidebar_visible is True


@pytest.mark.asyncio
async def test_toggle_bottom_panel():
    app = StitchTUI()
    async with app.run_test() as pilot:
        panel = app.query_one("#bottom-panel")
        assert panel.display is True
        await pilot.press("ctrl+b")
        assert panel.display is False
        assert app.app_state.bottom_visible is False
        await pilot.press("ctrl+b")
        assert panel.display is True
        assert app.app_state.bottom_visible is True
