"""Device detail screen — device info, ports, and neighbors."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from stitch.apps.tui.widgets.data_table import StitchDataTable
from stitch.apps.tui.widgets.key_value import KeyValue

PORT_COLUMNS = ["name", "type", "speed"]


class DeviceDetailScreen(Vertical):
    """Center workspace showing device info, ports, and neighbors."""

    def __init__(
        self,
        device: dict,
        neighbors: list[dict] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(id="center", **kwargs)
        self.device = device
        self.neighbors = neighbors or []

    def compose(self):
        name = self.device.get("name", "Unknown")
        dev_type = self.device.get("type", "")
        yield Static(f"[bold]{name}[/] ({dev_type})")

        # Info section
        for key in ("model", "management_ip", "mcp_source"):
            value = self.device.get(key)
            if value is not None:
                yield KeyValue(key, str(value))

        # Ports section
        ports = self.device.get("ports", [])
        yield Static("[bold]Ports[/]")
        ports_table = StitchDataTable()
        ports_table.load_items(ports, columns=PORT_COLUMNS)
        yield ports_table

        # Neighbors section
        yield Static("[bold]Neighbors[/]")
        neighbors_table = StitchDataTable()
        neighbors_table.load_items(self.neighbors)
        yield neighbors_table
