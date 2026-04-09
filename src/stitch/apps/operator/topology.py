"""stitch topology {show, diagnostics, export, diff} commands."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

topology_app = typer.Typer(name="topology", help="Topology operations.")


@topology_app.command("show")
def topology_show() -> None:
    """Show current topology."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("topology", "show")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@topology_app.command("diagnostics")
def topology_diagnostics() -> None:
    """Show topology diagnostics."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("topology", "diagnostics")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@topology_app.command("export")
def topology_export(
    format: Annotated[
        str, typer.Option("--format", help="Export format: json or yaml.")
    ] = "json",
) -> None:
    """Export the topology in a specified format."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("topology", "show")
            from stitch.apps.operator.output import OutputFormatter

            fmt = OutputFormatter(format)
            typer.echo(fmt.format_result(result))
        finally:
            await client.close()

    run_async(_run())


@topology_app.command("diff")
def topology_diff(
    before: Annotated[str, typer.Argument(help="Before snapshot ID")],
    after: Annotated[str, typer.Argument(help="After snapshot ID")],
) -> None:
    """Diff two topology snapshots."""

    async def _run():
        client = get_client()
        try:
            result = await client.command(
                "topology", "diff", params={"before": before, "after": after}
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
