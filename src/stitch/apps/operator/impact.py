"""stitch impact {preview} commands."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

impact_app = typer.Typer(name="impact", help="Change impact analysis.")


@impact_app.command("preview")
def impact_preview(
    action: Annotated[str, typer.Option("--action", help="Action to preview")],
    device: Annotated[str, typer.Option("--device", help="Target device")],
    port: Annotated[str, typer.Option("--port", help="Target port")],
) -> None:
    """Preview the impact of a change."""

    async def _run():
        client = get_client()
        try:
            result = await client.command(
                "impact",
                "preview",
                params={"action": action, "device": device, "port": port},
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
