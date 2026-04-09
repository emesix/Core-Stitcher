"""storekit — Persistence for pipeline runs.

Repository pattern. JSON file store for v0. Protocol-based so backends
are swappable.
"""

from stitch.agentcore.storekit.json_store import JsonRunStore
from stitch.agentcore.storekit.models import (
    ExecutorSelection,
    RunRecord,
    RunStatus,
    SelectionReason,
    StepKind,
    StepRecord,
    StepStatus,
    TaskExecution,
)
from stitch.agentcore.storekit.protocol import RunStore

__all__ = [
    "ExecutorSelection",
    "JsonRunStore",
    "RunRecord",
    "RunStatus",
    "RunStore",
    "SelectionReason",
    "StepKind",
    "StepRecord",
    "StepStatus",
    "TaskExecution",
]
