from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModuleManifest:
    capabilities_provided: list[str] = field(default_factory=list)
    capabilities_required: list[str] = field(default_factory=list)
