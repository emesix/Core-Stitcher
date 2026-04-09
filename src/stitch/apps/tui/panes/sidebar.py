"""Sidebar — explorer label + device list placeholder."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static


class Sidebar(Vertical):
    """Left sidebar with explorer label and placeholder device list."""

    def __init__(self) -> None:
        super().__init__(id="sidebar")

    def compose(self):
        yield Static("EXPLORER", classes="label")
        yield Static("(no devices loaded)", id="device-list-placeholder")
