from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any
from uuid import UUID, uuid4  # noqa: TC003

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EventRecord(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: str = Field(index=True)
    source: str
    project_id: str = Field(index=True)
    time: datetime = Field(index=True)
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    severity: str = "info"
    data: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class ModuleHealthRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    module_uuid: UUID = Field(index=True)
    status: str
    checked_at: datetime
    details: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))


class SessionRecord(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str = "active"
    metadata_: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class TaskRecord(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID | None = None
    parent_task_id: UUID | None = None
    module_uuid: UUID
    status: str = "pending"
    created_at: datetime
    updated_at: datetime
    result_summary: str | None = None
    budget_used: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
