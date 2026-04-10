---
name: remediation-planner
description: Safe sequence for fixing network issues — inspect, dry run, impact preview, approval, apply, verify
---

# Remediation Planning Guide

When a preflight finding indicates a real problem that needs fixing, follow this exact sequence. Never skip steps.

## The remediation sequence

```
1. INSPECT  — understand current state
2. DRY RUN  — preview what the fix would do
3. IMPACT   — check for collateral damage
4. APPROVE  — get explicit user confirmation
5. APPLY    — execute the change
6. VERIFY   — confirm the fix worked
```

## Step by step

### 1. INSPECT

Before fixing anything, understand the full picture:

```
stitch_device_detail(device_id="...")
stitch_device_neighbors(device_id="...")
stitch_topology_diagnostics()
```

Explain to the user what the current state is and what the problem looks like.

### 2. DRY RUN

Run the proposed fix in dry_run mode:

```
stitch_interface_assign(
  device_id="opnsense",
  physical_interface="ix0",
  assign_as="opt1",
  description="Frontend trunk to ONTi-FE",
  dry_run=true    ← ALWAYS start with true
)
```

Show the user the before/after diff from the dry run result.

### 3. IMPACT PREVIEW

Check what else would be affected:

```
stitch_impact_preview(
  action="remove_port",  // or whatever the inverse would be
  device="opnsense",
  port="ix0"
)
```

Explain the risk level and affected endpoints.

### 4. APPROVE

Present a clear summary to the user:

> "I propose to assign interface ix0 as OPT1 (Frontend trunk) on opnsense.
> Dry run shows: before=unassigned, after=opt1.
> Impact: low risk, 0 other devices affected.
> 
> Do you want me to apply this change?"

**Wait for explicit "yes" before proceeding.** Do not interpret ambiguous responses as approval.

### 5. APPLY

Only after explicit approval:

```
stitch_interface_assign(
  device_id="opnsense",
  physical_interface="ix0",
  assign_as="opt1",
  description="Frontend trunk to ONTi-FE",
  dry_run=false    ← only after approval
)
```

The pre-tool-use hook will block this if the approval context is missing.

### 6. VERIFY

Immediately after applying:

```
stitch_preflight_run(detail="standard")
stitch_device_detail(device_id="opnsense")
```

Compare the verification result to the pre-change state. Tell the user:
- What changed
- Whether the fix resolved the original finding
- Whether any new issues appeared

## Rules

1. **NEVER skip the dry run.** Even if the change looks trivial.
2. **NEVER apply without explicit user approval.** "Sure" is not "yes, apply ix0 as opt1 on opnsense."
3. **NEVER apply multiple changes at once.** One interface, one device, one change. Verify between each.
4. **If verify shows new problems, STOP and report.** Do not try to fix the fix.
5. **If the apply fails, DO NOT retry automatically.** Report the error and let the user decide.

## What's available in v1

Currently only `stitch_interface_assign` supports the apply path. It can:
- Assign unassigned physical interfaces to logical roles on OPNsense
- It CANNOT overwrite existing assignments
- It CANNOT configure VLANs, bridges, or IP addresses (yet)

If the user needs a change beyond interface assignment, explain what's available and what isn't. Don't pretend tools exist that don't.
