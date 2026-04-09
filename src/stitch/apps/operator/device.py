"""stitch device {list, show, inspect} commands."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

device_app = typer.Typer(name="device", help="Device operations.")


@device_app.command("list")
def device_list(
    filter: Annotated[list[str] | None, typer.Option("--filter", help="Filter")] = None,
    sort: Annotated[str | None, typer.Option("--sort")] = None,
    limit: Annotated[int | None, typer.Option("--limit")] = None,
) -> None:
    """List devices."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("device", "list")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@device_app.command("show")
def device_show(
    device_id: Annotated[str, typer.Argument(help="Device ID or alias")],
) -> None:
    """Show device detail."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("device", "show", resource_id=device_id)
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@device_app.command("inspect")
def device_inspect(
    device_id: Annotated[str, typer.Argument(help="Device ID or alias")],
) -> None:
    """Deep inspection: device detail + ports + neighbors."""

    async def _run():
        client = get_client()
        try:
            detail = await client.query("device", "show", resource_id=device_id)
            neighbors = await client.query("device", "neighbors", resource_id=device_id)
            fmt = get_formatter()
            typer.echo(fmt.format_result(detail))
            if neighbors.items:
                typer.echo("\nNeighbors:")
                typer.echo(fmt.format_result(neighbors))
        finally:
            await client.close()

    run_async(_run())
