"""stitch review {show, list, request, approve, reject} commands."""
from __future__ import annotations

from typing import Annotated

import typer

from stitch.apps.operator._client import get_client, get_formatter, run_async
from stitch.apps.operator.app import get_state

review_app = typer.Typer(name="review", help="Review and approval workflow.")


@review_app.command("show")
def review_show(
    review_id: Annotated[str, typer.Argument(help="Review / run ID")],
) -> None:
    """Show review detail."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "show", resource_id=review_id)
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@review_app.command("list")
def review_list(
    filter: Annotated[list[str] | None, typer.Option("--filter", help="Filter")] = None,
) -> None:
    """List reviews."""

    async def _run():
        client = get_client()
        try:
            result = await client.query("run", "list")
            typer.echo(get_formatter().format_result(result))
        finally:
            await client.close()

    run_async(_run())


@review_app.command("request")
def review_request(
    run_id: Annotated[str, typer.Argument(help="Run ID to request review for")],
) -> None:
    """Request a review for a run."""

    async def _run():
        client = get_client()
        try:
            result = await client.command("run", "review", resource_id=run_id)
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())


@review_app.command("approve")
def review_approve(
    review_id: Annotated[str, typer.Argument(help="Review / run ID")],
    comment: Annotated[str | None, typer.Option("--comment", help="Approval comment")] = None,
) -> None:
    """Approve a review."""
    if not get_state().yes:
        typer.confirm(f"Approve review {review_id}?", abort=True)

    async def _run():
        client = get_client()
        try:
            params: dict[str, str] = {"action": "approve"}
            if comment:
                params["comment"] = comment
            result = await client.command(
                "run", "review", resource_id=review_id, params=params
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())


@review_app.command("reject")
def review_reject(
    review_id: Annotated[str, typer.Argument(help="Review / run ID")],
    comment: Annotated[str | None, typer.Option("--comment", help="Rejection comment")] = None,
) -> None:
    """Reject a review."""
    if not get_state().yes:
        typer.confirm(f"Reject review {review_id}?", abort=True)

    async def _run():
        client = get_client()
        try:
            params: dict[str, str] = {"action": "reject"}
            if comment:
                params["comment"] = comment
            result = await client.command(
                "run", "review", resource_id=review_id, params=params
            )
            typer.echo(get_formatter().format_result_raw(result))
        finally:
            await client.close()

    run_async(_run())
