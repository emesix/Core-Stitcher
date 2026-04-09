"""Deterministic planner — work request to plan record.

No LLM. Takes explicit subtask specs from the request and builds
a dependency graph of PlannedTasks. If no subtasks, creates a
single root task.
"""

from __future__ import annotations

from vos.agentcore.plannerkit.models import PlannedTask, PlanRecord, WorkRequest


def plan_request(request: WorkRequest) -> PlanRecord:
    root = PlannedTask(
        description=request.description,
        domain=request.domain,
        priority=request.priority,
        is_root=True,
    )

    if not request.subtasks:
        return PlanRecord(
            request_description=request.description,
            tasks=[root],
        )

    # Build subtasks with index-based dependency resolution
    children: list[PlannedTask] = []
    for spec in request.subtasks:
        child = PlannedTask(
            description=spec.description,
            domain=spec.domain or request.domain,
            priority=spec.priority,
        )
        children.append(child)

    # Resolve depends_on indices to UUIDs
    for i, spec in enumerate(request.subtasks):
        deps: list = []
        for dep_idx in spec.depends_on:
            if 0 <= dep_idx < len(children) and dep_idx != i:
                deps.append(children[dep_idx].task_id)
        children[i] = children[i].model_copy(update={"depends_on": deps})

    # Root depends on all leaf tasks (tasks that nothing depends on)
    depended_on = {dep for child in children for dep in child.depends_on}
    leaves = [c for c in children if c.task_id not in depended_on]
    root = root.model_copy(update={"depends_on": [leaf.task_id for leaf in leaves]})

    return PlanRecord(
        request_description=request.description,
        tasks=[root, *children],
    )
