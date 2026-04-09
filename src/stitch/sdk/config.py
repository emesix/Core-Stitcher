"""Stitch SDK configuration — profiles, server, token resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

_DEFAULT_CONFIG_PATH = Path.home() / ".config" / "stitch" / "config.yaml"


class Defaults(BaseModel):
    output: str = "human"
    color: str = "auto"
    confirm: bool = True
    page_size: int = 50


class Profile(BaseModel):
    server: str
    token: str | None = None
    token_command: str | None = None

    def resolve_token(self) -> str | None:
        if self.token:
            return self.token
        if self.token_command:
            result = subprocess.run(
                self.token_command,
                shell=True,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        return None


class StitchConfig(BaseModel):
    default_profile: str | None = None
    profiles: dict[str, Profile] = Field(default_factory=dict)
    defaults: Defaults = Field(default_factory=Defaults)

    def resolve_profile(self, name: str | None) -> Profile:
        key = name or self.default_profile
        if key is None or key not in self.profiles:
            msg = f"Profile not found: {key}"
            raise KeyError(msg)
        return self.profiles[key]


def load_config(path: Path | None = None) -> StitchConfig:
    cfg_path = path or _DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return StitchConfig()
    raw = yaml.safe_load(cfg_path.read_text()) or {}
    return StitchConfig(**raw)
