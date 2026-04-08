from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any

import structlog

logger = structlog.get_logger()


class ModuleTypeRegistry:
    """Registry for module types. Supports manual registration and entry_point discovery."""

    def __init__(self) -> None:
        self._types: dict[str, Any] = {}

    def register(self, module_type: Any) -> None:
        """Register a module type class. Must have a type_name attribute."""
        name = module_type.type_name
        if name in self._types:
            raise ValueError(
                f"Module type '{name}' already registered "
                f"(existing: {self._types[name]}, new: {module_type})"
            )
        self._types[name] = module_type
        logger.info("module_type_registered", type_name=name, version=module_type.version)

    def get(self, type_name: str) -> Any | None:
        """Get a module type by name, or None if not found."""
        return self._types.get(type_name)

    def has_type(self, type_name: str) -> bool:
        return type_name in self._types

    def list_types(self) -> list[str]:
        return list(self._types.keys())

    def discover_entry_points(self, group: str = "vos.modules") -> int:
        """Discover and register module types from Python entry points.

        Returns the number of types discovered.
        """
        count = 0
        for ep in entry_points(group=group):
            try:
                module_type = ep.load()
                self.register(module_type)
                count += 1
            except Exception:
                logger.exception("entry_point_load_failed", name=ep.name, group=group)
        return count
