---
title: Transport Matters realtime agent state design review, Codex
type: research
tags: [transport-matters, activity, realtime, design-review, codex]
summary: Adversarial review found two blockers and three majors in the live overlay, reconnect behavior, and slice gates.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

# Transport Matters realtime agent state design review

Base: `main` at `ef52af6bb1df64ffc44c5dade1840b7dc02f1d2f`. The worktree was pristine before review.

## Findings

[BLOCKER] 3 `tm-realtime-spec.md §5.4`; `packages/activity/src/domain/runActivityContext.ts:foldReasoning` lines 478 to 487; `foldGenerating` lines 489 to 498; `packages/activity/src/domain/runActivityMachine.ts:runActivityMachine` lines 133 to 138 and 235 to 376. The promised unchanged `foldWireAsserted` path does not exist for `record.reasoning` or `record.generating`. Both machine actions call folds that write `lastActiveStatus` and never set `wireAssertedExchangeId`; the `reasoning` and `generating` source states also have no `wire.retracted` transition. A direct actor probe confirmed a wire reasoning event left `lastActiveStatus="reasoning"` and `wireAssertedExchangeId=null`, then ignored `wire.retracted`. Live reasoning and generating therefore pollute the record owned baseline and cannot retract on block stop, defeating the core non pollution guarantee.

[BLOCKER] 3 `tm-realtime-spec.md §5.3`; `api/src/transport_matters/exchange_recorder.py:persist_http_provisional_exchange` lines 286 to 338; `_finalize_http_provisional_exchange` lines 365 to 441; `api/src/transport_matters/codex/exchange.py:persist_codex_provisional_exchange` lines 78 to 155 and `finalize_codex_provisional_exchange` lines 403 to 417; `api/src/transport_matters/wire_store_observer.py:WireStoreObserver.on_exchange` lines 65 to 94; `packages/activity/src/adapters/postgresRecords.ts:WIRE_SNAPSHOT_BY_RUN_SQL` lines 423 to 442. The proposed `live.ts > snapshot.ts` authority test compares the live emitter clock with `wire_exchange.ts`, but finalized provisional exchanges preserve the `IndexEntry.ts` captured when the request was first persisted. `WireStoreObserver` copies that old timestamp into the finalized row. Every non null live fact emitted during the response is therefore newer than its own authoritative finalize snapshot. If the best effort stop or terminal upsert fails, the stale non null live row wins every future reconcile and the finalize plane can never clear it. Staleness is not absorbed; a single allowed live write failure can leave the run permanently Thinking, Tools, or Responding.

[MAJOR] 3 `tm-realtime-spec.md §§2 and 4.3`; `api/src/transport_matters/addon_handlers.py:handle_http_request` lines 129 to 144; `api/src/transport_matters/flow_state.py:RequestFlowState` lines 33 to 47; `packages/activity/src/adapters/postgresRecords.ts:WIRE_SNAPSHOT_BY_RUN_SQL` lines 418 to 442. The live fact and row carry only `run_id`, while the hook is described as resolving identity from `binding.run_id`. The request path already classifies `track_assignment.track_role` before response headers, and the finalized Activity query deliberately excludes `track_role='subagent'`. Without the same filter before live emission, any same run subagent response can overwrite the parent run's single `run_live_status` row and drive the primary Activity actor. This regresses the existing subagent exclusion contract exercised by `packages/activity/src/pgWireIntegration.test.ts` T12.

[MAJOR] 2 `tm-realtime-spec.md §3.3`; `packages/activity/src/service/activityIngestion.ts:ActivityIngestion.handlers` lines 111 to 127 and `markReconcileNeeded` lines 179 to 186; `packages/activity/src/projections/workspaceActivity.ts:WorkspaceActivityProjections` lines 116 to 123 and 245 to 265. Reconnect only requests reconcile for already materialized actors. Active workspace enumeration refreshes only after a decoded NOTIFY payload. If a new run's lifecycle and live doorbells are both lost while the listener is disconnected, the run has durable rows but no actor; reconnect ignores it and never relists the subscribed workspace. The claimed lossless doorbell invariant and empty at spawn behavior therefore have a reconnect hole until another matching notification or browser reconnect occurs.

[MAJOR] 9 `tm-realtime-spec.md §7`; `packages/activity/package.json` scripts; root `justfile` lines 76 to 88. Slice 4 and slice 5 gate TypeScript changes with Vitest commands but omit `pnpm --filter @tm/activity typecheck` or root `just check`; the package's `test` script is only `vitest run`. The proposed live `WireCandidate` variants use `assertId` while the current shared helpers require `exchangeId`, illustrating a compile contract that runtime tests need not catch. The named red tests also omit wire reasoning and generating ownership plus retraction, failed terminal write versus finalize authority, live subagent exclusion, and reconnect discovery of an unmaterialized run. The slices are not independently proven green against their stated invariants.

## Verification

- `pnpm --filter @tm/activity test`: 198 passed, 22 skipped, exit 0.
- `pnpm --filter @tm/activity typecheck`: exit 0.
- Focused Python pure tests for response streaming, streamed capture, and the wire observer: 25 passed, 1 database test explicitly deselected, exit 0.
- The first Python run reached 25 passes and then failed fixture setup for the database dependent observer test because no Transport Matters test database URL was configured. No database pass is claimed.
- Direct `tsx` actor probe reproduced the first blocker.
- Worktree remained clean after verification.

## Verdict

Conditional. Two blockers, three majors, zero minors.
