import pytest

from vos_workbench.config.models import ModuleConfig


def _mod(
    name: str,
    type_: str = "exec.shell",
    depends: list | None = None,
    soft_depends: list | None = None,
) -> ModuleConfig:
    """Helper to build a ModuleConfig for testing."""
    deps = []
    if depends:
        deps.extend({"ref": f"module://{d}", "kind": "hard"} for d in depends)
    if soft_depends:
        deps.extend({"ref": f"module://{d}", "kind": "soft"} for d in soft_depends)

    wiring = {"depends_on": deps} if deps else {}

    return ModuleConfig(
        uuid="2db742d5-5f23-4ce0-9c83-7d4dbf18e2c3",
        name=name,
        type=type_,
        wiring=wiring,
    )


def test_startup_no_deps():
    from vos_workbench.runtime.startup import compute_startup_order

    modules = [_mod("a"), _mod("b"), _mod("c")]
    plan = compute_startup_order(modules)
    assert len(plan.order) == 1
    assert set(plan.order[0]) == {"a", "b", "c"}
    assert plan.failed == {}


def test_startup_linear_chain():
    from vos_workbench.runtime.startup import compute_startup_order

    modules = [
        _mod("c", depends=["b"]),
        _mod("b", depends=["a"]),
        _mod("a"),
    ]
    plan = compute_startup_order(modules)
    assert len(plan.order) == 3
    assert plan.order[0] == ["a"]
    assert plan.order[1] == ["b"]
    assert plan.order[2] == ["c"]
    assert plan.failed == {}


def test_startup_parallel_groups():
    from vos_workbench.runtime.startup import compute_startup_order

    modules = [
        _mod("router", type_="core.router", depends=["policy", "memory"]),
        _mod("policy", type_="core.policy"),
        _mod("memory", type_="memory.file"),
    ]
    plan = compute_startup_order(modules)
    assert len(plan.order) == 2
    assert set(plan.order[0]) == {"memory", "policy"}
    assert plan.order[1] == ["router"]
    assert plan.failed == {}


def test_startup_circular_dependency():
    from vos_workbench.runtime.startup import CircularDependencyError, compute_startup_order

    modules = [
        _mod("a", depends=["b"]),
        _mod("b", depends=["a"]),
    ]
    with pytest.raises(CircularDependencyError):
        compute_startup_order(modules)


def test_startup_disabled_module_hard_dep_fails_dependent():
    """Hard dependency on disabled module → dependent fails."""
    from vos_workbench.runtime.startup import compute_startup_order

    mod_a = _mod("a")
    mod_b = _mod("b", depends=["a"])  # hard dep on a
    mod_a.enabled = False

    plan = compute_startup_order([mod_a, mod_b])
    assert "b" in plan.failed
    assert "missing or disabled" in plan.failed["b"]
    # Neither a nor b should be in the startup order
    names = [name for group in plan.order for name in group]
    assert "a" not in names
    assert "b" not in names


def test_startup_disabled_module_soft_dep_still_starts():
    """Soft dependency on disabled module → dependent still starts."""
    from vos_workbench.runtime.startup import compute_startup_order

    mod_a = _mod("a")
    mod_b = _mod("b", soft_depends=["a"])  # soft dep on a
    mod_a.enabled = False

    plan = compute_startup_order([mod_a, mod_b])
    assert plan.failed == {}
    names = [name for group in plan.order for name in group]
    assert "a" not in names
    assert "b" in names


def test_startup_missing_hard_dep_cascades():
    """If A hard-depends on B and B fails, A also fails."""
    from vos_workbench.runtime.startup import compute_startup_order

    # c depends on b, b depends on nonexistent x
    modules = [
        _mod("c", depends=["b"]),
        _mod("b", depends=["x"]),  # x doesn't exist
    ]
    plan = compute_startup_order(modules)
    assert "b" in plan.failed
    assert "c" in plan.failed
    assert "failed to start" in plan.failed["c"]
    assert plan.order == []


def test_startup_mixed_hard_soft():
    """Module with both hard and soft deps — hard satisfied, soft missing."""
    from vos_workbench.runtime.startup import compute_startup_order

    modules = [
        _mod("a"),
        _mod("b", depends=["a"], soft_depends=["missing"]),
    ]
    plan = compute_startup_order(modules)
    assert plan.failed == {}
    names = [name for group in plan.order for name in group]
    assert "a" in names
    assert "b" in names
