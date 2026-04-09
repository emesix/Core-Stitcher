"""Sidebar — explorer label + device list."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

_TYPE_INITIALS = {
    "switch": "S",
    "router": "R",
    "firewall": "F",
    "hypervisor": "H",
    "server": "V",
}


class Sidebar(Vertical):
    """Left sidebar with explorer label and device list."""

    def __init__(self) -> None:
        super().__init__(id="sidebar")

    def compose(self):
        yield Static("EXPLORER", classes="label")
        yield Vertical(
            Static("(no devices loaded)", id="device-list-placeholder"),
            id="device-list",
        )

    def update_devices(self, devices: list[dict]) -> None:
        """Update the explorer device list."""
        container = self.query_one("#device-list")
        container.remove_children()
        for device in devices:
            name = device.get("name", "unknown")
            dev_type = device.get("type", "")
            fallback = dev_type[:1].upper() if dev_type else "?"
            initial = _TYPE_INITIALS.get(dev_type.lower(), fallback)
            container.mount(Static(f"[{initial}] {name}", classes="device-entry"))
