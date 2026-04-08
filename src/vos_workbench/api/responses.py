from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ApiResponse(BaseModel):
    data: Any
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class PaginationMeta(BaseModel):
    offset: int
    limit: int
    count: int
    has_more: bool


class PaginatedApiResponse(BaseModel):
    data: list[dict[str, Any]]
    meta: PaginationMeta
