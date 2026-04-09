"""Store protocol — the contract for run persistence backends."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID

    from stitch.agentcore.storekit.models import RunRecord


@runtime_checkable
class RunStore(Protocol):
    def save(self, run: RunRecord) -> None: ...
    def get(self, run_id: UUID) -> RunRecord | None: ...
    def list_runs(self) -> list[RunRecord]: ...
    def delete(self, run_id: UUID) -> bool: ...
