---
title: TM realtime scout — TS product plane ingestion and live transport
type: research
tags: [transport-matters, activity, realtime, sse, xstate, scout]
summary: Live SSE UI stream already exists end to end; the only finalize-timed element is the wire snapshot feeding the server-side machine.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

# TM realtime scout: TS product plane (machine ingestion, live transport, contract, labels)

Scope: map what exists so a live per-block wire signal design reuses it. No design here. All symbols verified on `main` at `ef52af6`. Citations are `file` + `symbol`.

## CRUX answer first

**Yes, a live UI stream already exists and the machine can ride it.** The activity machine (`runActivityMachine`) runs **server-side** in `@tm/activity` (Node gateway), is already event-driven (pg NOTIFY → reconcile → actor), and its projections push **live SSE deltas** to the browser over `GET /v1/workspaces/:workspaceId/activity/stream` (`createActivityRouter` in `packages/activity/src/server/activityRouter.ts`), consumed by `useWorkspaceActivityStream` (`www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts`) into `useRunVitalsStore`. Any status change that reaches the server-side machine mid-turn flows to the UI **with zero frontend changes**. The finalize-timed element is upstream: the wire plane's only input to the machine is the finalized-exchange snapshot (`readWireSnapshotForRun`), so nothing wire-side enters mid-turn today.

## Reuse Map

### 1. Machine ingestion as-is

**Event vocabulary** (`packages/activity/src/domain/runActivityContext.ts`, `RunActivityEvent` union):
`run.started`, `run.exited`, `record.turn_open`, `record.reasoning`, `record.generating`, `record.tool_use`, `record.tool_result`, `record.tool_error`, `record.assistant_turn_ended`, `record.question_asked`, `record.transcript_error`, `usage.recorded`, `wire.retracted`.

Key fact: **there is no `wire.asserted` event type.** Wire assertion is minted as existing `record.*` events tagged `stream: "wire"`, `seq: 0`, id `wire:{exchangeId}:{kind}` (`wireCandidateEvent` in `packages/activity/src/domain/wireCandidate.ts`). `RunActivityEventStream` is `"lifecycle" | "record" | "wire"`; wire events never join the cursor space (`RunActivityCursorStream` excludes `"wire"`; `isNewEvent` returns true unconditionally for the wire stream; `markApplied` routes wire-stream events through `foldWireAsserted`, stamping `wireAssertedExchangeId`).

