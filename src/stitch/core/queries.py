"""Query model -- read-only requests with filtering and pagination."""
from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field

_FILTER_RE = re.compile(r"^(?P<field>[a-z_]+)(?P<op>!=|>=|<=|>|<|~|=)(?P<value>.+)$")


class FilterOp(StrEnum):
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    CONTAINS = "~"
    IN = "in"


class Filter(BaseModel):
    field: str
    op: FilterOp
    value: str | list[str]


class Query(BaseModel):
    resource_type: str
    resource_id: str | None = None
    filters: list[Filter] = Field(default_factory=list)
    sort: str | None = None
    limit: int | None = None
    cursor: str | None = None
    fields: list[str] | None = None


class QueryResult(BaseModel):
    items: list[dict]
    total: int | None = None
    next_cursor: str | None = None


def parse_filter(text: str) -> Filter:
    m = _FILTER_RE.match(text)
    if not m:
        msg = f"Invalid filter: {text}"
        raise ValueError(msg)
    field = m.group("field")
    op_str = m.group("op")
    value_str = m.group("value")
    if op_str == "=" and "," in value_str:
        return Filter(field=field, op=FilterOp.IN, value=value_str.split(","))
    op = FilterOp(op_str)
    return Filter(field=field, op=op, value=value_str)
