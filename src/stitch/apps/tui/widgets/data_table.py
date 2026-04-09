"""Convenience wrapper around Textual DataTable."""

from __future__ import annotations

from textual.widgets import DataTable


class StitchDataTable(DataTable):
    def load_items(self, items: list[dict], columns: list[str] | None = None) -> None:
        self.clear(columns=True)
        if not items:
            return
        cols = columns or list(items[0].keys())
        for col in cols:
            self.add_column(col.upper(), key=col)
        for item in items:
            self.add_row(*[str(item.get(c, "")) for c in cols])
