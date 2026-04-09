"""Lifecycle state machine for runs, tasks, reviews."""
from __future__ import annotations

from enum import StrEnum

_TERMINAL = frozenset({"succeeded", "failed", "cancelled", "timed_out"})
_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"queued", "cancelled", "failed"}),
    "queued": frozenset({"running", "cancelled"}),
    "running": frozenset({"succeeded", "failed", "cancelled", "timed_out"}),
}


class LifecycleState(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


def is_terminal(state: LifecycleState) -> bool:
    return state.value in _TERMINAL


def valid_transition(from_state: LifecycleState, to_state: LifecycleState) -> bool:
    allowed = _TRANSITIONS.get(from_state.value, frozenset())
    return to_state.value in allowed
