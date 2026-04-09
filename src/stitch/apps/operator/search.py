"""stitch search command."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async
from stitch.core.queries import QueryResult


def search_command(
    text: Annotated[str, typer.Argument(help="Search text")],
    type: Annotated[str | None, typer.Option("--type", help="Resource type filter")] = None,
    limit: Annotated[int, typer.Option("--limit", help="Max results")] = 20,
) -> None:
    """Search across all resources."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("device", "list")
            filtered = [
                item for item in result.items if text.lower() in str(item).lower()
            ]
            typer.echo(
                get_formatter().format_result(
                    QueryResult(items=filtered[:limit], total=len(filtered))
                )
            )
        finally:
            await client.close()

    run_async(_run())
