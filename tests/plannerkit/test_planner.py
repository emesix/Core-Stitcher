"""Tests for plannerkit — deterministic request-to-plan decomposition."""

from __future__ import annotations

from stitch.agentcore.plannerkit import PlanRecord, SubtaskSpec, WorkRequest, plan_request
from stitch.agentcore.taskkit import TaskPriority

# --- Single task ---


def test_single_task_plan():
    req = WorkRequest(description="verify topology")
    plan = plan_request(req)
    assert len(plan.tasks) == 1
    assert plan.tasks[0].is_root is True
    assert plan.tasks[0].description == "verify topology"


def test_single_task_inherits_domain():
    req = WorkRequest(description="check", domain="topology")
    plan = plan_request(req)
    assert plan.root_task is not None
    assert plan.root_task.domain == "topology"


def test_single_task_inherits_priority():
    req = WorkRequest(description="urgent check", priority=TaskPriority.CRITICAL)
    plan = plan_request(req)
    assert plan.root_task.priority == TaskPriority.CRITICAL


# --- Multi-task ---


def test_multi_task_plan():
    req = WorkRequest(
        description="full analysis",
        subtasks=[
            SubtaskSpec(description="collect data"),
            SubtaskSpec(description="analyze results"),
        ],
    )
    plan = plan_request(req)
    assert len(plan.tasks) == 3  # root + 2 children
    assert plan.root_task is not None
    assert plan.root_task.description == "full analysis"


def test_subtasks_inherit_parent_domain():
    req = WorkRequest(
        description="topology work",
        domain="topology",
        subtasks=[
            SubtaskSpec(description="step 1"),
            SubtaskSpec(description="step 2", domain="research"),
        ],
    )
    plan = plan_request(req)
    children = [t for t in plan.tasks if not t.is_root]
    assert children[0].domain == "topology"  # inherited
    assert children[1].domain == "research"  # overridden


def test_subtask_priority():
    req = WorkRequest(
        description="work",
        subtasks=[
            SubtaskSpec(description="low", priority=TaskPriority.LOW),
            SubtaskSpec(description="high", priority=TaskPriority.HIGH),
        ],
    )
    plan = plan_request(req)
    children = [t for t in plan.tasks if not t.is_root]
    assert children[0].priority == TaskPriority.LOW
    assert children[1].priority == TaskPriority.HIGH


# --- Dependencies ---


def test_dependency_edges():
    req = WorkRequest(
        description="pipeline",
        subtasks=[
            SubtaskSpec(description="step A"),
            SubtaskSpec(description="step B", depends_on=[0]),
            SubtaskSpec(description="step C", depends_on=[0, 1]),
        ],
    )
    plan = plan_request(req)
    children = [t for t in plan.tasks if not t.is_root]
    a, b, c = children

    assert b.depends_on == [a.task_id]
    assert set(c.depends_on) == {a.task_id, b.task_id}


def test_root_depends_on_leaves():
    req = WorkRequest(
        description="pipeline",
        subtasks=[
            SubtaskSpec(description="step A"),
            SubtaskSpec(description="step B", depends_on=[0]),
        ],
    )
    plan = plan_request(req)
    children = [t for t in plan.tasks if not t.is_root]
    # step B depends on step A, so step B is the leaf
    # root should depend on step B (the leaf)
    assert plan.root_task.depends_on == [children[1].task_id]


def test_self_dependency_ignored():
    req = WorkRequest(
        description="work",
        subtasks=[SubtaskSpec(description="step", depends_on=[0])],
    )
    plan = plan_request(req)
    children = [t for t in plan.tasks if not t.is_root]
    assert children[0].depends_on == []


def test_out_of_range_dependency_ignored():
    req = WorkRequest(
        description="work",
        subtasks=[SubtaskSpec(description="step", depends_on=[5, -1])],
    )
    plan = plan_request(req)
    children = [t for t in plan.tasks if not t.is_root]
    assert children[0].depends_on == []


# --- Execution order ---


def test_execution_order_single():
    req = WorkRequest(description="one thing")
    plan = plan_request(req)
    order = plan.execution_order()
    assert len(order) == 1
    assert order[0].is_root is True


def test_execution_order_respects_dependencies():
    req = WorkRequest(
        description="pipeline",
        subtasks=[
            SubtaskSpec(description="step A"),
            SubtaskSpec(description="step B", depends_on=[0]),
            SubtaskSpec(description="step C", depends_on=[1]),
        ],
    )
    plan = plan_request(req)
    order = plan.execution_order()
    descs = [t.description for t in order]
    assert descs.index("step A") < descs.index("step B")
    assert descs.index("step B") < descs.index("step C")
    assert descs.index("step C") < descs.index("pipeline")


# --- Determinism ---


def test_deterministic_output():
    req = WorkRequest(
        description="test",
        subtasks=[
            SubtaskSpec(description="a"),
            SubtaskSpec(description="b", depends_on=[0]),
        ],
    )
    plan1 = plan_request(req)
    plan2 = plan_request(req)
    # Structure should be identical (UUIDs will differ)
    assert len(plan1.tasks) == len(plan2.tasks)
    for t1, t2 in zip(plan1.tasks, plan2.tasks, strict=True):
        assert t1.description == t2.description
        assert t1.is_root == t2.is_root
        assert t1.domain == t2.domain
        assert t1.priority == t2.priority


# --- Serialization ---


def test_plan_serialization_roundtrip():
    req = WorkRequest(
        description="roundtrip",
        subtasks=[SubtaskSpec(description="child", depends_on=[])],
    )
    plan = plan_request(req)
    data = plan.model_dump(mode="json")
    restored = PlanRecord.model_validate(data)
    assert len(restored.tasks) == len(plan.tasks)
    assert restored.request_description == plan.request_description


def test_plan_root_task_none_when_empty():
    plan = PlanRecord(request_description="empty", tasks=[])
    assert plan.root_task is None
