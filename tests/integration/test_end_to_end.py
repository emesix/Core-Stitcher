"""End-to-end tests — request → plan → resolve → execute → review."""

from __future__ import annotations

from vos.agentcore.executorkit import ExecutorProtocol
from vos.agentcore.executorkit.mock import MockExecutor
from vos.agentcore.plannerkit import SubtaskSpec, WorkRequest, plan_request
from vos.agentcore.registry import ExecutorRegistry
from vos.agentcore.reviewkit import ReviewRequest, ReviewVerdict, Severity
from vos.agentcore.taskkit import TaskRecord, TaskStatus

# --- MockExecutor unit tests ---


def test_mock_implements_protocol():
    assert isinstance(MockExecutor(), ExecutorProtocol)


async def test_mock_execute_success():
    ex = MockExecutor()
    task = TaskRecord(description="do something")
    outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert "do something" in outcome.result
    assert outcome.executor_id == "mock-1"


async def test_mock_execute_domain_mismatch():
    ex = MockExecutor(domains=["research"])
    task = TaskRecord(description="verify", domain="topology")
    outcome = await ex.execute(task)
    assert outcome.status == TaskStatus.FAILED
    assert "not supported" in outcome.error


async def test_mock_review_with_criteria():
    ex = MockExecutor()
    req = ReviewRequest(criteria=["correctness", "completeness"])
    result = await ex.review(req)
    assert result.verdict == ReviewVerdict.APPROVE
    assert len(result.findings) == 2
    assert all(f.severity == Severity.INFO for f in result.findings)


async def test_mock_review_no_criteria():
    ex = MockExecutor()
    req = ReviewRequest()
    result = await ex.review(req)
    assert result.has_warnings is True
    assert len(result.findings) == 1


async def test_mock_healthy():
    ex = MockExecutor(healthy=True)
    h = await ex.health()
    assert h.status == "ok"


async def test_mock_unhealthy():
    ex = MockExecutor(healthy=False)
    h = await ex.health()
    assert h.status == "error"


# --- Registry integration ---


async def test_registry_resolves_mock():
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))
    reg.register(MockExecutor("research-exec", domains=["research"]))

    task = TaskRecord(description="verify", domain="topology")
    matches = reg.find_for_task(task)
    assert len(matches) == 1
    assert matches[0].executor_id == "topo-exec"


async def test_registry_filters_unhealthy():
    reg = ExecutorRegistry()
    reg.register(MockExecutor("good", healthy=True))
    reg.register(MockExecutor("bad", healthy=False))

    healthy = await reg.healthy_executors()
    ids = {ex.executor_id for ex, _h in healthy}
    assert ids == {"good"}


# --- Full pipeline ---


async def test_full_pipeline_single_task():
    """request → plan → resolve → execute → outcome"""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("topo-exec", domains=["topology"]))

    request = WorkRequest(description="verify topology", domain="topology")
    plan = plan_request(request)
    assert len(plan.tasks) == 1

    root = plan.root_task
    task = TaskRecord(description=root.description, domain=root.domain, priority=root.priority)

    executors = reg.find_for_task(task)
    assert len(executors) == 1

    outcome = await executors[0].execute(task)
    assert outcome.status == TaskStatus.COMPLETED
    assert outcome.executor_id == "topo-exec"


async def test_full_pipeline_multi_task():
    """Multi-task plan executed in order."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("general"))

    request = WorkRequest(
        description="full analysis",
        domain="topology",
        subtasks=[
            SubtaskSpec(description="collect"),
            SubtaskSpec(description="verify", depends_on=[0]),
        ],
    )
    plan = plan_request(request)
    assert len(plan.tasks) == 3

    outcomes = []
    for planned in plan.execution_order():
        task = TaskRecord(
            description=planned.description,
            domain=planned.domain,
            priority=planned.priority,
        )
        executors = reg.find_for_task(task)
        outcome = await executors[0].execute(task)
        outcomes.append(outcome)

    assert all(o.status == TaskStatus.COMPLETED for o in outcomes)
    assert len(outcomes) == 3


async def test_full_pipeline_with_review():
    """request → plan → execute → review"""
    reg = ExecutorRegistry()
    mock = MockExecutor("general")
    reg.register(mock)

    request = WorkRequest(description="build feature")
    plan = plan_request(request)

    task = TaskRecord(description=plan.root_task.description)
    outcome = await mock.execute(task)
    assert outcome.status == TaskStatus.COMPLETED

    review_req = ReviewRequest(
        plan_id=plan.plan_id,
        criteria=["correctness", "completeness"],
    )
    review = await mock.review(review_req)
    assert review.verdict == ReviewVerdict.APPROVE
    assert len(review.findings) == 2


async def test_full_pipeline_no_executor_for_domain():
    """Registry returns empty when no executor matches domain."""
    reg = ExecutorRegistry()
    reg.register(MockExecutor("research-only", domains=["research"]))

    request = WorkRequest(description="check topology", domain="topology")
    plan = plan_request(request)

    task = TaskRecord(description=plan.root_task.description, domain="topology")
    matches = reg.find_for_task(task)
    assert matches == []
