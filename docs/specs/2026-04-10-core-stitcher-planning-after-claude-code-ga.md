# Core-Stitcher Planning After Claude Code GA

**Date:** 2026-04-10  
**Context:** Reassessment after Claude Code became generally available and its extension ecosystem matured.

---

## 1. Executive decision

**Yes, the direction should be updated.**

The earlier pivot was directionally correct, but the current Claude Code platform strengthens that case even more than the first reassessment assumed:

- Claude Code is officially **generally available** in the release notes.
- Claude Code now officially supports **MCP**, **skills**, **hooks**, **subagents**, **plugins**, **project-scoped settings**, **GitHub Actions**, and an **Agent SDK**.
- That means the original “five custom operator clients” idea now has even less strategic value than it had when first questioned.

**Revised conclusion:**

Core-Stitcher should **not** keep investing as if it must become its own full operator shell ecosystem. It should instead become:

1. a **deterministic domain engine**,
2. a **safe write-path and verification layer**,
3. an **MCP-native capability provider** for Claude Code,
4. a **Git-backed SSOT/documentation system**,
5. plus a **small amount of custom UI only where Claude Code has real gaps**.

---

## 2. What changed since the previous reassessment

The earlier reassessment argued that Claude Code should become the primary operator surface, while Core-Stitcher remains the engine. That logic still holds.

What changed is that the Claude Code ecosystem is now more complete and more official:

- The release notes explicitly mark Claude Code **1.0.0 as generally available**.
- Official docs now treat **plugins** as the packaging layer for **skills, hooks, subagents, and MCP servers**.
- Official docs state Claude Code can connect to tools and APIs through **MCP**.
- Official docs recommend **hooks** for deterministic actions that must happen every time.
- Official docs support **project-scoped settings** for team-shared permissions, hooks, MCP servers, and plugins.
- Official docs expose the same building blocks through the **Agent SDK**.
- Official docs also provide **GitHub Actions** integration for repository automation.

This means the strategic question is no longer:

> “Should we experiment with Claude Code as an operator surface?”

It is now:

> “How do we redesign Core-Stitcher so Claude Code becomes the default operator shell without making us dependent on ad-hoc prompting?”

---

## 3. What remains unique to Core-Stitcher

Claude Code is now strong enough to replace a large amount of custom operator UX, but it does **not** replace the parts that are actually differentiated.

Core-Stitcher still owns the real product value:

### 3.1 Deterministic network logic

- topology verification,
- mismatch classification,
- trace and impact algorithms,
- state comparison,
- remediation planning,
- write-path guardrails.

These must stay testable, typed, and deterministic.

### 3.2 Infrastructure-specific write operations

Claude Code can invoke tools, but it should **not** be the place where the actual infrastructure semantics live.

Examples:

- assign OPNsense interfaces,
- apply VLANs,
- push switch changes,
- validate post-change state,
- refuse unsafe mutations.

### 3.3 Structured source of truth

The broader SSOT paper is still right: use mature systems instead of rebuilding them. A Git-backed Markdown repository should remain the documentation backbone, and structured infra truth should live in an existing system such as NetBox or Ralph where appropriate.

### 3.4 Visualization

Claude Code is strong for reasoning and orchestration, but not for topology canvas work, dashboards, or operational visuals.

---

## 4. Revised product shape

## 4.1 Primary operator surface

**Claude Code becomes the default operator interface.**

That means:

- conversation-first exploration,
- review and diagnosis in Claude Code,
- guided operations through MCP tools,
- team-shared behavior via project settings,
- reusable packaging via plugins.

## 4.2 Core-Stitcher becomes an execution and policy substrate

Core-Stitcher should expose:

- read tools,
- verification tools,
- topology diagnostics,
- remediation planners,
- safe write tools,
- audit-friendly outputs.

Claude Code should consume those capabilities, not replace them.

## 4.3 Minimal custom UI set

Keep only the UI surfaces that still have unique value:

- **CLI** for scripting, CI, batch, and low-cost deterministic use,
- **lite web/mobile rescue UI** for offline or degraded conditions,
- **topology canvas/dashboard UI** for visual operations.

Deprioritize or pause:

- TUI as a major investment area,
- full React operator console as the main workflow,
- desktop wrapper unless a later visual requirement truly demands it.

---

## 5. SSOT and documentation plan

The SSOT paper should not be treated as a separate initiative anymore. It should be merged into the Core-Stitcher direction.

## 5.1 Documentation backbone

Use a **Git-backed Markdown repository** as the canonical documentation layer.

Recommended shape:

- `docs/architecture/`
- `docs/runbooks/`
- `docs/network/`
- `docs/decisions/`
- `docs/inventory/`
- `docs/incidents/`
- `docs/generated/`

## 5.2 Publishing layer

Use **Docusaurus** or an equivalent static-site tool to publish Markdown content cleanly.

## 5.3 Structured infrastructure truth

Use an existing source-of-truth system where it adds value:

- **NetBox** if the emphasis is network topology, IPAM, racks, circuits, device relationships.
- **Ralph** if the emphasis is broader lifecycle and asset inventory.

## 5.4 Claude Code’s role in SSOT

Claude Code should:

- read Markdown docs,
- query structured infra systems through MCP or API adapters,
- generate or update draft docs,
- open PRs or patches,
- run validation hooks,
- leave final acceptance to review policy.

In other words: Claude helps maintain the SSOT, but Git and the structured infra system remain the authority.

---

