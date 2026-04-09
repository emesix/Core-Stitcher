from importlib.metadata import entry_points


def test_vos_modules_entry_points_registered():
    eps = entry_points(group="stitch.modules")
    names = {ep.name for ep in eps}
    expected = {
        "resource.switchcraft",
        "resource.opnsensecraft",
        "resource.proxmoxcraft",
        "resource.collectkit",
        "core.verifykit",
        "core.tracekit",
        "integration.interfacekit",
    }
    assert expected.issubset(names), f"Missing: {expected - names}"


def test_entry_points_load():
    eps = entry_points(group="stitch.modules")
    for ep in eps:
        module_type = ep.load()
        assert hasattr(module_type, "type_name")
        assert hasattr(module_type, "version")
        assert hasattr(module_type, "config_model")
