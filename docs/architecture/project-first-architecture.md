# Project-First Architecture

## Purpose

VOS Workbench is designed as a **project operating environment** rather than a chat application.

The system should not be built as:

`Web UI -> AI model -> tools`

It should be built as:

`Project Runtime -> State / Events / Policies / Tools / Memory -> Multiple Clients`

In this model:

- the **project** is the root object;
- AI is a **worker** rather than the owner of the application;
- the **headless backend** is primary;
- the **web UI** is only one client;
- terminals and desktop clients are first-class;
- all meaningful activity is captured as events.

## Core principles

### 1. Project is the primary unit of state
A project should outlive sessions, chats, models, and clients.

### 2. Chat is short-term, VOS is long-term
A chat is temporary working context.
VOS stores reviewed and durable knowledge.

### 3. Filesystem remains visible truth
Docs, manifests, scripts, and reports should remain real files in Git.
Databases support indexing and runtime state, but should not hide the truth.

### 4. Event-driven core
Every important action should become an event:

- prompt submitted
- context built
- tool requested
- policy denied
- command started
- command finished
- file changed
- memory promoted
- task completed

### 5. Policy before action
Permissions, scopes, and safety checks should be applied before execution, not after the AI has already improvised.

### 6. Modular growth
The tree structure should support future branches without forcing dead branches into existence now.

## Architectural layers

### Project Runtime
Central daemon that owns project state, task graph, event stream, module activation, and policy evaluation.

### Context Engine
Builds relevant context for an AI worker from files, memory, tasks, resource state, and prior summaries.

### Execution Engine
Runs shell commands, file operations, remote execution, API calls, and MCP tools in a controlled way.

### Memory Engine
Handles short-term session memory, working memory, curated VOS memory, and historical archive.

### Policy Engine
Determines which tools, actions, targets, and configuration changes are permitted.

### Client Layer
TUI, desktop UI, web UI, and API consumers all sit on top of the same backend.

## High-level flow

```text
[User or automation]
        |
        v
[Project Runtime]
   |        |        |
   v        v        v
[Context] [Policy] [Resources]
        \    |    /
         \   |   /
          [AI Worker]
               |
               v
       [Plan / Tool Request]
               |
               v
       [Execution Engine]
               |
               v
   [Artifacts + Events + Logs + UI updates]
```

## What the first implementation should include

The first implementation should avoid platform bloat and focus on:

- project manifest loading;
- node tree basics;
- event log;
- simple task model;
- shell execution;
- policy gates;
- one TUI client;
- minimal API.

## What should not be built yet

- full plugin marketplace;
- heavy desktop shell;
- broad multi-agent orchestration;
- fancy dashboards;
- autonomous self-modification without strict policy.

## Summary

The system should be a **small, headless, project-centered trunk** that can grow without structural surgery.
