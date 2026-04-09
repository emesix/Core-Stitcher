"""Stitch TUI — Textual application with 3-zone layout."""

from __future__ import annotations

import argparse
import os

from textual.app import App, ComposeResult
from textual.binding import Binding

from stitch.apps.tui.layout import ThreeZoneLayout
from stitch.apps.tui.panes.sidebar import Sidebar
from stitch.apps.tui.screens.device_detail import DeviceDetailScreen
from stitch.apps.tui.screens.device_list import DeviceListScreen
from stitch.apps.tui.screens.run_detail import RunDetailScreen
from stitch.apps.tui.state import AppState
from stitch.apps.tui.theme import THEMES
from stitch.apps.tui.widgets.command_palette import CommandPalette
from stitch.sdk.client import StitchClient
from stitch.sdk.config import Profile, load_config


class StitchTUI(App):
    """Terminal operator interface for Stitch."""

    TITLE = "Stitch TUI"
    CSS = THEMES["dark"]

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("ctrl+p", "command_palette", "Command palette"),
        Binding("ctrl+e", "toggle_sidebar", "Toggle sidebar"),
        Binding("ctrl+b", "toggle_bottom", "Toggle bottom panel"),
        Binding("tab", "focus_next", "Next pane"),
        Binding("shift+tab", "focus_previous", "Previous pane"),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("question_mark", "help", "Help", show=False),
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
        self._client: StitchClient | None = None
        self.app_state = AppState()
        self.app_state.profile = profile

    def compose(self) -> ComposeResult:
        yield ThreeZoneLayout(profile=self._profile)

    async def on_mount(self) -> None:
        """Connect SDK client from config (STITCH_SERVER env > profile.server)."""
        profile = self._resolve_profile()
        if profile is None:
            self.notify("No server configured", severity="warning")
            return

        try:
            self._client = StitchClient(profile)
            self.app_state.connected = True
            self.app_state.server = profile.server
            top_bar = self.query_one("#top-bar")
            top_bar.set_connection(connected=True, server=profile.server)
            await self._load_device_list()
        except Exception as exc:
            self.notify(f"Connection failed: {exc}", severity="error")

    def _resolve_profile(self) -> Profile | None:
        """Resolve server profile from env var or config file."""
        env_server = os.environ.get("STITCH_SERVER")
        if env_server:
            return Profile(server=env_server)
        try:
            config = load_config()
            return config.resolve_profile(self._profile)
        except (KeyError, FileNotFoundError):
            return None

    async def navigate_to(self, resource_type: str, resource_id: str) -> None:
        """Navigate center workspace to a resource detail view."""
        self.app_state.navigate(f"stitch:/{resource_type}/{resource_id}")

        if self._client is None:
            self.notify("Not connected to server", severity="warning")
            return

        try:
            if resource_type == "device":
                result = await self._client.query("device", "get", resource_id=resource_id)
                device = result.items[0] if result.items else {}
                neighbors_result = await self._client.query(
                    "device", "neighbors", resource_id=resource_id
                )
                await self._replace_center(
                    DeviceDetailScreen(device=device, neighbors=neighbors_result.items)
                )
            elif resource_type == "run":
                result = await self._client.query("run", "get", resource_id=resource_id)
                run = result.items[0] if result.items else {}
                await self._replace_center(RunDetailScreen(run=run))
        except Exception as exc:
            self.notify(f"Navigation failed: {exc}", severity="error")

    async def _replace_center(self, new_widget) -> None:
        """Replace the center workspace content."""
        old = self.query_one("#center")
        parent = old.parent
        await old.remove()
        await parent.mount(new_widget)

    async def _load_device_list(self) -> None:
        """Fetch devices and update sidebar + center."""
        if self._client is None:
            return
        try:
            result = await self._client.query("device", "list")
            devices = result.items
            sidebar = self.query_one(Sidebar)
            sidebar.update_devices(devices)
            await self._replace_center(DeviceListScreen(items=devices))
        except Exception as exc:
            self.notify(f"Failed to load devices: {exc}", severity="error")

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display
        self.app_state.sidebar_visible = sidebar.display

    def action_toggle_bottom(self) -> None:
        panel = self.query_one("#bottom-panel")
        panel.display = not panel.display
        self.app_state.bottom_visible = panel.display

    def action_command_palette(self) -> None:
        self.push_screen(CommandPalette())

    async def action_refresh(self) -> None:
        await self._load_device_list()

    def action_help(self) -> None:
        bindings = "\n".join(
            f"  {b.key:<16} {b.description}" for b in self.BINDINGS if b.description
        )
        self.notify(f"Keybindings:\n{bindings}", timeout=8)


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
