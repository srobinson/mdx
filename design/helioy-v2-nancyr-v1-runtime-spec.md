# Nancyr V2: V1 Runtime Specification

Date: 2026-03-11
Status: Build spec
Author: Codex

## Purpose

This document defines the first buildable version of `nancyr`.

It is not the full long-term vision.

It is the smallest runtime that can credibly prove the thesis that:

**a coordinated small team of specialized actors can outperform a single undifferentiated agent on scoped work, while producing a durable ledger of collaboration and learning**

This spec translates the broader Helioy and HumanWork direction into:

- concrete entities
- canonical event types
- bus message schema
- coordinator protocol
- first product surfaces

## Scope of V1

V1 supports:

- one Org
- one or more Workspaces
- one Job at a time per coordinator
- 2-4 specialist machine actors plus optional human reviewer
- explicit role assignment
- explicit scope ownership
- structured bus communication
- deliverable production
- review and sign-off
- retrospection
- ledger-backed observability

V1 explicitly does **not** require:

- dynamic role invention
- automatic topology search
- deep AM integration in the critical path
- full context compiler integration
- large-scale autonomous societies

## Product Promise

V1 promises:

- clear division of labor
- explicit handoffs
- durable review records
- auditable collaboration state
- a measurable basis for future self-improvement

It does not promise:

- generalized autonomy
- total workflow automation
- self-evolving agent identity

## System Model

`nancyr` sits above:

- `helioy-bus` for identity and messaging
- `fmm` / `mdcontext` / `am` as optional context services

and is responsible for:

- actor coordination
- job lifecycle
- workflow guidance
- review and approval flow
- ledger emission
- retrospective generation

## Core Entities

### Org

Top-level ownership and policy boundary.

```yaml
org:
  id: string
  name: string
  created_at: timestamp
```

Responsibilities:

- owns workspaces
- owns members and policies
- owns cross-workspace learning in later phases

V1 note:

- Org exists, but V1 can implement only minimal policy.

### Workspace

Bounded context where work occurs.

```yaml
workspace:
  id: string
  org_id: string
  name: string
  purpose: string?
  created_at: timestamp
  status: enum(active, paused, archived)
```

Responsibilities:

- execution boundary
- cost attribution boundary
- deliverable namespace
- ledger namespace

V1 rule:

- no implicit state sharing across workspaces

### Role

Stable responsibility definition.

```yaml
role:
  name: string
  mandate: [string]
  constraints: [string]
```

V1 default role set:

- `coordinator`
- `frontend-engineer`
- `backend-engineer`
- `ux-designer`
- `reviewer`

### Actor

First-class labor primitive.

```yaml
actor:
  id: string
  type: enum(human, machine)
  role: string
  workspace_id: string
  capabilities: [string]
  authority_level: enum(instructional, consultative, supervisory, exploratory)
  cost_model:
    unit: enum(hour, token, fixed)
    rate: number
  runtime_ref: string?
  status: enum(idle, assigned, active, blocked, awaiting_review, completed, offline)
```

Important:

- `Agent` is not the primary primitive in V1
- machine agents are one subtype of `Actor`
- humans can also be addressed and participate in checkpoints and corrections

### Job

Human-meaningful coordination envelope.

```yaml
job:
  id: string
  workspace_id: string
  title: string
  description: string?
  created_at: timestamp
  created_by: actor_id
  workflow_id: string?
  status: enum(created, planning, active, awaiting_review, blocked, completed, abandoned)
```

Responsibilities:

- stable handle for a piece of work
- groups execution contexts, messages, deliverables, and reviews

### Scope

Explicit unit of ownership and mutation.

```yaml
scope:
  id: string
  workspace_id: string
  label: string
  kind: enum(code, doc, design, analysis, decision, mixed)
  references: [string]
```

V1 hard rule:

- no two active execution contexts may own the same mutable scope without explicit conflict resolution

### Execution Context

Concrete scoped work attempt.

```yaml
execution_context:
  id: string
  job_id: string
  workspace_id: string
  assigned_actor_id: string
  scope_ids: [string]
  workflow_phase: string?
  authority_level: enum(instructional, consultative, supervisory, exploratory)
  created_at: timestamp
  status: enum(created, active, blocked, awaiting_review, paused, completed, terminated)
```

Responsibilities:

- binds actor to a specific scope of work
- carries runtime state for an attempt
- emits durable ledger events

### Workflow

Reusable coordination guidance.

```yaml
workflow:
  id: string
  name: string
  version: string
  roles: [string]
  phases: [string]
  checkpoint_types: [string]
```

V1 rule:

