"""MockExecutor — deterministic executor for testing the full pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

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


class MockExecutor:
    """Deterministic executor that returns canned results based on task properties."""

    def __init__(
        self,
        executor_id: str = "mock-1",
        domains: list[str] | None = None,
        healthy: bool = True,
        review_verdicts: list[ReviewVerdict] | None = None,
    ) -> None:
        self._id = executor_id
        self._capability = ExecutorCapability(domains=domains or [])
        self._healthy = healthy
        self._review_verdicts = review_verdicts or [ReviewVerdict.APPROVE]
        self._review_call_count = 0

    @property
    def executor_id(self) -> str:
        return self._id

    @property
    def capability(self) -> ExecutorCapability:
        return self._capability

    async def execute(self, task: TaskRecord) -> TaskOutcome:
        if task.domain and self._capability.domains and task.domain not in self._capability.domains:
            return TaskOutcome(
                status=TaskStatus.FAILED,
                error=f"domain '{task.domain}' not supported",
                executor_id=self._id,
            )

        return TaskOutcome(
            status=TaskStatus.COMPLETED,
            result=f"mock result for: {task.description}",
            executor_id=self._id,
        )

    async def review(self, request: ReviewRequest) -> ReviewResult:
        idx = min(self._review_call_count, len(self._review_verdicts) - 1)
        verdict = self._review_verdicts[idx]
        self._review_call_count += 1

        findings = []
        for criterion in request.criteria:
            sev = Severity.ERROR if verdict != ReviewVerdict.APPROVE else Severity.INFO
            findings.append(
                ReviewFinding(
                    description=f"checked: {criterion}",
                    severity=sev,
                    category=criterion,
                    suggestion=f"fix {criterion}" if sev == Severity.ERROR else None,
                )
            )

        if not request.criteria:
            findings.append(
                ReviewFinding(description="no criteria specified", severity=Severity.WARNING)
            )

        return ReviewResult(
            request_id=request.review_id,
            verdict=verdict,
            findings=findings,
            summary=f"mock review #{self._review_call_count}: {verdict}",
        )

    async def health(self) -> ExecutorHealth:
        if self._healthy:
            return ExecutorHealth(status="ok", latency_ms=1.0)
        return ExecutorHealth(status="error", message="mock unhealthy")
