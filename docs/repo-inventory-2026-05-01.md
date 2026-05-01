# `~/git` Repository Inventory — 2026-05-01

Operator: emesix
Host scope: `/home/emesix/git/`
Method: read-only inspection via `git -C <path>` (no writes, no fetches, no
network calls). Generated under AI-Collab Planning task
`planning-20260501T033134Z-a9ac7c`, target work repo
`/home/emesix/git/The-Stitch`.

This document is **evidence**, not policy. Decisions about what to merge,
archive, or delete live in the activation gate doc, not here.

---

## 1. Stitch family (canonical members)

The four members named by `~/git/stitch/README.md`. All four have remotes
and clean working trees as of capture.

| Codename | Canonical path | Branch | HEAD | Last commit | Remote | Dirty |
|---|---|---|---|---|---|---|
| **The Stitch** | `/home/emesix/git/The-Stitch` | `main` | `305d234` | 2026-04-11 | `https://github.com/emesix/Core-Stitcher.git` | 0 |
| **The SOW** | `/home/emesix/git/Stitch-Lab` | `feat/stage9-t1-dmz-mail-design` | `13f59eb` | 2026-04-28 | `https://gitea.lab.emesix.nl/lab/stitch-lab.git` | 0 |
| **Q-Loop Killer** | `/home/emesix/git/AI-Collaboration` | `feat/ai-collab-operating-model-v2` | `a72b4c8` | 2026-05-01 | `https://github.com/emesix/AI-Collaboration.git` | 0 (unpushed branch) |
| **Secret Railgunner** | `/home/emesix/git/SQ-A` | `main` | `8a5d642` | 2026-04-28 | `https://github.com/emesix/SQ-A.git` | 0 |

Notes:
- The Stitch and Backup-Stitcher both target `Core-Stitcher.git`. Backup-
  Stitcher is **not** the canonical member (see §4).
- Q-Loop Killer's working branch is **ahead of its remote** with the
  operating-model-v2 docs commit (`a72b4c8`). Push remains an explicit
  operator boundary.
- Stitch-Lab's remote is the **only** member on the lab gitea instance
  (others are on github.com). Mixed-host topology is intentional.

## 2. Stitch umbrella scaffold

Path: `/home/emesix/git/stitch/`

Contents (4 symlinks + README, no `.git`):

```
q-loop-killer       -> ../AI-Collaboration
secret-railgunner   -> ../SQ-A
the-sow             -> ../Stitch-Lab
the-stitch          -> ../The-Stitch
README.md           (1.2 kB, defines codenames + tagline "Kill the loop. Guard the payload.")
```

The README points at `the_stitch_naming_and_realtime_activation.md` §4 as
the activation gate. **That document does not exist anywhere on disk**
(searched `~/git` excluding `.venv/` / `node_modules/` / `.git/` —
zero hits). The umbrella is currently *named* but *ungated*. Resolving
this is the activation gate doc's job.

## 3. Proofing / Discovery workspace (existing, no .git)

Path: `/home/emesix/git/AI-Collab-QS-A Proofing/`

Contents:

```
AI-Collaboration/        nested git checkout (proofing copy, NOT canonical)
SQ-A/                    nested git checkout (proofing copy, NOT canonical)
docs/                    superpowers/ specs cache
.claude/                 settings.local.json
Improvement on AI-Collab.md     improvement spec
proofing-evidence.md            real-world plugin proofing report (2026-04-28)
```

Status of nested checkouts:

| Nested | Branch | HEAD | Dirty | Remote | Newer than canonical? |
|---|---|---|---|---|---|
| `Proofing/AI-Collaboration` | `feat/ralph-chatgpt-v1` | `2136311` (2026-04-28) | 2 | none | **NO** — canonical is at `a72b4c8` (2026-05-01) on `feat/ai-collab-operating-model-v2`, two branches ahead |
| `Proofing/SQ-A` | `main` | `e97b588` (2026-04-28) | 0 | none | **DIFFERENT** — canonical at `8a5d642` (2026-04-28). Same date, different commit — divergence requires reconciliation if either copy is canonical for any decision. |

Purpose (inferred from `proofing-evidence.md`): a *joint* working area
that proofs SQ-A and AI-Collab against the live Stitch-Lab repo. The
outputs (`proofing-evidence.md`, `Improvement on AI-Collab.md`) are the
shape Pre-Project / Discovery would produce. The folder itself has no
git — it is a working sandbox, not a tracked artefact.

## 4. Literal merge / consolidation candidates

These are *git-mergeable* in the strict sense — duplicate work that
should converge to one path.

### 4.1 Backup-Stitcher → The-Stitch (same remote)

| Path | Branch | HEAD | Remote |
|---|---|---|---|
| `/home/emesix/git/The-Stitch` | `main` | `305d234` | `Core-Stitcher.git` |
| `/home/emesix/git/Backup-Stitcher` | `main` | `4527e34` | `Core-Stitcher.git` |

