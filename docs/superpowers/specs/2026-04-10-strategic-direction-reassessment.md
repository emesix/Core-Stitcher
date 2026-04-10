# Core-Stitcher: Strategic Direction Reassessment

**Date:** 2026-04-10
**Trigger:** Claude Code went GA, plugins/skills/MCP ecosystem matured. Do we still need 5 custom client surfaces?

---

## The Honest Question

We just built 5 operator client surfaces (CLI, TUI, Lite HTML, React WebUI, Tauri Desktop) following the spec's "one contract, five clients" vision. Meanwhile, Claude Code — which we're literally using right now — already has:

- Direct MCP tool access to our entire infrastructure (switchcraft, opnsense, proxmox, zabbix)
- Natural language operator interface
- Hooks for guardrails and audit
- Skills for domain knowledge
- Subagents for specialized tasks
- Scheduling, background execution, remote control

**The question isn't "was the architecture wrong?" — it's "where should the investment go now?"**

---

## What We Built vs What Already Exists

| Capability | Our custom build | Claude Code already does this |
|---|---|---|
| Browse devices | `stitch device list` | "Show me all devices" → calls MCP tools |
| Run preflight | `stitch preflight run` | "Run a preflight check" → calls verify endpoint |
| Trace VLAN | `stitch trace run 42` | "Trace VLAN 42 from sw-core-01" → calls trace endpoint |
| Watch run progress | `stitch run watch` | Live in conversation |
| Review + approve | `stitch review approve` | "Review that run and tell me what's wrong" |
| Command palette | Ctrl+P in TUI/WebUI | Just type in Claude Code |
| Search anything | `stitch search` | Just ask |
| Keyboard shortcuts | Custom per client | Not applicable (conversational) |
| Batch scripting | `stitch device list --output json \| jq` | Same, but also natural language piping |
| Topology visualization | Not built yet | Not available (conversational) |
| Dashboards | Not built yet | Not available (conversational) |

**Key insight:** For ~80% of operator workflows, Claude Code with our MCP gateway IS the operator surface. It's already wired up.

---

## What Claude Code Does NOT Replace

| Need | Why custom code still matters |
|---|---|
| **Deterministic verification** | `verify_topology(declared, observed)` must produce the same result every time. This is pure Python logic, not AI inference. |
| **Domain models** | Device, Port, Link, VLAN, TopologySnapshot — typed Pydantic models are the source of truth. Claude Code consumes them, doesn't define them. |
| **Graph traversal** | BFS path tracing, impact analysis, diagnostics — algorithmic, testable, fast. |
| **Batch/scripted ops** | CI/CD pipelines, cron jobs, automation — need `stitch preflight run --output json` not a conversation. |
| **Visual dashboards** | Topology canvas, real-time status grids — Claude Code can't render these. |
| **Offline/air-gapped** | No API = no Claude Code. The lite HTML UI works without internet. |
| **Cost control** | Every Claude Code interaction costs tokens. `stitch device list` costs zero. |
| **Sub-second queries** | `stitch device show sw-core-01` returns in <100ms. Claude Code takes 2-5 seconds. |

---

## The Revised Architecture

```
                    ┌─────────────────────────┐
                    │     OPERATOR LAYER       │
                    │                          │
                    │  Claude Code + Skills    │  ← PRIMARY operator interface
                    │  (natural language,      │     for exploration, diagnosis,
                    │   MCP tools, hooks,      │     review, approval
                    │   subagents, scheduling) │
                    └────────────┬────────────┘
                                 │ MCP
┌──────────────┐    ┌────────────┴────────────┐    ┌──────────────┐
│  stitch CLI  │    │     MCP GATEWAY         │    │  stitch-lite │
│  (scripting, │    │                          │    │  (rescue UI, │
│   automation,│    │  switchcraft, opnsense,  │    │   mobile,    │
│   CI/CD)     │    │  proxmox, zabbix, etc.   │    │   offline)   │
└──────┬───────┘    └────────────┬────────────┘    └──────┬───────┘
       │                         │                        │
       └─────────────────────────┴────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │     DOMAIN ENGINE        │
                    │                          │
                    │  stitch-core types       │
                    │  contractkit protocols   │
                    │  modelkit domain models  │
                    │  graphkit traversal      │
                    │  verifykit verification  │
                    │  tracekit path tracing   │
                    │  collectkit merging      │
                    │  agentcore orchestration │
                    └─────────────────────────┘
```

### What changes

| Component | Old plan | New plan |
|---|---|---|
| **Claude Code** | Not in the picture | **PRIMARY operator interface** — skills, hooks, subagents |
| **stitch CLI** | Primary operator tool | **Scripting/automation escape hatch** — keep it, but it's not the main UI |
| **stitch-tui** | Secondary operator tool | **Deprioritize** — Claude Code IS a TUI already |
| **stitch-lite** | Rescue UI | **Keep** — offline/mobile/low-bandwidth fallback |
| **stitch-web (React)** | Main operator console | **Repurpose** — topology canvas + dashboards only (not a full operator console) |
| **stitch-desktop (Tauri)** | Desktop wrapper | **Pause** — no unique value over Claude Code + browser |
| **Domain engine** | Backend | **Unchanged** — this is the real product |
| **MCP integration** | Adapter layer | **Expand** — expose Core-Stitcher operations as MCP tools for Claude Code |

---

## The New Priority Stack

### Tier 1: Essential (do now)

