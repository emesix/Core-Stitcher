# Working Product — First Vertical Slice

## How to run

```bash
./scripts/dev_up.sh     # start backend + lite
./scripts/smoke_ui.sh   # verify everything works
./scripts/dev_down.sh   # stop
```

Then open http://localhost:8080

## What works

| Page | What you see |
|---|---|
| `/devices` | Real device list from `topologies/lab.json` |
| `/devices/{id}` | Device detail with ports and neighbors |
| `/topology` | Topology summary — device/link/VLAN counts |
| `/preflight` | Preflight form (run against live domain engine) |
| `/runs` | Run history from `~/.stitch/runs/` |
| `/runs/{id}` | Run detail with tasks and status |
| `/system` | System info |

## What doesn't work yet

- Reviews approve/reject (hidden from UI)
- Reports page (no route)
- Search (stub in CLI only)
- Live WebSocket streaming
- Topology canvas visualization

## Architecture

```
Browser → stitch-lite (:8080) → StitchClient → stitch-server (:8000) → domain engine
                                                                       → topology file
                                                                       → run store
                                                                       → agentcore
```

Both CLI (`stitch`) and lite use the same backend. No mocks on the product path.

## Smoke tests

- `./scripts/smoke_test.sh` — full system (unit tests + lint + live backends + orchestration)
- `./scripts/smoke_ui.sh` — UI pages + real data verification