Backup-Stitcher is **1 commit behind** The-Stitch on the same remote.
No unique work; pure duplication. Decision belongs in the activation
gate doc.

### 4.2 VOS-Network-Failed → VOS-Network-Redux (same project, two attempts)

| Path | Branch | HEAD | Dirty | Ahead/behind | Remote |
|---|---|---|---|---|---|
| `/home/emesix/git/VOS-Network-Failed` | `main` | `090c8ec` | 19 | 0/1 | `git@github.com:emesix/VOS-Network.git` |
| `/home/emesix/git/VOS-Network-Redux` | `main` | `f2c6b34` | 0 | n/a | (no remote) |

`-Failed` has 19 dirty changes and is 1 commit behind its remote.
`-Redux` is the second attempt (clean, no remote). Either rescue the
19 dirty changes from `-Failed` or formally abandon them. **Not a
Stitch-family concern**, recorded here for completeness.

### 4.3 cmrat (lower) vs CMrat (upper)

| Path | Type | Contents |
|---|---|---|
| `/home/emesix/git/cmrat` | git repo, `main` `c591afa` (2025-08-13), `DTVElectronics/cmrat.git` remote | manufacturing/, photos/, 3d-models/, README.md |
| `/home/emesix/git/CMrat` | no .git | three `lineage-*` image files only |

`CMrat` (upper) is **not** a duplicate of `cmrat` (lower) — it's a stash
of LineageOS images that happen to share the case-different name. Pure
filesystem-collision artefact.

## 5. Repos with no remote (work that exists nowhere else)

These have local git history but no `origin`. If the directory is
deleted, the work is lost.

| Path | Branch | HEAD | Last | Dirty |
|---|---|---|---|---|
| `/home/emesix/git/adb-mcp` | `main` | `56946ea` | 2026-01-29 | 2 |
| `/home/emesix/git/AI-Browser-API` | `master` | `809e223` | 2026-04-26 | 9 |
| `/home/emesix/git/docflow-mcp` | `main` | `f53fcf2` | 2026-01-26 | 0 |
| `/home/emesix/git/INTELL-A770` | `feat/executor-sidecar` | `3f34c68` | 2026-04-10 | 0 |
| `/home/emesix/git/openWRT-Forum-extraction-MCP` | `master` | `da731bf` | 2026-01-31 | 0 |
| `/home/emesix/git/OPNsense-Proxmox` | `main` | `f353552` | 2026-04-09 | 0 |
| `/home/emesix/git/Searchcraft` | `main` | `229434d` | 2026-04-07 | 1 |
| `/home/emesix/git/VOS-Network-Redux` | `main` | `f2c6b34` | 2026-04-07 | 0 |
| `/home/emesix/git/VOS-Project-Explorer` | `master` | `619e016` | 2026-04-08 | 0 |

## 6. Repos with empty branch / no commits

These are partially-initialised — `git init` was run but no commit yet.

| Path | Branch | Dirty |
|---|---|---|
| `/home/emesix/git/ARR-Stack` | `HEAD` (no commits) | 4 |
| `/home/emesix/git/Gamarr` | `HEAD` (no commits) | 5 |
| `/home/emesix/git/vos-docs` | `HEAD` (no commits) | 1 |

## 7. Repos with unpushed work

| Path | Branch | Ahead | Notes |
|---|---|---|---|
| `/home/emesix/git/AI-Collaboration` | `feat/ai-collab-operating-model-v2` | n/a (no upstream) | docs commit `a72b4c8` not on origin |
| `/home/emesix/git/VOS-Ruggensgraat` | `master` | 5 ahead, 0 behind | also dirty (1) |
| `/home/emesix/git/VOS-Network-Failed` | `main` | 0 ahead, 1 behind | also dirty (19) |

## 8. Snapshot / archive files at `~/git/` top level

Pre-umbrella point-in-time backups, not tracked anywhere:

```
459K  AI-Browser-API-29-4-26.zip
 11M  AI-Collaboration-29-4-26.zip
 67M  AI-Collaboration-30-4-26.zip
 24K  ARR-Stack.zip
 32M  docflow-mcp.tar.gz
 34M  docflow-mcp.zip
8.5M  Hentai-Reader-29-4-26.zip
1.0M  Hentai-Reader.tar.gz
2.7M  OPNsense-MCP-fix-29-4-26.zip
1.2M  SQ-A-29-4-26.zip
 11M  Stitch-Lab-29-4-26.zip
399K  VOS-Network.zip
```

Total: ~165 MB across 12 files. Each one is "lost-restart-point"
optionality — no guarantee any of them is reachable from the live
repos' git history.

## 9. Other directories at `~/git/` top level (no .git, not in scope)

These are domain folders, not engineering projects:

