"""Stitch CLI entry point."""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer

from stitch.apps.operator.output import OutputMode

__version__ = "0.1.0"

app = typer.Typer(
    name="stitch",
    help="Stitch operator CLI — manage topology, devices, and preflight from the terminal.",
    no_args_is_help=True,
)


@dataclass
class GlobalState:
    profile: str | None = None
    output: OutputMode = "human"
    config: Path | None = None
    no_color: bool = False
    quiet: bool = False
    verbose: bool = False
    yes: bool = False
    non_interactive: bool = False
    pager: bool = True
    _extra: dict = field(default_factory=dict)


_state = GlobalState()


def get_state() -> GlobalState:
    return _state


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    profile: Annotated[str | None, typer.Option("--profile", help="Config profile.")] = None,
    output: Annotated[
        str | None,
        typer.Option("-o", "--output", help="Output format: json, compact, table, human, yaml."),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Path to config file."),
    ] = None,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colour.")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", help="Suppress non-essential output.")] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Increase output verbosity.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip confirmation prompts.")
    ] = False,
    non_interactive: Annotated[
        bool, typer.Option("--non-interactive", help="Disable interactive prompts.")
    ] = False,
    pager: Annotated[
        bool, typer.Option("--pager/--no-pager", help="Page long output.")
    ] = True,
) -> None:
    """Stitch operator CLI."""
    global _state  # noqa: PLW0603
    is_tty = sys.stdout.isatty()

    resolved_output: OutputMode = "human"
    if output is not None:
        resolved_output = output  # type: ignore[assignment]
    elif not is_tty:
        resolved_output = "compact"

    _state = GlobalState(
        profile=profile,
        output=resolved_output,
        config=config,
        no_color=no_color or not is_tty,
        quiet=quiet,
        verbose=verbose,
        yes=yes,
        non_interactive=non_interactive or not is_tty,
        pager=pager and is_tty,
    )

    if ctx.invoked_subcommand is None:
        raise typer.Exit()


# -- system subcommand group --

system_app = typer.Typer(name="system", help="System information and diagnostics.")
app.add_typer(system_app)

from stitch.apps.operator.device import device_app  # noqa: E402
from stitch.apps.operator.preflight import preflight_app  # noqa: E402
from stitch.apps.operator.run_cmds import run_app  # noqa: E402
from stitch.apps.operator.trace import trace_app  # noqa: E402

app.add_typer(device_app)
app.add_typer(preflight_app)
app.add_typer(run_app)
app.add_typer(trace_app)


@system_app.command("version")
def system_version() -> None:
    """Show Stitch CLI version."""
    state = get_state()
    if state.output == "json":
        import json

        typer.echo(json.dumps({"name": "stitch", "version": __version__}))
    else:
        typer.echo(f"stitch {__version__}")


@system_app.command("health")
def system_health() -> None:
    """Check connectivity to the Stitch API."""
    state = get_state()
    if state.output == "json":
        import json

        typer.echo(json.dumps({"status": "ok", "note": "no server configured"}))
    else:
        typer.echo("health: ok (no server configured)")


def main() -> None:
    app()
