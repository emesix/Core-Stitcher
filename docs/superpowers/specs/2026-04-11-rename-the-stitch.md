# Rename: Core-Stitcher → The Stitch

**Date:** 2026-04-11
**Status:** Ready to execute
**Effort:** 2-4 hour PR

## Scope

Display-name only. Python package namespace stays `stitch`. Entry points stay `stitch`, `stitch-mcp`, `stitch-lite`, `stitch-server`.

## What changes

| File | Change |
|---|---|
| `pyproject.toml` | `name = "the-stitch"` |
| `README.md` | Title, description |
| `CLAUDE.md` | Project name references |
| `WORKING_PRODUCT.md` | Title |
| `src/stitch/mcp/server.py` | `FastMCP("The Stitch", ...)` display name |
| `src/stitch/apps/lite/templates/base.html` | Logo text: "The Stitch" |
| `src/stitch/apps/lite/templates/system.html` | Application name |
| `src/stitch/apps/lite/templates/index.html` | Welcome text |
| `docs/superpowers/specs/*.md` | References to "Core-Stitcher" |
| GitHub repo | Rename `Core-Stitcher` → `The-Stitch` (or `the-stitch`) |

## What does NOT change

- Python import paths (`from stitch.xxx import yyy` — stays `stitch`)
- CLI commands (`stitch`, `stitch-lite`, `stitch-server`, `stitch-mcp`)
- Package directory structure (`src/stitch/`)
- Test files
- `.mcp.json` server config (uses `stitch-mcp` binary name)
- MCP tool names (`stitch_*`)

## Why display-name only

Renaming the Python package from `stitch` to `the_stitch` would touch every import in 120+ source files and 100+ test files. That's a multi-day refactor with high regression risk for zero functional value. The package namespace is an implementation detail; the product name is what users see.

## Execution

Single PR. Can be a Ralph loop or inline:

```
/ralph-loop:ralph-loop "Rename Core-Stitcher to The Stitch. Display name only — change pyproject.toml name, README, CLAUDE.md, templates, MCP server display name, docs. Do NOT change Python import paths, CLI commands, or package directory structure. Run ruff + pytest + pyright after. Commit with 'chore: rename Core-Stitcher to The Stitch'" --completion-promise "RENAME COMPLETE" --max-iterations 5
```