| Path | Contents type |
|---|---|
| `/home/emesix/git/3D-Printers` | per-printer subdirs (anycubic, bambu, ender, mars, mendelmax, sk-tank) |
| `/home/emesix/git/CMrat` | LineageOS image stash (see §4.3) |
| `/home/emesix/git/data` | scraper outputs (galleries, scraper_state.yaml, thumbnails) |
| `/home/emesix/git/Datalogic Scanner` | device docs |
| `/home/emesix/git/DIY-EMC-LAB` | hardware notes |
| `/home/emesix/git/EVE-line` | empty |
| `/home/emesix/git/H96-MAX-V58` | empty |
| `/home/emesix/git/Kobra-2-PRO` | empty |
| `/home/emesix/git/ONT-S508CL-8S` | single file |
| `/home/emesix/git/OPNsense-MCP-fix` | `briefing/`, `repo/` |
| `/home/emesix/git/pikvm` | empty |
| `/home/emesix/git/repos` | `emesix/` (contains `docs.git` — appears bare) |
| `/home/emesix/git/Samsung-A55` | empty |
| `/home/emesix/git/tuya` | empty |
| `/home/emesix/git/VvE` | property association docs |

## 10. Other tracked repos (separate platforms, NOT in Stitch scope)

Recorded for completeness so the activation gate can explicitly defer
them.

### 10.1 VOS family (own platform, separate from Stitch)
- `/home/emesix/git/VOS-Network-Failed` (see §4.2, §7)
- `/home/emesix/git/VOS-Network-Redux` (see §4.2, §5)
- `/home/emesix/git/VOS-Project-Explorer` (see §5)
- `/home/emesix/git/VOS-Ruggensgraat` (see §7) — `git@github.com:emesix/VOS-Ruggensgraat.git`
- `/home/emesix/git/VOS-Workbench-standalone` — `feat/phase1-stabilize-contracts`, dirty (6), `git@github.com:emesix/VOS-Workbench.git`

### 10.2 Network / homelab infrastructure
- `/home/emesix/git/homelable` (Pouzor's repo, third-party)
- `/home/emesix/git/switchcraft` — `main` clean-but-dirty(5), `emesix/switchcraft.git`
- `/home/emesix/git/ONT-S207CW-62TS-SE`, `/home/emesix/git/ONT-S207CW-91TSM` (device repos)
- `/home/emesix/git/OPNsense-Proxmox` (no remote, see §5)

### 10.3 MCP servers / tooling
- `/home/emesix/git/adb-mcp` (no remote, see §5)
- `/home/emesix/git/docflow-mcp` (no remote, see §5)
- `/home/emesix/git/openWRT-Forum-extraction-MCP` (no remote, see §5)
- `/home/emesix/git/PixelPilotMCP` — `emesix/PixelPilotMCP.git`

### 10.4 Personal / unrelated
- `/home/emesix/git/Hentai-Reader` — `emesix/hentai-reader.git`
- `/home/emesix/git/cmrat` — `DTVElectronics/cmrat.git`
- `/home/emesix/git/vve-ogierssingel-bollandstraat.github.io` — `vve-ogierssingel-bollandstraat/...`

---

## 11. Inventory totals

| Category | Count |
|---|---|
| Tracked repos with remote | 16 |
| Tracked repos without remote | 9 |
| Tracked repos with no commits | 3 |
| Non-git directories | 16 |
| Snapshot files (`.zip` / `.tar.gz`) | 12 |
| Stitch-family canonical repos | 4 |
| Stitch-family duplicate checkouts | 1 (Backup-Stitcher) |
| Proofing-folder nested checkouts | 2 (AI-Collaboration, SQ-A) |

---

## 12. What this inventory does NOT do

- Does not delete, move, archive, or modify any file outside
  `/home/emesix/git/The-Stitch/docs/`.
- Does not push, fetch, or otherwise touch any remote.
- Does not read secrets.
- Does not classify the VOS family or homelab cluster — those are out
  of scope for the Stitch activation. They appear in §10 only so the
  activation gate can defer them explicitly rather than by silence.
- Does not reconcile `Proofing/SQ-A` divergence with canonical SQ-A —
  the activation gate doc records that this reconciliation is
  required before the proofing folder can be promoted to a tracked
  workspace.

---

## 13. Capture evidence

The inventory above was produced by:

```sh
cd ~/git && for d in */; do
  git -C "${d%/}" rev-parse --abbrev-ref HEAD 2>/dev/null
  git -C "${d%/}" log -1 --format="%h %cs %s" 2>/dev/null
  git -C "${d%/}" status --short 2>/dev/null | wc -l
  git -C "${d%/}" remote get-url origin 2>/dev/null
  git -C "${d%/}" rev-list --left-right --count "@{upstream}...HEAD" 2>/dev/null
done
```

plus targeted probes of `AI-Collab-QS-A Proofing/`, `~/git/stitch/`,
and snapshot files via `ls -lhd ~/git/*.zip ~/git/*.tar.gz`.

No state was mutated. The inventory reflects `~/git` at
2026-05-01T03:31:34Z (task arming time) — operator changes after that
moment are not captured here.