- workflow guides
- workflow does not execute

### Deliverable

Immutable work product.

```yaml
deliverable:
  id: string
  workspace_id: string
  job_id: string
  execution_context_id: string
  type: enum(code, doc, design, decision, review, retrospective, recommendation)
  title: string
  uri: string?
  metadata: object
  created_at: timestamp
  produced_by: actor_id
```

Important:

- V1 should use `deliverable` as the product-facing term
- internal implementation may still map to existing artifact concepts

### Checkpoint

Structured point of human or coordinator re-engagement.

```yaml
checkpoint:
  id: string
  job_id: string
  execution_context_id: string?
  type: enum(approval, review, decision, exit)
  requested_by: actor_id
  assigned_to: actor_id?
  prompt: string
  created_at: timestamp
  status: enum(open, satisfied, rejected, expired)
```

### Correction Event

Primary intelligence-capture primitive.

```yaml
correction_event:
  id: string
  workspace_id: string
  job_id: string
  actor_id: string
  target_id: string
  target_type: enum(deliverable, decision, review, message, workflow)
  diff_ref: string?
  rationale: string?
  pattern_type: enum(tone, structure, facts, logic, policy, scope, sequencing, style)
  magnitude: enum(minor, moderate, major, rewrite)
  created_at: timestamp
```

### Ledger Event

Canonical immutable system record.

```yaml
ledger_event:
  id: string
  workspace_id: string
  job_id: string?
  execution_context_id: string?
  actor_id: string?
  type: string
  payload: object
  created_at: timestamp
  sequence: integer
```

## Canonical Event Types

V1 should define and emit a narrow canonical set.

### Workspace Events

- `workspace.created`
- `workspace.paused`
- `workspace.archived`

### Job Events

- `job.created`
- `job.planning_started`
- `job.activated`
- `job.blocked`
- `job.awaiting_review`
- `job.completed`
- `job.abandoned`

### Actor Events

- `actor.registered`
- `actor.assigned`
- `actor.unassigned`
- `actor.blocked`
- `actor.completed`

### Execution Context Events

- `execution_context.created`
- `execution_context.started`
- `execution_context.progress_reported`
- `execution_context.blocked`
- `execution_context.paused`
- `execution_context.awaiting_review`
- `execution_context.completed`
- `execution_context.terminated`

### Deliverable Events

- `deliverable.produced`
- `deliverable.submitted_for_review`
- `deliverable.approved`
- `deliverable.rejected`
- `deliverable.promoted`

### Checkpoint Events

- `checkpoint.opened`
- `checkpoint.satisfied`
- `checkpoint.rejected`
- `checkpoint.expired`

### Correction Events

- `correction.recorded`

### Coordination Events

- `handoff.requested`
- `handoff.accepted`
- `handoff.rejected`
- `review.requested`
- `review.completed`
- `directive.sent`
- `directive.acknowledged`

### Retrospective Events

- `retrospective.generated`
- `protocol_improvement.proposed`
- `protocol_improvement.adopted`

## Bus Message Schema

`helioy-bus` remains the transport substrate.

V1 `nancyr` must define the message contract that rides on it.

### Message Envelope

```yaml
message:
  id: string
  sent_at: timestamp
  sender_actor_id: string
  recipient:
    type: enum(actor, role, coordinator, broadcast)
    value: string
  workspace_id: string
  job_id: string?
  execution_context_id: string?
  purpose: enum(assign, status, block, review, handoff, directive, decision, result, retrospective)
  urgency: enum(low, normal, high, critical)
  requires_ack: boolean
  payload: object
```

### Allowed Payload Shapes

#### Assignment

```yaml
payload:
  task_title: string
  task_description: string
  scope_ids: [string]
  expected_deliverables: [string]
  constraints: [string]
  deadline_hint: string?
```

#### Status

```yaml
payload:
  state: enum(active, blocked, awaiting_review, completed)
  summary: string
  next_action: string?
  risk: string?
  deliverable_ids: [string]
```

#### Block

```yaml
payload:
  blocker_type: enum(scope_conflict, dependency, missing_context, failed_review, technical_issue)
  summary: string
  requested_action: string
```

#### Review Request

```yaml
payload:
  deliverable_ids: [string]
  review_type: enum(technical, design, product, final)
  focus_areas: [string]
```

#### Handoff

```yaml
payload:
  from_scope_ids: [string]
  to_scope_ids: [string]
  reason: string
  required_context: [string]
  deliverable_ids: [string]
```

### Bus Rules

V1 bus rules:

- every message must reference `workspace_id`
- most coordination messages should reference `job_id`
- messages that require acknowledgement must emit `directive.acknowledged`
- free-form text is allowed inside payload fields, but not as the envelope itself

