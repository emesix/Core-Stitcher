import pytest
from pydantic import BaseModel


def test_registry_register_and_get():
    from stitch_workbench.registry.registry import ModuleTypeRegistry

    registry = ModuleTypeRegistry()

    class DummyConfig(BaseModel):
        command: str = "echo"

    class DummyModule:
        type_name = "exec.shell"
        version = "0.1.0"
        config_model = DummyConfig
        capabilities = ["shell.execute"]
        secret_requirements: dict = {}

    registry.register(DummyModule)
    assert registry.get("exec.shell") is DummyModule
    assert "exec.shell" in registry.list_types()


def test_registry_get_unknown():
    from stitch_workbench.registry.registry import ModuleTypeRegistry

    registry = ModuleTypeRegistry()
    assert registry.get("nonexistent.type") is None


def test_registry_has_type():
    from stitch_workbench.registry.registry import ModuleTypeRegistry

    registry = ModuleTypeRegistry()

    class DummyModule:
        type_name = "core.router"
        version = "0.1.0"
        config_model = BaseModel
        capabilities = []
        secret_requirements: dict = {}

    registry.register(DummyModule)
    assert registry.has_type("core.router") is True
    assert registry.has_type("core.missing") is False


def test_registry_duplicate_raises():
    from stitch_workbench.registry.registry import ModuleTypeRegistry

    registry = ModuleTypeRegistry()

    class Mod1:
        type_name = "exec.shell"
        version = "0.1.0"
        config_model = BaseModel
        capabilities = []
        secret_requirements: dict = {}

    class Mod2:
        type_name = "exec.shell"
        version = "0.2.0"
        config_model = BaseModel
        capabilities = []
        secret_requirements: dict = {}

    registry.register(Mod1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(Mod2)
