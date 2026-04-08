"""Tests for Alembic migration infrastructure."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session

from vos_workbench.storage.database import create_db_engine, run_migrations


def test_run_migrations_creates_tables_on_empty_db(tmp_path: Path):
    """Auto mode: empty DB gets all tables via Alembic."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_db_engine(db_url)

    run_migrations(engine, migration_policy="auto")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "eventrecord" in tables
    assert "modulehealthrecord" in tables
    assert "sessionrecord" in tables
    assert "taskrecord" in tables
    assert "alembic_version" in tables


def test_run_migrations_strict_mode_fails_on_empty_db(tmp_path: Path):
    """Strict mode: empty DB (no alembic_version) raises."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_db_engine(db_url)

    with pytest.raises(RuntimeError, match="migration_policy.*strict"):
        run_migrations(engine, migration_policy="strict")


def test_run_migrations_strict_mode_passes_when_current(tmp_path: Path):
    """Strict mode: fully migrated DB passes."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_db_engine(db_url)

    # First: auto-migrate to get to head
    run_migrations(engine, migration_policy="auto")

    # Second: strict should pass (already at head)
    run_migrations(engine, migration_policy="strict")


def test_run_migrations_idempotent(tmp_path: Path):
    """Running auto twice does not error."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_db_engine(db_url)

    run_migrations(engine, migration_policy="auto")
    run_migrations(engine, migration_policy="auto")

    inspector = inspect(engine)
    assert "eventrecord" in set(inspector.get_table_names())


def test_migration_preserves_data(tmp_path: Path):
    """Data written after migration survives a second run_migrations call."""
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_db_engine(db_url)

    run_migrations(engine, migration_policy="auto")

    # Insert a row
    with Session(engine) as session:
        session.exec(
            text(
                "INSERT INTO eventrecord (id, type, source, project_id, time, severity, data) "
                "VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'test', 'src', 'proj', "
                "'2026-01-01T00:00:00', 'info', '{}')"
            )
        )
        session.commit()

    # Run migrations again
    run_migrations(engine, migration_policy="auto")

    # Data still there
    with Session(engine) as session:
        result = session.exec(text("SELECT count(*) FROM eventrecord")).one()
        assert result[0] == 1
