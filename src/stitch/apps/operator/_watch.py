"""Watch mode -- live display for run progress and logs."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.text import Text

if TYPE_CHECKING:
    from stitch.core.streams import StreamEvent

console = Console(stderr=True)

_STATUS_STYLES = {
    "succeeded": "green",
    "running": "yellow",
    "failed": "red",
    "cancelled": "dim",
    "timed_out": "red",
    "pending": "dim",
    "queued": "dim",
}

_TERMINAL_STATUSES = frozenset({"succeeded", "failed", "cancelled", "timed_out"})


def render_watch_event(event: StreamEvent) -> None:
    status = event.payload.get("status", "")
    style = _STATUS_STYLES.get(status, "")
    description = event.payload.get("description", event.resource)
    task_id = event.payload.get("task_id", "")
    prefix = f"  {task_id}" if task_id else ""
    status_text = Text(status.upper(), style=style) if style else Text(status.upper())
    console.print(f"{prefix} {status_text} {description}", highlight=False)


def render_watch_complete(result: dict) -> None:
    status = result.get("status", "unknown")
    style = _STATUS_STYLES.get(status, "")
    console.print(f"\nRun {result.get('run_id', '?')}: {Text(status.upper(), style=style)}")
