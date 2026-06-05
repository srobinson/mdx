---
title: Realtime Agent State Design Review for Transport Matters
type: research
tags: [transport-matters, activity, realtime, design-review, sse, postgres, xstate]
summary: Spec v6 carries generation in memory without changing Tier-1 or Inspector output, but its slice gate still omits a complete Tier-1 file-tree equality assertion.
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


# Spec v2 Delta Reverification

## Executive Summary

The amended `~/.mdx/projects/tm-realtime-spec.md` closes the original machine ownership blocker and the subagent, reconnect, Codex open item, abort, and TypeScript gate majors. One freshness blocker remains because the two Postgres transactions have no ordering barrier, and one slice plan major remains because the stated landing independence conflicts with the new reconnect test placement.

## Closed Findings

1. **Wire reasoning and generating ownership:** Section 5.4 now explicitly adds `eventStream(event) === "wire"` branches to `foldReasoning` and `foldGenerating`, routes them through `foldWireAsserted`, and adds `WIRE_RETRACTED_TRANSITIONS` to the `reasoning` and `generating` nodes (`tm-realtime-spec.md:508-550`). Excluding `starting` is sound. Every wire assertion leaves `starting` for its asserted state, and a retraction can only restore `starting` after clearing ownership.
2. **Subagent exclusion:** Section 4.3 now skips tap installation when `RequestFlowState.track_assignment.track_role` is `subagent`, matching the finalized snapshot filter. The Python red test is assigned to slice 3.
3. **Reconnect discovery:** Section 3.3 now requires the projections layer to relist every active owner workspace on listener reconnect, which reaches runs that have durable rows but no materialized actor.
4. **Codex interleaving:** Section 2.2 now tracks an open item set and emits a stop only when the set becomes empty. Server direction filtering and the overlapping item test are explicit.
5. **Abort and error:** Section 4.3 now requires a best effort null fact from the flow error or teardown path and assigns failure isolation tests to slice 3.
6. **Gates:** Slices 4 and 5 now include `pnpm --filter @tm/activity typecheck`, and sections 4.4 and 5.5 enumerate the missing red cases.

## Residual Blocker

[BLOCKER] 2 and 3 `tm-realtime-spec.md §5.3`; `api/src/transport_matters/wire_store_observer.py:WireStoreObserver._schedule` lines 118 to 127; `api/src/transport_matters/session/writer.py:SessionWriter._commit_wire_raising` lines 231 to 237. The new comparison uses `run_live_status.updated_at > wire_exchange.created_at` and calls both values commit times. Both writes run in independent transactions on separate observer paths, with no barrier that drains the live slot before finalization. PostgreSQL `now()` is fixed at transaction start. A slow finalize transaction can start first, then a live non null transaction can start later and commit before finalize; the live row still has the later timestamp after finalize becomes visible. The reverse commit order is also possible when an earlier live submission waits on its pool connection. If the terminal null write then fails, the same assert remains wire owned and the same assert standing rule preserves it. Admit once prevents later readmission after record ownership changes, but it does not retract a currently standing assertion. A stale live row can therefore still shadow finalize.

The design needs a causal ordering mechanism such as a finalize generation that dominates every live fact for that turn, a transactionally written overlay tombstone, or an explicit observer drain before the finalize row becomes authoritative. Timestamp comparison across unordered transactions does not provide that guarantee.

## Residual Major

[MAJOR] 9 `tm-realtime-spec.md §7` lines 657 to 669 and `§5.5` lines 556 to 576. The plan still says slice 5 can land in any order, but slice 5 now requires a reconnect relist test whose implementation is assigned to slice 4. Slice 5 cannot land with its stated gate before slice 4. Section 5.5 also assigns slice 4 a consumer side subagent row exclusion test, while `run_live_status` carries no `track_role`; Activity cannot distinguish such a row. The enforceable subagent test belongs at the slice 3 emit boundary unless the row contract gains track identity. Move the generic reconnect relist earlier or declare slice 4 as a prerequisite for slice 5, and remove or relocate the impossible consumer test.

