from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
import yaml

if TYPE_CHECKING:
    from pathlib import Path

from vos_workbench.config.models import ModuleConfig, WorkbenchConfig

logger = structlog.get_logger()


class ConfigLoadError(Exception):
    """Raised when config loading fails."""


def load_workbench_config(project_root: Path) -> WorkbenchConfig:
    """Load and validate workbench.yaml from project root."""
    config_path = project_root / "workbench.yaml"
    if not config_path.exists():
        raise ConfigLoadError(f"workbench.yaml not found in {project_root}")

    raw = yaml.safe_load(config_path.read_text())
    if raw is None:
        raise ConfigLoadError(f"workbench.yaml is empty in {project_root}")

    return WorkbenchConfig.model_validate(raw)


def load_module_configs(project_root: Path) -> list[ModuleConfig]:
    """Load all module.yaml files from modules/ subdirectories."""
    modules_dir = project_root / "modules"
    if not modules_dir.exists():
        return []

    modules: list[ModuleConfig] = []
    for mod_dir in sorted(modules_dir.iterdir()):
        if not mod_dir.is_dir():
            continue

        module_yaml = mod_dir / "module.yaml"
        if not module_yaml.exists():
            logger.warning("module_dir_missing_yaml", dir=str(mod_dir))
            continue

        raw = yaml.safe_load(module_yaml.read_text())
        if raw is None:
            logger.warning("module_yaml_empty", path=str(module_yaml))
            continue

        config = ModuleConfig.model_validate(raw)

        # Enforce directory name == module name
        if mod_dir.name != config.name:
            raise ConfigLoadError(
                f"Directory name '{mod_dir.name}' must match module name "
                f"'{config.name}' in {module_yaml}"
            )

        modules.append(config)

    return modules
