---
name: network-operator
description: How to operate the network using Stitch MCP tools — when to use which tool, detail levels, workflow order
---

# Network Operator Guide

You have access to Stitch MCP tools for managing a home lab network. This skill tells you when and how to use them.

## Available tools

### Read tools (safe, no side effects)
- `stitch_topology_summary` — quick overview: device/link/VLAN counts
- `stitch_devices` — list all devices with type, model, IP
- `stitch_device_detail` — deep dive into one device: ports, config
- `stitch_device_neighbors` — who is connected to a device
- `stitch_topology_diagnostics` — health check: dangling ports, orphans, missing endpoints

### Workflow tools (may have side effects)
- `stitch_preflight_run` — full verification: collect live data, compare to declared topology
- `stitch_trace_vlan` — trace a VLAN path hop-by-hop through the network
- `stitch_impact_preview` — "what would happen if I remove this link/port/VLAN?"
- `stitch_interface_assign` — assign a physical interface to a role (WRITE operation, dry_run by default)

## When to use what

**User asks about the network layout:**
→ Start with `stitch_topology_summary`, then `stitch_devices`

**User asks about a specific device:**
→ `stitch_device_detail` for the device, then `stitch_device_neighbors` for context

**User asks "is everything working?":**
→ `stitch_preflight_run` with `detail: "standard"` — this is the primary health check

**User asks about VLAN connectivity:**
→ `stitch_trace_vlan` with the VLAN ID and source device

**User asks "what would break if I remove X?":**
→ `stitch_impact_preview` with the action, device, and port

**User wants to make a change:**
→ ALWAYS run dry_run first, then review, then apply. See remediation-planner skill.

## Detail levels

Most tools accept `detail`:
- `summary` — minimal output, fast, low tokens
- `standard` (default) — balanced, includes top findings
- `full` — everything, can be large (10K+ tokens)

**Start with standard.** Only use full if the user needs to see every check.

## Response format

Every tool returns:
```json
{"ok": true/false, "summary": "...", "result": {...}, "meta": {...}}
```

Read `summary` first. Only dig into `result` if the user needs details.

## Important rules

1. **Never call `stitch_interface_assign` with `dry_run: false` without explicit user approval**
2. **Always run preflight before and after any change** to verify the network state
3. **If a tool returns `ok: false`, explain the error clearly** — don't retry blindly
4. **The topology file is the source of truth** — if live observations differ from declared topology, that's a finding, not a bug
