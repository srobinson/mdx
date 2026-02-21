# Nancyr V2: V1 Schema Pack

Date: 2026-03-11
Status: Implementation schema pack
Author: Codex

## Purpose

This document converts the V1 runtime spec into concrete schemas that can be implemented in:

- JSON
- YAML
- SQLite / PostgreSQL
- bus message payloads

It is intentionally boring.

That is a feature.

The goal is to reduce ambiguity at build time.

This schema pack covers:

- core entities
- canonical ledger events
- bus message envelope
- review and correction structures
- a minimal relational model

## Conventions

### ID Format

IDs should be opaque strings. UUIDv7 is preferred.

Examples:

- `org_01jpnx...`
- `ws_01jpnx...`
- `job_01jpnx...`
- `ctx_01jpnx...`

### Timestamps

All timestamps are ISO 8601 UTC strings.

Example:

- `2026-03-11T14:21:44Z`

### Enums

Enums should be stored as lowercase snake_case strings.

### JSON Columns

Where a relational model uses flexible structures, store them in JSON columns rather than over-normalizing too early.

## Entity Schemas

### Org

```yaml
org:
  id: string
  name: string
  created_at: timestamp
  metadata: object
```

JSON Schema shape:

```json
{
  "type": "object",
  "required": ["id", "name", "created_at"],
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string", "minLength": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "metadata": { "type": "object" }
  },
  "additionalProperties": false
}
```

### Workspace

```yaml
workspace:
  id: string
  org_id: string
  name: string
  purpose: string?
  status: enum(active, paused, archived)
  created_at: timestamp
  metadata: object
```

### Role

```yaml
role:
  name: string
  mandate: [string]
  constraints: [string]
  metadata: object
```

### Actor

```yaml
actor:
  id: string
  workspace_id: string
  type: enum(human, machine)
  role: string
  authority_level: enum(instructional, consultative, supervisory, exploratory)
  status: enum(idle, assigned, active, blocked, awaiting_review, completed, offline)
  capabilities: [string]
  cost_model:
    unit: enum(hour, token, fixed)
    rate: number
  runtime_ref: string?
  metadata: object
  created_at: timestamp
```

Notes:

- `runtime_ref` may point to a tmux target, bus agent ID, or future runtime handle
- `capabilities` is intentionally free-form in V1

### Job

```yaml
job:
  id: string
  workspace_id: string
  title: string
  description: string?
  workflow_id: string?
  status: enum(created, planning, active, awaiting_review, blocked, completed, abandoned)
  created_by: string
  created_at: timestamp
  metadata: object
```

### Scope

```yaml
scope:
  id: string
  workspace_id: string
  label: string
  kind: enum(code, doc, design, analysis, decision, mixed)
  references: [string]
  mutable: boolean
  status: enum(open, locked, completed, archived)
  metadata: object
  created_at: timestamp
```

Notes:

- `references` can include repo paths, file globs, URLs, issue IDs, or doc URIs
- `mutable` allows the system to distinguish review-only scopes from editable ones

### Execution Context

```yaml
execution_context:
  id: string
  workspace_id: string
  job_id: string
  assigned_actor_id: string
  authority_level: enum(instructional, consultative, supervisory, exploratory)
  workflow_phase: string?
  status: enum(created, active, blocked, awaiting_review, paused, completed, terminated)
  scope_ids: [string]
  input_refs: [string]
  created_at: timestamp
  started_at: timestamp?
  completed_at: timestamp?
  metadata: object
```

### Workflow

```yaml
workflow:
  id: string
  name: string
  version: string
  roles: [string]
  phases: [string]
  checkpoint_types: [string]
  metadata: object
```

### Deliverable

```yaml
deliverable:
  id: string
  workspace_id: string
  job_id: string
  execution_context_id: string
  produced_by: string
  type: enum(code, doc, design, decision, review, retrospective, recommendation)
  title: string
  uri: string?
  status: enum(draft, submitted, approved, rejected, superseded)
  created_at: timestamp
  metadata: object
```

Recommended `metadata` examples:

- code deliverable:
  - repo
  - branch
  - commit
  - files
- decision deliverable:
  - options_considered
  - decision
  - rationale
- review deliverable:
  - target_deliverable_ids
  - outcome
  - findings

### Checkpoint

```yaml
checkpoint:
  id: string
  workspace_id: string
  job_id: string
  execution_context_id: string?
  type: enum(approval, review, decision, exit)
  requested_by: string
  assigned_to: string?
  prompt: string
  status: enum(open, satisfied, rejected, expired)
  created_at: timestamp
  resolved_at: timestamp?
  metadata: object
```

### Correction Event

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
  metadata: object
```

### Retrospective

This can be implemented as a `deliverable` of type `retrospective`, but its expected shape should be standardized.

```yaml
retrospective:
  job_id: string
  helped: [string]
  hindered: [string]
  role_issues: [string]
  protocol_changes_proposed: [string]
  protocol_changes_adopted: [string]
