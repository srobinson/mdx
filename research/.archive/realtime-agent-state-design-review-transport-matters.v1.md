---
title: Realtime Agent State Design Review for Transport Matters
type: research
tags: [transport-matters, activity, realtime, design-review, sse, postgres, xstate]
summary: The proposed live wire overlay reaches the correct synchronous tee, but two non pollution defects and three reconciliation, scope, and gate gaps block implementation as filed.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

# Executive Summary

Transport Matters proposes a Postgres backed live status overlay that converts provider stream blocks into mid turn Activity state changes while preserving the finalized wire store. The capture timing and doorbell transaction are sound, but the filed design has two blockers and three majors: reasoning and generating bypass wire ownership, finalize freshness uses an older request timestamp, subagent traffic can enter the parent tier, reconnect misses unmaterialized runs, and the slice gates omit type checking and critical failure cases.

# Project Metadata

- Languages: Python 3.14 and TypeScript.
- Frameworks: mitmproxy, FastAPI, Fastify, XState, React, Vitest, pytest.
- Storage: Postgres through psycopg and `pg`; Alembic migrations.
- Build and workspace: uv and Hatch for Python, pnpm 10.8.1 with Node 20.19 or newer for TypeScript.
- Indexed topology: 1,104 files and 177,425 LOC across `api/`, `www/`, `packages/`, and `desktop/`.
- Helioy signal: the repository contains `.fmm.db` and was analyzed at `ef52af6bb1df64ffc44c5dade1840b7dc02f1d2f` with a pristine worktree.

# Architecture

The Python capture plane receives live provider bytes in `install_response_tee` at `api/src/transport_matters/response_stream.py:13-26`. Completed exchanges flow through Tier 1 persistence, `WireStoreObserver`, and `SessionWriter` into the finalized Postgres wire store. The proposed overlay adds a stateful SSE classifier at the tee, then upserts one `run_live_status` row per run and emits an identity only `tm_events` notification in the same transaction.

The TypeScript product plane receives notifications through `TmEventsActivityListener`, reconciles Postgres rows in `ActivityIngestion`, advances the server side `runActivityMachine`, and publishes projection changes to the browser through the existing Activity SSE route. This downstream path is already push driven. The timing gap sits between the synchronous tee and Activity reconciliation.

# Key Patterns

- Postgres row as truth, with `NOTIFY` used only as a doorbell.
- Serialized per run reconciliation through `ReconcileLoop`.
- Separate lifecycle, record, and cursorless wire event streams.
- Wire assertions as reversible overlays over record owned context.
- Snapshot first browser SSE, followed by deduplicated deltas.
- Composition level observers preserve the `storage` to `session` import boundary.

# Detailed Findings

## Blockers

### 1. Reasoning and generating do not use wire ownership

The spec states that live `record.reasoning` and `record.generating` events reuse `foldWireAsserted` without changing machine states. Current actions call `foldReasoning` and `foldGenerating` directly (`packages/activity/src/domain/runActivityMachine.ts:133-138`). Those folds write `lastActiveStatus` through `markApplied` and never set `wireAssertedExchangeId` (`packages/activity/src/domain/runActivityContext.ts:478-498`). The `reasoning` and `generating` states also omit `wire.retracted` handlers (`packages/activity/src/domain/runActivityMachine.ts:235-376`).

A direct actor probe sent a wire reasoning event followed by `wire.retracted`. The actor remained in `reasoning`, `lastActiveStatus` became `reasoning`, and `wireAssertedExchangeId` stayed null. Block stop therefore cannot restore the record baseline, and live facts pollute record owned state. The design must add wire aware reasoning and generating folds plus retraction handling before claiming exact reuse.

### 2. Finalize cannot supersede a lost terminal live write

The spec selects a live row when `live.ts > snapshot.ts` (`~/.mdx/projects/tm-realtime-spec.md:345-362`). Parsed HTTP and Codex flows create provisional `IndexEntry.ts` at request persistence (`api/src/transport_matters/exchange_recorder.py:286-338`; `api/src/transport_matters/codex/exchange.py:78-155`). Their finalize paths preserve that timestamp (`api/src/transport_matters/exchange_recorder.py:394-401`; `api/src/transport_matters/codex/exchange.py:403-417`). `WireStoreObserver` copies it into `wire_exchange.ts` (`api/src/transport_matters/wire_store_observer.py:65-94`), which Activity exposes as the snapshot timestamp (`packages/activity/src/adapters/postgresRecords.ts:423-442`).