**How a wire signal enters today** (`packages/activity/src/service/activityIngestion.ts`):
- `TmEventsActivityListener` (`packages/activity/src/adapters/tmEvents.ts`) does `LISTEN` on channel `tm_events` (`TM_EVENTS_NOTIFY_CHANNEL` in `packages/activity/src/server/pgContracts.ts`); `parseTmEventsPayload` decodes to `TmEventsPayload` (`packages/activity/src/ports.ts`): `SessionEventsPayload` | `RunLifecyclePayload` | `WireExchangePayload` (write + deleted flavors). Producer: Python `SessionWriter` fires `pg_notify` after commit (`api/src/transport_matters/session/writer.py`, `_notify_payload` / `_run_lifecycle_notify_payload`).
- Load-bearing invariant (stated in the `ActivityIngestion` class header): **a NOTIFY carries no data the actor applies; it only marks the run reconcile-needed. The store is the source of truth** (every row commits before its NOTIFY). Lossless under listener drops via `onConnected → reconcileMaterialized`.
- `ActivityIngestion.reconcile` order per pass: lifecycle `run-started` → records past watermark (`activityRecordToEvent` in `packages/activity/src/service/runActivityEvents.ts`) → `reconcileWireSnapshot` → lifecycle `run-exited` last.
- `reconcileWireSnapshot`: reads `store.readWireSnapshotForRun` (at most ONE row, the run's **latest finalized parent exchange**), maps to `WireCandidate` (`wireCandidateFromSnapshot`), admits or refuses (`wireCandidateAdmitted`, `wireAssertSuppressedBySilenceStall`), sends `wireRetractedEvent` when a wire-owned status loses its admissible candidate.

**Timing = finalize.** `WIRE_SNAPSHOT_BY_RUN_SQL` (`packages/activity/src/adapters/postgresRecords.ts`) requires `response_id IS NOT NULL` on `wire_exchange` (and excludes the sidechain `track_role`), so only exchanges whose response committed are visible. The `WireExchangePayload` NOTIFY itself fires at exchange finalize. Mid-turn, the wire plane contributes nothing; mid-turn liveness today comes only from transcript records, which the harness journals late (the temporal collapse behind the Thinking bug).

**Could the vocabulary extend to a live per-block signal?**
- Reuse precedent exists: the wire plane does not mint `record.reasoning` / `record.generating` today, but those plus `record.tool_use` are first-class machine events with dedicated states and folds (`foldReasoning`, `foldGenerating`, `foldToolUse`), and the `stream: "wire"` tagging plus `foldWireAsserted` show exactly how a wire-origin event rides the existing types. Extending `WireCandidate` (today: `asked` | `running-tools` | `anomaly` | `idle` — all end-of-turn semantics) with block-start kinds is structurally additive.
- What does NOT exist and would be new: (a) a **mid-turn admission contract** — `wireCandidateAdmitted` is finalize-oriented (tool-call-id resolution for `asked`/`running-tools`; cold-start `recordSessionId === null` for `anomaly`/`idle`) and would refuse most mid-turn asserts; (b) a **block-stop representation** — the only wire un-assert is `wire.retracted` (`foldWireRetracted` → `statusAfterWireRetraction` recompute over record-owned fields; per-state `wireRetractionRestores` guards and the `WIRE_RETRACTED_TRANSITIONS` list in `packages/activity/src/domain/runActivityMachine.ts`); (c) any **store/NOTIFY vocabulary for block events** — `WireExchangePayload` names a finalized exchange only.
- Also relevant: the stall plane. `stallTimeout` (default `DEFAULT_STALL_TIMEOUT_MS` = 10 min) fires per state; a live per-block signal would interact with `applySilenceTimeout` / `wireAssertSuppressedBySilenceStall` semantics.

### 2. Live transport into the UI (the slice-4 stream, end to end)

Server (Node product plane):
- Route: `GET /workspaces/:workspaceId(.+)/activity/stream` in `createActivityRouter` (`packages/activity/src/server/activityRouter.ts`). SSE via `reply.hijack()`, `text/event-stream`, keepalive comment every `ACTIVITY_STREAM_KEEPALIVE_MS` (15 s). Protocol: one `{type:"snapshot", items, rollup}` frame, then `{type:"delta", item, rollup}` per projection change; pending deltas buffered during snapshot assembly and deduped against it (`sameRunActivityProjection`).
- Delta source: `WorkspaceActivityProjections.subscribeWorkspaceActivity` (`packages/activity/src/projections/workspaceActivity.ts`). Per run, `run()` materializes the actor and `actor.subscribe(...)` recomputes `runActivityProjection` on every machine transition; `store()` emits only on real change. NOTIFY-driven refresh: `subscribeReconcileNeeded` → `refreshSubscribedWorkspaces` re-lists on matching payloads. **So the server path is push-driven end to end; the machine is NOT read only at finalize — its input is.**
- Mount: `@tm/gateway` registers the router at prefix `/v1` (`ACTIVITY_CONTEXT_PREFIX`, `packages/gateway/src/app.ts`). The Python FastAPI origin proxies `/v1` run/activity routes to the supervised gateway via `RunRouteProxy` (`api/src/transport_matters/api/v1/run_proxy.py`; supervision plan in `api/src/transport_matters/main.py`, `plan_gateway_supervision`).
- Composition root: `createActivityGatewayDeps` (`packages/activity/src/gatewayDeps.ts`) wires `PostgresActivityReader` → `ActivityIngestion` → `WorkspaceActivityProjections` → listener.

Client (browser):
- Hook: `useWorkspaceActivityStream` (`www/packages/canvas/src/infrastructure/stream/useWorkspaceActivityStream.ts`) on `useEventSource` (`www/packages/core/src/useEventSource.ts`), URL from `workspaceActivityStreamUrl` (`www/packages/core/src/transport.ts`) → `/v1/workspaces/{id}/activity/stream?owner=`. Snapshot-on-connect, 1 s reconnect, no resume cursor.
- Consumer: `SessionCanvasRoute` (`www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`) wires `onEvents` → `useRunVitalsStore.applyFrames` (`www/packages/canvas/src/model/runVitalsStore.ts`), a non-persisted zustand store keyed by `run_id`, folding via the pure `applyActivityStreamFrame` (`www/packages/core/src/activityStreamEvents.ts`; `parseActivityStreamFrame` drops malformed frames; unknown frame types are a tolerated no-op — forward-compatible).
- Reader: `RunVitalsStrip` (`www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx`) reads `byRunId[runId]` via `capturedRunStore` key resolution.

### 3. Contract (`@tm/contract/activity`, `packages/contract/src/activity/wire.ts`)

Existing DTOs: `ActivityWireRun` (snake_case: `run_id`, `status`, `needs_you`, `since_ts`, `initial_prompt`, `last_message`, `context_tokens`, `total_usage`, `exit_reason`), `ActivityWireUsageTotals`, `ActivityWorkspaceRollup`, `ActivityWorkspaceResponse`, `ActivityStreamFrame = snapshot | delta`, `ActivityNeedsYou`/`ActivityNeedsYouAsked`, `activityStatuses` (10 values incl. reserved `needs-you-gated`), `activityStatusTier`, `DEFAULT_ACTIVITY_OWNER`, `emptyStatusCounts`, `emptyActivityUsageTotals`.

Two seam facts the design needs:
- `@tm/contract` is the **product-plane ↔ browser** seam only. For status-only liveness no new browser DTO is required: a mid-turn status change surfaces as an ordinary `delta` frame (`status` + `since_ts` change on `ActivityWireRun`). A richer live block-delta frame would be a third `ActivityStreamFrame` variant; the client fold's unknown-type no-op means it ships without breaking older bundles.
- The **proxy ↔ product** seam is NOT `@tm/contract`. It is Postgres rows plus the `tm_events` NOTIFY payloads: Python encodes (`writer.py` `_notify_payload` family), TS decodes (`ports.ts` `TmEventsPayload`, columns pinned in `server/pgContracts.ts`). A live per-block signal crossing planes either adds a NOTIFY flavor/table at this seam or introduces a new ingress; note the "NOTIFY carries no data" invariant above.

### 4. Labels + Starting

`STATUS_LABELS` in `RunVitalsStrip.tsx` is **complete** over all 10 `ActivityStatus` values: `starting→"Starting"`, `reasoning→"Thinking"`, `generating→"Responding"`, `running-tools→"Tools"`, `needs-you-asked→"Needs you"`, `needs-you-gated→"Needs you"`, `idle→"Idle"`, `stalled→"Stalled"`, `exited→"Exited"`.

`"Starting"` exists and is the machine's **initial state** (`createMachine({ initial: "starting" })`), with `usageRestoresStarting` / `retractionRestoresStarting` paths. It is unreachable at spawn in the UI because run discovery is owner-gated through the session table: `RUNS_BY_WORKSPACE_SQL` (`packages/activity/src/adapters/postgresRecords.ts`) INNER JOINs `session` on run_id + workspace and filters `session.owner = $3` + `PRIMARY_SESSION_FILTER`. A freshly spawned run has a `run_lifecycle_event` row but no session row until the harness journals its first transcript event, so `listWorkspaceActivity` omits it, no snapshot/delta ever names it, and the strip renders `data-empty`. Backend gate, not a label or frontend gap.

## Quality Map

- Clean stream separation already engineered: wire events are `seq 0`, never advance `entry.watermark`, and `isNewEvent` short-circuits for them — a second live wire signal will not corrupt record cursors.
- Per-run serialization: `ReconcileLoop` (one per run) with backoff and telemetry (`wireAdmitted`/`wireRefused`/`wireRetracted`, `reconcileFailed`) — any new per-block ingestion inherits ordering for free if it enters through the same loop, or must define its own ordering if it bypasses it.
- Frame chattiness is bounded by `sameRunActivityProjection` dedupe; per-block signals will multiply delta frames, but the fold and rollup recompute are already O(runs).
- SSE has no resume cursor (documented posture: snapshot-on-connect heals gaps). Fine for status; matters if block deltas become payload-bearing.
- `ActivityStore` port is exactly three read methods — the extension seam is explicit and test-doubled everywhere (`activityIngestion.test.ts`, `wireIngestion.test.ts`).

## Plan (seam inventory for the designers — not a design)

A live per-block signal must cross, in order: proxy plane (Python, sees provider SSE bytes mid-turn — outside this scout) → transport into the Node product plane (existing: `tm_events` NOTIFY + store row; the no-data-in-NOTIFY invariant is the decision point) → `ActivityIngestion` (new candidate kind/admission for mid-turn assert + a stop/handoff rule; `reconcileWireSnapshot` is the template) → machine (existing `record.reasoning`/`record.generating`/`record.tool_use` vocabulary + `stream:"wire"` tagging reusable as-is) → `WorkspaceActivityProjections` (no change) → SSE `/activity/stream` (no change) → `useWorkspaceActivityStream`/`runVitalsStore`/`RunVitalsStrip` (no change). The empty-at-spawn fix is orthogonal: it lives in `RUNS_BY_WORKSPACE_SQL`'s session join, not in any of the above.
