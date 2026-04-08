# VOS Intent Graph and Path Diagnostics — Counter-Proposal

**Date:** 2026-04-07  
**Status:** Counter-proposal for Claude Code  
**Working name:** VOS-PathMap

---

## 1. Executive Summary

The current proposal frames the project as a **network topology visualizer with live verification**. That is useful, but it is still too close to a passive documentation tool.

This counter-proposal reframes the project as an:

> **AI preflight planning and path diagnostics system for VOS infrastructure**

The core problem is not lack of diagrams.  
The core problem is that both humans and AIs tend to act **ad hoc** in a system that has hidden dependencies. One local fix breaks another part of the environment because the intended state, dependency chain, and blast radius are not explicit enough before execution.

The new design therefore prioritizes:

1. **Path tracing for failures**
2. **Impact preview for planned changes**
3. **Constraint-aware execution support for AI**
4. **Post-change verification against intended state**

The visual topology remains important, but becomes a **consumer of the model**, not the main product.

---

## 2. Problem Statement

The VOS environment is no longer simple enough to troubleshoot or modify safely through memory, scattered notes, or local reasoning by an AI.

Current failure mode:

- An AI sees a local issue
- It applies a local fix
- The fix changes a bridge, VLAN, uplink, service location, or interface assumption
- Another path silently breaks
- Documentation lags behind reality
- Troubleshooting starts over from scratch

This gets worse as the environment becomes more interconnected.

The missing component is not merely a diagram.  
The missing component is an **externalized operational model** that can answer two questions before and after a change:

1. **Where did the path break?**
2. **What else breaks if I change this path?**

---

## 3. Thesis

The system should not primarily model *how the network looks*.  
It should model:

- what paths are supposed to exist
- what each path depends on
- what each device/service requires
- what constraints must remain true
- how to detect divergence from plan
- how to estimate blast radius before execution

This makes the tool useful to both:

- **Humans**, who need fast visual fault isolation
- **AIs**, which need explicit structure before proposing or applying changes

---

## 4. Product Definition

### 4.1 What this is

VOS-PathMap is a:

- **path diagnostics engine**
- **change impact engine**
- **constraint map**
- **verification layer**
- **AI planning substrate**

### 4.2 What this is not

It is not:

- a general-purpose diagramming app
- a replacement for OPNsense, Proxmox, or switch UIs
- a full DCIM/CMDB replacement
- a configuration management platform
- a monitoring/alerting system
- a purely portfolio-driven frontend project

---

## 5. Core Operating Modes

## 5.1 Mode A — Trace Failure

Purpose:

> Given a VLAN, interface, device, service, or management path, determine where the expected chain diverges from observed reality.

### Example

"VLAN 254 does not reach device X."

The engine should trace:

- service dependency
- VM/container
- host bridge
- host NIC
- cable
- switch port
- trunk membership
- upstream path
- terminating gateway/interface

And then report:

- expected chain
- observed chain
- first mismatch
- likely cause
- next best checks

### Desired output

```json
{
  "mode": "trace_failure",
  "target": "vlan:254 -> device:pve-hx310-db",
  "status": "failed",
  "first_mismatch": {
    "node": "onti-be:eth1/0/7",
    "expected": {
      "link": "up",
      "mac": "84:8B:CD:4D:BD:30",
      "vlan_254": "present"
    },
    "observed": {
      "link": "down",
      "mac": null,
      "vlan_254": "unknown"
    }
  },
  "likely_causes": [
    "missing or failed SFP module",
    "bad cable",
    "port disabled"
  ]
}
```

---

## 5.2 Mode B — Impact Preview

Purpose:

> Given a proposed infrastructure change, determine what paths, devices, and services are likely to be affected before execution.

### Example

"Remove VLAN 254 from trunk on ONTi-BE port 7."

The engine should evaluate:

* which hosts lose management
* which VMs/containers become unreachable
* which services depend on that management path
* whether alternative paths exist
* whether the change touches a critical chain
* whether the action should be blocked, staged, or approved

### Desired output

```json
{
  "mode": "impact_preview",
  "proposed_change": "remove vlan 254 from onti-be eth1/0/7",
  "risk": "high",
  "impacted": [
    "pve-hx310-db management",
    "vmbr1 vlan 254 path",
    "claude access to host-level diagnostics"
  ],
  "recommended_execution": [
    "migrate management path first",
    "validate alternate uplink",
    "run pre-checks before modifying trunk"
  ],
  "safe_to_apply": false
}
```

