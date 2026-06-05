---
title: Activity Slice 1a PG Contracts
type: sessions
tags: [backend, activity, postgres, contracts]
summary: Implemented Activity slice 1a database contracts, cross-plane constants, harness registry, and record fixture mapping.
status: active
source: backend-engineer
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Summary

Implemented Transport Matters Activity slice 1a on branch `feat/activity-slice-1a`, final commit `627bad2`.

Key decisions:

1. Added the durable `run_lifecycle_event` Postgres contract and DAO insert surface only. No producer writes were introduced.
2. Kept lifecycle rows decoupled from session creation. `session_id` is nullable text with no foreign key, so `run-started` can precede the first session row.
3. Centralized cross-plane literals through Python constants, TypeScript constants, and a shared Activity JSON contract.
4. Kept domain `Harness` opaque while adding the Activity package harness bundle registry for known adapters.
5. Narrowed Activity DTO output through fixture-tested transcript mapping from raw Postgres event payloads.
6. Addressed the second-family review fix round covering 4 majors and 11 minors.

## API Contract

No public HTTP API was added in this slice.

TypeScript contract additions:

```typescript
export const TM_EVENTS_NOTIFY_CHANNEL = "tm_events" as const;
export const RUN_LIFECYCLE_PAYLOAD_TYPE = "run_lifecycle" as const;
export const RUN_LIFECYCLE_EVENT_TABLE = "run_lifecycle_event" as const;

export const HARNESSES = ["claude", "codex"] as const;
export type KnownHarness = (typeof HARNESSES)[number];
```

Activity record DTO additions:

```typescript
export const activityRecordKinds = [
  "turn-open",
  "tool-use",
  "tool-result",
  "tool-error",
  "turn-end",
  "question-asked",
  "transcript-error",
  "usage",
] as const;
```

The DTO now aligns transcript and tool error naming with domain event fields: `reason` for transcript errors, `message` for tool errors, and `errorMessage` for errored tool results. One exhaustive mapping connects each `ActivityRecordKind` to a domain event type.

The Activity package now exposes server Postgres constants through `@tm/activity/server` rather than the browser-reachable root barrel.

## Database Changes

Added Alembic migration `0007_run_lifecycle_event`.

Table: `run_lifecycle_event`

Columns:

1. `run_id text not null`
2. `event_type text not null`
3. `ts timestamptz not null`
4. `workspace_slug text not null`
5. `workspace_hash text not null`
6. `space_id uuid null`
7. `worktree_id uuid null`
8. `harness text not null`
9. `launch_kind text not null`
10. `session_id text null`
11. `exit_reason text null`
12. `exit_code integer null`
13. `error text null`

Constraints and indexes:

1. Primary key on `(run_id, event_type)` to support idempotent insert ignore semantics.
2. `event_type` check generated from `RUN_LIFECYCLE_EVENT_TYPES`.
3. `launch_kind` check generated from `RUN_LIFECYCLE_LAUNCH_KINDS`.
4. Workspace time index on `(workspace_slug, workspace_hash, ts)`.
5. Partial session index on `session_id where session_id is not null`.
6. No `session_id` foreign key by design.

DAO additions:

1. `RunLifecycleEventRow` model.
2. `run_lifecycle_event_params` and `run_lifecycle_event_row` converters.
3. `run_lifecycle_event_params` strips decoded NULs from scalar fields before binding.
4. `INSERT_RUN_LIFECYCLE_EVENT_SQL` with `ON CONFLICT (run_id, event_type) DO NOTHING`.
5. `AsyncSessionDao.insert_run_lifecycle_event` returning the inserted row or `None` for duplicates.

## Security Considerations

No new public endpoint or producer path was added. The DAO uses parameterized statements only. The lifecycle table stores non-secret run metadata and nullable error text. The insert parameter path strips decoded NULs from text values before Postgres binding. Future producers should sanitize error text before persistence if it can include provider payloads or environment details.

## Performance Notes

The table uses a compact primary key for idempotency and two read-path indexes for expected workspace timeline and session correlation queries. The insert path is a single parameterized statement with conflict ignore and no read before write.

The transcript adapter now uses an exhaustive `Record<KnownHarness, parser>` registry. Unknown harness values from the Postgres boundary degrade to empty records and increment an unknown-harness drop count rather than silently routing through Codex.

Verification run:

1. `fmm generate && fmm validate`
2. `just check`
3. `just test`
4. `just build`
5. Literal grep for `tm_events`, `run_lifecycle`, `run_lifecycle_event`, lifecycle enum values, and server contract barrel boundaries

All gates passed on 2026-07-03.

## Open Items

1. Wire producers should be added in a later slice through the existing run lifecycle seams.
2. Activity readers can consume the DAO and DTO mapping after the read model surface is scoped.
3. Producer error text policy should be finalized before storing runtime failures at scale.
