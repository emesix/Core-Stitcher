"""Planning data types — work requests, planned tasks, and plan records."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from stitch.agentcore.taskkit.models import TaskPriority


class SubtaskSpec(BaseModel, frozen=True):
    """User-supplied subtask hint within a work request."""

    description: str
    domain: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    depends_on: list[int] = Field(default_factory=list)


class WorkRequest(BaseModel):
    """Input to the planner — what the user wants done."""

    description: str
    domain: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    subtasks: list[SubtaskSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlannedTask(BaseModel):
    """A task within a plan, with dependency edges."""

    task_id: UUID = Field(default_factory=uuid4)
    description: str
    domain: str | None = None
    priority: TaskPriority = TaskPriority.NORMAL
    depends_on: list[UUID] = Field(default_factory=list)
    is_root: bool = False


class PlanRecord(BaseModel):
    """The output of planning — an ordered set of tasks with dependency graph."""

    plan_id: UUID = Field(default_factory=uuid4)
    request_description: str
    tasks: list[PlannedTask] = Field(default_factory=list)

    @property
    def root_task(self) -> PlannedTask | None:
        for t in self.tasks:
            if t.is_root:
                return t
        return None

    def execution_order(self) -> list[PlannedTask]:
        """Topological sort of tasks by dependency edges."""
        id_to_task = {t.task_id: t for t in self.tasks}
        visited: set[UUID] = set()
        order: list[PlannedTask] = []

        def visit(task_id: UUID) -> None:
            if task_id in visited:
                return
            visited.add(task_id)
            task = id_to_task[task_id]
            for dep in task.depends_on:
                if dep in id_to_task:
                    visit(dep)
            order.append(task)

        for t in self.tasks:
            visit(t.task_id)
        return order