## Verification

- Delta only comparison against archived spec v1.
- Relevant source symbols rechecked at `ef52af6bb1df64ffc44c5dade1840b7dc02f1d2f`.
- Worktree remained pristine.

## Verdict

Conditional. One blocker and one major remain in spec v2.


# Spec v3 Final Bounded Confirmation

## Scope

This pass checked only the v2 residuals against `~/.mdx/projects/tm-realtime-spec.md` v3 at repository head `ef52af6bb1df64ffc44c5dade1840b7dc02f1d2f`.

## Closed Residuals

1. **Subagent scope:** The finalize spend is guarded by `write.track_role != subagent`, so a subagent finalize cannot null the parent's active row. Live subagent exclusion remains producer side, which is coherent because `run_live_status` carries no `track_role`. The slice 3 red now asserts that a subagent response leaves the parent's row untouched.
2. **Slice dependency graph:** Section 7 now declares the real sequence: dark store and spend, pure Python and TypeScript machinery, producer emit, consumer admission plus reconnect relist, then empty at spawn. Slice 5 explicitly depends on slice 4. The machine changes moved to the dark pure machinery slice and have their own Activity test and type check gate.

## Residual Blocker

[BLOCKER] 2 and 3 `tm-realtime-spec.md §§3.2 and 5.3`; `api/src/transport_matters/wire_store_observer.py:WireStoreObserver._schedule` lines 118 to 127; `api/src/transport_matters/session/writer.py:SessionWriter._commit_wire_raising` lines 231 to 237. Nulling `run_live_status.kind` inside the wire exchange transaction removes timestamp adjudication and makes the wire row plus spend atomic. It does not prevent an older non null live submission from committing after that transaction. The planned live observer and current wire observer schedule independent transactions and share no drain, per turn generation, or conditional update that rejects a pre-finalize fact after spend. A non null write already in flight can therefore overwrite `kind = NULL` after finalize. If the queued terminal null then fails or the writer dies, Activity sees the old turn fact as a fresh assert because candidate selection now tests only `kind IS NOT NULL`. Same assert standing preserves the wire owned state; admit once limits reapplication after ownership changes but does not retract a standing assertion.

The v3 statement that every post-spend non null write belongs to a new stream is unsupported. Scheduling after stream end does not establish database commit order across the two observers. A correct closure needs one of these causal guards: drain the live observer through its terminal before the finalize transaction, tag rows with a turn or exchange generation and make the spend dominate that generation, or make later live upserts conditional on a store generation that finalize advances.

## Verdict

Conditional. One blocker remains in spec v3.


# Spec v4 Final Consensus Confirmation

## Scope

This pass checked only the generation fence, the already closed machine and subagent residuals, and the sequenced slice graph against spec v4 and source at `ef52af6bb1df64ffc44c5dade1840b7dc02f1d2f`.

## Confirmed Behavior

1. For a turn whose live and finalized paths share generation G, the guarded upsert rejects a G write after the finalize transaction has set `closed=true` for G. Observer scheduling cannot resurrect that row.
2. A live write for next generation H passes the predicate and resets `generation=H`, `closed=false`, so the next turn reopens correctly.
3. A slow G finalize cannot close H because the update is scoped by both `run_id` and `generation=G`.
4. The reasoning and generating wire folds, retraction transitions, producer side subagent exclusion, and sequenced slice dependency graph remain coherent and in scope.

## Residual

[BLOCKER] 2 and 3 `tm-realtime-spec.md §§3.2 and 4.3`; `api/src/transport_matters/exchange_recorder.py:persist_http_exchange` lines 216 to 242; `_finalize_http_provisional_exchange` lines 371 to 418; `api/src/transport_matters/codex/exchange.py:finalize_codex_provisional_exchange` lines 294 to 328; `_persist_codex_exchange` lines 217 to 238. The spec assumes the provisional exchange id always becomes `WireExchangeWrite.exchange_id`. Existing recovery paths violate that premise. HTTP falls through after a failed provisional finalize and mints a new UUID at `persist_http_exchange:229`; Codex falls back when provisional readback is missing and `_persist_codex_exchange` mints a new UUID at line 217. Live facts were already stamped with the earlier provisional id, while the final writer closes only `generation = write.exchange_id`. The close therefore matches no row and a lost terminal can leave the earlier live generation open.

