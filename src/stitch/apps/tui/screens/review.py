"""Review screen — review verdict, findings, and actions."""

from __future__ import annotations

from typing import Any

from textual.containers import Vertical
from textual.widgets import Static

from stitch.apps.tui.widgets.key_value import KeyValue
from stitch.apps.tui.widgets.status_badge import StatusBadge

_SEVERITY_CLASS: dict[str, str] = {
    "ERROR": "status-error",
    "CRITICAL": "status-error",
    "WARNING": "status-warning",
    "INFO": "status-pending",
}


class ReviewScreen(Vertical):
    """Center workspace showing review verdict and findings."""

    def __init__(self, review: dict, **kwargs: Any) -> None:
        super().__init__(id="center", **kwargs)
        self.review = review

    def compose(self):
        run_id = self.review.get("run_id", "unknown")
        verdict = self.review.get("verdict", "pending")
        reviewer = self.review.get("reviewer", "unknown")
        findings = self.review.get("findings", [])

        yield Static(f"[bold orange1]\u25b2 Review: {run_id}[/]")
        yield StatusBadge(verdict)
        yield KeyValue("reviewer", reviewer)

        # Findings
        yield Static("[bold]Findings[/]")
        for finding in findings:
            severity = finding.get("severity", "INFO")
            description = finding.get("description", "")
            css_class = _SEVERITY_CLASS.get(severity, "status-pending")
            label = Static(f"\u25cf {severity}: {description}", classes=css_class)
            yield label
            suggestion = finding.get("suggestion")
            if suggestion:
                yield Static(f"  \u2192 {suggestion}")

        yield Static("[dim]a: approve  R: reject  d: diff  q: back[/]")
