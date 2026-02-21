# Nancyr V2: Repo Build Breakdown

Date: 2026-03-11
Status: Implementation planning
Author: Codex

## Purpose

This document answers four practical questions:

1. what should live in `helioy-bus`
2. what should live in `nancyr`
3. what should remain documentation-only for now
4. what the first implementation tickets should be

It assumes the V1 runtime and schema docs are the source design inputs:

- [helioy-v2-nancyr-v1-runtime-spec.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-runtime-spec.md)
- [helioy-v2-nancyr-v1-schema-pack.md](/Users/alphab/.mdx/design/helioy-v2-nancyr-v1-schema-pack.md)

## Repo Responsibilities

### `helioy-bus`

`helioy-bus` should remain the communication substrate.

It should own:

- agent or actor registration
- identity resolution
- inbox delivery
- role-based addressing
- message persistence
- acknowledgement plumbing
- warroom spawning
- lightweight observability of message flow

It should not own:

- job planning
- scope ownership logic
- deliverable semantics
- review policy
- retrospection
- protocol improvement logic

In short:

- `helioy-bus` moves messages
- it does not decide what the work means

### `nancyr`

`nancyr` should own the collaborative runtime.

It should own:

- core entity model
- job lifecycle
- scope definitions
- execution context lifecycle
- coordinator protocol
- specialist task assignment
- deliverable lifecycle
- checkpoints
- review and sign-off
- correction event capture
- ledger append model
- retrospection

It may consume:

- `helioy-bus` for transport
- later `fmm`, `mdcontext`, and `am` for context enrichment

In short:

- `nancyr` decides what collaboration is happening and how it improves

### Docs-Only for Now

These should remain conceptual until the first runtime wedge is working:

- deep AM integration in the critical path
- automatic process crystallization
- dynamic role invention
- topology self-optimization
- advanced authority adaptation heuristics
- enterprise-wide cross-workspace learning
- heavy semantic or geometric memory claims in the runtime core

These are valid future directions, but they are not V1 blockers.

## Proposed Code Boundaries

### `helioy-bus` additions

Add or tighten:

- message envelope validation
- acknowledgement support
- structured payload conventions
- actor profile or capability metadata if useful

Prefer not to add:

- runtime entity storage
- workflow logic
- review state

### `nancyr` core modules

Recommended top-level modules:

```text
nancyr/
  src/
    entities/
    ledger/
    coordinator/
    review/
    retrospection/
    bus_adapter/
    storage/
```

Suggested responsibilities:

- `entities`
  typed models for Actor, Job, Scope, ExecutionContext, Deliverable, Checkpoint, CorrectionEvent

- `ledger`
  append-only event model, event validation, event queries

- `coordinator`
  planning, assignment, status handling, block resolution, final synthesis orchestration

- `review`
  review requests, review outcomes, sign-off handling

- `retrospection`
  job-close summaries and protocol improvement proposals

- `bus_adapter`
  interface between `nancyr` entities/events and `helioy-bus` messages

- `storage`
  relational persistence and repositories

## Suggested Integration Pattern

The cleanest V1 integration pattern is:

1. `helioy-bus` remains an external transport service
2. `nancyr` uses a bus adapter to publish and consume structured messages
3. `nancyr` maintains its own entity and ledger store
4. warroom-spawned actors register on the bus
5. coordinator logic in `nancyr` binds bus actors to runtime actors

This avoids overloading the bus with application semantics.

## First Ticket Set

These are the first implementation tickets I would create.

### Ticket 1: Define Bus Message Contract

Repo:

- `helioy-bus`

Goal:

- introduce the V1 message envelope and payload validation rules

Deliverables:

- message schema docs in repo
- validation helpers
- tests for valid and invalid envelopes

Done when:

- all messages can be validated against the canonical shape

### Ticket 2: Add Ack Semantics to Bus

Repo:

- `helioy-bus`

Goal:

- support `requires_ack` and acknowledgement records cleanly

Deliverables:

- ack write path
- ack query path
- message status visibility

Done when:

- coordinator can know whether critical directives were acknowledged

### Ticket 3: Create Nancyr Core Entity Types

Repo:

- `nancyr`

Goal:

