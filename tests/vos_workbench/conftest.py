from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from sqlmodel import Session

from vos_workbench.storage.database import create_db_engine, run_migrations


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a minimal valid project tree in a temp directory."""
    # workbench.yaml
    workbench = {
        "schema_version": 1,
        "project": {"id": "test-project", "name": "Test Project"},
    }
    (tmp_path / "workbench.yaml").write_text(yaml.dump(workbench))

    # modules/echo-shell/module.yaml
    mod_dir = tmp_path / "modules" / "echo-shell"
    mod_dir.mkdir(parents=True)
    module = {
        "uuid": str(uuid4()),
        "name": "echo-shell",
        "type": "exec.shell",
        "config": {"command": "echo hello"},
    }
    (mod_dir / "module.yaml").write_text(yaml.dump(module))

    return tmp_path


@pytest.fixture
def db_engine(tmp_path: Path):
    db_path = tmp_path / "test.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    run_migrations(engine, migration_policy="auto")
    return engine


@pytest.fixture
def db_session(db_engine):
    with Session(db_engine) as session:
        yield session
