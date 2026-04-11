# Working Product — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `./scripts/dev_up.sh` starts the backend + stitch-lite. Open browser at localhost:8080, see live homelab, run real preflight, submit work, inspect results. No mocks on the product path.

**Architecture:** The operator backend (FastAPI) serves real topology, devices, preflight, and runs via the existing `interfacekit` routes + `project_stitcher` API. Stitch-lite connects to it via `StitchClient`. One boot script starts both. Templates stay unchanged — the existing API already returns the right shapes.

**Tech Stack:** FastAPI, uvicorn, Typer, Jinja2, stitch domain libraries, stitch SDK client

**Why not bypass the backend:** The CLI, lite, and future clients all share the same backend. Hardwiring lite to files breaks the client architecture and creates a second path to maintain.

---

## File Structure

| Action | File | Responsibility |
|---|---|---|
| Create | `src/stitch/apps/backend/server.py` | Unified backend server — mounts explorer, preflight, project_stitcher routes |
| Create | `scripts/dev_up.sh` | Start backend + stitch-lite, print URLs |
| Create | `scripts/dev_down.sh` | Stop both |
| Create | `scripts/smoke_ui.sh` | Verify all pages return 200 with real data |
| Create | `WORKING_PRODUCT.md` | Product slice contract — what works, what doesn't |
| Modify | `src/stitch/apps/lite/app.py` | Default STITCH_SERVER to localhost:8000 |
| Modify | `pyproject.toml` | Add `stitch-server` entry point |
| Modify | `src/stitch/apps/lite/routes.py` | Hide unsupported pages (reviews approve/reject) |
| Modify | `src/stitch/apps/lite/templates/base.html` | Remove nav links for unsupported pages |

---

### Task 1: Backend server — mount real routes into one FastAPI app

**Files:**
- Create: `src/stitch/apps/backend/__init__.py`
- Create: `src/stitch/apps/backend/server.py`
- Test: manual (Task 6 smoke test)

This is the missing piece. The routes exist in `interfacekit/` but nobody starts them.

- [ ] **Step 1: Create the backend server**

```python
# src/stitch/apps/backend/__init__.py
```

```python
# src/stitch/apps/backend/server.py
"""Stitch backend server — unified API for all clients."""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from stitch.interfacekit.explorer_routes import create_explorer_router
from stitch.interfacekit.routes import create_health_router, create_preflight_router
from stitch.storekit.loader import load_topology


def create_app(topology_path: str | None = None) -> FastAPI:
    topo_path = Path(topology_path or "topologies/lab.json")
    topo = load_topology(topo_path)

    # Build a lightweight workflow facade for the explorer and preflight routes
    from stitch.apps.backend.workflow import BackendWorkflow

    workflow = BackendWorkflow(topo, topo_path)

    app = FastAPI(title="Stitch Backend", version="1.0")

    # Mount explorer routes (devices, topology, neighbors, vlans, diagnostics)
    app.include_router(create_explorer_router(workflow), prefix="/api/v1/explorer")

    # Mount preflight routes (verify, trace, impact, diff)
    app.include_router(create_preflight_router(workflow), prefix="/api/v1")

    # Mount health
    app.include_router(
        create_health_router(workflow.health), prefix="/api/v1"
    )

    # Mount project_stitcher run API
    from stitch.agentcore.bootstrap import build_alpha_registry
    from stitch.agentcore.storekit import JsonRunStore
    from stitch.apps.project_stitcher.api import create_router as create_run_router

    registry, routing = build_alpha_registry()
    run_store = JsonRunStore(Path.home() / ".stitch" / "runs")
    app.include_router(create_run_router(run_store, registry, routing=routing), prefix="/api/v1")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(prog="stitch-server")
    parser.add_argument("--topology", default="topologies/lab.json")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    app = create_app(topology_path=args.topology)
    uvicorn.run(app, host=args.host, port=args.port)
```

- [ ] **Step 2: Create the workflow facade**

The explorer and preflight routes expect a workflow protocol. Create a thin facade that wraps the real domain engine:

```python
# src/stitch/apps/backend/workflow.py
"""Workflow facade — connects interfacekit routes to real domain engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stitch.graphkit.neighbors import find_neighbors
from stitch.modelkit.topology import TopologySnapshot
from stitch.storekit.loader import load_topology
from stitch.tracekit.engine import trace_vlan
from stitch.verifykit.engine import run_verification


class BackendWorkflow:
    """Implements PreflightWorkflowProtocol and ExplorerWorkflowProtocol."""

    def __init__(self, topology: TopologySnapshot, topology_path: Path) -> None:
        self._topology = topology
        self._topology_path = topology_path

    @property
    def topology(self) -> TopologySnapshot:
        return self._topology

    @property
    def declared_topology(self) -> TopologySnapshot:
        return self._topology

    async def run_verification(self):
        return await run_verification(self._topology)

    async def run_trace(self, request):
        return trace_vlan(self._topology, request)

    async def run_impact_preview(self, request):
        from stitch.verifykit.impact import impact_preview
        return impact_preview(self._topology, request)

    def get_neighbors(self, device_id: str):
        return find_neighbors(self._topology, device_id)

    def get_vlan_ports(self, vlan_id: str):
        vlan = self._topology.vlans.get(vlan_id)
        if vlan is None:
            return []
        return vlan.ports if hasattr(vlan, "ports") else []

    def get_diagnostics(self):
        from stitch.verifykit.diagnostics import topology_diagnostics
        return topology_diagnostics(self._topology)

    async def health(self) -> dict[str, Any]:
        return {"status": "ok", "topology": str(self._topology_path)}
```