```

## Ledger Event Schema

Every important state change should emit a ledger event.

### Common Envelope

```yaml
ledger_event:
  id: string
  workspace_id: string
  job_id: string?
  execution_context_id: string?
  actor_id: string?
  type: string
  sequence: integer
  created_at: timestamp
  payload: object
```

JSON Schema shape:

```json
{
  "type": "object",
  "required": ["id", "workspace_id", "type", "sequence", "created_at", "payload"],
  "properties": {
    "id": { "type": "string" },
    "workspace_id": { "type": "string" },
    "job_id": { "type": ["string", "null"] },
    "execution_context_id": { "type": ["string", "null"] },
    "actor_id": { "type": ["string", "null"] },
    "type": { "type": "string" },
    "sequence": { "type": "integer", "minimum": 1 },
    "created_at": { "type": "string", "format": "date-time" },
    "payload": { "type": "object" }
  },
  "additionalProperties": false
}
```

## Canonical Event Payloads

### `job.created`

```yaml
payload:
  title: string
  description: string?
  workflow_id: string?
```

### `actor.assigned`

```yaml
payload:
  actor_id: string
  role: string
  scope_ids: [string]
  authority_level: string
```

### `execution_context.created`

```yaml
payload:
  assigned_actor_id: string
  scope_ids: [string]
  workflow_phase: string?
  authority_level: string
  input_refs: [string]
```

### `execution_context.progress_reported`

```yaml
payload:
  state: enum(active, blocked, awaiting_review, completed)
  summary: string
  next_action: string?
  risk: string?
  deliverable_ids: [string]
```

### `deliverable.produced`

```yaml
payload:
  deliverable_id: string
  deliverable_type: string
  title: string
  uri: string?
```

### `review.requested`

```yaml
payload:
  review_type: enum(technical, design, product, final)
  target_deliverable_ids: [string]
  focus_areas: [string]
  reviewer_actor_id: string?
```

### `review.completed`

```yaml
payload:
  review_deliverable_id: string
  outcome: enum(approved, approved_with_notes, rejected)
  target_deliverable_ids: [string]
  finding_count: integer
```

### `correction.recorded`

```yaml
payload:
  correction_event_id: string
  target_id: string
  target_type: string
  pattern_type: string
  magnitude: string
```

### `retrospective.generated`

```yaml
payload:
  retrospective_deliverable_id: string
  proposed_change_count: integer
  adopted_change_count: integer
```

## Bus Message Schema

The bus message envelope is the minimum contract for coordination.

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

### JSON Schema Shape

```json
{
  "type": "object",
  "required": [
    "id",
    "sent_at",
    "sender_actor_id",
    "recipient",
    "workspace_id",
    "purpose",
    "urgency",
    "requires_ack",
    "payload"
  ],
  "properties": {
    "id": { "type": "string" },
    "sent_at": { "type": "string", "format": "date-time" },
    "sender_actor_id": { "type": "string" },
    "recipient": {
      "type": "object",
      "required": ["type", "value"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["actor", "role", "coordinator", "broadcast"]
        },
        "value": { "type": "string" }
      },
      "additionalProperties": false
    },
    "workspace_id": { "type": "string" },
    "job_id": { "type": ["string", "null"] },
    "execution_context_id": { "type": ["string", "null"] },
    "purpose": {
      "type": "string",
      "enum": ["assign", "status", "block", "review", "handoff", "directive", "decision", "result", "retrospective"]
    },
    "urgency": {
      "type": "string",
      "enum": ["low", "normal", "high", "critical"]
    },
    "requires_ack": { "type": "boolean" },
    "payload": { "type": "object" }
  },
  "additionalProperties": false
}
```

## Bus Payload Shapes

### Assignment Payload

```yaml
payload:
  task_title: string
  task_description: string
  scope_ids: [string]
  expected_deliverables: [string]
  constraints: [string]
  deadline_hint: string?
```

### Status Payload

```yaml
payload:
  state: enum(active, blocked, awaiting_review, completed)
  summary: string
  next_action: string?
  risk: string?
  deliverable_ids: [string]
```

### Block Payload

```yaml
payload:
  blocker_type: enum(scope_conflict, dependency, missing_context, failed_review, technical_issue)
  summary: string
  requested_action: string
```

### Review Payload

```yaml
payload:
  review_type: enum(technical, design, product, final)
  target_deliverable_ids: [string]
  focus_areas: [string]
```

### Handoff Payload

```yaml
payload:
  from_scope_ids: [string]
  to_scope_ids: [string]
  reason: string
  required_context: [string]
  deliverable_ids: [string]
