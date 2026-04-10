"""OpenAI-compatible executor — first real provider integration.

Works with any OpenAI-style chat completions endpoint: OpenAI, local
models (Ollama, vLLM, llama.cpp), OpenRouter, etc. Turns TaskRecords
into chat completions requests and parses responses into TaskOutcomes.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
from pydantic import BaseModel, Field

from stitch.agentcore.executorkit.protocol import ExecutorCapability, ExecutorHealth
from stitch.agentcore.reviewkit.models import (
    ReviewFinding,
    ReviewResult,
    ReviewVerdict,
    Severity,
)
from stitch.agentcore.taskkit.models import TaskOutcome, TaskStatus

if TYPE_CHECKING:
    from stitch.agentcore.reviewkit.models import ReviewRequest
    from stitch.agentcore.taskkit.models import TaskRecord


class OpenAIExecutorConfig(BaseModel):
    """Configuration for an OpenAI-compatible executor."""

    base_url: str = "https://api.openai.com"
    api_path: str = "/v1/chat/completions"
    models_path: str | None = "/v1/models"
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"
    timeout: float = 60.0
    max_tokens: int = 4096
    temperature: float = 0.0
    domains: list[str] = Field(default_factory=list)
    executor_id: str = "openai-compat"


class OpenAICompatibleExecutor:
    """Executor that talks to OpenAI-style chat completions endpoints."""

    def __init__(self, config: OpenAIExecutorConfig | None = None) -> None:
        self._config = config or OpenAIExecutorConfig()

    @property
    def executor_id(self) -> str:
        return self._config.executor_id

    @property
    def capability(self) -> ExecutorCapability:
        return ExecutorCapability(
            domains=self._config.domains,
            max_concurrent=1,
            supports_streaming=False,
        )

    def _api_key(self) -> str | None:
        return os.environ.get(self._config.api_key_env)

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        key = self._api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def health(self) -> ExecutorHealth:
        key = self._api_key()
        if not key:
            return ExecutorHealth(
                status="error",
                message=f"API key not set ({self._config.api_key_env})",
            )

        if self._config.models_path is None:
            return await self._health_tcp()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self._config.base_url}{self._config.models_path}",
                    headers=self._headers(),
                )
                if resp.status_code == 200:
                    try:
                        ms = resp.elapsed.total_seconds() * 1000
                    except RuntimeError:
                        ms = None
                    return ExecutorHealth(status="ok", latency_ms=ms)
                return ExecutorHealth(
                    status="degraded",
                    message=f"models endpoint returned {resp.status_code}",
                )
        except httpx.HTTPError as e:
            return ExecutorHealth(status="error", message=str(e))

    async def _health_tcp(self) -> ExecutorHealth:
        """TCP-only health probe — avoids burning inference tokens."""
        import asyncio
        from urllib.parse import urlparse

        parsed = urlparse(self._config.base_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0,
            )
            writer.close()
            await writer.wait_closed()
            return ExecutorHealth(status="ok", message="tcp connect ok")
        except (OSError, TimeoutError) as e:
            return ExecutorHealth(status="error", message=f"tcp connect failed: {e}")

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        started = datetime.now(UTC)
        messages = self._build_execute_messages(task)

        try:
            content = await self._chat_completion(messages)
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
            result=content,
            executor_id=self.executor_id,
            started_at=started,
            finished_at=datetime.now(UTC),
        )

    async def review(self, request: ReviewRequest) -> ReviewResult:
        messages = self._build_review_messages(request)

        try:
            content = await self._chat_completion(messages)
            return self._parse_review_response(content, request)
        except Exception as e:
            return ReviewResult(
                request_id=request.review_id,
                verdict=ReviewVerdict.REQUEST_CHANGES,
                findings=[
                    ReviewFinding(
                        description=f"Review failed: {e}",
                        severity=Severity.ERROR,
                    )
                ],
                summary=f"Review error: {e}",
            )

    async def _chat_completion(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self._config.model,
            "messages": messages,
            "max_tokens": self._config.max_tokens,
            "temperature": self._config.temperature,
        }

        async with httpx.AsyncClient(timeout=self._config.timeout) as client:
            resp = await client.post(
                f"{self._config.base_url}{self._config.api_path}",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _build_execute_messages(self, task: TaskRecord) -> list[dict[str, str]]:
        system = "You are a task executor. Complete the given task concisely and accurately."
        if task.domain:
            system += f" Domain: {task.domain}."

        user = task.description
        if task.metadata:
            user += f"\n\nContext: {json.dumps(task.metadata)}"

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _build_review_messages(self, request: ReviewRequest) -> list[dict[str, str]]:
        system = (
            "You are a code/task reviewer. Evaluate the given content against the criteria. "
            "Respond with a JSON object: "
            '{"verdict": "approve"|"request_changes"|"reject", '
            '"findings": [{"description": "...", "severity": "info"|"warning"|"error"|"critical", '
            '"category": "...", "suggestion": "..."}], '
            '"summary": "..."}'
        )

        content_str = str(request.content) if request.content else "No content provided"
        criteria_str = ", ".join(request.criteria) if request.criteria else "general quality"
        user = f"Content to review:\n{content_str}\n\nCriteria: {criteria_str}"

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _parse_review_response(self, content: str, request: ReviewRequest) -> ReviewResult:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return ReviewResult(
                request_id=request.review_id,
                verdict=ReviewVerdict.APPROVE,
                findings=[
                    ReviewFinding(description=content, severity=Severity.INFO)
                ],
                summary="Non-JSON response treated as approval with note",
            )

        verdict_str = data.get("verdict", "approve")
        try:
            verdict = ReviewVerdict(verdict_str)
        except ValueError:
            verdict = ReviewVerdict.APPROVE

        findings = []
        for f in data.get("findings", []):
            sev_str = f.get("severity", "info")
            try:
                sev = Severity(sev_str)
            except ValueError:
                sev = Severity.INFO
            findings.append(
                ReviewFinding(
                    description=f.get("description", ""),
                    severity=sev,
                    category=f.get("category"),
                    suggestion=f.get("suggestion"),
                )
            )

        return ReviewResult(
            request_id=request.review_id,
            verdict=verdict,
            findings=findings,
            summary=data.get("summary", ""),
        )