- define V1 entities exactly once in code

Entities:

- Actor
- Job
- Scope
- ExecutionContext
- Deliverable
- Checkpoint
- CorrectionEvent
- LedgerEvent

Done when:

- codebase has canonical typed models with validation

### Ticket 4: Implement Nancyr Storage Schema

Repo:

- `nancyr`

Goal:

- create relational schema from the schema pack

Deliverables:

- migrations
- repository interfaces
- basic CRUD for core entities

Done when:

- entities can be created and queried reliably

### Ticket 5: Implement Ledger Append Path

Repo:

- `nancyr`

Goal:

- every important state change emits an append-only ledger event

Deliverables:

- event appender
- sequence allocation strategy
- basic event query helpers

Done when:

- entity lifecycle changes can be observed as ledger events

### Ticket 6: Build Coordinator Planning Flow

Repo:

- `nancyr`

Goal:

- coordinator can create a job plan, scopes, and actor assignments

Deliverables:

- plan creation API
- scope assignment logic
- assignment message generation through bus adapter

Done when:

- one scoped job can be planned and assigned to 2-4 actors

### Ticket 7: Add Execution Context Lifecycle

Repo:

- `nancyr`

Goal:

- track concrete work attempts per actor and scope

Deliverables:

- create/start/block/complete transitions
- lifecycle ledger events
- basic status surface

Done when:

- coordinator can see active and blocked execution contexts

### Ticket 8: Add Deliverable Submission Flow

Repo:

- `nancyr`

Goal:

- actors can submit deliverables tied to execution contexts

Deliverables:

- deliverable creation path
- submit-for-review transition
- provenance enforcement

Done when:

- meaningful work products exist as first-class runtime objects

### Ticket 9: Implement Review Queue and Outcomes

Repo:

- `nancyr`

Goal:

- support review requests and sign-off

Deliverables:

- review request entity or deliverable metadata
- review outcome model
- approval and rejection events

Done when:

- no major deliverable can be finalized without review

### Ticket 10: Add Correction Event Capture

Repo:

- `nancyr`

Goal:

- record how humans or authorized actors changed outputs

Deliverables:

- correction capture API
- target validation
- rationale and pattern type support

Done when:

- correction intelligence is durably stored and queryable

### Ticket 11: Add Retrospective Generation

Repo:

- `nancyr`

Goal:

- every completed job produces a retrospective deliverable

Deliverables:

- retrospective template
- structured output fields
- protocol improvement proposal field

Done when:

- job closeout creates durable learning artifacts

### Ticket 12: Warroom Integration Pass

Repos:

- `helioy-bus`
- `nancyr`

Goal:

- connect real warroom actors to the runtime model

Deliverables:

- actor identity mapping
- coordinator-to-bus routing
- inbox-driven status and review loop

Done when:

- a live warroom can execute one end-to-end scoped job through `nancyr`

## Execution Order

Build in this order:

1. bus schema
2. bus ack
3. nancyr entities
4. nancyr storage
5. ledger append path
6. coordinator planning
7. execution context lifecycle
8. deliverable submission
9. review flow
10. correction events
11. retrospectives
12. live warroom integration

This order matters because:

- transport comes first
- runtime model comes second
- quality control and learning come after basic execution works

## What to Measure During Build

Do not wait until “later” to define success.

Track:

- assignments sent
- assignments acknowledged
- execution contexts created
- blocked contexts
- deliverables submitted
- review turnaround time
- rejections per deliverable
- correction events per job
- retrospective generation rate

These are the first hard signals that the runtime is either real or theatrical.

## Recommended First Demo

The first honest demo should be:

- one scoped job
- one coordinator
- two specialists
- one reviewer
- one human checkpoint
- one retrospective

Example:

- coordinator splits a small feature task
- backend and frontend actors work on separate scopes
- reviewer catches one issue
- human records one correction
- job closes with final synthesis and retrospective

If that works cleanly, the architecture has legs.

## Final Guidance

The key discipline is:

- let `helioy-bus` stay small and sharp
- let `nancyr` become the runtime of meaning and coordination
- keep AM, `fmm`, and `mdcontext` outside the critical path until the runtime wedge proves itself

That is the fastest route to a believable system.
