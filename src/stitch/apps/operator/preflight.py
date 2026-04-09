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
                run_id = result.get("run_id")
                if not run_id:
                    typer.echo("No run_id in response, cannot watch.", err=True)
                    return
                from stitch.apps.operator._watch import (
                    _TERMINAL_STATUSES,
                    render_watch_complete,
                    render_watch_event,
                )

                typer.echo(f"Watching run {run_id}...", err=True)
                try:
                    stream = await client.stream_connect(f"/ws/runs/{run_id}")
                    async for event in stream.events():
                        render_watch_event(event)
                        status = event.payload.get("status", "")
                        if status in _TERMINAL_STATUSES:
                            render_watch_complete(event.payload)
                            break
                except Exception as e:
                    typer.echo(f"Stream error: {e}", err=True)
                    typer.echo("Falling back to poll mode.", err=True)
        finally:
            await client.close()

    run_async(_run())