The fence itself is sound once both paths share a token. The design must either require fallback persistence to reuse the provisional id, or carry the live generation separately on `WireExchangeWrite` and use that field for the close. Red tests must drive both HTTP and Codex provisional fallback branches and prove the earlier generation closes.

## Verdict

Conditional. The shared generation premise remains false on existing fallback finalization paths.


# Spec v5 Final Confirmation

## Confirmed Closure

The generation token now remains identical across main HTTP, HTTP remint fallback, main Codex WebSocket, Codex remint fallback, and abort paths. `WireExchangeWrite.generation` carries the stable provisional id separately from the potentially reminted durable exchange id, so the finalize close matches the live row on every named path. The `ts` field is correctly documented as event stamping only and never participates in authority.

## New Inconsistency

[MAJOR] 4 `tm-realtime-spec.md §3.2`; `api/src/transport_matters/storage/base.py:IndexEntry` lines 115 to 143; `api/src/transport_matters/storage/disk.py:DiskStorageBackend._rewrite_index` lines 194 to 206, `append_index` lines 208 to 215, and `persist_exchange` lines 230 to 258; `api/src/transport_matters/storage/disk_helpers.py:DiskStorageFileOpsMixin._atomic_write_model_json` lines 56 to 67; `api/src/transport_matters/api/v1/exchanges.py:ExchangeDetailResponse` lines 151 to 161 and `list_exchanges` lines 164 to 185. The proposed additive `IndexEntry.generation` field is serialized by the existing unfiltered `model_dump_json()` calls into both per-exchange `entry.json` and `index.jsonl`. FastAPI also returns `IndexEntry` directly from the frozen Inspector list and detail surfaces. Adding the field therefore changes Tier-1 artifact bytes and the Inspector response contract, contradicting the spec's frozen-plane and byte-identical-artifact requirements.

The stable token should travel outside the serialized `IndexEntry` contract, for example in a nonpersisted exchange-sink envelope, or the field must be explicitly excluded from serialization and API output while every finalize path sets it from live flow state before observer delivery. The red gate should compare `entry.json`, `index.jsonl`, and Inspector payloads before and after enabling live status.

## Verdict

Conditional. The fallback token residual is closed, but its proposed `IndexEntry` carrier violates frozen-plane invariants.


# Spec v6 Frozen Plane Confirmation

## Confirmed Closure

`ExchangeArtifacts.generation` reaches `WireStoreObserver` in memory and is ignored by the disk backend. `DiskStorageBackend._write_exchange_files` writes only the established request, response, transport, event, and turn fields (`api/src/transport_matters/storage/disk.py:512-555`); it never serializes the `ExchangeArtifacts` model and defines no generation path. `read_exchange` reconstructs the same established fields (`disk.py:372-448`). `IndexEntry` remains unchanged, so `entry.json`, `index.jsonl`, and the Inspector list and detail responses retain their contracts. The stable provisional token is reattached at each final artifact build, including the HTTP and Codex remint fallbacks, and `WireStoreObserver` forwards it through `WireExchangeWrite.generation` for the generation-scoped close.

## Residual Gate Gap

[MINOR] 9 `tm-realtime-spec.md §7`, slice 1. The v6 source design preserves the complete Tier-1 tree, but the named frozen-plane gate asserts only `entry.json`, `index.jsonl`, and Inspector output. The requested guard must compare the entire pre-change and live-enabled Tier-1 file manifest plus every file's bytes. That broader assertion is what proves no new generation sidecar appears and no established request, response, transport, event, or turn file changes.

## Verdict

Conditional on adding the complete Tier-1 file-tree equality red test. The architecture and generation threading are otherwise clean.
