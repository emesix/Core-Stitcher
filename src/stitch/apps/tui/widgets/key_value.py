"""Key-value display widget."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static


class KeyValue(Static):
    def __init__(self, key: str, value: str, **kwargs: Any) -> None:
        super().__init__(f"[bold]{key}:[/bold] {value}", **kwargs)
