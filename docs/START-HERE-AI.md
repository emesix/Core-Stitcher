# Start Here — VOS-Ruggensgraat

## What this repo is

A **topology domain capability pack** (Layer B). It provides network topology verification, VLAN tracing, and impact preview as capabilities the VOS Agent Backbone can invoke.

## What this repo is NOT

- Not the top-level product. The product is **Project Explorer / Agent Core**.
- Not a standalone application. It is a set of domain modules consumed by the orchestrator.
- Not the place to add AI orchestration, task routing, or executor logic.

## Guardrails

1. Changes here should improve **topology domain capabilities** — not orchestration logic.
2. All modules expose verbs via `contractkit` protocols. No direct imports between domain packs.
3. Do not add LLM/AI provider calls here. Inference is the executor layer's job.
4. This repo proves the **module composition pattern** — keep it clean for that purpose.
5. If you're about to add a feature that isn't topology-specific, it probably belongs in the backbone.

## North Star

Read before making architectural decisions: `emesix/vos-docs/docs/architecture/VOS-NORTH-STAR.md`

Full architecture spec: `emesix/vos-docs/docs/architecture/VOS-ECOSYSTEM-REFRAME.md`
