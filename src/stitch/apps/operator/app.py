"""Stitch CLI entry point."""

import typer

app = typer.Typer(
    name="stitch",
    help="Stitch operator CLI — manage topology, devices, and preflight from the terminal.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def _root(ctx: typer.Context) -> None:
    """Stitch operator CLI."""
    if ctx.invoked_subcommand is None:
        raise typer.Exit()


def main() -> None:
    app()