```

## Suggested SQLite / PostgreSQL Tables

This is a pragmatic relational starting point.

### `orgs`

```sql
CREATE TABLE orgs (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `workspaces`

```sql
CREATE TABLE workspaces (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL REFERENCES orgs(id),
  name TEXT NOT NULL,
  purpose TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `roles`

```sql
CREATE TABLE roles (
  name TEXT PRIMARY KEY,
  mandate JSON NOT NULL,
  constraints JSON NOT NULL,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `actors`

```sql
CREATE TABLE actors (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  type TEXT NOT NULL,
  role TEXT NOT NULL REFERENCES roles(name),
  authority_level TEXT NOT NULL,
  status TEXT NOT NULL,
  capabilities JSON NOT NULL DEFAULT '[]',
  cost_model JSON NOT NULL,
  runtime_ref TEXT,
  metadata JSON NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
```

### `jobs`

```sql
CREATE TABLE jobs (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  title TEXT NOT NULL,
  description TEXT,
  workflow_id TEXT,
  status TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `scopes`

```sql
CREATE TABLE scopes (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  label TEXT NOT NULL,
  kind TEXT NOT NULL,
  mutable INTEGER NOT NULL,
  status TEXT NOT NULL,
  references_json JSON NOT NULL DEFAULT '[]',
  metadata JSON NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
```

### `execution_contexts`

```sql
CREATE TABLE execution_contexts (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  job_id TEXT NOT NULL REFERENCES jobs(id),
  assigned_actor_id TEXT NOT NULL REFERENCES actors(id),
  authority_level TEXT NOT NULL,
  workflow_phase TEXT,
  status TEXT NOT NULL,
  scope_ids JSON NOT NULL,
  input_refs JSON NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  started_at TEXT,
  completed_at TEXT,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `deliverables`

```sql
CREATE TABLE deliverables (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  job_id TEXT NOT NULL REFERENCES jobs(id),
  execution_context_id TEXT NOT NULL REFERENCES execution_contexts(id),
  produced_by TEXT NOT NULL REFERENCES actors(id),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  uri TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `checkpoints`

```sql
CREATE TABLE checkpoints (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  job_id TEXT NOT NULL REFERENCES jobs(id),
  execution_context_id TEXT REFERENCES execution_contexts(id),
  type TEXT NOT NULL,
  requested_by TEXT NOT NULL REFERENCES actors(id),
  assigned_to TEXT REFERENCES actors(id),
  prompt TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `correction_events`

```sql
CREATE TABLE correction_events (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  job_id TEXT NOT NULL REFERENCES jobs(id),
  actor_id TEXT NOT NULL REFERENCES actors(id),
  target_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  diff_ref TEXT,
  rationale TEXT,
  pattern_type TEXT NOT NULL,
  magnitude TEXT NOT NULL,
  created_at TEXT NOT NULL,
  metadata JSON NOT NULL DEFAULT '{}'
);
```

### `ledger_events`

```sql
CREATE TABLE ledger_events (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  job_id TEXT,
  execution_context_id TEXT,
  actor_id TEXT,
  type TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  payload JSON NOT NULL
);
```

Recommended indexes:

```sql
CREATE INDEX idx_ledger_workspace_sequence
  ON ledger_events(workspace_id, sequence);

CREATE INDEX idx_ledger_job_sequence
  ON ledger_events(job_id, sequence);

CREATE INDEX idx_jobs_workspace_status
  ON jobs(workspace_id, status);

CREATE INDEX idx_contexts_job_status
  ON execution_contexts(job_id, status);

CREATE INDEX idx_deliverables_job_type
  ON deliverables(job_id, type);
```

## Minimal Validation Rules

V1 should enforce these rules in application logic.

### Rule 1: Scope Exclusivity

No two active execution contexts may hold the same mutable scope unless:

- one is marked read-only
- or an explicit conflict-resolution mode is opened

### Rule 2: Deliverable Provenance

Every deliverable must link to:

- a workspace
- a job
- an execution context
- a producing actor

### Rule 3: Required Review

Meaningful deliverables should not move directly from `draft` to `approved` without a review event.

### Rule 4: Ledger Immutability

Ledger events are append-only.
No updates.
No deletes.

### Rule 5: Correction Referential Integrity

Every correction event must point to a real target object.

## Recommended File Layout for Implementation

If building this in Rust or TypeScript, a reasonable module split is:

```text
nancyr-core/
  src/
    entities/
      org
      workspace
      role
      actor
      job
      scope
      execution_context
      deliverable
      checkpoint
      correction_event
    ledger/
      event_types
      append
      queries
    bus/
      message
      payloads
      validation
    storage/
      schema
      repositories
```

## Immediate Build Recommendation

Implement in this order:

1. relational tables for entities
2. ledger event append path
3. bus message validation
4. coordinator assignment flow
5. deliverable + review flow
6. correction event capture

That order gives you a working spine without overfitting the future.
