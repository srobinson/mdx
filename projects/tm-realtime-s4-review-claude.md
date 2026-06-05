---
title: PR #265 adversarial review — realtime slice 4 (consumer admission + reconnect relist)
type: review-findings
reviewer: claude
pr: 265
branch: realtime-slice4-consumer-admission
head: a5331d303928e43b79d52be15d9de05bf3607954
spec: ~/.mdx/projects/tm-realtime-spec.md (§3.3, §5.1–§5.5, §7 row 4)
date: 2026-07-11
verdict: 2 MINOR, 0 MAJOR, 0 BLOCKER
---

# Verdict

Two MINORs, both coverage/discipline gaps rather than behavior defects: the
new pending-refresh coalescing branch is untested (mutation survives the full
suite), and the three new pg-contracts.json keys have no Python-side pin. The
liveness payoff is real and proven against real Postgres rows, the admit-once
and same-assert mechanisms both die under mutation, retract and finalize
handoff converge in both interleavings, and the refactor is byte-identical
move-only. Every claim verified against source at head `a5331d3`. Working
tree confirmed pristine before and after; all mutations and the probe ran in
a scratchpad clone, never in the repo.

# 1. Liveness end-to-end — CONFIRMED (real rows, not finalize-shaped)

The admission consumes the live `run_live_status` row, not a finalize
signal. `reconcileWireSnapshot` (`activityIngestion.ts`) reads
`readLiveStatusForRun` (SQL `LIVE_STATUS_BY_RUN_SQL` against
`run_live_status`, `postgresRecords.ts`) alongside the wire snapshot and
prefers the live candidate; the `run_live_status` NOTIFY flavor routes
through `parseTmEventsPayload` to the same identity-only reconcile doorbell.

**Mid-turn movement is proven at the acceptance tier.** T13
(`pgWireIntegration.test.ts`) drives real Postgres upserts + `pg_notify`
through the real listener and asserts the projected
`RunActivityProjection.status` walks reasoning → generating → running-tools
with **zero `wire_exchange` rows in existence** — nothing finalize-shaped can
be driving it. This is exactly the pin PR-3 lacked. The final step upserts
`kind = null` (the abort/stop terminal shape) and the projection returns to
the record baseline with `wireAssertedExchangeId` nulled. I ran the suite
against real Postgres: 243 passed, 0 skipped (pg suites executed).

**Propagation to the browser surface:** the delta path for a live change is
the actor subscription inside `WorkspaceActivityProjections.run()`
(`actor.subscribe(() => this.store(...))` → `emit`), so any actor transition
from a reconcile reaches subscribed-workspace deltas and the existing SSE
router; the reconnect test additionally observes a live-derived status
arriving through a real `subscribeWorkspaceActivity` delta. Unit tier:
`wireIngestion.test.ts` `it.each` admits all three kinds mid-turn with the
`live:{runId}:{seq}` stamp.

**Precedence is pinned by mutation.** MUT3 (swap candidate precedence to
snapshot-first) fails the convergence test's snapshot-first branch: with a
finalize snapshot committed while the live row is still non-null, the status
must stay live (`generating`) until the stop lands. Live-shadows-finalize is
exactly §5.3 step 3's fence semantics.

# 2. Admit-once / no flap — CONFIRMED, mutation-tested

Two interlocking mechanisms, each with its own red:

- **Same-assert-standing no-op** (`reconcileWireSnapshot`): candidate key
  equal to `context.wireAssertedExchangeId` returns before suppression,
  admission, or retract. MUT2 (remove it) fails 3 tests, including the
  no-re-enter test and the stalled-suppression test's new telemetry pins.
  The no-re-enter test is load-bearing beyond flap: it proves the unchanged
  row does not `reenter` (stall timer keeps running: reconcile at +5min,
  stall still fires at +10min).
