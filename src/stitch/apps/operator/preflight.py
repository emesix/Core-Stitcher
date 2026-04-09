"""stitch preflight run [--watch] command."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

preflight_app = typer.Typer(name="preflight", help="Preflight verification.")


@preflight_app.command("run")
def preflight_run(
    scope: Annotated[str | None, typer.Option("--scope", help="Scope")] = None,
    watch: Annotated[bool, typer.Option("--watch", help="Watch live progress")] = False,
) -> None:
    """Run preflight verification."""

    async def _run():
        client = get_client()
        try:
            params: dict[str, str] = {}
            if scope:
                params["scope"] = scope
            result = await client.command("preflight", "run", params=params or None)
            fmt = get_formatter()
            typer.echo(fmt.format_result_raw(result))
            if watch:
                typer.echo("(--watch streaming will be implemented in Task 10)", err=True)
        finally:
            await client.close()

    run_async(_run())
