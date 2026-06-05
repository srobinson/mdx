---
title: Helioy Bus Specification
type: projects
tags: [helioy, helioy-bus, spec, architecture, codex, runtime, warroom]
summary: Target specification for helioy-bus as a multi-runtime local agent control plane.
status: active
created: 2026-04-17
updated: 2026-04-17
project: helioy-bus
confidence: high
related: [helioy-bus-audit, helioy-bus-proposal]
---

# Helioy Bus Specification

## Purpose

`helioy-bus` is the local control plane for agent runtimes operating on the same machine and shared filesystem.

It is responsible for:

- stable agent identity
- presence and liveness
- directed and role based messaging
- warroom orchestration
- runtime aware spawning and discovery
- operational inspection and reconciliation

The system must support multiple runtimes. Claude is the incumbent runtime. Codex is the next required runtime.

## Problem

The current implementation works, but its core model is implicit.

Identity is derived differently depending on path. Warroom membership is keyed too weakly. Runtime specific behavior is spread through hooks, tmux conventions, and handler code. Messaging, orchestration, and reconciliation are mixed directly into MCP tools.

That is acceptable for a proof of concept. It is not an adequate foundation for a multi-runtime system.

## Goals

- support Claude and Codex on the same bus
- define canonical runtime independent agent identity
- model warrooms with stable membership records
- separate application logic from adapters and infrastructure
- keep deployment local and simple
- preserve current useful behaviors where they are still sound

## Non Goals

- introducing a network daemon
- distributed multi host coordination
- replacing tmux immediately
- rewriting the system from scratch

## Design Principles

1. Domain first. Runtime, tmux, shell hooks, and MCP are implementation details around a stable model.
2. Identity is explicit. Pane title and cwd may inform identity, but they do not define it.
3. Reads should be observational. Reconciliation may happen lazily, but it must be explicit in the design.
4. Runtime behavior is adapter scoped. Claude and Codex logic must not leak across the core.
5. The local deployment model remains first class. SQLite and filesystem based operation are valid choices.

## Logical Architecture

The system is divided into four layers.

### 1. Domain

Owns stable concepts and invariants.

Core entities:

- `AgentInstance`
- `AgentAddress`
- `Message`
- `Delivery`
- `Warroom`
- `WarroomMember`
- `AgentRole`
- `RuntimeKind`

### 2. Application

Owns use cases and orchestration of domain operations.

Required services:

- `AgentRegistryService`
- `IdentityService`
- `MessageService`
- `WarroomService`
- `RuntimeCatalogService`
- `ReconciliationService`

### 3. Infrastructure

Owns side effects and persistence.

Required adapters:

- `SqliteRegistryRepository`
- `MessageStore`
- `TmuxGateway`
- `PluginCatalog`
- `ClaudeRuntimeAdapter`
- `CodexRuntimeAdapter`

### 4. Adapters

Owns external entrypoints.

Examples:

- MCP servers
- CLI
- shell hooks
- development proxy

## Core Data Model

## Agent Instance

An `AgentInstance` represents one live or recently live runtime process known to the bus.

Required fields:

- `agent_instance_id`
- `runtime`
- `repo`
- `role`
- `cwd`
- `session_id`
- `tmux_target`
- `pane_id`
- `pid`
- `registered_at`
- `last_seen`
- `status`
- `metadata`

Notes:

- `agent_instance_id` is the primary identifier.
- `tmux_target` is an attribute, not the identity.
- `role` may be `general`.
- `runtime` is at minimum `claude` or `codex`.

## Agent Address

An `AgentAddress` is a human meaningful address that can be used in messaging or display.

It may be derived from:

- repo
- role
- runtime
- tmux placement

It is not the primary key.

## Warroom

A `Warroom` represents desired team composition and layout.

Required fields:

- `warroom_id`
- `cwd`
- `layout`
- `status`
- `created_at`
- `runtime_policy`
- `metadata`

## Warroom Member

A `WarroomMember` represents one desired or observed seat in a warroom.

Required fields:

- `warroom_member_id`
- `warroom_id`
- `spawn_order`
- `desired_runtime`
- `desired_role`
- `desired_repo`
- `state`
- `agent_instance_id`
- `tmux_target`
- `pane_id`
- `created_at`
- `updated_at`

Invariants:

- membership is never keyed by role alone
- duplicate roles are valid
- repo mode is just multiple members with `desired_role = general`

## Message

A `Message` represents one logical communication event.

Required fields:

- `message_id`
- `from_agent_instance_id`
- `reply_to`
- `topic`
- `content`
- `created_at`
- `metadata`

## Delivery

A `Delivery` represents a message addressed to one recipient.

Required fields:

- `delivery_id`
- `message_id`
- `to_agent_instance_id`
- `delivery_state`
- `delivered_at`
- `read_at`
- `archived_at`
- `transport_metadata`

This separates logical message creation from recipient specific state.

## Identity Rules

Identity must resolve through a single canonical algorithm.

### Canonical Rule

Registration creates or confirms `agent_instance_id`.

All later calls that need self identity must resolve back to that same instance id through the registered runtime adapter and persisted registration state.

