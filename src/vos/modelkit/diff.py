"""Diff types for comparing two VerificationReports."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CheckDiff(BaseModel, frozen=True):
    check: str
    port: str
    change: Literal["added", "removed", "changed"]
    before_flag: str | None = None
    after_flag: str | None = None


class LinkDiff(BaseModel):
    link: str
    change: Literal["added", "removed", "changed", "unchanged"]
    check_diffs: list[CheckDiff] = Field(default_factory=list)


class DiffSummary(BaseModel):
    added: int = 0
    removed: int = 0
    changed: int = 0
    unchanged: int = 0


class VerificationDiff(BaseModel):
    before_timestamp: datetime
    after_timestamp: datetime
    links: list[LinkDiff] = Field(default_factory=list)
    summary: DiffSummary = Field(default_factory=DiffSummary)
