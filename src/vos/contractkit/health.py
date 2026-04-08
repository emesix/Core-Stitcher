from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModuleHealth:
    status: str
    message: str | None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModuleStatus:
    module_name: str
    module_type: str
    health: ModuleHealth
