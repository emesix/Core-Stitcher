# The Stitch — Activation Gate v1

Status: gate definition (v1). Defines what The Stitch family is, what
"activation" means, and what must be true before the umbrella stops
being a lore namespace and becomes a binding architectural unit.

Authority order for this document:
1. This file.
2. `/home/emesix/git/The-Stitch/docs/repo-inventory-2026-05-01.md` —
   the evidence backing every claim here.
3. `/home/emesix/git/stitch/README.md` — the original symlink scaffold
   and codename map.

This file replaces the *missing* `the_stitch_naming_and_realtime_activation.md`
that the symlink README references. If that older file is found, treat
this v1 as the canonical successor and supersede the older draft;
record the supersession explicitly.

The PRISM frame this gate sits inside:

```
Pre-Project   ← this document is one of its outputs
Discovery     ← (proofing workspace, see §6)
Design        ← per-member specs in each repo's docs/
Delivery      ← per-member implementation work
Closure       ← per-member PR / merge
Post-Project Benefits Realization (PRBR) ← deferred; see §10
```

---

## 1. The four-member Stitch family

Single source of truth. Codename, canonical repo, remote, and one-line
purpose. Anything else claiming to be a Stitch member is wrong.

| # | Codename | Canonical repo | Remote | One-line purpose |
|---|---|---|---|---|
| 1 | **The Stitch** | `/home/emesix/git/The-Stitch` | `https://github.com/emesix/Core-Stitcher.git` | operator platform / lore home / spine runtime + topology + AI orchestrator |
| 2 | **The SOW** (Statement of Work) | `/home/emesix/git/Stitch-Lab` | `https://gitea.lab.emesix.nl/lab/stitch-lab.git` | active operator body — where the SOW gets executed against real infrastructure |
| 3 | **Q-Loop Killer** (formerly "AI-Collab") | `/home/emesix/git/AI-Collaboration` | `https://github.com/emesix/AI-Collaboration.git` | anti-clarification-loop workflow controller / Claude Code plugin |
| 4 | **Secret Railgunner** | `/home/emesix/git/SQ-A` | `https://github.com/emesix/SQ-A.git` | credential-safety controller / secret pipeline plugin |

Tagline (from `~/git/stitch/README.md`):

> **Kill the loop. Guard the payload.**

Q-Loop Killer kills the loop. Secret Railgunner guards the payload.
The SOW is the body the family operates on. The Stitch is the spine
they all attach to.

## 2. What each member owns

### 2.1 The Stitch (the spine)
- Spine runtime (`src/`).
- Topology domain modules.
- AI orchestrator.
- Network-stitcher and project-stitcher behaviour templates
  (per `The-Stitch/CLAUDE.md`).
- The umbrella's *own* docs (this file, the inventory, the future
  PROJECT-MAP).
