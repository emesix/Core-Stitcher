"""App factory — wire store, registry, and routes into a FastAPI app."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from stitch.agentcore.bootstrap import build_alpha_registry
from stitch.agentcore.storekit import JsonRunStore
from stitch.apps.project_stitcher.api import create_router


def create_app(
    store_dir: str | Path = "~/.stitch/project-stitcher/runs",
) -> FastAPI:
    store = JsonRunStore(Path(store_dir).expanduser())
    registry, routing = build_alpha_registry()

    app = FastAPI(title="Stitch Project Explorer", version="0.1.0")
    app.include_router(create_router(store, registry, routing))
    return app
