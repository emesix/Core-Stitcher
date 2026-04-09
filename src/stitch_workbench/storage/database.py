from __future__ import annotations

from pathlib import Path
from typing import Literal

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import event
from sqlmodel import Session, create_engine

import stitch_workbench.storage.models  # noqa: F401
from alembic import command

# Alembic directory is at project root: <repo>/alembic/
_ALEMBIC_DIR = Path(__file__).resolve().parents[3] / "alembic"
_ALEMBIC_INI = _ALEMBIC_DIR.parent / "alembic.ini"


def create_db_engine(db_url: str = "sqlite:///stitch_workbench.db"):
    engine = create_engine(db_url, echo=False)

    if db_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def run_migrations(
    engine,
    migration_policy: Literal["auto", "strict"] = "auto",
) -> None:
    """Run or verify Alembic migrations.

    - auto: run upgrade head (creates tables on empty DB, applies pending).
    - strict: compare current revision to head; raise if they differ.
    """
    alembic_cfg = Config(str(_ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(_ALEMBIC_DIR))

    with engine.connect() as connection:
        alembic_cfg.attributes["connection"] = connection

        if migration_policy == "auto":
            command.upgrade(alembic_cfg, "head")
        elif migration_policy == "strict":
            context = MigrationContext.configure(connection)
            current_rev = context.get_current_revision()

            script = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script.get_current_head()

            if current_rev != head_rev:
                raise RuntimeError(
                    f"migration_policy is 'strict' but schema is not at head. "
                    f"Current: {current_rev}, Head: {head_rev}. "
                    f"Run 'alembic upgrade head' manually."
                )


def get_session(engine) -> Session:
    return Session(engine)
