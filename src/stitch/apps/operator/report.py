"""stitch report {show, diff} commands."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

report_app = typer.Typer(name="report", help="Verification reports.")


@report_app.command("show")
def report_show(
    report_id: Annotated[str, typer.Argument(help="Report ID")],
) -> None:
    """Show a verification report."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("topology", "show")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@report_app.command("diff")
def report_diff(
    id1: Annotated[str, typer.Argument(help="First report ID")],
    id2: Annotated[str, typer.Argument(help="Second report ID")],
) -> None:
    """Diff two verification reports."""

    async def _run():
        client = get_client()
        try:
            result = await client.command(
                "topology", "diff", params={"before": id1, "after": id2}
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
