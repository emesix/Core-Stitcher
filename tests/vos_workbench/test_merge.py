def test_merge_two_scalars_override():
    from vos_workbench.config.merge import merge_two

    result = merge_two({"a": 1}, {"a": 2})
    assert result == {"a": 2}


def test_merge_two_dict_deep():
    from vos_workbench.config.merge import merge_two

    base = {"a": {"x": 1, "y": 2}}
    override = {"a": {"y": 3, "z": 4}}
    result = merge_two(base, override)
    assert result == {"a": {"x": 1, "y": 3, "z": 4}}


def test_merge_two_list_replaces():
    from vos_workbench.config.merge import merge_two

    result = merge_two({"tags": ["a", "b"]}, {"tags": ["c"]})
    assert result == {"tags": ["c"]}


def test_merge_two_null_removes():
    from vos_workbench.config.merge import merge_two

    result = merge_two({"debug": True, "keep": 1}, {"debug": None})
    assert result == {"keep": 1}


def test_merge_two_absent_inherits():
    from vos_workbench.config.merge import merge_two

    result = merge_two({"a": 1, "b": 2}, {"b": 3})
    assert result == {"a": 1, "b": 3}


def test_merge_two_preserves_vos_refs():
    from vos_workbench.config.merge import merge_two

    result = merge_two(
        {"key": "module://old"},
        {"key": "module://new"},
    )
    assert result == {"key": "module://new"}


def test_merge_layers_precedence():
    from vos_workbench.config.merge import merge_layers

    # Precedence: managed > bootstrap > project > local > runtime
    # Applied lowest-first: runtime, local, project, bootstrap, managed
    # runtime sets mode=execution  -> project sets mode=planning (project > runtime, wins)
    # local sets debug=False       -> project sets debug=True (project > local, wins)
    # managed sets security=strict -> highest priority, always wins
    effective, _ = merge_layers(
        managed={"security": "strict"},
        bootstrap={"db": "sqlite"},
        project={"mode": "planning", "debug": True},
        local={"debug": False},
        runtime={"mode": "execution"},
    )
    assert effective["security"] == "strict"  # managed, highest priority
    assert effective["db"] == "sqlite"  # bootstrap, no conflict
    assert effective["mode"] == "planning"  # project > runtime
    assert effective["debug"] is True  # project > local


def test_merge_layers_tracing():
    from vos_workbench.config.merge import merge_layers

    _, sources = merge_layers(
        managed={},
        bootstrap={"db": "sqlite"},
        project={"mode": "planning"},
        local={},
        runtime={"mode": "execution"},
    )
    assert sources["db"] == "bootstrap"
    assert sources["mode"] == "project"  # project > runtime


def test_merge_layers_null_removes():
    from vos_workbench.config.merge import merge_layers

    effective, _ = merge_layers(
        managed={},
        bootstrap={},
        project={"debug": True},
        local={},
        runtime={},
    )
    assert effective["debug"] is True


def test_merge_layers_managed_wins():
    from vos_workbench.config.merge import merge_layers

    effective, sources = merge_layers(
        managed={"security": "strict"},
        bootstrap={},
        project={"security": "lax"},
        local={},
        runtime={},
    )
    assert effective["security"] == "strict"
    assert sources["security"] == "managed"