- **Once-per-assertId** (`wireCandidateAdmitted` +
  `RunIngestionEntry.lastLiveAssertId`): survives record-stream supersession
  because it lives on the service entry, not machine context. MUT1 (remove
  the guard, the directive's named mutation) fails 2 tests — the Esc test
  (below) and the domain-level once test. The generation is the causal
  anchor one level down: `assertId = live:{runId}:{seq}` and a seq is minted
  per generation stream by the slice-3 producer; a re-read row carries the
  same key, a genuine new fact carries a new one.

The sticky-attention deadlock the spec warns about is directly tested:
"never re-admits a stale generating row after an Esc interrupt journals" —
records journal the interrupt, `wireAssertedExchangeId` clears, the stale
`generating` row is refused by `lastLiveAssertId`, and the refusal does not
retract (asserted is null), so the machine keeps record truth. No sticky
Responding. T12's rewrite (spy on completed live reads instead of waiting on
`wireAdmitted`) correctly adapts the unchanged-exchange no-flap acceptance
test to the new no-op semantics and additionally pins `wireAdmitted` flat.

# 3. Retract + handoff — CONFIRMED

- **Block stop → retract:** `kind = null` yields no live candidate; with no
  finalize snapshot the trailing branch sends `wireRetractedEvent`. The unit
  test pins the restored record baseline AND the data-derived stamp
  (`sinceTs === stopped.ts` — the retraction timestamp now prefers the stop
  fact's row ts over `lastEventTs`, still replay-deterministic, no wall
  clock).
- **Finalize handoff, both orders:** "converges to finalize whether stop or
  the wire snapshot is observed first" drives both interleavings to
  `needs-you-asked` with `wireAssertedExchangeId` flipped to the exchange id.
  No timestamp adjudication anywhere in the step — candidate choice is
  null-kind-vs-non-null only (fence semantics; clock rules absent by
  construction, `RunLiveStatus.ts` is used solely for event/retraction
  stamping per §5.1).
- **T14 (acceptance):** concurrent parent facts converge on main
  (running_tool utility → generating main), finalize with the closed nulled
  row hands off to `needs-you-asked`, and a new generation's live assert
  reopens and is admitted as a fresh assert, never a survivor.
- Esc-mid-response: covered at both tiers (unit Esc test; T13's terminal
  `kind = null` step).

# 4. Reconnect relist — CONFIRMED, mutation-tested (one MINOR)

`onConnected` → `handleConnected` → `reconcileMaterialized()` plus
`connectedListeners` → `refreshAllSubscribedWorkspaces()`, which re-lists
every active owner-workspace through the same `listWorkspaceActivity` read
the browser snapshot uses — materializing rows-without-actors. The test
seeds lifecycle + live rows with no doorbell ever delivered and asserts the
run appears as `generating` after `onConnected`, via a real subscription
delta, with `isMaterialized` true. MUT4 (unwire the relist callback) fails
it.

**MINOR 1 — pending-refresh coalescing branch untested.**
`refreshOwnerWorkspace` previously dropped a refresh request when one was in
flight; the PR adds `pendingRefreshes` so a relist landing during an
in-flight refresh queues exactly one follow-up (`finally` re-runs). That
branch is what stops the reconnect relist being silently swallowed by a
racing NOTIFY-triggered refresh — the exact hole §3.3 closes, one race
window over. MUT5 (revert to the plain `if (this.refreshes.has(key))
return;`) survives the FULL activity suite including the Postgres
integration suites (243 passed). I probed the branch with a throwaway test
in the clone (slow first `runsForWorkspace`, `onConnected` mid-flight): the
queued relist correctly re-runs after the in-flight refresh completes — the
code is right, the branch is uncovered. One test with a gated store read
closes it; my probe shape works as-is.

# 5. Non-pollution — CONFIRMED

Live kinds mint the existing `record.*` vocabulary with `stream: "wire"`,
routing through the slice-2 `foldWireAsserted` branches; `foldToolUse`'s
wire branch never touches `pendingToolCallIds` (verified at source), so the
`toolCallId ?? ""` on the minted live-tool event is inert. Wire events
structurally cannot advance `entry.watermark` — it is written only in the
record-read loop of `reconcile`, and `reconcileWireSnapshot` never touches
the entry beyond `lastLiveAssertId`. The exited guard now also lives in
`wireCandidateAdmitted` (spec §5.2). Slice-2's fold-purity and retract reds
continue to pass unchanged.

# 6. Refactor — CONFIRMED move-only

`runActivityContext.ts` (689 → 606) sheds the event alphabet to new
`runActivityEvent.ts` (128). I extracted every moved declaration from
`main`'s file and diffed against the new module: all 18 (BaseRunActivityEvent,
the 13 event interfaces, RunActivityEvent union, launchKinds, LaunchKind,
Harness) are byte-identical modulo the `export` prefix on
`BaseRunActivityEvent`. `runActivityContext.ts` re-exports the full set, so
existing import sites are untouched; `domain/index.ts` grows only
`candidateAssertKey`.

