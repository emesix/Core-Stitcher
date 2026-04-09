"""Project Stitcher CLI — plan work requests from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from stitch.agentcore.plannerkit import PlanRecord, SubtaskSpec, WorkRequest, plan_request
from stitch.agentcore.taskkit import TaskPriority

if TYPE_CHECKING:
    from uuid import UUID


def _short_id(uid: UUID) -> str:
    return str(uid)[:8]


def _format_plan(plan: PlanRecord) -> str:
    lines: list[str] = []
    lines.append(f"Plan {_short_id(plan.plan_id)}")
    lines.append(f"  Request: {plan.request_description}")
    lines.append(f"  Tasks: {len(plan.tasks)}")
    lines.append("")

    order = plan.execution_order()
    id_to_idx: dict[UUID, int] = {t.task_id: i + 1 for i, t in enumerate(order)}

    lines.append("Execution order:")
    for i, task in enumerate(order, 1):
        root_marker = " [root]" if task.is_root else ""
        domain_str = f" ({task.domain})" if task.domain else ""
        priority_str = f" [{task.priority}]" if task.priority != TaskPriority.NORMAL else ""

        dep_parts = []
        for dep_id in task.depends_on:
            dep_num = id_to_idx.get(dep_id)
            if dep_num is not None:
                dep_parts.append(f"#{dep_num}")
        dep_str = f" depends={','.join(dep_parts)}" if dep_parts else ""

        lines.append(
            f"  #{i} {_short_id(task.task_id)} {task.description}"
            f"{domain_str}{priority_str}{dep_str}{root_marker}"
        )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-stitcher",
        description="Plan work requests using Agent Core",
    )
    parser.add_argument("description", help="What needs to be done")
    parser.add_argument("--domain", default=None, help="Task domain (e.g. topology, research)")
    parser.add_argument(
        "--priority",
        choices=[p.value for p in TaskPriority],
        default="normal",
        help="Task priority",
    )
    parser.add_argument(
        "--subtask",
        action="append",
        default=[],
        help="Add a subtask (repeatable)",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    subtask_specs = [SubtaskSpec(description=s) for s in args.subtask]

    request = WorkRequest(
        description=args.description,
        domain=args.domain,
        priority=TaskPriority(args.priority),
        subtasks=subtask_specs,
    )

    plan = plan_request(request)

    if args.json_output:
        sys.stdout.write(json.dumps(plan.model_dump(mode="json"), indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(_format_plan(plan))
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
