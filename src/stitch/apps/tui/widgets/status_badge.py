"""Status badge widget and helpers."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static

_SYMBOLS: dict[str, str] = {
    "succeeded": "\u2713",
    "failed": "\u2717",
    "running": "\u25cf",
    "pending": "\u25cb",
    "queued": "\u25cb",
    "cancelled": "\u2014",
    "timed_out": "\u2717",
    "ok": "\u2713",
    "warning": "\u25cf",
    "error": "\u2717",
    "degraded": "\u25cf",
    "healthy": "\u2713",
}

_CLASSES: dict[str, str] = {
    "succeeded": "status-ok",
    "ok": "status-ok",
    "healthy": "status-ok",
    "failed": "status-error",
    "error": "status-error",
    "timed_out": "status-error",
    "running": "status-running",
    "warning": "status-warning",
    "degraded": "status-warning",
    "pending": "status-pending",
    "queued": "status-pending",
    "cancelled": "status-cancelled",
}


def status_symbol(status: str) -> str:
    return _SYMBOLS.get(status, "?")


def status_class(status: str) -> str:
    return _CLASSES.get(status, "status-pending")


class StatusBadge(Static):
    def __init__(self, status: str, **kwargs: Any) -> None:
        self._status = status
        symbol = status_symbol(status)
        super().__init__(f"{symbol} {status.upper()}", **kwargs)
        self.add_class(status_class(status))
