"""Footer — key hints and current mode."""

from __future__ import annotations

from textual.widgets import Static

from stitch.apps.tui.state import Mode


class Footer(Static):
    """Single-line footer showing key hints and mode."""

    def __init__(self) -> None:
        super().__init__(id="footer")
        self._mode = Mode.BROWSE

    def on_mount(self) -> None:
        self._refresh_content()

    def set_mode(self, mode: Mode) -> None:
        self._mode = mode
        self._refresh_content()

    def _refresh_content(self) -> None:
        hints = (
            " ^Q Quit  |  ^E Sidebar  |  ^B Bottom  |  Tab Focus"
            f"  |  mode: {self._mode.value}"
        )
        self.update(hints)
