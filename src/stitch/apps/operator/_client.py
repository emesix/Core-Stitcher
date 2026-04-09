"""Client lifecycle helper for CLI commands."""
from __future__ import annotations

import asyncio
import os

from stitch.apps.operator.app import get_state
from stitch.apps.operator.output import OutputFormatter
from stitch.sdk.client import StitchClient
from stitch.sdk.config import Profile, load_config


def get_client() -> StitchClient:
    state = get_state()
    config = load_config(state.config)
    env_server = os.environ.get("STITCH_SERVER")
    env_profile = os.environ.get("STITCH_PROFILE")
    profile_name = state.profile or env_profile
    profile = Profile(server=env_server) if env_server else config.resolve_profile(profile_name)
    return StitchClient(profile)


def get_formatter() -> OutputFormatter:
    state = get_state()
    return OutputFormatter(state.output)


def run_async(coro):
    return asyncio.run(coro)