## 6. Updated priorities

## Tier 1 — Do now

### 6.1 Build the Core-Stitcher MCP layer

This is now the highest-leverage move.

Expose tools such as:

- `stitch_preflight_run`
- `stitch_trace_vlan`
- `stitch_impact_preview`
- `stitch_device_inspect`
- `stitch_topology_diagnostics`
- `stitch_report_diff`

Design requirement:

- every tool returns structured results first,
- human-readable summaries second,
- stable schemas from day one.

### 6.2 Build the first real write-path commands

This remains the biggest product gap.

Start with one narrow, high-value remediation path:

- `stitch_interface_assign`

Likely first scope:

- configure unassigned OPNsense interfaces,
- validate target names and physical mappings,
- apply change through adapter layer,
- re-read state,
- emit before/after report,
- refuse execution if ambiguity remains.

Then extend to:

- VLAN apply,
- bridge membership changes,
- config push with verification.

### 6.3 Define safety hooks and policy boundaries

Use Claude Code hooks and project settings for enforcement, not just advisory instructions.

Minimum policy set:

- destructive operations require confirmation,
- all write-path tools are logged,
- post-change verification is mandatory,
- session stop checks for unreviewed changes.

### 6.4 Package team behavior as a plugin

Do not leave this as scattered repo-local setup.

Create a **Stitch plugin** that bundles:

- skills,
- hooks,
- subagents,
- MCP server definitions,
- maybe later an LSP/code-intelligence extension if useful.

That gives repeatable installation and team-wide consistency.

---

## Tier 2 — Do next

### 6.5 Hardening the CLI

Keep CLI as the deterministic escape hatch.

Add:

- machine-readable outputs,
- stdin-driven batch mode,
- shell completion,
- exact exit code policy,
- non-interactive auth/profile handling.

### 6.6 Build only the visual layer that Claude Code cannot replace

Focus the React surface on:

- topology graph,
- state diff visualizer,
- change preview canvas,
- health/status dashboards.

Do **not** rebuild a general-purpose operator shell around it.

### 6.7 Tie documentation generation into Git workflows

Have Claude Code support:

- draft runbook generation,
- architecture drift notes,
- incident postmortem drafts,
- generated inventory pages.

Keep these behind review and commit flow.

---

## Tier 3 — Deprioritize

### 6.8 Textual TUI as a flagship surface

Useful as an experiment. No longer a strategic centerpiece.

### 6.9 Full desktop wrapper

Pause unless a later offline/visual requirement demands native packaging.

### 6.10 Any large custom planner shell that duplicates Claude Code

Avoid rebuilding:

- command palette UX,
- conversational search UX,
- generic approval UI,
- generic task routing UI,
- plugin marketplace behavior.

---

## 7. Practical 90-day roadmap

## Phase A — Weeks 1–2

- Freeze the five-client vision as historical architecture, not active roadmap.
- Define the minimal supported surface set: Claude Code, CLI, lite UI, visual UI.
- Write the canonical schemas for MCP tool inputs/outputs.
- Pick the first write-path target: `stitch_interface_assign`.

## Phase B — Weeks 3–5

- Implement the first Core-Stitcher MCP server.
- Ship read-only tools first.
- Add one safe write-path tool.
- Add post-change verification output.

## Phase C — Weeks 6–8

- Create the Stitch plugin.
- Add project-scoped settings.
- Add hooks for confirmation, audit, and session-end checks.
- Add one or two focused subagents, such as:
  - topology reviewer,
  - device inspector,
  - remediation planner.

## Phase D — Weeks 9–12

- Harden CLI and non-interactive flows.
- Add Git-backed documentation workflows.
- Start the topology canvas as a thin visual app.
- Evaluate whether NetBox should become the structured topology SSOT.

---

## 8. Architecture guardrails

Use these as planning rules from now on.

### Rule 1

**Do not build custom UI where Claude Code already has an official, supported feature.**

### Rule 2

**Do build custom code where determinism, safety, topology logic, or visualization matter.**

### Rule 3

**All write-path features must be reversible, auditable, and post-verified.**

### Rule 4

**The SSOT must live in Git and/or a structured infra system, not in conversation state.**

### Rule 5

**Claude Code is the default shell, not the only shell.**

That means keeping escape hatches:

- CLI,
- lite UI,
- direct APIs,
- exported reports.

---

## 9. Final planning call

### We should continue — but with a narrower and sharper scope.

The new light is not a reason to stop Core-Stitcher.
It is a reason to stop pretending Core-Stitcher should grow into five equal operator surfaces.

The best plan now is:

1. **make Core-Stitcher the deterministic network/infrastructure brain,**
2. **make Claude Code the primary operator shell,**
3. **make MCP the contract between them,**
4. **make Git + Markdown + structured infra data the SSOT,**
5. **make the write path the next real milestone.**

### Immediate next build recommendation

If choosing one thing to do next, it should be:

**Build the first production-grade MCP-backed write path around `stitch_interface_assign`, with safety hooks and post-change verification.**

That is the shortest path from “interesting architecture” to “real operator capability.”

---

## 10. Source basis for this planning update

This planning update is based on:

- the earlier strategic reassessment that argued for Claude Code as the primary operator surface,
- the SSOT paper arguing for Git-backed Markdown plus mature structured infra tools instead of bespoke replacements,
- current official Claude Code documentation showing GA status, MCP, hooks, skills, subagents, plugins, project-scoped settings, Agent SDK, and GitHub Actions.
