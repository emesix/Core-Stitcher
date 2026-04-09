import pytest

from stitch.sdk.config import Profile, StitchConfig, load_config


def test_config_from_dict():
    cfg = StitchConfig(
        default_profile="lab",
        profiles={
            "lab": Profile(
                server="https://stitch.lab.local:8443",
                token="dev-token",
            )
        },
    )
    assert cfg.default_profile == "lab"
    assert cfg.profiles["lab"].server == "https://stitch.lab.local:8443"


def test_resolve_profile_explicit():
    cfg = StitchConfig(
        default_profile="lab",
        profiles={
            "lab": Profile(server="http://localhost:8000", token="t"),
            "prod": Profile(server="https://prod:8443", token="p"),
        },
    )
    p = cfg.resolve_profile("prod")
    assert p.server == "https://prod:8443"


def test_resolve_profile_default():
    cfg = StitchConfig(
        default_profile="lab",
        profiles={"lab": Profile(server="http://localhost:8000", token="t")},
    )
    p = cfg.resolve_profile(None)
    assert p.server == "http://localhost:8000"


def test_resolve_profile_missing():
    cfg = StitchConfig(default_profile="lab", profiles={})
    with pytest.raises(KeyError):
        cfg.resolve_profile("lab")


def test_load_config_from_yaml(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "default_profile: test\n"
        "profiles:\n"
        "  test:\n"
        "    server: http://localhost:9000\n"
        "    token: test-token\n"
        "defaults:\n"
        "  output: json\n"
        "  page_size: 25\n"
    )
    cfg = load_config(cfg_file)
    assert cfg.default_profile == "test"
    assert cfg.profiles["test"].token == "test-token"
    assert cfg.defaults.output == "json"


def test_load_config_missing_file():
    from pathlib import Path

    cfg = load_config(Path("/nonexistent/config.yaml"))
    assert cfg.default_profile is None
    assert cfg.profiles == {}


def test_profile_token_command():
    p = Profile(server="http://localhost:8000", token_command="echo secret-tok")
    assert p.resolve_token() == "secret-tok"


def test_profile_token_direct():
    p = Profile(server="http://localhost:8000", token="direct-tok")
    assert p.resolve_token() == "direct-tok"
