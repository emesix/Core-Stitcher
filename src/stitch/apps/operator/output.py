"""Output formatters for the Stitch CLI."""
from __future__ import annotations

import json
from io import StringIO
from typing import TYPE_CHECKING, Any, Literal

import yaml
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from stitch.core.queries import QueryResult

OutputMode = Literal["json", "compact", "table", "human", "yaml"]


class OutputFormatter:
    def __init__(self, mode: OutputMode | str) -> None:
        self.mode: OutputMode = mode  # type: ignore[assignment]

    def format_result(self, qr: QueryResult) -> str:
        match self.mode:
            case "json":
                return self._json(qr)
            case "compact":
                return self._compact(qr)
            case "table":
                return self._table(qr)
            case "human":
                return self._human(qr)
            case "yaml":
                return self._yaml(qr)
            case _:
                return self._json(qr)

    def format_result_raw(self, data: dict[str, Any]) -> str:
        match self.mode:
            case "json":
                return json.dumps(data, indent=2, default=str)
            case "yaml":
                return yaml.dump(data, default_flow_style=False, sort_keys=False)
            case "compact":
                return "\t".join(str(v) for v in data.values())
            case _:
                return json.dumps(data, indent=2, default=str)

    # -- private formatters --

    def _json(self, qr: QueryResult) -> str:
        if qr.total == 1 and len(qr.items) == 1:
            return json.dumps(qr.items[0], indent=2, default=str)
        payload = {"items": qr.items, "total": qr.total}
        if qr.next_cursor:
            payload["next_cursor"] = qr.next_cursor
        return json.dumps(payload, indent=2, default=str)

    def _compact(self, qr: QueryResult) -> str:
        lines: list[str] = []
        for item in qr.items:
            parts = [str(v) for v in item.values()]
            lines.append("\t".join(parts))
        return "\n".join(lines)

    def _table(self, qr: QueryResult) -> str:
        if not qr.items:
            return ""
        columns = list(qr.items[0].keys())
        table = Table(show_header=True, header_style="bold")
        for col in columns:
            table.add_column(col)
        for item in qr.items:
            table.add_row(*(str(item.get(c, "")) for c in columns))
        buf = StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        console.print(table)
        return buf.getvalue()

    def _human(self, qr: QueryResult) -> str:
        if not qr.items:
            return ""
        if len(qr.items) == 1:
            return self._key_value(qr.items[0])
        return self._table(qr)

    def _yaml(self, qr: QueryResult) -> str:
        if qr.total == 1 and len(qr.items) == 1:
            return yaml.dump(qr.items[0], default_flow_style=False, sort_keys=False)
        return yaml.dump(
            {"items": qr.items, "total": qr.total},
            default_flow_style=False,
            sort_keys=False,
        )

    def _key_value(self, item: dict[str, Any]) -> str:
        max_key = max(len(k) for k in item) if item else 0
        lines = [f"{k:<{max_key}}  {v}" for k, v in item.items()]
        return "\n".join(lines)