A live start fact occurs after the request timestamp, so it remains newer than its own finalized snapshot. If the allowed best effort stop or terminal upsert fails, the stale non null row wins every reconcile and the authoritative finalize candidate cannot clear it. The resolution contract needs a comparable finalize commit watermark or an explicit overlay clear that survives terminal emitter failure.

## Majors

### 3. Subagent traffic can overwrite the primary run overlay

The final snapshot query excludes `track_role='subagent'` (`packages/activity/src/adapters/postgresRecords.ts:418-442`), and the existing integration suite pins this rule in T12. Track assignment is already known before response headers through `handle_http_request` and `RequestFlowState` (`api/src/transport_matters/addon_handlers.py:129-144`; `api/src/transport_matters/flow_state.py:33-47`).

The proposed fact and row carry only `run_id`, and the hook resolves identity from the run binding. A subagent response in the same run can therefore overwrite the parent run's single live row. Live emission must apply the existing primary track rule before the upsert, with a parity test beside T12.

### 4. Reconnect does not rediscover an unmaterialized run

`ActivityIngestion.handlers().onConnected` calls `reconcileMaterialized`, which requests work only for existing actors (`packages/activity/src/service/activityIngestion.ts:111-127`). Unmaterialized notifications are ignored after projection listeners receive them (`packages/activity/src/service/activityIngestion.ts:179-186`). Active workspace enumeration refreshes only from a decoded payload (`packages/activity/src/projections/workspaceActivity.ts:116-123,245-265`).

If both lifecycle and live notifications for a new run are lost while the listener is disconnected, Postgres contains the rows but reconnect never relists the active workspace. The run remains absent until another matching notification or browser reconnect. Lossless recovery and empty at spawn require reconnect to refresh active owner workspaces as well as materialized actors.

### 5. Slice gates omit compile proof and critical failure cases

The slice 4 and slice 5 gates run Vitest but omit `pnpm --filter @tm/activity typecheck` and root `just check`. The Activity `test` script is only `vitest run`, while type checking is a separate script. The root check explicitly includes Activity type checking (`justfile:76-88`). The filed live candidate variants also introduce `assertId` while current shared helpers read `exchangeId`, a representative compile contract that runtime tests need not reject.

Required red tests should cover wire reasoning and generating ownership, stop retraction from both states, failed terminal write versus finalize authority, live subagent exclusion, and reconnect discovery for a previously unmaterialized run.

# Dependencies

- mitmproxy provides the synchronous streamed response callback and Codex WebSocket hooks.
- psycopg and psycopg pool provide transactional upsert plus commit ordered `pg_notify`.
- `pg` provides the Activity reader and LISTEN client.
- XState owns Activity transitions, timers, guards, and reversible wire state.
- Fastify serves the Activity SSE route; React and Zustand consume its projections.

# Relevance to Helioy

This design is a useful Helioy pattern once corrected: a best effort live overlay can coexist with an authoritative durable plane when ownership, precedence, and reconnect recovery are explicit. The review also reinforces a broader requirement for Helioy run models: primary and subagent scopes must remain consistent across both finalized and live transports.

# Verification

- `pnpm --filter @tm/activity test`: 198 passed, 22 skipped, exit 0.
- `pnpm --filter @tm/activity typecheck`: exit 0.
- Focused Python pure tests for response streaming, streamed capture, and the wire observer: 25 passed, 1 database test deselected, exit 0.
- The database dependent observer test could not start because no Transport Matters test database URL was configured. No database result is claimed.
- Direct `tsx` actor probe reproduced blocker 1.
- The repository remained clean at the pinned head.

# Open Questions

1. Which durable timestamp should order the overlay against finalize: a new response commit timestamp, wire row `updated_at`, or an explicit finalize sequence?
2. Should terminal finalize delete the live row, write a tombstone with a durable sequence, or advance a shared per run generation?
3. Should listener reconnect expose a dedicated projection refresh hook, or should `onConnected` carry a synthetic workspace reconciliation signal?
