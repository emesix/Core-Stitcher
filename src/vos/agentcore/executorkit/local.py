"""LocalExecutor — hot-pluggable local inference executor (INTELL-A770 etc).

Wraps an OpenAI-compatible endpoint running on local hardware. Adds
discovery via health heartbeat, graceful unavailability handling, and
tier-aware registration for budget policy routing.

When the local endpoint is unreachable, the executor reports itself as
unhealthy so the registry can fall back to cloud executors.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel, Field

from vos.agentcore.executorkit.openai_compat import OpenAICompatibleExecutor, OpenAIExecutorConfig
from vos.agentcore.executorkit.protocol import ExecutorCapability, ExecutorHealth
from vos.agentcore.orchestration.budget import ExecutorTier
from vos.agentcore.taskkit.models import TaskOutcome, TaskStatus

if TYPE_CHECKING:
    from vos.agentcore.reviewkit.models import ReviewRequest, ReviewResult
    from vos.agentcore.taskkit.models import TaskRecord


class LocalExecutorConfig(BaseModel):
    """Configuration for a local inference executor."""

    base_url: str = "http://192.168.254.50:11434/v1"
    model: str = "llama3.2"
    executor_id: str = "local-a770"
    timeout: float = 120.0
    max_tokens: int = 4096
    temperature: float = 0.0
    tier: ExecutorTier = ExecutorTier.LOCAL
    tags: list[str] = Field(default_factory=lambda: ["local", "a770"])


class LocalExecutor:
    """Local inference executor with availability-aware health."""

    def __init__(self, config: LocalExecutorConfig | None = None) -> None:
        self._config = config or LocalExecutorConfig()
        self._inner = OpenAICompatibleExecutor(
            OpenAIExecutorConfig(
                base_url=self._config.base_url,
                model=self._config.model,
                api_key_env="__LOCAL_NO_KEY__",
                timeout=self._config.timeout,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                executor_id=self._config.executor_id,
            )
        )
        self._available: bool | None = None
        self._last_check: datetime | None = None

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

    @property
    def tier(self) -> ExecutorTier:
        return self._config.tier

    @property
    def available(self) -> bool | None:
        return self._available

    async def health(self) -> ExecutorHealth:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._config.base_url}/models")
                self._last_check = datetime.now(UTC)
                if resp.status_code == 200:
                    self._available = True
                    return ExecutorHealth(status="ok", message="local endpoint reachable")
                self._available = False
                return ExecutorHealth(
                    status="error",
                    message=f"local endpoint returned {resp.status_code}",
                )
        except httpx.HTTPError:
            self._available = False
            self._last_check = datetime.now(UTC)
            return ExecutorHealth(status="error", message="local endpoint unreachable")

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        if self._available is False:
            return TaskOutcome(
                status=TaskStatus.FAILED,
                error="local executor unavailable",
                executor_id=self.executor_id,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )
        return await self._inner.execute(task)

    async def review(self, request: ReviewRequest) -> ReviewResult:
        return await self._inner.review(request)
