"""stitch trace {run,show,list} commands."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async

trace_app = typer.Typer(name="trace", help="VLAN path tracing.")


@trace_app.command("run")
def trace_run(
    vlan_id: Annotated[int, typer.Argument(help="VLAN ID to trace")],
    from_device: Annotated[str, typer.Option("--from", help="Source device")],
    to_device: Annotated[str | None, typer.Option("--to", help="Target device")] = None,
) -> None:
    """Trace a VLAN path through the topology."""

    async def _run():
        client = get_client()
        try:
            params: dict[str, str | int] = {"vlan": vlan_id, "source": from_device}
            if to_device:
                params["target"] = to_device
            result = await client.command("trace", "run", params=params)
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