---

## 6. Design Principles

### 6.1 Planner first, UI second

The most important artifact is not the canvas.
The most important artifact is the **model and reasoning layer**.

### 6.2 Intent first, observation second

The system must know:

* what should exist
* what is allowed
* what is critical
* what depends on what

Only then can live observations be compared meaningfully.

### 6.3 No hidden assumptions

If a path matters, it must be modeled explicitly.

### 6.4 AI must inspect before acting

The AI must not jump from "issue found" to "fix applied."

Required flow:

1. identify target path
2. trace current path
3. preview impact of proposed change
4. present risk
5. apply only when allowed
6. verify after execution

### 6.5 Use mature tools where possible

This project should not duplicate the responsibilities of:

* Git-backed docs
* Docusaurus/MkDocs-style publishing
* NetBox/Ralph-style infra inventory

It should focus on the VOS-specific layer:

> **path intent + path diagnostics + change impact + AI execution guardrails**

---

## 7. System Architecture

## 7.1 High-level architecture

```text
┌────────────────────────────────────────────────────┐
│                  Human / Claude Code               │
└────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────┐
│               Planning / Diagnostics API           │
│                                                    │
│  - trace_failure()                                 │
│  - preview_change()                                │
│  - verify_path()                                   │
│  - explain_dependencies()                          │
└────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────┐
│ Intent Model│ │ Live Queries  │ │ Optional UI      │
│ JSON/YAML   │ │ MCP / APIs    │ │ Topology Canvas  │
└─────────────┘ └──────────────┘ └──────────────────┘
        │               │
        ▼               ▼
┌─────────────┐ ┌──────────────────────────────┐
│ Git Repo    │ │ switchcraft / OPNsense /     │
│ Reviewed     │ │ Proxmox / future NetBox      │
│ Versioned    │ │                              │
└─────────────┘ └──────────────────────────────┘
```

---

## 8. Core Data Model

The current topology model is a good starting point, but it needs to expand beyond devices/cables/VLANs.

## 8.1 Required object classes

### Devices

Physical or virtual things that host interfaces, services, or child objects.

### Interfaces

Ports, NICs, bridges, VLAN subinterfaces, logical uplinks.

### Paths

Named chains that represent end-to-end connectivity or operational reachability.

### Dependencies

Relationships that explain what relies on what.

### Constraints

Rules that must remain true.

### Capabilities

What actions are safe, unsafe, or blocked for a given object.

### Observations

What live systems currently report.

---

## 8.2 Example model shape

```json
{
  "meta": {
    "name": "VOS PathMap",
    "version": "2.0",
    "updated": "2026-04-07T12:00:00Z"
  },
  "devices": {},
  "interfaces": {},
  "paths": {},
  "dependencies": [],
  "constraints": [],
  "capabilities": {},
  "observations": {}
}
```

---

## 8.3 New first-class entities

### Path

A path is not just a cable. It is an end-to-end operational chain.

Examples:

* `mgmt-vlan-254-to-hx310-db`
* `internet-edge-opnsense-to-vlan25`
* `wiki-db-path`
* `proxmox-storage-reachability`

Example:

```json
{
  "paths": {
    "mgmt-vlan-254-to-hx310-db": {
      "kind": "management",
      "criticality": "high",
      "segments": [
        "opnsense:vlan254",
        "onti-be:eth1/0/1",
        "onti-be:eth1/0/7",
        "pve-hx310-db:nic1",
        "pve-hx310-db:vmbr1"
      ],
      "required_conditions": [
        "vlan 254 tagged on trunk ports",
        "link up on all physical segments",
        "expected neighbor mac observed on edge ports"
      ]
    }
  }
}
```

### Dependency

```json
{
  "source": "service:wiki",
  "depends_on": "path:mgmt-vlan-254-to-hx310-db",
  "reason": "host management and diagnostics path"
}
```

### Constraint

```json
{
  "target": "onti-be:eth1/0/7",
  "rule": "must_carry_vlan",
  "value": 254,
  "severity": "critical"
}
```

### Capability

```json
{
  "target": "onti-be:eth1/0/7",
  "allowed_actions": [
    "read",
    "verify"
  ],
  "blocked_actions": [
    "remove_vlan_254"
  ],
  "override_required": true
}
```

---

## 9. API Design

## 9.1 Required endpoints

### Read model

* `GET /api/model`
* `GET /api/paths`
* `GET /api/devices`
* `GET /api/dependencies`

### Diagnostics

