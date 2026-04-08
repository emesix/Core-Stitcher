from vos_workbench.sdk import ModuleType


def test_switchcraft_module_type():
    from vos.switchcraft import SwitchcraftModule

    assert isinstance(SwitchcraftModule(), ModuleType)
    assert SwitchcraftModule.type_name == "resource.switchcraft"


def test_opnsensecraft_module_type():
    from vos.opnsensecraft import OpnsensecraftModule

    assert isinstance(OpnsensecraftModule(), ModuleType)
    assert OpnsensecraftModule.type_name == "resource.opnsensecraft"


def test_proxmoxcraft_module_type():
    from vos.proxmoxcraft import ProxmoxcraftModule

    assert isinstance(ProxmoxcraftModule(), ModuleType)
    assert ProxmoxcraftModule.type_name == "resource.proxmoxcraft"


def test_collectkit_module_type():
    from vos.collectkit import CollectkitModule

    assert isinstance(CollectkitModule(), ModuleType)
    assert CollectkitModule.type_name == "resource.collectkit"


def test_verifykit_module_type():
    from vos.verifykit import VerifykitModule

    assert isinstance(VerifykitModule(), ModuleType)
    assert VerifykitModule.type_name == "core.verifykit"


def test_tracekit_module_type():
    from vos.tracekit import TracekitModule

    assert isinstance(TracekitModule(), ModuleType)
    assert TracekitModule.type_name == "core.tracekit"


def test_interfacekit_module_type():
    from vos.interfacekit import InterfacekitModule

    assert isinstance(InterfacekitModule(), ModuleType)
    assert InterfacekitModule.type_name == "integration.interfacekit"
