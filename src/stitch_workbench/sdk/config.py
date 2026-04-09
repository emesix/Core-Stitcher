from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfigAccessor(Protocol):
    def get(self) -> Any: ...
