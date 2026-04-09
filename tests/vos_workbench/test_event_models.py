from datetime import datetime


def test_vos_event_minimal():
    from stitch_workbench.events.models import VosEvent

    event = VosEvent(
        type="module.started",
        source="module://name/exec-shell",
        project_id="test-project",
    )
    assert event.id is not None
    assert event.severity == "info"
    assert event.data == {}
    assert event.correlation_id is None
    assert isinstance(event.time, datetime)


def test_vos_event_full():
    from uuid import uuid4

    from stitch_workbench.events.models import VosEvent

    corr = uuid4()
    cause = uuid4()
    event = VosEvent(
        type="task.completed",
        source="module://name/router-main",
        project_id="vos",
        correlation_id=corr,
        causation_id=cause,
        data={"task_name": "deploy", "result": "success"},
        severity="info",
    )
    assert event.correlation_id == corr
    assert event.causation_id == cause
    assert event.data["task_name"] == "deploy"


def test_vos_event_severity_values():
    from stitch_workbench.events.models import VosEvent

    for sev in ("debug", "info", "warning", "error"):
        event = VosEvent(
            type="test",
            source="module://name/test",
            project_id="test",
            severity=sev,
        )
        assert event.severity == sev


def test_vos_event_time_is_utc():
    from stitch_workbench.events.models import VosEvent

    event = VosEvent(
        type="test",
        source="module://name/test",
        project_id="test",
    )
    assert event.time.tzinfo is not None
