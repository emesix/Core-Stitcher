"""Stitch TUI — Textual application with 3-zone layout."""

from __future__ import annotations

import argparse

from textual.app import App, ComposeResult
from textual.binding import Binding

from stitch.apps.tui.layout import ThreeZoneLayout
from stitch.apps.tui.state import AppState
from stitch.apps.tui.theme import THEMES


class StitchTUI(App):
    """Terminal operator interface for Stitch."""

    TITLE = "Stitch TUI"
    CSS = THEMES["dark"]

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+e", "toggle_sidebar", "Toggle sidebar"),
        Binding("ctrl+b", "toggle_bottom", "Toggle bottom panel"),
        Binding("tab", "focus_next", "Next pane"),
        Binding("shift+tab", "focus_previous", "Previous pane"),
    ]

    def __init__(
        self,
        profile: str = "default",
        theme_name: str = "dark",
        no_animation: bool = False,
    ) -> None:
        super().__init__()
        self._profile = profile
        self._theme_name = theme_name
        self._no_animation = no_animation
        self.app_state = AppState()
        self.app_state.profile = profile

    def compose(self) -> ComposeResult:
        yield ThreeZoneLayout(profile=self._profile)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display
        self.app_state.sidebar_visible = sidebar.display

    def action_toggle_bottom(self) -> None:
        panel = self.query_one("#bottom-panel")
        panel.display = not panel.display
        self.app_state.bottom_visible = panel.display


def _build_app(
    profile: str = "default",
    theme_name: str = "dark",
    no_animation: bool = False,
) -> StitchTUI:
    """Build a StitchTUI with the requested theme applied as CSS."""
    css = THEMES.get(theme_name, THEMES["dark"])
    # Dynamically create a subclass with the requested theme CSS
    themed_cls = type("StitchTUI", (StitchTUI,), {"CSS": css})
    return themed_cls(profile=profile, theme_name=theme_name, no_animation=no_animation)


def main() -> None:
    """Launch the Stitch TUI."""
    parser = argparse.ArgumentParser(description="Stitch TUI — terminal operator interface")
    parser.add_argument(
        "--profile",
        default="default",
        help="Configuration profile name (default: default)",
    )
    parser.add_argument(
        "--theme",
        default="dark",
        choices=list(THEMES),
        help="Color theme (default: dark)",
    )
    parser.add_argument(
        "--no-animation",
        action="store_true",
        help="Disable animations",
    )
    args = parser.parse_args()
    app = _build_app(
        profile=args.profile,
        theme_name=args.theme,
        no_animation=args.no_animation,
    )
    app.run()
