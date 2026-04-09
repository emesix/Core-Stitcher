"""ExecutorRegistry — in-memory executor resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vos.agentcore.executorkit.protocol import ExecutorHealth, ExecutorProtocol
    from vos.agentcore.taskkit.models import TaskRecord


class ExecutorNotFoundError(LookupError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(f"No executor found{': ' + detail if detail else ''}")


class ExecutorRegistry:
    """Registers executors and resolves them against task requirements."""

    def __init__(self) -> None:
        self._executors: dict[str, ExecutorProtocol] = {}

    def register(self, executor: ExecutorProtocol) -> None:
        self._executors[executor.executor_id] = executor

    def unregister(self, executor_id: str) -> None:
        self._executors.pop(executor_id, None)

    def get(self, executor_id: str) -> ExecutorProtocol:
        executor = self._executors.get(executor_id)
        if executor is None:
            raise ExecutorNotFoundError(executor_id)
        return executor

    def list_all(self) -> list[ExecutorProtocol]:
        return list(self._executors.values())

    def find_for_task(self, task: TaskRecord) -> list[ExecutorProtocol]:
        """Return executors whose capabilities match the task's domain."""
        matches = []
        for executor in self._executors.values():
            cap = executor.capability
            if task.domain is None or not cap.domains or task.domain in cap.domains:
                matches.append(executor)
        return matches

    async def healthy_executors(self) -> list[tuple[ExecutorProtocol, ExecutorHealth]]:
        """Return all executors with status 'ok' or 'degraded', with their health."""
        results = []
        for executor in self._executors.values():
            h = await executor.health()
            if h.status in ("ok", "degraded"):
                results.append((executor, h))
        return results

    def __len__(self) -> int:
        return len(self._executors)