# 7. Scope / DRY / sizing — CONFIRMED (one MINOR)

- **Scope:** the PR touches `packages/activity/` only — no producer, no
  store, no api/, no shell/canvas/contract packages, no gated creep. The
  local gateway bundle containing built activity code is gitignored (not a
  PR artifact).
- **DRY:** `runPayloadIdentity` deduplicates the three identity-payload
  parsers in `tmEvents.ts` (net improvement); `liveCandidateFromRow` sits
  beside `wireCandidateFromSnapshot` as the spec prescribes; the pg harness
  DDL and upsert source every column from the shared `pgContracts.ts`
  constants.
- **Sizing:** all touched files under 700 — largest are `runActivityContext.ts`
  606, `pgWireIntegration.test.ts` 542, `wireIngestion.test.ts` 542,
  `postgresRecords.ts` 558. The slice-2 watch item (689) is resolved by the
  split.

**MINOR 2 — the new contract keys are pinned one-sided.**
`pg-contracts.json` gains `runLiveStatusPayloadType`, `runLiveStatusTable`,
`runLiveStatusKinds`, and `pgContracts.test.ts` pins the TS constants to the
JSON — but `api/src/transport_matters/session/test_activity_pg_contracts.py`
(the established two-sided pattern: it pins every lifecycle and wire key
against the Python constants) has no live-status assertions. The Python
constants exist (`session/live_status_contracts.py`:
`RUN_LIVE_STATUS_PAYLOAD_TYPE`, `RUN_LIVE_STATUS_TABLE`,
`RUN_LIVE_STATUS_KINDS`; values verified equal to the JSON today, including
kind order). Until a third test function lands there, a Python-side rename
drifts the shared contract silently — the exact failure that file exists to
catch. Five-line api test addition.

# Observations (not findings)

- Two §5.5 reds are writer-side by nature and live in slice 1's suite, not
  here: the atomic null-and-close commit and the closed-generation straggler
  no-resurrection (the TS pg harness seeds effect-states with its own
  unguarded upsert; the §3.1 guarded SQL is Python). Likewise the
  remint-fallback "end-to-end here" red is not deliverable under slice 4's
  pnpm-only gates; store-level reds shipped in slice 1. T14 simulates the
  closed-row effect consumer-side, consistent with how the finalize plane's
  acceptance suite seeds state.
- The same-assert-standing no-op changes finalize-plane telemetry semantics
  (an unchanged exchange no longer re-admits, a stall no longer counts a
  refusal); T11 and the stalled test were updated to pin the new behavior,
  which §5.3 step 4 explicitly blesses.
- The NOTIFY payload is identity-only at the producer
  (`_run_live_status_notify_payload`: run_id, workspace slugs, owner — no
  kind/seq/ts), and the tmEvents test proves extra data fields are dropped.

# Gate

Run at head in the clone, judged by output content, with
`TRANSPORT_MATTERS_TEST_DATABASE_URL` set so the Postgres acceptance suites
execute: `pnpm --filter @tm/activity typecheck` clean;
`pnpm --filter @tm/activity test` → 243 passed, 0 skipped (20 files);
`pnpm --filter @tm/shell test` (full suite) → 1207 passed (163 files).

# Mutation / probe table

| # | Mutation (scratchpad clone, each reverted) | Red test | Result |
|---|---|---|---|
| MUT1 | Remove the `lastLiveAssertId` once-guard in `wireCandidateAdmitted` | Esc re-admit test + domain admit-once test | 2 FAILED ✓ |
| MUT2 | Remove the same-assert-standing no-op in `reconcileWireSnapshot` | no-re-enter test + stalled telemetry pins | 3 FAILED ✓ |
| MUT3 | Swap candidate precedence to snapshot-first | finalize-convergence test (snapshot-first branch) | FAILED ✓ |
| MUT4 | Unwire the `subscribeConnected` relist callback | reconnect-relist projection test | FAILED ✓ |
| MUT5 | Drop `pendingRefreshes` queueing | — | SURVIVED full suite incl. pg (MINOR 1) |
| probe | Throwaway test driving the queueing branch (slow refresh + mid-flight relist) | — | branch behaves correctly |
