# Self-Configuration Model

## Purpose

VOS Workbench should be able to inspect and adjust its own project-level configuration through declared interfaces.

This does **not** mean uncontrolled self-modification.
It means controlled reconciliation through APIs and MCP tools under policy control.

## Core idea

Self-configuration should mean that the system can:

- inspect current state;
- compare actual state against desired state;
- propose changes;
- apply safe changes automatically when allowed;
- require approval for risky changes;
- record diffs, audit events, and rollback points.

## Configuration levels

### Level A: Bootstrap config
Rarely changed, usually file-based.

Examples:
- database connections
- core secrets references
- identity provider
- base policy roots
- runtime paths

### Level B: Project config
Frequently changed and should be API/MCP addressable.

Examples:
- enabled modules
- allowed hosts
- model bindings
- active resources
- memory settings
- default client layout
- policy settings per project

### Level C: Session/runtime config
Ephemeral and freely adjustable.

Examples:
- active model
- context budget
- selected terminal
- current debug level
- focused task id

## Desired-state approach

The project should define desired state in structured config.
A reconciler compares desired state with actual state.

Possible outcomes:

- no change needed;
- safe automatic change;
- change requiring approval;
- rejected by policy.

## Example flow

```text
[Request config change]
        |
        v
[Inspect actual state]
        |
        v
[Compare with desired state]
        |
        v
[Policy + validation]
   |         |         |
   |         |         |
   v         v         v
 no-op   auto-apply   approval required
              \         /
               \       /
                [Reconciler]
                     |
                     v
         [Diff + event + audit + rollback]
```

## Suggested MCP/API tools

- `get_runtime_config`
- `get_project_config`
- `set_project_config`
- `diff_project_config`
- `validate_config`
- `apply_desired_state`
- `rollback_config`
- `list_resources`
- `register_resource`
- `enable_module`
- `disable_module`
- `bind_model_to_agent`
- `set_policy_rule`

## Guardrails

Every self-configuration path should support:

- dry-run mode;
- diff preview;
- plan/apply separation;
- approval workflow;
- scoped credentials;
- rollback;
- full audit logging.

## Anti-patterns

Avoid:

- hidden UI-only settings;
- direct mutation without audit;
- unscoped model-driven reconfiguration;
- config stored only in a database with no export path;
- no distinction between bootstrap, project, and runtime settings.

## Summary

The system should be able to reconfigure itself, but only through **declared, auditable, policy-controlled interfaces**.