## Coordinator Protocol

The coordinator is the center of V1.

It is not a mystical planner.
It is a disciplined controller of collaborative work.

### Coordinator Responsibilities

1. Read and interpret the job
2. Decide whether parallelism is justified
3. Create scopes
4. Assign scopes to actors
5. Request and track deliverables
6. Trigger checkpoints and reviews
7. Resolve blocks or escalate
8. Produce final synthesis
9. Generate retrospective

### Coordinator Must Not

- do specialist work by default
- endlessly respawn actors
- assign overlapping mutable scopes silently
- skip review on substantial changes

### Coordinator Lifecycle

#### 1. Planning

Emits:

- `job.planning_started`
- `scope` definitions
- `actor.assigned`
- `directive.sent`

Output:

- initial plan
- execution contexts created

#### 2. Active Coordination

Receives:

- status reports
- block notices
- review outputs

Actions:

- sequence dependencies
- request revisions
- escalate to human or reviewer

#### 3. Review and Integration

Requires:

- at least one review cycle for meaningful work

Produces:

- integration summary
- final deliverable set

#### 4. Retrospection

Produces:

- retrospective deliverable
- protocol improvement proposal if applicable

## Specialist Protocol

Each specialist actor in V1 follows a narrow contract.

### Required Behavior

- accept one bounded assignment
- operate only on assigned scopes
- emit structured status updates
- raise blocks early
- submit deliverables for review

### Forbidden Behavior

- assign work to unrelated actors without coordinator involvement
- silently expand scope
- bypass review on meaningful changes
- hold exclusive hidden state

## Review Protocol

Review is mandatory in V1 for meaningful work.

### Review Types

- technical review
- design review
- product review
- final sign-off

### Review Outcomes

- approved
- approved_with_notes
- rejected

### Review Deliverable

Each review should produce a deliverable with:

- review target
- findings
- approval status
- required changes

Rejections should emit:

- `deliverable.rejected`
- `review.completed`
- optionally `correction.recorded`

## Authority Levels

V1 should support four modes.

### Instructional

- human or coordinator directs each major step

### Consultative

- actor proposes, human or coordinator selects

### Supervisory

- actor executes within bounds, human intervenes on triggers

### Exploratory

- actor and human or coordinator can iterate more freely

V1 requirement:

- every execution context has one explicit authority level

## First Product Surfaces

V1 only needs a few legible surfaces.

### 1. Warroom View

Shows:

- active actors
- roles
- assigned scopes
- job status
- unread directives
- blocks
- pending reviews

### 2. Job View

Shows:

- job plan
- assigned actors
- execution contexts
- deliverables
- checkpoints
- final outcome

### 3. Ledger View

Shows:

- canonical event stream
- filters by job, actor, event type
- correlation to deliverables and checkpoints

### 4. Review Queue

Shows:

- open review requests
- target deliverables
- assigned reviewer
- age and urgency

### 5. Retrospective View

Shows:

- what helped
- what hindered
- proposed protocol changes
- adopted improvements over time

## V1 Storage Model

Minimal persistence layers:

- relational or document store for entities
- append-only ledger store for events
- bus transport persistence from `helioy-bus`
- filesystem or object store references for deliverables

Hard rule:

- derived operational state must be rebuildable from the ledger plus durable entity state

## Success Criteria

V1 is successful if it can repeatedly:

1. coordinate 2-4 specialists on one scoped task
2. avoid silent scope collisions
3. route review and sign-off reliably
4. produce a coherent final synthesis
5. record corrections and review outcomes durably
6. generate retrospectives that can improve future runs

## Non-Goals

V1 is not trying to prove:

- company-wide autonomous execution
- self-modifying role ontologies
- fully automatic process crystallization
- universal prompt optimization

Those can come later.

## Immediate Build Sequence

### Step 1

Define and implement:

- `Actor`
- `Job`
- `Scope`
- `ExecutionContext`
- `Deliverable`
- `LedgerEvent`

### Step 2

Define the bus message envelope and payload schemas.

### Step 3

Implement coordinator planning and assignment flow.

### Step 4

Implement review requests, review deliverables, and sign-off outcomes.

### Step 5

Implement `CorrectionEvent` capture.

### Step 6

Implement retrospective generation and protocol-improvement proposals.

## Final Thesis

V1 `nancyr` should be built as:

**a coordinator-centered collaborative runtime with explicit actors, scopes, deliverables, review, and ledger-backed learning**

If that system proves useful, then the broader Helioy vision becomes much more credible.
