from datetime import UTC, datetime
from uuid import uuid4

from sqlmodel import select


def test_create_event_record(db_session):
    from vos_workbench.storage.models import EventRecord

    record = EventRecord(
        id=uuid4(),
        type="module.started",
        source="module://name/exec-shell",
        project_id="test",
        time=datetime.now(UTC),
        severity="info",
        data={"module": "exec-shell"},
    )
    db_session.add(record)
    db_session.commit()

    result = db_session.get(EventRecord, record.id)
    assert result is not None
    assert result.type == "module.started"
    assert result.data["module"] == "exec-shell"


def test_create_module_health_record(db_session):
    from vos_workbench.storage.models import ModuleHealthRecord

    record = ModuleHealthRecord(
        module_uuid=uuid4(),
        status="active",
        checked_at=datetime.now(UTC),
    )
    db_session.add(record)
    db_session.commit()

    statement = select(ModuleHealthRecord)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    assert results[0].status == "active"


def test_query_events_by_type(db_session):
    from vos_workbench.storage.models import EventRecord

    now = datetime.now(UTC)
    for evt_type in ["a", "b", "a", "c"]:
        db_session.add(
            EventRecord(
                id=uuid4(),
                type=evt_type,
                source="module://name/test",
                project_id="test",
                time=now,
                severity="info",
                data={},
            )
        )
    db_session.commit()

    statement = select(EventRecord).where(EventRecord.type == "a")
    results = db_session.exec(statement).all()
    assert len(results) == 2
