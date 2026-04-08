import pytest


def test_parse_module_by_name_shorthand():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("module://policy-main")
    assert ref.scheme == "module"
    assert ref.authority == "name"
    assert ref.path == "policy-main"


def test_parse_module_by_name_explicit():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("module://name/policy-main")
    assert ref.scheme == "module"
    assert ref.authority == "name"
    assert ref.path == "policy-main"


def test_parse_module_by_uuid():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("module://uuid/2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3")
    assert ref.scheme == "module"
    assert ref.authority == "uuid"
    assert ref.path == "2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3"


def test_parse_secret():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("secret://env/ANTHROPIC_API_KEY")
    assert ref.scheme == "secret"
    assert ref.authority == "env"
    assert ref.path == "ANTHROPIC_API_KEY"


def test_parse_secret_file():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("secret://file/~/.ssh/id_ed25519")
    assert ref.scheme == "secret"
    assert ref.authority == "file"
    assert ref.path == "~/.ssh/id_ed25519"


def test_parse_system():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("system://eventbus")
    assert ref.scheme == "system"
    assert ref.authority is None
    assert ref.path == "eventbus"


def test_parse_capability():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("capability://chat.fast")
    assert ref.scheme == "capability"
    assert ref.authority is None
    assert ref.path == "chat.fast"


def test_parse_invalid_scheme():
    from vos_workbench.uri.parser import VosReference

    with pytest.raises(ValueError, match="Unknown scheme"):
        VosReference.parse("foobar://thing")


def test_parse_malformed():
    from vos_workbench.uri.parser import VosReference

    with pytest.raises(ValueError, match="Invalid VOS URI"):
        VosReference.parse("not-a-uri")


def test_validate_valid():
    from vos_workbench.uri.parser import VosReference

    assert VosReference.validate_uri("module://policy-main") is True


def test_validate_invalid():
    from vos_workbench.uri.parser import VosReference

    assert VosReference.validate_uri("garbage") is False


def test_normalize():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("module://policy-main")
    assert str(ref) == "module://name/policy-main"


def test_normalize_uuid():
    from vos_workbench.uri.parser import VosReference

    ref = VosReference.parse("module://uuid/2DB742D5-5F23-4CE0-9C83-7D4DBF18E2C3")
    assert str(ref) == "module://uuid/2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3"


def test_parse_module_uuid_invalid_format():
    from vos_workbench.uri.parser import VosReference

    with pytest.raises(ValueError, match="Invalid UUID"):
        VosReference.parse("module://uuid/not-a-real-uuid")
