"""Device list screen — filterable table of all devices."""

from __future__ import annotations

from typing import Any

from textual.containers import Vertical
from textual.widgets import Static

from stitch.apps.tui.widgets.data_table import StitchDataTable

DEVICE_COLUMNS = ["name", "type", "model", "management_ip"]


class DeviceListScreen(Vertical):
    """Center workspace showing a filterable device table."""

    def __init__(self, items: list[dict], **kwargs: Any) -> None:
        super().__init__(id="center", **kwargs)
        self.items = items

    def compose(self):
        yield Static("[bold]DEVICES[/]")
        table = StitchDataTable()
        table.load_items(self.items, columns=DEVICE_COLUMNS)
        yield table