- **Does NOT own**: operator field work (that's The SOW), workflow
  policy (that's Q-Loop Killer), or credential plumbing (that's
  Secret Railgunner).

### 2.2 The SOW / Stitch-Lab (the body)
- Active per-stage operator work (currently
  `feat/stage9-t1-dmz-mail-design`, last commit 2026-04-28).
- Real network/infrastructure topologies the family acts on
  (`topologies/`, `deploy/`).
- Stage-by-stage SOW execution evidence.
- **Does NOT own**: spine code (that's The Stitch), Claude policy
  (that's Q-Loop Killer), or credential reads (that's Secret
  Railgunner — Stitch-Lab is the *target*, not the *guard*).

### 2.3 Q-Loop Killer / AI-Collaboration (the workflow controller)
- The five mode commands (`Concept`, `Specs`, `Planning`, `Reviewing`,
  `Answer-All`) and two utility commands (`Doctor`, `Clean`).
- The hook surface (`PreToolUse Bash` guard, `Stop` boundary
  supervisor, `gpt-judge`, `gpt-reviewer`).
- The contract / sanitizer / state machine
  (`hooks/_ai_collab/`).
- The operating-model-v2 control law
  (`docs/plugin/operating-model-v2.md`, currently on unpushed branch
  `feat/ai-collab-operating-model-v2` at `a72b4c8`).
- **Does NOT own**: any operator infrastructure mutation (that's
  Stitch-Lab's domain), credential reads (Secret Railgunner), or the
  spine substrate (The Stitch).

### 2.4 Secret Railgunner / SQ-A (the payload guard)
- Credential pipeline.
- SQ-A discipline skill (in any consuming repo).
- Vaultwarden wrapper paths (the only sanctioned credential surface).
- **Does NOT own**: workflow policy (Q-Loop Killer), spine code (The
  Stitch), or the body (The SOW).

## 3. What must NOT be merged

These distinctions are load-bearing. Violations create the same
"plugin became Stitch became memory store became everything" drift
that this document exists to prevent.

- **Q-Loop Killer ≠ The Stitch.** Q-Loop Killer is a Claude Code
  plugin; The Stitch is the platform. Q-Loop Killer is a *client* of
  any future Stitch-side memory or policy plane, never the owner of
  it.
- **The SOW ≠ The Stitch.** The SOW does field work; The Stitch
  defines the substrate. Stage 9 networking work belongs in
  Stitch-Lab, not Core-Stitcher.
- **Secret Railgunner stays separate.** The credential pipeline must
  not be folded into Q-Loop Killer's hook surface. Their
  responsibilities only overlap at the SQ-A discipline skill, which is
  a *thin* read-only consumer.
- **`Backup-Stitcher` is not a member.** It is a stale duplicate
  checkout of `Core-Stitcher.git` (1 commit behind The Stitch — see
  inventory §4.1). It must never appear in any Stitch dependency
  graph.
- **Proofing copies are not canonical.** `AI-Collab-QS-A
  Proofing/AI-Collaboration` and `Proofing/SQ-A` are sandbox clones
  (no remote, divergent heads — see inventory §3). They are *evidence
  surfaces*, not authoritative repos.

## 4. The proofing / Discovery workspace

Path: `/home/emesix/git/AI-Collab-QS-A Proofing/`

This folder predates this gate. It is the *de facto* Discovery
workspace for the Stitch family — the place where SQ-A and Q-Loop
Killer get proofed against the live SOW (Stitch-Lab) before changes
land. Its outputs (`proofing-evidence.md`,
`Improvement on AI-Collab.md`) are the shape Pre-Project / Discovery
produces inside the PRISM frame.

What the gate decides about it:

- **It is recognised as the Discovery surface for the family**, not
  an orphan staging folder.
- **Its name is wrong** — `QS-A` is a typo for `SQ-A` (recorded in
  `proofing-evidence.md` itself: "QS-A in the proofing-dir name is a
  transposition typo"). The activation work renames it.
- **Its nested checkouts are non-canonical** — they must never be
  pushed, never be the source of truth, and any divergence between a
  proofing copy and its canonical repo must be reconciled into the
  canonical repo before activation completes.
- **It has no git of its own.** The activation work either promotes
  it to a tracked workspace (its own `.git`) or folds its useful
  outputs into `The-Stitch/docs/discovery/` and decommissions the
  folder. Both are acceptable; choosing between them is part of
  activation work.

## 5. What "activation complete" means

The umbrella crosses from "lore namespace" to "binding architecture"
when **all** of the following hold:

1. **Family identity is durable.**
   - This document (`the-stitch-activation-gate-v1.md`) and the
     evidence inventory live in `/home/emesix/git/The-Stitch/docs/`,
     committed to `Core-Stitcher.git`.
   - Each canonical member's repo has a `STITCH-MEMBERSHIP.md`
     (or equivalent `CLAUDE.md` section) that declares its codename,
     its purpose, and its non-overlap rules per §2-3 above.

2. **Q-Loop Killer's operating-model-v2 is landed.**
   - PR #3 for `feat/ai-collab-operating-model-v2` is merged into
     `feat/ralph-chatgpt-v1` (or whichever base branch is chosen).
   - The rename from "AI-Collab" to "Q-Loop Killer" is documented;
     code-level renames remain explicitly *deferred* (see §9).

3. **Backup-Stitcher is resolved.**
   - Either the duplicate checkout is folded into The Stitch's
     working tree and the `Backup-Stitcher/` directory is
     decommissioned, or it is explicitly retained with a written
     reason. Silence is not acceptable.

4. **Proofing workspace decision is made.**
   - The `AI-Collab-QS-A Proofing/` folder is either promoted to a
     tracked git repo (with its own remote, optional) under a
     correctly-spelled name, or its outputs are folded into
     `The-Stitch/docs/discovery/` and the folder is decommissioned.

5. **PROJECT-MAP exists.**
   - `/home/emesix/git/The-Stitch/PROJECT-MAP.md` is committed and
     lists every Stitch-family path with full absolute paths so the
     operator never again says "without full path names I can't find
     the documents".

6. **The symlink scaffold is reconciled.**
   - `/home/emesix/git/stitch/README.md` is updated to point at this
     activation gate (not the missing
     `the_stitch_naming_and_realtime_activation.md`).
   - Either the symlink folder is retained as a convenience namespace
     (with a one-line note that the canonical paths are in
     `The-Stitch/docs/`), or it is decommissioned.

When all six hold, the activation gate is **passed**. Until then, the
umbrella is *defined* but not *binding* — operators may still proceed
without referencing it, and downstream subsystems (Stitch Memory Lite,
Pre-Project machinery) MUST NOT assume the family identity is durable
yet.

## 6. What activation does NOT require

Explicit non-criteria, to keep the gate small:

- **No code-level renames.** Q-Loop Killer's bin scripts can keep the
  `ai-collab-*` prefix; `_ai_collab/` python package keeps its name.
  The codename rename is documentary, not refactoring. Renames remain
  a separate, deferred decision (see §9).
- **No new mode commands.** `/ai-collab:Auditing` proposed in
  `operating-model-v2.md` §7 stays deferred.
- **No memory implementation.** Stitch Memory Lite stays deferred
  until activation completes (see §8).
- **No hook changes.** Existing hard hooks remain the safety floor.
- **No push of unmerged feature branches** unless the operator
  authorises it explicitly per branch.

## 7. Parallel non-Stitch concerns (explicitly deferred)

The inventory (§10) lists three other clusters under `~/git`. The
gate explicitly **does not** annex them:

- **VOS family** (5 repos: VOS-Network-Failed/Redux, VOS-Project-
  Explorer, VOS-Workbench-standalone, VOS-Ruggensgraat, vos-docs).
  Separate platform with its own consolidation problem.
  VOS-Network-Failed has 19 dirty changes that need rescue or formal
  abandonment — that is a VOS-side decision, not a Stitch-side one.
- **Network / homelab infrastructure** (homelable, switchcraft, ONT-*,
  OPNsense-Proxmox, OPNsense-MCP-fix). These are *what The SOW acts
  on*, not Stitch members. They are operator infrastructure.
- **MCP servers** (adb-mcp, docflow-mcp, openWRT-Forum-extraction-
  MCP, PixelPilotMCP). Tooling consumed by other things.

These clusters remain governed by whatever they were governed by
before this document existed. The activation gate's only obligation
to them is to *name* them so they can be excluded by reference rather
than by silence.

## 8. What activation enables

Once the gate is passed:

- **Stitch Memory Lite** (the SQL-backed memory/policy/diagnostics
  service from the API-Memory strategy doc) gains a canonical home
  inside The Stitch — `/home/emesix/git/The-Stitch/services/stitch-
  memory/` or as a sibling repo cleanly named — and stops being
  "another orphan project that will later need merging".
- **Pre-Project / PRBR machinery** (the missing P and final-stage of
  PRISM) gains a place to live: Pre-Project as a Q-Loop Killer mode
  that consults Stitch Memory; PRBR as a Stitch-Memory-side report
  surface.
- **The Discovery folder gets a stable identity** — proofing evidence
  for any family member lands in one known place, with a real git
  history.

These are *consequences* of activation, not part of it.

## 9. Deferred renames

The following renames are sensible but deliberately scoped out of v1:

- `~/git/AI-Collaboration/` → `~/git/Q-Loop-Killer/` (filesystem
  rename + symlink + remote rename).
- `~/git/SQ-A/` → `~/git/Secret-Railgunner/` (same).
- `~/git/Stitch-Lab/` → `~/git/The-SOW/` (same; non-trivial because
  it has live mid-flight Stage 9 work).
- `~/git/AI-Collab-QS-A Proofing/` → `~/git/Stitch-Discovery/` (after
  §5 decision lands).

Doing any of these now would interrupt active work (Stitch-Lab's
Stage 9, Q-Loop Killer's operating-model-v2 PR). Renames are tracked
as a separate post-activation chore; they MUST NOT be done as a side
effect of activation work.

## 10. PRBR (Post-Project Benefits Realization) deferral

PRBR is the sixth PRISM stage and the natural home for cross-session
memory. The activation gate explicitly defers it:

- **Why deferred:** PRBR needs Stitch Memory Lite (or equivalent)
  as a substrate. That substrate cannot be built coherently until the
  family identity is durable (i.e. until this gate passes).
- **What gets carried forward:** the proofing evidence already in
  `AI-Collab-QS-A Proofing/proofing-evidence.md` is the seed corpus
  for whatever PRBR ends up looking like. It must not be lost during
  the §5 decision about that folder's fate.
- **When PRBR work resumes:** after gate criteria 1-6 (§5) are all
  satisfied. The first PRBR question to answer at that point is
  "what does Stitch Memory Lite need to read from a 30-day-old
  shipped feature so the operator knows it's still useful?"

---

## 11. Summary

| Question | Answer |
|---|---|
| What is The Stitch? | An umbrella over four canonical repos (§1). |
| What does each member own? | §2. |
| What must not be merged? | §3. |
| Where is Discovery? | The existing `AI-Collab-QS-A Proofing/` folder, until §5 is decided. |
| When is activation complete? | When all six criteria in §5 hold. |
| What is explicitly NOT activation work? | §6. |
| What is deferred? | §7 (parallel clusters), §9 (renames), §10 (PRBR / Stitch Memory). |
| What evidence backs this? | `repo-inventory-2026-05-01.md`. |

## 12. Operator decisions required (before activation can begin)

These are the **only** real decisions the operator must make. Boring
verifiable work (running git, classifying repos, writing docs) was
done by AI per operating-model-v2. The following are not chores; they
are policy:

1. **PR #3 push authorisation.** Push
   `feat/ai-collab-operating-model-v2` to origin and open the PR for
   merge into `feat/ralph-chatgpt-v1`?  *(Boundary: push.)*
2. **Backup-Stitcher fate.** Decommission (delete the directory; The
   Stitch already has the same remote and is 1 commit ahead) or
   retain with a written reason?  *(Boundary: destructive deletion of
   a working tree, even if the work is duplicated upstream.)*
3. **Proofing folder fate.** Promote to tracked repo with a
   correctly-spelled name, or fold into
   `The-Stitch/docs/discovery/`?  *(Boundary: scope choice; both
   options are reversible but pick a direction.)*
4. **Symlink scaffold fate.** Retain `~/git/stitch/` as a convenience
   namespace, or decommission once `PROJECT-MAP.md` exists?
   *(Boundary: minor; either is fine.)*

Once those four are answered, the rest of activation is mechanical and
can be done by AI under future Q-Loop Killer mode contracts.