* `POST /api/trace`
* `POST /api/verify/path`
* `GET /api/verify/last`

### Planning

* `POST /api/preview-change`
* `POST /api/explain-impact`
* `POST /api/validate-plan`

### Optional authoring

* `POST /api/model/update`
* `POST /api/model/import`
* `GET /api/model/export`

### Health

* `GET /api/health`

---

## 10. Claude Code Interaction Model

Claude Code should not treat the system as a drawing tool.
Claude Code should use it as a **mandatory planning oracle**.

## 10.1 Required AI workflow

Before proposing an infra change, Claude must:

1. query the relevant path(s)
2. query dependencies
3. query constraints
4. run impact preview
5. present result to human
6. only then propose execution steps

After the change, Claude must:

1. run path verification
2. compare intended vs observed state
3. record the result
4. update docs/model only if verified

## 10.2 Forbidden AI behavior

Claude should not:

* assume a VLAN path from prior memory
* infer bridge/trunk state without checking
* apply "obvious" network changes without impact preview
* rewrite intended state to match broken reality without human review

---

## 11. UI Strategy

The visual layer remains useful, but is now secondary.

## 11.1 V1 UI goals

* display paths, not only cables
* highlight critical chains
* highlight dependency fan-out
* trace from failure point to affected services
* preview affected objects before execution

## 11.2 What to deprioritize

* draggable layout perfection
* complex edge styling
* portfolio polish
* advanced D3 interactions before diagnostics are solid

---

## 12. Storage Strategy

## 12.1 Near-term

Use a Git-tracked JSON or YAML model.

Reason:

* simple
* reviewable
* diffable
* AI-readable
* compatible with local filesystem workflows

## 12.2 Mid-term

Optional integration with NetBox or similar for inventory/IPAM truth.

Reason:

* avoid reinventing full infra inventory
* keep this project focused on path logic and execution safety

---

## 13. Implementation Phases

## Phase 1 — Model and CLI diagnostics

Deliver:

* schema for devices, interfaces, paths, dependencies, constraints
* path trace engine
* change preview engine
* CLI or API only
* no canvas required

Success condition:

* given VLAN 254 + target host, system identifies first mismatch in chain
* given proposed change, system returns impacted paths and services

## Phase 2 — Live verification adapters

Deliver:

* switchcraft adapter
* OPNsense adapter
* Proxmox adapter
* normalized observations

Success condition:

* trace results use live data rather than static assumptions

## Phase 3 — Minimal web UI

Deliver:

* path-centric view
* failure trace panel
* impact preview panel
* dependency view

Success condition:

* human can diagnose or preview a change visually

## Phase 4 — Claude Code integration

Deliver:

* prompt contract / API contract
* mandatory preflight call sequence
* post-change verification workflow

Success condition:

* Claude no longer proposes ad hoc infra changes without model-backed checks

## Phase 5 — Optional inventory/docs integration

Deliver:

* sync to docs repo
* optional export for Docusaurus
* optional NetBox bridging

Success condition:

* docs reflect verified intent, not hand-maintained guesses

---

## 14. Non-Goals

This project will not, in V1:

* replace NetBox
* become a full CMDB
* manage switch configuration directly
* become a monitoring stack
* become a generic topology editor
* optimize for public portfolio visuals over operational correctness

---

## 15. Success Criteria

The counter-proposal succeeds if:

1. A broken VLAN path can be traced to a first mismatch quickly
2. A proposed change can be scored for blast radius before execution
3. Claude Code is forced into a preflight workflow instead of ad hoc fixes
4. The model captures dependencies and constraints explicitly
5. The visual layer reflects the model, rather than hiding missing logic
6. Documentation becomes a byproduct of verified state, not a separate manual artifact

---

## 16. Final Position

The original concept is strongest where it models expected state and verifies reality.
This counter-proposal keeps that strength, but changes the center of gravity.

### Original center of gravity

* topology canvas
* port rendering
* VLAN overlays
* visual verification

### New center of gravity

* path intent
* failure tracing
* impact preview
* dependency reasoning
* AI execution guardrails

The result is a tool that is more useful operationally, more valuable to Claude Code, and less likely to become another passive documentation project.

---

## 17. Recommended Working Name

Preferred names:

* **VOS-PathMap**
* **VOS-IntentGraph**
* **VOS-Preflight**
* **VOS-ChainMap**

Best fit:

> **VOS-Preflight: Intent Graph and Path Diagnostics for AI-Assisted Infrastructure Changes**
