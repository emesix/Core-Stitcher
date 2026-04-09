"""TopologyExecutor — domain executor backed by Ruggensgraat's REST API.

Routes topology-domain tasks to a running Ruggensgraat instance.
Maps task metadata to specific API calls (verify, trace, impact,
diagnostics). Returns raw domain results as TaskOutcome.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import BaseModel

from vos.agentcore.executorkit.protocol import ExecutorCapability, ExecutorHealth
from vos.agentcore.taskkit.models import TaskOutcome, TaskStatus

if TYPE_CHECKING:
    from vos.agentcore.taskkit.models import TaskRecord


class TopologyExecutorConfig(BaseModel):
    """Configuration for a Ruggensgraat topology executor."""

    base_url: str = "http://localhost:8000"
    timeout: float = 30.0
    executor_id: str = "topology-ruggensgraat"


# Maps action names to (method, path, body_builder)
_ACTION_MAP: dict[str, tuple[str, str]] = {
    "verify": ("POST", "/verify"),
    "trace": ("POST", "/trace"),
    "impact": ("POST", "/impact"),
    "diff": ("POST", "/diff"),
    "topology": ("GET", "/topology"),
    "devices": ("GET", "/explorer/devices"),
    "device": ("GET", "/explorer/devices/{device_id}"),
    "neighbors": ("GET", "/explorer/devices/{device_id}/neighbors"),
    "vlans": ("GET", "/explorer/vlans/{vlan_id}"),
    "diagnostics": ("GET", "/explorer/diagnostics"),
}


class TopologyExecutor:
    """Executor that delegates topology tasks to a Ruggensgraat instance."""

    def __init__(self, config: TopologyExecutorConfig | None = None) -> None:
        self._config = config or TopologyExecutorConfig()

    @property
    def executor_id(self) -> str:
        return self._config.executor_id

    @property
    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            domains=["topology"],
            max_concurrent=1,
            tags=list(_ACTION_MAP.keys()),
        )

    async def health(self) -> ExecutorHealth:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._config.base_url}/topology")
                if resp.status_code == 200:
                    return ExecutorHealth(status="ok")
                return ExecutorHealth(
                    status="degraded",
                    message=f"topology endpoint returned {resp.status_code}",
                )
        except httpx.HTTPError as e:
            return ExecutorHealth(status="error", message=str(e))

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        started = datetime.now(UTC)
        action = task.metadata.get("action", "verify")
        params = task.metadata.get("params", {})

        spec = _ACTION_MAP.get(action)
        if spec is None:
            return TaskOutcome(
                status=TaskStatus.FAILED,
                error=f"Unknown topology action: {action}",
                executor_id=self.executor_id,
                started_at=started,
                finished_at=datetime.now(UTC),
            )

        method, path_template = spec
        path = path_template.format(**params) if "{" in path_template else path_template

        try:
            result = await self._call(method, path, params if method == "POST" else None)
        except Exception as e:
            return TaskOutcome(
                status=TaskStatus.FAILED,
                error=str(e),
                executor_id=self.executor_id,
                started_at=started,
                finished_at=datetime.now(UTC),
            )

        return TaskOutcome(
            status=TaskStatus.COMPLETED,
            result=result,
            executor_id=self.executor_id,
            started_at=started,
            finished_at=datetime.now(UTC),
        )

    async def _call(self, method: str, path: str, body: Any | None = None) -> Any:
        url = f"{self._config.base_url}{path}"
        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            if method == "POST":
                resp = await client.post(url, json=body or {})
            else:
                resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
