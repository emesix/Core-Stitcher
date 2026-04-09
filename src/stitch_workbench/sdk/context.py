from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModuleContext:
    module_name: str
    module_uuid: str
    publisher: Any  # EventPublisher at runtime
    config: Any  # ConfigAccessor at runtime
    capabilities: Any  # CapabilityResolver at runtime