1. **Expose Core-Stitcher as MCP tools**
   - `stitch-preflight-run` → runs verification, returns report
   - `stitch-trace-vlan` → traces VLAN path
   - `stitch-impact-preview` → previews change impact
   - `stitch-device-inspect` → deep device detail
   - `stitch-topology-diagnostics` → graph health
   
   This lets Claude Code call Core-Stitcher directly, not just the raw adapter MCP tools.

2. **Write Claude Code skills for Stitch**
   - `network-operator.md` — how to run preflight, interpret results, trace VLANs
   - `topology-verifier.md` — verification workflow, what checks mean, how to fix
   - `device-inspector.md` — how to drill into device detail, read ports, follow links
   
   These encode the domain knowledge that makes Claude Code a competent operator.

3. **Write Claude Code hooks for safety**
   - PreToolUse hook: block destructive operations without confirmation
   - PostToolUse hook: audit log all infrastructure changes
   - Stop hook: verify no pending changes before session ends

4. **Build the write path (remediation commands)**
   - This was already the biggest gap (2.5/10)
   - Now it matters even more: Claude Code can suggest AND execute fixes
   - `stitch-interface-assign`, `stitch-vlan-apply`, `stitch-config-push`

### Tier 2: Important (do next)

5. **Topology canvas in WebUI**
   - This is the ONE thing Claude Code genuinely can't do
   - Interactive SVG graph of the network
   - Keep the React WebUI, but scope it to visualization, not operator workflows

6. **stitch CLI hardening**
   - Keep for scripting/CI/CD
   - Add `--from-stdin` batch support
   - Shell completion
   - This is the "deterministic escape hatch"

7. **stitch-lite keep alive**
   - Rescue UI for when Claude Code is unavailable
   - Mobile-friendly for walking around the lab
   - Already built, just maintain

### Tier 3: Deprioritize

8. **stitch-tui** — Claude Code in terminal IS the TUI. The Textual app adds complexity without unique value. Keep the code, don't invest more.

9. **stitch-desktop (Tauri)** — Pause. If we need a desktop app, it's for the topology canvas, which is a browser feature not a native one.

10. **Full WebUI operator console** — The IDE layout we built is nice, but Claude Code + skills replaces 80% of it. Repurpose the React app as a visualization/dashboard tool, not a full operator console.

---

## What We Keep vs What We Pause

### Keep and invest

| Component | Why |
|---|---|
| **Domain engine** (stitch-core, contractkit, modelkit, etc.) | The real product. Deterministic, testable, fast. |
| **stitch CLI** | Scripting, CI/CD, batch ops. Zero-cost queries. |
| **stitch-lite** | Rescue UI, mobile, offline. Already built. |
| **MCP exposure layer** | Bridge between domain engine and Claude Code. |
| **Claude Code skills/hooks** | Encode domain knowledge. The operator interface. |
| **React topology canvas** | Visual what Claude Code can't do. |

### Keep but don't invest further

| Component | Why |
|---|---|
| **stitch-tui** | Works, but Claude Code covers the use case. |
| **React IDE layout** | Nice shell, but repurpose for dashboards only. |

### Pause

| Component | Why |
|---|---|
| **stitch-desktop (Tauri)** | No unique value. Resume if topology canvas needs native features. |

---

## Concrete Next Steps

### Phase 6: Core-Stitcher as MCP Server (NEW — highest priority)

Build an MCP server that exposes Core-Stitcher operations:

```
stitch-mcp/
    server.py          — MCP server (FastMCP or raw protocol)
    tools/
        preflight.py   — run_preflight, get_report, diff_reports
        trace.py       — trace_vlan, impact_preview
        topology.py    — get_topology, get_device, get_diagnostics
        verify.py      — verify_link, verify_device
```

Register in MCP gateway. Now Claude Code can:
```
"Run preflight on the lab topology"
→ calls stitch-mcp/preflight.run
→ returns structured verification report
→ Claude interprets and explains findings
```

### Phase 7: Claude Code Skills + Hooks

```
.claude/skills/
    network-operator.md
    topology-verifier.md
    device-inspector.md
.claude/hooks/
    pre-tool-use-safety.sh
    post-tool-use-audit.sh
```

### Phase 8: Write Path (Remediation)

Wire the first actual write operations through the adapter MCP tools:
- Assign OPNsense interfaces (ix0, ix1)
- Apply VLAN configuration
- Push config changes

### Phase 9: Topology Canvas

React component for interactive network graph. This is the ONE visual thing worth building custom.

---

## The Key Insight

> **Core-Stitcher's value is the domain engine, not the operator UI.**
> 
> The domain engine (topology models, verification logic, graph traversal, impact analysis) is unique, testable, and irreplaceable. The operator UI is a commodity — Claude Code does it better than anything we'd build.
> 
> Invest in making the domain engine accessible via MCP, encode the domain knowledge as skills, and let Claude Code be the operator.

---

## Updated Scorecard Impact

If we execute Phases 6-9:

| Dimension | Current | Target | How |
|---|---|---|---|
| Write Path | 2.5 | **7** | Phase 8: remediation commands |
| Live Integration | 6.5 | **8** | Phase 6: MCP server makes all ops accessible |
| Visualization | 8 | **9** | Phase 9: topology canvas |
| AI Orchestration | 7 | **9** | Phase 7: skills encode domain knowledge, Claude Code does the reasoning |
| Ecosystem Reuse | 6 | **8** | Phase 6: MCP integration makes Core-Stitcher consumable by any MCP client |

**Projected overall: 8.5/10** (from current 7.5)
