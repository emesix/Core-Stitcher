"""Tests for the run detail screen."""

from __future__ import annotations

from stitch.apps.tui.screens.run_detail import RunDetailScreen


def test_run_detail_creation():
    run = {
        "run_id": "run_4f8a",
        "status": "running",
        "description": "preflight site-rdam",
        "tasks": [
            {"task_id": "tsk_001", "status": "succeeded", "description": "collect switchcraft"},
            {"task_id": "tsk_002", "status": "running", "description": "collect proxmox"},
        ],
    }
    screen = RunDetailScreen(run=run)
    assert screen.run["run_id"] == "run_4f8a"
    assert len(screen.run["tasks"]) == 2


def test_run_detail_empty_tasks():
    run = {"run_id": "run_x", "status": "pending", "description": "test", "tasks": []}
    screen = RunDetailScreen(run=run)
    assert screen.run["tasks"] == []