- [ ] **Step 3: Add entry point to pyproject.toml**

Add to `[project.scripts]`:
```
stitch-server = "stitch.apps.backend.server:main"
```

- [ ] **Step 4: Verify it starts**

```bash
uv run stitch-server --port 8000 &
sleep 2
curl -s http://localhost:8000/api/v1/explorer/devices | head -5
kill %1
```

Expected: JSON device list from `topologies/lab.json`

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check src/stitch/apps/backend/
git add src/stitch/apps/backend/ pyproject.toml
git commit -m "feat: add unified backend server mounting real domain routes"
```

---

### Task 2: Wire stitch-lite to the backend

**Files:**
- Modify: `src/stitch/apps/lite/app.py`
- Modify: `src/stitch/sdk/endpoints.py` (check URL mapping)

- [ ] **Step 1: Check what URLs the StitchClient sends**

Read `src/stitch/sdk/endpoints.py` to understand the URL mapping. The backend serves at `/api/v1/explorer/devices` but the client may send to different paths. Map any mismatches.

- [ ] **Step 2: Update app.py default server**

Change the fallback server from `http://localhost:8000` to `http://localhost:8000` (already correct) but remove the profile/config loading complexity for now — just default to localhost:

```python
# In create_app(), simplify to:
import os
server = os.environ.get("STITCH_SERVER", "http://localhost:8000")
prof = Profile(server=server)
client = StitchClient(prof)
```

- [ ] **Step 3: Fix endpoint mismatches**

If `resolve_endpoint("device", "list")` returns `/device` but the backend serves at `/api/v1/explorer/devices`, add route aliases on the backend or fix the endpoint resolver. Document the exact mapping.

- [ ] **Step 4: Test stitch-lite against backend**

```bash
uv run stitch-server &
sleep 2
uv run stitch-lite --port 8080 &
sleep 2
curl -s http://localhost:8080/devices | grep "opnsense"
kill %1 %2
```

Expected: Device page shows real devices from lab.json

- [ ] **Step 5: Commit**

```bash
git add src/stitch/apps/lite/app.py src/stitch/sdk/endpoints.py
git commit -m "feat(lite): wire stitch-lite to real backend server"
```

---

### Task 3: Hide unsupported features

**Files:**
- Modify: `src/stitch/apps/lite/routes.py`
- Modify: `src/stitch/apps/lite/templates/base.html`

- [ ] **Step 1: Remove review approve/reject routes**

Delete `review_approve` and `review_reject` POST handlers. Keep `review_list` and `review_detail` as read-only. Or remove reviews entirely if the backend doesn't serve them yet.

- [ ] **Step 2: Remove nav links for unsupported pages**

In `base.html`, remove or disable the "Reports" nav link (no route exists). If reviews are removed, disable that too.

- [ ] **Step 3: Commit**

```bash
git add src/stitch/apps/lite/routes.py src/stitch/apps/lite/templates/base.html
git commit -m "refactor(lite): hide unsupported features from UI"
```

---

### Task 4: One-command startup

**Files:**
- Create: `scripts/dev_up.sh`
- Create: `scripts/dev_down.sh`

- [ ] **Step 1: Create dev_up.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Starting Stitch backend on :8000..."
uv run stitch-server --port 8000 &
BACKEND_PID=$!
echo "$BACKEND_PID" > /tmp/stitch-backend.pid

sleep 2

# Verify backend is up
if ! curl -s -f http://localhost:8000/api/v1/explorer/devices > /dev/null 2>&1; then
    echo "ERROR: Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo "Starting Stitch Lite on :8080..."
uv run stitch-lite --port 8080 &
LITE_PID=$!
echo "$LITE_PID" > /tmp/stitch-lite.pid

sleep 2

if ! curl -s -f http://localhost:8080/ > /dev/null 2>&1; then
    echo "ERROR: Lite failed to start"
    kill $BACKEND_PID $LITE_PID 2>/dev/null
    exit 1
fi

