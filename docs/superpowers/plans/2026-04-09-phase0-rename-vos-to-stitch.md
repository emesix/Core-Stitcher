# Phase 0: Rename vos -> stitch

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename all `vos` references to `stitch` across the codebase. Mechanical only — no architectural changes.

**Architecture:** Find-and-replace across package directories, imports, pyproject.toml, configs, tests. The rename is cosmetic; all behavior stays identical.

**Tech Stack:** Python, git mv, sed/ruff

**Spec:** `docs/superpowers/specs/2026-04-09-stitch-operator-surface-design.md` §9 Phase 0

---

## Rules

- This is purely mechanical. No new features, no refactoring, no API changes.
- Every test that passed before must pass after.
- Commit in logical chunks (directories, then imports, then config, then tests).

---

### Task 1: Rename Package Directories

- [ ] **Step 1: Rename src/vos_workbench/ -> src/stitch_workbench/**

```bash
git mv src/vos_workbench src/stitch_workbench
```

- [ ] **Step 2: Rename src/vos/ -> src/stitch/**

```bash
git mv src/vos src/stitch
```

- [ ] **Step 3: Update pyproject.toml**

Replace all `vos` references:
- Package name stays `core-stitcher`
- Entry points: `vos_workbench:main` -> `stitch_workbench:main`
- Entry points: `vos.apps.project_stitcher.cli:main` -> `stitch.apps.project_stitcher.cli:main`
- Module entry points: `vos.switchcraft:SwitchcraftModule` -> `stitch.switchcraft:SwitchcraftModule` (all of them)
- Console script: `vos-workbench` -> `stitch-workbench`

- [ ] **Step 4: Commit directory renames**

```bash
git add -A
git commit -m "refactor: rename vos -> stitch package directories"
```

---

### Task 2: Update All Imports

- [ ] **Step 1: Replace imports across src/**

```bash
# Replace all import references
# vos_workbench -> stitch_workbench
# from vos. -> from stitch.
# import vos. -> import stitch.
```

Use ruff or a find-and-replace tool. The patterns are:
- `from vos_workbench` -> `from stitch_workbench`
- `import vos_workbench` -> `import stitch_workbench`
- `from vos.` -> `from stitch.`
- `import vos.` -> `import stitch.`
- `"vos.` -> `"stitch.` (in string references like entry points)

- [ ] **Step 2: Replace imports across tests/**

Same patterns as Step 1, applied to `tests/` directory.

- [ ] **Step 3: Update any YAML/JSON config files that reference vos**

Check `configs/`, fixture files, and any YAML that contains module references.

- [ ] **Step 4: Run all tests**

Run: `uv run pytest tests/ -v`
Expected: All tests pass with new import paths.

- [ ] **Step 5: Run lint**

Run: `uv run ruff check src/ tests/`
Expected: Clean (fix any import ordering issues from the rename).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: update all imports vos -> stitch"
```

---

### Task 3: Update CLAUDE.md and Documentation

- [ ] **Step 1: Update CLAUDE.md**

Replace all `vos` package references with `stitch`. Update the package structure section. Remove the "do NOT rename" note for vos_workbench.

- [ ] **Step 2: Update README and any other docs**

Replace `vos` references in documentation files.

- [ ] **Step 3: Verify install**

Run: `uv pip install -e ".[dev]"`
Run: `uv run stitch-workbench` (or whatever the new entry point is)
Expected: Works as before.

- [ ] **Step 4: Run full test suite one more time**

Run: `uv run ruff check src/ tests/ && uv run pytest tests/ -v`
Expected: All green.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs: update documentation for vos -> stitch rename"
```
