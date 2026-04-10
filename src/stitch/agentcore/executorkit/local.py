"""LocalExecutor — hot-pluggable local inference executor (INTELL-A770 etc).

Wraps an OpenAI-compatible endpoint running on local hardware. Adds
discovery via health heartbeat, graceful unavailability handling, and
tier-aware registration for budget policy routing.

When the local endpoint is unreachable, the executor reports itself as
unhealthy so the registry can fall back to cloud executors. Automatically
re-checks health after a configurable TTL so it recovers when the
hardware comes back online.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel, Field

from stitch.agentcore.executorkit.openai_compat import (
    OpenAICompatibleExecutor,
    OpenAIExecutorConfig,
)
from stitch.agentcore.executorkit.protocol import ExecutorCapability, ExecutorHealth
from stitch.agentcore.orchestration.budget import ExecutorTier
from stitch.agentcore.taskkit.models import TaskOutcome, TaskStatus

if TYPE_CHECKING:
    from stitch.agentcore.reviewkit.models import ReviewRequest, ReviewResult
    from stitch.agentcore.taskkit.models import TaskRecord

LOCAL_EXECUTOR_URL_ENV = "LOCAL_EXECUTOR_URL"


class LocalExecutorConfig(BaseModel):
    """Configuration for a local inference executor."""

    base_url: str = "http://172.16.0.109:8000"
    api_path: str = "/v3/chat/completions"
    models_path: str | None = None
    model: str = "qwen25-7b"
    executor_id: str = "local-gpu"
    timeout: float = 120.0
    max_tokens: int = 4096
    temperature: float = 0.0
    tier: ExecutorTier = ExecutorTier.LOCAL
    tags: list[str] = Field(default_factory=lambda: ["local", "a770", "gpu"])
    health_ttl: float = 60.0


class LocalExecutor:
    """Local inference executor with availability-aware health."""

    def __init__(self, config: LocalExecutorConfig | None = None) -> None:
        self._config = config or LocalExecutorConfig()
        # Environment override for base_url (supports IP migration)
        effective_url = os.environ.get(LOCAL_EXECUTOR_URL_ENV, self._config.base_url)
        self._inner = OpenAICompatibleExecutor(
            OpenAIExecutorConfig(
                base_url=effective_url,
                api_path=self._config.api_path,
                models_path=self._config.models_path,
                model=self._config.model,
                api_key_env="__LOCAL_NO_KEY__",
                timeout=self._config.timeout,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                executor_id=self._config.executor_id,
            )
        )
        self._effective_url = effective_url
        self._available: bool | None = None
        self._last_check: datetime | None = None
        self._loaded_models: list[str] = []

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

    @property
    def loaded_models(self) -> list[str]:
        return self._loaded_models

    def _health_stale(self) -> bool:
        if self._last_check is None:
            return True
        elapsed = (datetime.now(UTC) - self._last_check).total_seconds()
        return elapsed > self._config.health_ttl

    async def health(self) -> ExecutorHealth:
        self._last_check = datetime.now(UTC)

        if self._config.models_path is not None:
            # Full HTTP health probe via models endpoint
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"{self._effective_url}{self._config.models_path}"
                    )
                    try:
                        latency = resp.elapsed.total_seconds() * 1000
                    except RuntimeError:
                        latency = None
                    if resp.status_code == 200:
                        self._available = True
                        data = resp.json()
                        self._loaded_models = [
                            m.get("id", "")
                            for m in data.get("data", data.get("models", []))
                        ]
                        model_info = (
                            ", ".join(self._loaded_models)
                            if self._loaded_models
                            else "none"
                        )
                        return ExecutorHealth(
                            status="ok",
                            message=f"models: {model_info}",
                            latency_ms=latency,
                        )
                    self._available = False
                    return ExecutorHealth(
                        status="error",
                        message=f"local endpoint returned {resp.status_code}",
                        latency_ms=latency,
                    )
            except httpx.HTTPError:
                self._available = False
                return ExecutorHealth(
                    status="error", message="local endpoint unreachable"
                )

        # TCP-only health probe (models_path is None — e.g. OVMS)
        h = await self._inner._health_tcp()
        self._available = h.status == "ok"
        return h

    async def _ensure_available(self) -> bool:
        """Re-check health if stale, return availability."""
        if self._available is False and self._health_stale():
            await self.health()
        return self._available is not False

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        if not await self._ensure_available():
            return TaskOutcome(
                status=TaskStatus.FAILED,
                error="local executor unavailable",
                executor_id=self.executor_id,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
            )
        return await self._inner.execute(task)

    async def review(self, request: ReviewRequest) -> ReviewResult:
        if not await self._ensure_available():
            from stitch.agentcore.reviewkit.models import ReviewFinding, ReviewVerdict, Severity
            from stitch.agentcore.reviewkit.models import ReviewResult as RR

            return RR(
                request_id=request.review_id,
                verdict=ReviewVerdict.REQUEST_CHANGES,
                findings=[
                    ReviewFinding(
                        description="Local executor unavailable",
                        severity=Severity.ERROR,
                    )
                ],
                summary="Local executor unavailable — retry with cloud",
            )
        return await self._inner.review(request)
