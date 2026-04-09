"""Top bar — profile, server, connection state."""

from __future__ import annotations

from textual.widgets import Static


class TopBar(Static):
    """Single-line top bar showing profile, server, and connection status."""

    def __init__(
        self,
        profile: str = "default",
        server: str = "localhost",
        connected: bool = False,
    ) -> None:
        self._profile = profile
        self._server = server
        self._connected = connected
        super().__init__(id="top-bar")

    def on_mount(self) -> None:
        self._refresh_content()

    def set_connection(self, *, connected: bool, server: str | None = None) -> None:
        self._connected = connected
        if server is not None:
            self._server = server
        self._refresh_content()

    def _refresh_content(self) -> None:
        icon = "\u25cf" if self._connected else "\u25cb"
        state = "connected" if self._connected else "disconnected"
        self.update(f" {self._profile}  |  {self._server}  |  {icon} {state}")
