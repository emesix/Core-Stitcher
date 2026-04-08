# Memory Model

## Purpose

VOS Workbench separates temporary conversation state from long-term project knowledge.

This avoids turning every chat into permanent truth.

## Core rule

> A chat is not memory yet.
> It becomes memory only after extraction, validation, and placement into VOS.

## Layers

### 1. Session Memory
Short-lived context for the current conversation or execution session.

Examples:
- recent prompts
- current discussion
- immediate command results
- short-lived assumptions

### 2. Working Memory
Temporary task state that may survive across a small number of sessions.

Examples:
- current plan draft
- blockers
- selected files
- target host list
- pending actions

### 3. VOS Memory
Curated long-term project knowledge.

Examples:
- architecture decisions
- host roles
- naming conventions
- lessons learned
- validated procedures
- stable preferences
- trusted mappings

### 4. Historical Archive
Past sessions, logs, reports, decisions, and event history.

This should be searchable but clearly marked as historical, not current truth.

## Promotion pipeline

```text
Chat / execution results
          |
          v
   Candidate extraction
          |
          v
    Classification step
   /         |          \
  /          |           \
ignore   working mem   candidate for VOS
                         |
                         v
                  human or policy review
                         |
                         v
                     promote to VOS
```

## What belongs in VOS

- confirmed facts
- approved decisions
- validated procedures
- reusable project knowledge
- long-term operational rules

## What does not belong in VOS by default

- random brainstorming
- emotional phrasing
- temporary debugging noise
- one-off guesses
- stale speculation

## Metadata that memory entries should carry

Each memory item should ideally store:

- id
- type
- source
- confidence
- status
- created_at
- updated_at
- scope
- verification_state
- related_files
- related_tasks

## Verification states

Suggested states:

- `draft`
- `derived`
- `needs_review`
- `approved`
- `deprecated`
- `superseded`

## Why this matters

This model keeps:

- chats fast;
- long-term knowledge clean;
- context windows smaller;
- system behavior more predictable;
- project knowledge portable across model changes.

## Summary

**Chats produce candidate knowledge; VOS stores approved knowledge.**
