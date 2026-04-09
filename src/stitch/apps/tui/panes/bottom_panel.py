"""Bottom panel — tabbed logs, events, steps, notifications."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static, TabbedContent, TabPane


class BottomPanel(Vertical):
    """Bottom panel with tabbed content areas."""

    def __init__(self) -> None:
        super().__init__(id="bottom-panel")

    def compose(self):
        with TabbedContent():
            with TabPane("Logs", id="tab-logs"):
                yield Static("(no logs)")
            with TabPane("Events", id="tab-events"):
                yield Static("(no events)")
            with TabPane("Steps", id="tab-steps"):
                yield Static("(no steps)")
            with TabPane("Notifications", id="tab-notifications"):
                yield Static("(no notifications)")
