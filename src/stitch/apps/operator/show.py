"""stitch show command — open any resource by stitch URI."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async
from stitch.core.resources import parse_uri


def show_command(
    uri: Annotated[str, typer.Argument(help="Stitch URI (e.g. stitch:/device/sw-core-01)")],
) -> None:
    """Open any resource by its stitch URI."""

    async def _run():
        parsed = parse_uri(uri)
        client = get_client()
        try:
            result = await client.query(
                parsed.resource_type, "show", resource_id=parsed.resource_id
            )
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())
