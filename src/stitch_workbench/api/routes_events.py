from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Query

from stitch_workbench.api.responses import PaginatedApiResponse, PaginationMeta

if TYPE_CHECKING:
    from stitch_workbench.runtime.runtime import Runtime


def create_event_routes(runtime: Runtime) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.get("/events")
    async def get_events(
        type: str | None = Query(None, description="Filter by event type"),
        source: str | None = Query(None, description="Filter by source (glob pattern)"),
        severity: str | None = Query(None, description="Filter by severity"),
        since: str | None = Query(None, description="Events after this ISO 8601 timestamp"),
        until: str | None = Query(None, description="Events before this ISO 8601 timestamp"),
        offset: int = Query(0, ge=0, description="Skip N records"),
        limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    ) -> PaginatedApiResponse:
        since_dt = datetime.fromisoformat(since) if since else None
        until_dt = datetime.fromisoformat(until) if until else None

        events, count, has_more = runtime.query_events(
            event_type=type,
            source=source,
            severity=severity,
            since=since_dt,
            until=until_dt,
            offset=offset,
            limit=limit,
        )

        return PaginatedApiResponse(
            data=events,
            meta=PaginationMeta(
                offset=offset,
                limit=limit,
                count=count,
                has_more=has_more,
            ),
        )

    return router
