from pathlib import Path
from uuid import uuid4

import yaml


def test_load_workbench_config(tmp_project: Path):
    from vos_workbench.config.loader import load_workbench_config

    cfg = load_workbench_config(tmp_project)
    assert cfg.project.id == "test-project"


def test_load_workbench_config_missing_file(tmp_path: Path):
    import pytest

    from vos_workbench.config.loader import ConfigLoadError, load_workbench_config

    with pytest.raises(ConfigLoadError, match="workbench.yaml"):
        load_workbench_config(tmp_path)


def test_load_module_configs(tmp_project: Path):
    from vos_workbench.config.loader import load_module_configs

    modules = load_module_configs(tmp_project)
    assert len(modules) == 1
    assert modules[0].name == "echo-shell"
    assert modules[0].type == "exec.shell"


def test_load_module_name_mismatch(tmp_path: Path):
    import pytest

    from vos_workbench.config.loader import ConfigLoadError, load_module_configs

    mod_dir = tmp_path / "modules" / "dir-name"
    mod_dir.mkdir(parents=True)
    module = {
        "uuid": str(uuid4()),
        "name": "different-name",
        "type": "exec.shell",
    }
    (mod_dir / "module.yaml").write_text(yaml.dump(module))

    with pytest.raises(ConfigLoadError, match="must match"):
        load_module_configs(tmp_path)


def test_load_empty_modules_dir(tmp_path: Path):
    from vos_workbench.config.loader import load_module_configs

    (tmp_path / "modules").mkdir()
    modules = load_module_configs(tmp_path)
    assert modules == []


def test_load_no_modules_dir(tmp_path: Path):
    from vos_workbench.config.loader import load_module_configs

    modules = load_module_configs(tmp_path)
    assert modules == []
