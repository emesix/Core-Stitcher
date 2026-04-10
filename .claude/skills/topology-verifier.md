---
name: topology-verifier
description: How to interpret preflight verification results — what findings mean, severity classification, common patterns
---

# Topology Verification Guide

When you run `stitch_preflight_run`, the result contains findings that compare the **declared topology** (what should exist) against **live observations** (what adapters actually see). This skill helps you interpret those findings.

## Understanding the verdict

- **pass** — all links verified, no errors or warnings
- **warning** — some mismatches found, but none critical
- **fail** — errors found that indicate real connectivity problems

## Common finding patterns

### "Device not found in observed topology"
The declared topology says this device exists, but no adapter returned observations for it.

**Likely causes:**
- Device is offline or unreachable
- No adapter is configured for this device's `mcp_source`
- Network path to the device is broken

**Action:** Check if the device is powered on and the adapter MCP server is running.

### "Port not found on device"
The declared topology says this port exists, but the live observation doesn't include it.

**Likely causes:**
- Interface is physically present but not configured in the OS (common with fresh installs)
- Port name mismatch between declared and observed (e.g., "ix0" vs "ixl0")
- Interface was removed or renamed

**Action:** Use `stitch_device_detail` to see what ports the device actually has. Compare with the declared topology.

### "Neighbor mismatch"
The declared topology says port A connects to device B, but the live data shows a different neighbor or no neighbor.

**Likely causes:**
- Cable was moved
- LLDP/CDP not enabled or not converged
- Declared topology is out of date

### "VLAN mismatch"
Expected VLAN membership doesn't match observed.

**Likely causes:**
- VLAN not configured on the port
- Trunk vs access mode mismatch
- VLAN pruned by upstream switch

## Severity guide

- **error** — connectivity is definitely broken. Something declared is missing or wrong.
- **warning** — something is suspicious but may not be broken. Often caused by partial observation data.
- **info** — informational, no action needed.

## Partial data awareness

Preflight verification with only some adapters running will produce many "not found" findings for devices whose adapters are offline. This is **expected behavior**, not a system failure.

**Key question:** "How many observations were collected?" Check `result.observations_collected`. If it's 0, the entire report is "declared vs empty" — everything will show as missing. That's accurate but not actionable.

## Recommended workflow

1. Run `stitch_preflight_run` with `detail: "standard"`
2. Read the verdict and summary counts
3. Focus on **error** findings first
4. For each error, use `stitch_device_detail` and `stitch_device_neighbors` to investigate
5. If a finding is about a VLAN path, use `stitch_trace_vlan` to trace the route
6. If a fix is needed, follow the remediation-planner skill