echo ""
echo "Stitch is running:"
echo "  Backend API: http://localhost:8000"
echo "  Stitch Lite: http://localhost:8080"
echo ""
echo "Stop with: ./scripts/dev_down.sh"
```

- [ ] **Step 2: Create dev_down.sh**

```bash
#!/usr/bin/env bash
for pidfile in /tmp/stitch-backend.pid /tmp/stitch-lite.pid; do
    if [ -f "$pidfile" ]; then
        kill "$(cat "$pidfile")" 2>/dev/null && echo "Stopped $(basename "$pidfile" .pid)"
        rm -f "$pidfile"
    fi
done
```

- [ ] **Step 3: Make executable and commit**

```bash
chmod +x scripts/dev_up.sh scripts/dev_down.sh
git add scripts/dev_up.sh scripts/dev_down.sh
git commit -m "feat: add one-command startup for stitch product"
```

---

### Task 5: Smoke test for UI

**Files:**
- Create: `scripts/smoke_ui.sh`

- [ ] **Step 1: Create smoke_ui.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC} $1"; }
fail() { echo -e "${RED}FAIL${NC} $1"; exit 1; }

BACKEND="http://localhost:8000"
LITE="http://localhost:8080"

echo "=== UI Smoke Test ==="

# Backend health
curl -s -f "$BACKEND/api/v1/health/modules" > /dev/null && pass "Backend health" || fail "Backend unreachable"

# Backend API endpoints
curl -s -f "$BACKEND/api/v1/explorer/devices" > /dev/null && pass "Backend: devices" || fail "Backend: devices"
curl -s -f "$BACKEND/api/v1/explorer/topology" > /dev/null && pass "Backend: topology" || fail "Backend: topology"

# Lite pages
for path in / /devices /topology /runs /preflight /system; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$LITE$path")
    if [ "$STATUS" = "200" ]; then
        pass "Lite: $path"
    else
        fail "Lite: $path (HTTP $STATUS)"
    fi
done

# Real data check
curl -s "$LITE/devices" | grep -q "opnsense" && pass "Lite: real device data" || fail "Lite: no real device data"
curl -s "$LITE/topology" | grep -q "emesix" && pass "Lite: real topology name" || fail "Lite: no topology name"

echo ""
echo "=== UI smoke test complete ==="
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x scripts/smoke_ui.sh
git add scripts/smoke_ui.sh
git commit -m "feat: add UI smoke test script"
```

---

### Task 6: Product slice contract

**Files:**
- Create: `WORKING_PRODUCT.md`

- [ ] **Step 1: Write the contract**

```markdown
# Working Product — First Slice

## What works

- `./scripts/dev_up.sh` starts backend + lite
- Open http://localhost:8080 in browser
- `/devices` — real device list from topology
- `/devices/{id}` — device detail with ports and neighbors
- `/topology` — topology summary with counts
- `/preflight` — run real preflight against live domain engine
- `/runs` — list runs from JSON store
- `/runs/{id}` — run detail with tasks and status
- `/system` — system info

## What doesn't work yet

- Reviews approve/reject (hidden, not wired)
- Reports (no route)
- Search (stub)
- Live preflight from UI button (needs endpoint wiring)
- WebSocket streaming

## Architecture

- Backend: `stitch-server` (FastAPI, port 8000)
- Frontend: `stitch-lite` (FastAPI + Jinja2, port 8080)
- Client: `StitchClient` (SDK HTTP client)
- This is not a bypass — both CLI and lite use the same backend

## How to run

```bash
./scripts/dev_up.sh     # start
./scripts/smoke_ui.sh   # verify
./scripts/dev_down.sh   # stop
```
```

- [ ] **Step 2: Commit**

```bash
git add WORKING_PRODUCT.md
git commit -m "docs: working product slice contract"
```

---

### Task 7: End-to-end integration test

- [ ] **Step 1: Start product**

```bash
./scripts/dev_up.sh
```

- [ ] **Step 2: Run UI smoke test**

```bash
./scripts/smoke_ui.sh
```

Expected: all PASS

- [ ] **Step 3: Run full smoke test**

```bash
./scripts/smoke_test.sh
```

Expected: all PASS (including A770 if online)

- [ ] **Step 4: Open browser and verify manually**

Open http://localhost:8080 and click through every page. Verify real homelab data shows.

- [ ] **Step 5: Final commit and tag**

```bash
git commit --allow-empty -m "milestone: stitch working product — first vertical slice"
git tag working-product-v0
git push && git push origin working-product-v0
```

---

## Verification

After all tasks:
1. `uv run ruff check src/ tests/` — lint clean
2. `uv run pytest tests/ -v` — all tests pass
3. `uv run pyright src/` — type check clean
4. `./scripts/dev_up.sh` — starts without error
5. `./scripts/smoke_ui.sh` — all pages 200 with real data
6. Browser shows real homelab at localhost:8080
7. No mock on the product path

## What this is NOT

This is the first vertical slice — a working prototype that proves one real operator loop through a browser. It is not:
- Full TUI parity
- Multi-surface orchestration
- The final client architecture
- A replacement for Claude Code + MCP (that remains the power-user path)

Features meant for all clients must later be lifted into the operator API layer, not hardwired into lite.
