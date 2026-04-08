import pytest
from pydantic import ValidationError


def test_workbench_config_minimal():
    from vos_workbench.config.models import WorkbenchConfig

    cfg = WorkbenchConfig(
        project={"id": "test-project", "name": "Test Project"},
    )
    assert cfg.project.id == "test-project"
    assert cfg.schema_version == 1
    assert cfg.state.durable_runtime == "sqlite"


def test_workbench_config_precedence_default():
    from vos_workbench.config.models import SettingsLayer, WorkbenchConfig

    cfg = WorkbenchConfig(
        project={"id": "test", "name": "Test"},
    )
    assert cfg.settings_precedence == [
        SettingsLayer.MANAGED,
        SettingsLayer.BOOTSTRAP,
        SettingsLayer.PROJECT,
        SettingsLayer.LOCAL,
        SettingsLayer.RUNTIME,
    ]


def test_workbench_config_invalid_project_id():
    from vos_workbench.config.models import WorkbenchConfig

    with pytest.raises(ValidationError, match="pattern"):
        WorkbenchConfig(
            project={"id": "has spaces!", "name": "Bad"},
        )


def test_module_config_valid():
    from vos_workbench.config.models import ModuleConfig

    cfg = ModuleConfig(
        uuid="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
        name="exec-local-shell",
        type="exec.shell",
    )
    assert cfg.family.value == "exec"
    assert cfg.lifecycle == "persistent"
    assert cfg.enabled is True


def test_module_config_name_rejects_uuid_format():
    from vos_workbench.config.models import ModuleConfig

    with pytest.raises(ValidationError, match="UUID"):
        ModuleConfig(
            uuid="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
            name="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
            type="exec.shell",
        )


def test_module_config_invalid_type_format():
    from vos_workbench.config.models import ModuleConfig

    with pytest.raises(ValidationError, match="pattern"):
        ModuleConfig(
            uuid="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
            name="bad-module",
            type="BadType",
        )


def test_module_config_family_derived():
    from vos_workbench.config.models import ModuleConfig, ModuleFamily

    cfg = ModuleConfig(
        uuid="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
        name="my-router",
        type="core.router",
    )
    assert cfg.family == ModuleFamily.CORE


def test_module_config_with_dependencies():
    from vos_workbench.config.models import ModuleConfig

    cfg = ModuleConfig(
        uuid="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
        name="my-router",
        type="core.router",
        wiring={
            "depends_on": [
                {"ref": "module://policy-main", "kind": "hard"},
                {"ref": "module://memory-main", "kind": "soft"},
            ],
            "provides": ["capability://routing"],
        },
    )
    assert len(cfg.wiring.depends_on) == 2
    assert cfg.wiring.depends_on[0].kind == "hard"
    assert cfg.wiring.depends_on[1].kind == "soft"


def test_dependency_rejects_uuid_ref():
    from vos_workbench.config.models import Dependency

    with pytest.raises(ValidationError, match="module names"):
        Dependency(ref="module://uuid/2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3")


def test_module_config_budget():
    from vos_workbench.config.models import ModuleConfig

    cfg = ModuleConfig(
        uuid="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
        name="worker-1",
        type="worker.coder",
        lifecycle="ephemeral",
        budget={"max_tokens": 50000, "max_seconds": 300},
    )
    assert cfg.budget is not None
    assert cfg.budget.max_tokens == 50000
