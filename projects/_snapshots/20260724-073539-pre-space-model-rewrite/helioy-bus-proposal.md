---
title: Helioy Bus Proposal
type: projects
tags: [helioy, helioy-bus, architecture, proposal, codex, runtime]
summary: Proposed target architecture and migration plan for helioy-bus as a multi-runtime local agent control plane.
status: active
created: 2026-04-17
updated: 2026-04-17
project: helioy-bus
confidence: high
related: [helioy-bus-audit]
---

# Helioy Bus Proposal

## Goal

Evolve `helioy-bus` from a Claude shaped proof of concept into a robust local control plane for multiple agent runtimes, starting with Claude and Codex.

This proposal assumes:

- local machine deployment remains the core model
- SQLite remains acceptable as the state store
- tmux remains an important orchestration substrate
- a rewrite is unnecessary

## Product Intent

The target system should provide:

- stable agent identity across runtimes
- presence and liveness tracking
- directed and role based messaging
- team orchestration through warrooms
- runtime aware spawning and capability discovery
- reliable operational state inspection
- a clear path to add more runtimes without rewriting the core

## Design Principle

Treat `helioy-bus` as a local agent control plane with adapters, not as a pair of MCP scripts plus hooks.

The important shift is conceptual:

- MCP is an adapter
- CLI is an adapter
- shell hooks are adapters
- tmux is infrastructure
- Claude and Codex are runtimes
- the domain model sits above all of them

## Proposed Architecture

### Domain Layer

Core types:

- `AgentInstance`
- `AgentRuntime`
- `AgentIdentity`
- `Message`
- `Delivery`
- `Warroom`
- `WarroomMember`
- `AgentType` or `Role`

These types should be runtime agnostic and independent from tmux.

### Application Layer

Services:

- `AgentRegistryService`
- `IdentityService`
- `MessageService`
- `WarroomService`
- `RuntimeCatalogService`
- `ReconciliationService`

This layer owns use cases and business rules.

### Infrastructure Layer

Ports and adapters:

- `SqliteRegistryRepository`
- `SqliteMessageRepository` or `FilesystemMessageStore`
- `TmuxGateway`
- `PluginCatalog`
- `ClaudeRuntimeAdapter`
- `CodexRuntimeAdapter`
- `HookBridge`

This layer owns subprocesses, files, SQL, and runtime specific mechanics.

### Adapter Layer

Entry surfaces:

- `bus_server.py`
- `warroom_server.py`
- `warroom_cli.py`
- shell hooks
- optional proxy

These should become thin translation layers.

## Identity Proposal

Identity needs to be explicit and canonical.

### New Model

Define two related concepts:

- `agent_instance_id`: stable primary identifier for a running agent instance
- `agent_address`: optional human meaningful address used in messaging and display

Recommended fields for an agent instance:

- `agent_instance_id`
- `runtime` such as `claude` or `codex`
- `repo`
- `role`
- `cwd`
- `tmux_target`
- `session_id`
- `process_id`
- `registered_at`
- `last_seen`
- `metadata`

Pane title can still exist, but it becomes a projection of identity rather than the source of truth.

## Warroom Proposal

Warrooms should store desired topology explicitly.

### New Model

`warrooms`

- `warroom_id`
- `layout`
- `cwd`
- `runtime_policy`
- `created_at`
- `status`

`warroom_members`

- `warroom_member_id`
- `warroom_id`
- `desired_role`
- `desired_runtime`
- `desired_repo`
- `spawn_order`
- `agent_instance_id` nullable until registered
- `tmux_target` nullable
- `pane_id` nullable
- `state`

This fixes the current inability to represent duplicate roles or multiple general repo mode panes.

## Messaging Proposal

There are two viable directions.

### Option A

Keep filesystem inboxes, but hide them behind a `MessageStore` interface. This is lower risk and lower effort.

### Option B

Move delivery tracking fully into SQLite with explicit delivery state. This is architecturally cleaner and gives better observability and reconciliation.

My recommendation is phased:

1. abstract the message store first
2. keep filesystem delivery initially
3. move to SQLite delivery if operational complexity grows

## Runtime Adapter Proposal

This is the key to Claude plus Codex support.

Each runtime adapter should own:

- process launch command construction
- hook integration model
- identity bootstrap behavior
- token capture behavior
- runtime capability metadata
- runtime specific display conventions

### Claude Runtime Adapter

Current Claude specific assumptions move here:

- `claude --agent ...`
- Claude hook lifecycle
- Claude pane title behavior
- Claude token capture handling

### Codex Runtime Adapter

Codex support should be implemented as a sibling adapter, not as Claude compatibility hacks spread through the codebase.

Questions the adapter should answer:

- how is a Codex agent launched
- how is its identity declared
- what lifecycle hooks exist, if any
- how are usage metrics captured
- what environment markers distinguish it from Claude

## Reconciliation Proposal

Today reconciliation is hidden inside reads.

That should change.

Create an explicit reconciliation service that compares:

- desired state in SQLite
- observed tmux state
- observed registered agent state
- delivery state if tracked

Then expose:

- `status` as read only inspection
- `reconcile` as explicit repair logic

Lazy cleanup can still exist, but it should be an implementation detail of a service, not a surprise side effect of a read tool.

## Testing Proposal

### Keep

- current Python unit coverage around registry and routing logic
- shell parsing tests

### Add

1. hook contract tests
2. tmux gateway adapter tests
3. runtime adapter tests
4. one end to end smoke path

The highest value smoke path is:

- register through hook or runtime adapter
- send a message
- surface unread state
- drain messages
- capture usage
- unregister

## Migration Plan

### Phase 1

Stabilize the model without changing deployment shape.

- add explicit config object
- extract service layer
- extract tmux gateway
- define canonical identity model
- fix warroom member schema

### Phase 2

Extract runtime specific behavior.

- create `ClaudeRuntimeAdapter`
- move hook assumptions behind adapter interfaces
- define Codex runtime contract

### Phase 3

Improve reconciliation and testing.

- remove state mutation from read paths where possible
- add hook contract test suite
- add tmux and runtime adapter tests
- add end to end smoke coverage

### Phase 4

Add Codex support.

- implement Codex registration path
- implement Codex spawn path
- ensure Claude and Codex agents can coexist on the same bus
- validate cross runtime messaging and warroom composition

## Immediate Tactical Changes

If work starts now, the first concrete tasks should be:

1. redesign `warroom_members`
2. define canonical agent identity and stop deriving different ids in different paths
3. extract `TmuxGateway`
4. extract `IdentityService`
5. add contract tests for hooks

These are the highest leverage changes because they reduce uncertainty before Codex support begins.

## Bottom Line

The right move is not to harden the current Claude specific implementation by accretion.

The right move is to lift the codebase one level up conceptually:

- from transport handlers to services
- from pane titles to explicit identity
- from Claude assumptions to runtime adapters
- from ad hoc orchestration to a proper local control plane

That gives `helioy-bus` a clean path to support Codex without turning the code into a stack of runtime specific exceptions.
