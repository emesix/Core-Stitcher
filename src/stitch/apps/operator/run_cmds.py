"""stitch run {list, show, watch, execute, cancel} commands."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

run_app = typer.Typer(name="run", help="Run orchestration lifecycle.")


@run_app.command("list")
def run_list(
    filter: Annotated[list[str] | None, typer.Option("--filter")] = None,
) -> None:
    """List runs."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "list")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("show")
def run_show(run_id: Annotated[str, typer.Argument(help="Run ID")]) -> None:
    """Show run detail."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "show", resource_id=run_id)
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("watch")
def run_watch(run_id: Annotated[str, typer.Argument(help="Run ID to watch")]) -> None:
    """Watch a run's progress live."""
    from stitch.apps.operator._watch import (
        _TERMINAL_STATUSES,
        render_watch_complete,
        render_watch_event,
    )

    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "show", resource_id=run_id)
            if result.items:
                status = result.items[0].get("status", "")
                if status in _TERMINAL_STATUSES:
                    typer.echo(get_formatter().format_result(result))
                    return

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
                result = await client.query("run", "show", resource_id=run_id)
                typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("execute")
def run_execute(run_id: Annotated[str, typer.Argument(help="Run ID")]) -> None:
    """Execute a planned run."""

    async def _run():
        client = get_client()
        try:
            result = await client.command("run", "execute", resource_id=run_id)
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())


@run_app.command("cancel")
def run_cancel(
    run_id: Annotated[str, typer.Argument(help="Run ID")],
    reason: Annotated[str | None, typer.Option("--reason")] = None,
) -> None:
    """Cancel an in-progress run."""

    async def _run():
        client = get_client()
        try:
            params = {"reason": reason} if reason else None
            result = await client.command("run", "cancel", resource_id=run_id, params=params)
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