### Prohibited Pattern

It is invalid for:

- hook registration
- `register_agent()`
- `_self_agent_id()`
- tmux title parsing

to generate different primary identifiers for the same live process.

### Allowed Inputs To Identity Resolution

- runtime provided session metadata
- process id mapping
- explicitly injected runtime environment
- tmux metadata as supporting context

### Disallowed As Sole Source Of Truth

- basename of cwd
- pane title alone
- tmux target alone

## Runtime Adapter Contract

Each runtime adapter must implement:

- `runtime_kind()`
- `launch_command(spec)`
- `resolve_self_identity(context)`
- `register_startup(context)`
- `register_shutdown(context)`
- `capture_usage(context)`
- `describe_capabilities()`

### Claude Adapter

Owns:

- Claude launch command generation
- Claude hook conventions
- Claude token capture integration
- Claude specific metadata parsing

### Codex Adapter

Owns:

- Codex launch command generation
- Codex session integration
- Codex usage capture or equivalent metadata
- Codex specific identity resolution

The Codex adapter must be implemented without assuming Claude pane title or hook behavior.

## Tmux Gateway Contract

`TmuxGateway` is the only layer allowed to execute tmux subprocesses.

Required operations:

- `pane_exists(target)`
- `send_nudge(target, payload)`
- `spawn_window(spec)`
- `spawn_pane(spec)`
- `kill_window(target)`
- `select_layout(target, layout)`
- `set_pane_title(target, title)`
- `get_session_name()`
- `get_pane_metadata(target)`

No application service or MCP handler may call `subprocess.run(["tmux", ...])` directly.

## Message Store Contract

The system may keep filesystem inboxes in the short term, but the storage must be abstracted.

Required operations:

- `create_message(message, recipients)`
- `list_unread(agent_instance_id, topic=None)`
- `mark_read(delivery_ids)`
- `archive(delivery_ids)`
- `prune_retention()`

If filesystem mailboxes remain in v1 of the refactor, they must satisfy this interface.

## Reconciliation

Reconciliation is an explicit service responsibility.

The system must compare:

- registered agent instances
- runtime observed instances
- tmux observed panes
- warroom desired members
- message delivery state

`status` operations are read oriented views over current state.

Repair logic belongs in reconciliation routines, not in ad hoc mutations hidden inside ordinary reads.

## Persistence

SQLite remains the default state store.

### Required Schema Direction

At minimum the system needs durable tables for:

- `agent_instances`
- `warrooms`
- `warroom_members`
- `messages`
- `deliveries`
- `runtime_capabilities` or cached discovery state if persisted

### Migration Requirement

Schema changes must move to explicit versioned migrations.

The bootstrap pattern of best effort `ALTER TABLE` calls on open is not sufficient as the model grows.

## MCP Tool Surface

The MCP surface should remain thin.

Expected bus tools:

- register
- unregister
- whoami
- list agents
- send message
- get messages
- heartbeat

Expected warroom tools:

- discover runtimes or agent types
- spawn warroom
- spawn repo warroom
- inspect status
- add member
- remove member
- kill warroom
- manage presets

Handlers should delegate immediately into application services.

## Hook Strategy

Shell hooks remain acceptable as adapters, but they must become thin.

They should:

- collect runtime context
- invoke shared Python entrypoints or shared libraries
- avoid embedding duplicated business logic

The hook layer must not be a second independent implementation of registration, liveness, and messaging behavior.

## Testing Requirements

The target test strategy has four layers.

### 1. Domain and Service Tests

Pure unit tests for invariants and service logic.

### 2. Adapter Tests

Focused tests for:

- tmux gateway behavior
- runtime adapters
- filesystem message store if retained

### 3. Hook Contract Tests

Real shell execution against temp state for:

- register
- unread mail surfacing
- token capture
- unregister

### 4. End To End Smoke Path

At minimum:

1. start runtime registration
2. send a message
3. surface unread context
4. read and archive message
5. capture runtime usage
6. unregister cleanly

This path must run in CI.

## Migration Plan

### Phase 1

Extract interfaces and stabilize the data model.

- create config object
- create services
- create tmux gateway
- create identity service
- redesign warroom member schema

### Phase 2

Introduce runtime adapters.

- implement Claude adapter
- design and implement Codex adapter
- move runtime specific assumptions out of handlers

### Phase 3

Move reconciliation and testing to explicit boundaries.

- reduce mutation in read flows
- add hook contract tests
- add adapter tests
- add smoke coverage

### Phase 4

Cut over MCP and CLI entrypoints to the new services completely.

## Success Criteria

The refactor is successful when:

- Claude and Codex can both register on the same bus
- self identity resolution is canonical across all code paths
- warrooms can represent duplicate roles and repo mode correctly
- runtime specific behavior is isolated to adapters
- status inspection no longer depends on hidden mutations
- default CI covers the operational shell boundary

## Bottom Line

`helioy-bus` should become a multi-runtime local agent control plane with explicit identity, explicit membership, explicit runtime boundaries, and thin adapters.

That is the architectural level required to support Codex cleanly without turning the codebase into a Claude specific system with Codex exceptions bolted onto the side.
