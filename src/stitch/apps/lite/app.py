"""Stitch Lite — minimal HTML server."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from stitch.sdk.client import StitchClient
from stitch.sdk.config import Profile, load_config

_HERE = Path(__file__).parent


def create_app(profile: str | None = None) -> FastAPI:
    app = FastAPI(title="Stitch Lite", docs_url=None, redoc_url=None)

    # Templates and static files
    templates = Jinja2Templates(directory=str(_HERE / "templates"))
    app.mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static")

    # SDK client (in-process, not HTTP loopback)
    config = load_config()
    env_server = os.environ.get("STITCH_SERVER")
    if env_server:
        prof = Profile(server=env_server)
    else:
        try:
            prof = config.resolve_profile(profile)
        except KeyError:
            prof = Profile(server="http://localhost:8000")

    client = StitchClient(prof)

    # Store on app state for route access
    app.state.client = client
    app.state.templates = templates

    # Register routes
    from stitch.apps.lite.routes import create_routes

    app.include_router(create_routes())

    return app


def main() -> None:
    parser = argparse.ArgumentParser(prog="stitch-lite")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    app = create_app(profile=args.profile)
    uvicorn.run(app, host=args.host, port=args.port)
