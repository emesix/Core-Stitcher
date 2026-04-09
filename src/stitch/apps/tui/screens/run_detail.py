"""Run detail screen — run info, progress, and task list."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import ProgressBar, Static

from stitch.apps.tui.widgets.data_table import StitchDataTable
from stitch.apps.tui.widgets.status_badge import StatusBadge

TASK_COLUMNS = ["task_id", "status", "description"]


class RunDetailScreen(Vertical):
    """Center workspace showing run progress and task breakdown."""

    def __init__(self, run: dict, **kwargs: object) -> None:
        super().__init__(id="center", **kwargs)
        self.run = run

    def compose(self):
        run_id = self.run.get("run_id", "unknown")
        description = self.run.get("description", "")
        status = self.run.get("status", "pending")
        tasks = self.run.get("tasks", [])

        yield Static(f"[bold]{run_id}[/] {description}")
        yield StatusBadge(status)

        # Progress
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get("status") == "succeeded")
        yield Static(f"{completed}/{total} tasks complete")
        bar = ProgressBar(total=max(total, 1), show_eta=False)
        bar.advance(completed)
        yield bar

        # Task list
        yield Static("[bold]Tasks[/]")
        task_table = StitchDataTable()
        task_table.load_items(tasks, columns=TASK_COLUMNS)
        yield task_table
