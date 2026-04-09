"""3-zone layout — top bar, sidebar+center, bottom panel, footer."""

from __future__ import annotations

from textual.containers import Horizontal, Vertical

from stitch.apps.tui.panes.bottom_panel import BottomPanel
from stitch.apps.tui.panes.footer import Footer
from stitch.apps.tui.panes.sidebar import Sidebar
from stitch.apps.tui.panes.top_bar import TopBar
from stitch.apps.tui.screens.welcome import WelcomeScreen


class ThreeZoneLayout(Vertical):
    """IDE-inspired layout: top bar, sidebar+center, bottom panel, footer."""

    def __init__(
        self,
        profile: str = "default",
        server: str = "localhost",
    ) -> None:
        super().__init__()
        self._profile = profile
        self._server = server

    def compose(self):
        yield TopBar(profile=self._profile, server=self._server)
        with Horizontal():
            yield Sidebar()
            yield WelcomeScreen()
        yield BottomPanel()
        yield Footer()
