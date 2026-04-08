"""Initial schema: EventRecord, ModuleHealthRecord, SessionRecord, TaskRecord.

Revision ID: 001
Revises:
Create Date: 2026-04-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eventrecord",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("causation_id", sa.Uuid(), nullable=True),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eventrecord_type"), "eventrecord", ["type"])
    op.create_index(op.f("ix_eventrecord_project_id"), "eventrecord", ["project_id"])
    op.create_index(op.f("ix_eventrecord_time"), "eventrecord", ["time"])

    op.create_table(
        "modulehealthrecord",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("module_uuid", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_modulehealthrecord_module_uuid"),
        "modulehealthrecord",
        ["module_uuid"],
    )

    op.create_table(
        "sessionrecord",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("metadata_", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "taskrecord",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("parent_task_id", sa.Uuid(), nullable=True),
        sa.Column("module_uuid", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("result_summary", sa.String(), nullable=True),
        sa.Column("budget_used", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("taskrecord")
    op.drop_table("sessionrecord")
    op.drop_index(op.f("ix_modulehealthrecord_module_uuid"), table_name="modulehealthrecord")
    op.drop_table("modulehealthrecord")
    op.drop_index(op.f("ix_eventrecord_time"), table_name="eventrecord")
    op.drop_index(op.f("ix_eventrecord_project_id"), table_name="eventrecord")
    op.drop_index(op.f("ix_eventrecord_type"), table_name="eventrecord")
    op.drop_table("eventrecord")
