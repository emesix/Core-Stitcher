"""SidecarExecutor — thin read-only work executor for the A770 sidecar.

Dispatches structured compute tasks to the INTELL-A770 sidecar service.
Does NOT speak chat completions — this is a work executor, not an LLM.
Implements ExecutorProtocol (not ReviewableExecutorProtocol).

Fail-closed: if sidecar is down, task fails. No silent LLM fallback.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel, Field

from stitch.agentcore.executorkit.protocol import ExecutorCapability, ExecutorHealth
from stitch.agentcore.taskkit.models import TaskOutcome, TaskStatus

if TYPE_CHECKING:
    from stitch.agentcore.taskkit.models import TaskRecord


class SidecarConfig(BaseModel):
    """Configuration for the sidecar compute executor."""

    base_url: str = "http://172.16.0.109:8080"
    executor_id: str = "local-sidecar"
    timeout: float = 30.0
    tags: list[str] = Field(default_factory=lambda: ["local", "a770", "sidecar", "compute"])


class SidecarExecutor:
    """Thin work executor for structured compute dispatch to the A770 sidecar."""

    def __init__(self, config: SidecarConfig | None = None) -> None:
        self._config = config or SidecarConfig()

    @property
    def executor_id(self) -> str:
        return self._config.executor_id

    @property
    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            domains=[],
            max_concurrent=1,
            supports_streaming=False,
            tags=self._config.tags,
        )

    async def health(self) -> ExecutorHealth:
        """Hit sidecar health endpoint, return status + backend details."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._config.base_url}/health")
                if resp.status_code == 200:
                    try:
                        latency = resp.elapsed.total_seconds() * 1000
                    except RuntimeError:
                        latency = None
                    data = resp.json()
                    details = data.get("details", {})
                    detail_str = ", ".join(
                        f"{k}: {v}" for k, v in details.items()
                    ) if details else data.get("status", "ok")
                    return ExecutorHealth(
                        status=data.get("status", "ok"),
                        message=detail_str,
                        latency_ms=latency,
                    )
                return ExecutorHealth(
                    status="error",
                    message=f"sidecar returned {resp.status_code}",
                )
        except httpx.HTTPError:
            return ExecutorHealth(status="error", message="sidecar unreachable")

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        """Dispatch a structured read-only task to the sidecar."""
        started = datetime.now(UTC)

        payload = self._build_payload(task)

        try:
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                resp = await client.post(
                    f"{self._config.base_url}/work",
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                return TaskOutcome(
                    status=TaskStatus.COMPLETED,
                    result=result,
                    executor_id=self.executor_id,
                    started_at=started,
                    finished_at=datetime.now(UTC),
                )
        except Exception as e:
            return TaskOutcome(
                status=TaskStatus.FAILED,
                error=str(e),
                executor_id=self.executor_id,
                started_at=started,
                finished_at=datetime.now(UTC),
            )

    def _build_payload(self, task: TaskRecord) -> dict[str, Any]:
        """Build sidecar WorkRequest — mirrors TaskRecord shape over the wire."""
        payload: dict[str, Any] = {
            "id": str(task.id),
            "description": task.description,
        }
        if task.domain:
            payload["domain"] = task.domain
        if task.metadata:
            payload["metadata"] = task.metadata
        return payload
