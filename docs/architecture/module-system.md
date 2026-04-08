# Module System

## Purpose

VOS Workbench should be modular enough to grow without redesigning the trunk.

That does **not** mean every possible module should exist from day one.

## Core rule

> Build the biology of the tree, not every branch.

## Module categories

### Client modules
- TUI
- desktop
- web
- editor integrations

### Runtime modules
- task manager
- event bus
- context engine
- memory engine
- policy engine
- resource registry

### Execution modules
- local shell
- SSH
- Git
- HTTP/API
- MCP

### AI modules
- Claude adapter
- OpenAI adapter
- local LLM adapter
- summarizer
- embeddings

### Storage modules
- Postgres state store
- file indexer
- vector backend
- event sink

## Module contract

Each module should declare:

- module id
- version
- capabilities
- config schema
- dependencies
- required permissions
- subscribed events
- emitted events
- health status

## Activation model

A module should move through states such as:

- inactive
- available
- active
- degraded

A branch in the tree should appear only when:

- the module is active;
- a resource exists;
- or the branch is explicitly pinned by the user.

## Example

An SSH module may provide:

- remote command execution
- remote file read/write
- remote terminal nodes

But none of those branches should appear until at least one SSH resource is registered.

## Why this matters

This keeps the system:

- flexible;
- sparse by default;
- easier to understand;
- less cluttered;
- less likely to become another config swamp.

## Summary

The module system should allow broad structural growth while keeping the default installation lean and honest.
