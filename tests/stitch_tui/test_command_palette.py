"""Tests for the command palette widget."""

from __future__ import annotations

import pytest

from stitch.apps.tui.app import StitchTUI
from stitch.apps.tui.widgets.command_palette import CommandPalette


def test_command_palette_default_commands():
    palette = CommandPalette()
    assert len(palette._commands) == len(CommandPalette.DEFAULT_COMMANDS)


def test_command_palette_custom_commands():
    cmds = [("foo", "Do foo"), ("bar", "Do bar")]
    palette = CommandPalette(commands=cmds)
    assert palette._commands == cmds


def test_app_has_palette_binding():
    app = StitchTUI()
    binding_keys = [b.key for b in app.BINDINGS]
    assert "ctrl+p" in binding_keys


def test_app_has_refresh_binding():
    app = StitchTUI()
    binding_keys = [b.key for b in app.BINDINGS]
    assert "r" in binding_keys


def test_app_has_help_binding():
    app = StitchTUI()
    binding_keys = [b.key for b in app.BINDINGS]
    assert "question_mark" in binding_keys


@pytest.mark.asyncio
async def test_command_palette_opens():
    app = StitchTUI()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+p")
        # Palette should now be on the screen stack
        assert isinstance(app.screen, CommandPalette)


@pytest.mark.asyncio
async def test_command_palette_dismiss_on_escape():
    app = StitchTUI()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+p")
        assert isinstance(app.screen, CommandPalette)
        await pilot.press("escape")
        assert not isinstance(app.screen, CommandPalette)


@pytest.mark.asyncio
async def test_command_palette_filters():
    app = StitchTUI()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+p")
        palette = app.screen
        assert isinstance(palette, CommandPalette)

        from textual.widgets import Input, OptionList

        options = palette.query_one("#palette-options", OptionList)
        initial_count = options.option_count

        # Type a filter that matches only some commands
        inp = palette.query_one("#palette-input", Input)
        inp.value = "device"
        await pilot.pause()

        filtered_count = options.option_count
        assert filtered_count < initial_count
        assert filtered_count > 0
