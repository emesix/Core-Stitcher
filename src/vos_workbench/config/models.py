from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, Field, computed_field, field_validator

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


class SettingsLayer(StrEnum):
    MANAGED = "managed"
    BOOTSTRAP = "bootstrap"
    PROJECT = "project"
    LOCAL = "local"
    RUNTIME = "runtime"


class StateBackends(BaseModel):
    desired: Literal["git"] = "git"
    durable_runtime: Literal["sqlite", "postgres"] = "sqlite"
    ephemeral_runtime: Literal["memory"] = "memory"
    artifacts: Literal["filesystem"] = "filesystem"


class CommunicationConfig(BaseModel):
    direct_calls: Literal["runtime-mediated"] = "runtime-mediated"
    events: Literal["pubsub"] = "pubsub"
    module_to_module_direct: bool = False


class WiringConfig(BaseModel):
    default_mode: Literal["explicit", "selector"] = "explicit"
    selector_mode: Literal["optional", "disabled"] = "optional"


class EphemeralConfig(BaseModel):
    visible_in_runtime: bool = True
    persisted_in_desired_tree: bool = False
    require_parent_task: bool = True
    require_budget: bool = True
    archive_on_exit: bool = True


class ProjectConfig(BaseModel):
    id: str = Field(pattern=r"^[a-zA-Z0-9._-]+$")
    name: str
    version: int = 1


class WorkbenchConfig(BaseModel):
    schema_version: int = 1
    project: ProjectConfig
    settings_precedence: list[SettingsLayer] = [
        SettingsLayer.MANAGED,
        SettingsLayer.BOOTSTRAP,
        SettingsLayer.PROJECT,
        SettingsLayer.LOCAL,
        SettingsLayer.RUNTIME,
    ]
    state: StateBackends = StateBackends()
    communication: CommunicationConfig = CommunicationConfig()
    wiring: WiringConfig = WiringConfig()
    ephemeral_modules: EphemeralConfig = EphemeralConfig()


class ModuleFamily(StrEnum):
    CORE = "core"
    EXEC = "exec"
    MEMORY = "memory"
    MODEL = "model"
    RESOURCE = "resource"
    INTEGRATION = "integration"
    CLIENT = "client"
    WORKER = "worker"


class Dependency(BaseModel):
    ref: str
    kind: Literal["hard", "soft"] = "hard"

    @field_validator("ref")
    @classmethod
    def ref_must_use_name_authority(cls, v: str) -> str:
        """Alpha constraint: depends_on refs must use module names, not UUIDs.
        UUID refs are runtime-only and not supported in persisted config."""
        if v.startswith("module://uuid/"):
            raise ValueError(
                "depends_on refs must use module names (module://name/x or module://x), "
                "not UUIDs. UUID refs are runtime-only."
            )
        return v


class ModuleWiring(BaseModel):
    depends_on: list[Dependency] = Field(default_factory=list)
    provides: list[str] = Field(default_factory=list)


class ModuleVisibility(BaseModel):
    can_see: list[str] = Field(default_factory=list)


class BudgetConfig(BaseModel):
    max_tokens: int | None = None
    max_seconds: float | None = None
    max_tool_calls: int | None = None


class RestartPolicy(BaseModel):
    max_restarts: int = 3
    backoff_seconds: list[float] = Field(default_factory=lambda: [1.0, 5.0, 30.0])
    reset_after_seconds: float = 300.0


class ModuleConfig(BaseModel):
    uuid: UUID
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    type: str = Field(pattern=r"^[a-z]+\.[a-z][a-z0-9._-]*$")
    lifecycle: Literal["persistent", "ephemeral"] = "persistent"
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    wiring: ModuleWiring = Field(default_factory=ModuleWiring)
    visibility: ModuleVisibility = Field(default_factory=ModuleVisibility)
    budget: BudgetConfig | None = None
    restart_policy: RestartPolicy | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_look_like_uuid(cls, v: str) -> str:
        if UUID_PATTERN.match(v):
            raise ValueError("Module names must not match UUID format")
        return v

    @computed_field
    @property
    def family(self) -> ModuleFamily:
        return ModuleFamily(self.type.split(".")[0])
