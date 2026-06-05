# Build spec — PR-3: wire-derived agent state (all finalize-knowable states)

Revision 2, after the architect review at
`~/.mdx/projects/tm-agent-state-spec-pr3-architect.md` (all four findings
accepted). Revision 1's `created_at >= lastEventTs` admission is WITHDRAWN:
`created_at` is the transaction-start stamp of an asynchronous write
(`WireStoreObserver` queues behind `_write_slot`; Postgres `now()` is
`transaction_timestamp()`), so no wall-clock key on the wire row can order it
against transcript progress. The admission is reworked as a **causal
resolution contract** (§3) with explicit delete retraction and a widened
red-first test matrix (§6).

Promoted from `~/.mdx/projects/tm-agent-state-scout-wire-coverage.md`
(main `157f781`). Locked decisions: **(b)** surface ALL finalize-knowable wire
states — `asked` (authoritative + durable), `running_tool` onset, `idle`,
anomaly (supplementary) — each under its own admission rule (§3.2). **(c)**
plan_review/ExitPlanMode heuristic DEFERRED to Slice 3. **(a)** admission key:
**no migration** — and not because zero-migration outranks correctness: a
`wire_seq` identity column orders wire rows against each other, but every HIGH
defect here is CROSS-plane (a fresh, never-applied wire row that is causally
stale versus transcript progress), which no wire-internal commit-order key can
decide. The sound cross-plane anchor is the shared tool-call id domain (§3.1).

Scope: `packages/activity` only (+ `@tm/contract` untouched). Zero frozen-plane
edits, zero migrations. Supersedes the "`wire` stream/cursor" wording in
`~/.mdx/projects/tm-http-store-spec.md` §8 PR-3; that section's acceptance
discipline stands.

## 1. Signal path, end to end

Producer (ALL ON MAIN, ships dark — no work):

1. `storage/exchange_sink.py:emit_to_index` fires exactly once per exchange at
   finalize (single-fire contract, store-spec §4);
   `exchange_recorder.py:emit_exchange_deleted` fires the deleted registry
   after a successful tier-1 delete.
2. `wire_store_observer.py:WireStoreObserver.on_exchange` /
   `on_exchange_deleted` schedule onto the writer loop — **asynchronously**,
   serialized behind `_write_slot`; a wire row can commit arbitrarily later
   than its finalize instant. §3 is designed around this fact.
3. `session/writer.py:SessionWriter.submit_wire_exchange` commits
   `session/wire_store.py:write_wire_exchange` (UPSERT by `exchange_id`) and,
   in the same transaction, NOTIFYs `tm_events` via
   `session/writer.py:_wire_exchange_notify_payload`:
   `{type: "wire_exchange" | "wire_exchange_deleted", run_id, exchange_id,
   workspace_slug, workspace_hash, owner}` (types in
   `session/wire_contracts.py`). `submit_wire_exchange_deleted` NOTIFYs only
   when a row actually went away.

Consumer (the PR):

4. `packages/activity/src/adapters/tmEvents.ts:parseTmEventsPayload` gains two
   cases building a `WireExchangePayload` (carrying `exchangeId`) added to the
   `TmEventsPayload` union in `packages/activity/src/ports.ts`; payload-type
   consts in `packages/activity/src/server/pgContracts.ts`.
5. `packages/activity/src/service/activityIngestion.ts:markReconcileNeeded`
   already routes any payload by `payload.runId`; both wire payloads reduce to
   "run X needs reconcile" (NOTIFY-as-trigger, store-as-data).
6. The reconcile pass (`ActivityIngestion.reconcile`) gains one step AFTER the
   record batch and BEFORE the `run-exited` replay: read the run's **latest
   finalized parent-track wire exchange** via a new
   `packages/activity/src/adapters/postgresRecords.ts:PostgresActivityReader.readWireSnapshotForRun`
   (one row: `run_id = $1 AND track_role IS DISTINCT FROM 'subagent' AND
   response_id IS NOT NULL`, latest by `created_at` with `exchange_id`
   tiebreak — ordering here only picks the newest stored row, it is NOT the
   admission rule; served by `wire_exchange_run_ix` +
   `wire_response_tool_ix`), derive at most ONE candidate event (§2), admit or
   refuse it (§3), and `actor.send` accordingly (including the retraction
   event, §3.3).
7. Domain (`packages/activity/src/domain/runActivityContext.ts`): candidate
   events are existing `record.*` types carrying a `stream: "wire"`
   discriminator; `eventStream` checks the discriminator FIRST (before the
   `sessionId` rotation shortcut); wire events never touch
   `seqCursors`/`recordSessionId`/`recordSubSeq`. Each status fold
   (`foldQuestionAsked`, `foldToolUse`, `foldTurnIdle`,
   `foldTranscriptError`) gains a one-line head: a `stream:"wire"` event
   routes to `foldWireAsserted` (§3.3), which sets `status` (and
   `wireAssertedExchangeId`) but PRESERVES the transcript baseline —
   `lastActiveStatus` and `pendingToolCallIds` are written exclusively by
   transcript folds. One NEW event: `wire.retracted` (§3.3) — the only
   machine-table change in this PR.
8. Projection unchanged: `domain/wireStatus.ts:wireStatusFromMachineState` →
   `projections/workspaceActivity.ts` → `needsYouForStatus` →
   `ActivityWireRun.needs_you` → `RunVitalsStrip.tsx` via `activityStatusTier`.

## 2. State mapping table

Derivation over the latest finalized parent exchange; first match wins, at most
ONE candidate per snapshot. Mapping says WHAT the row means; §3 says WHETHER it
may apply.

| Priority | Wire-IR signal | Candidate event (`stream:"wire"`) | Machine state | Canonical state | Admission rule (§3.2) |
|---|---|---|---|---|---|
| 1 | `tool_use` block with `tool_name` ∈ askToolNames = {`AskUserQuestion`, `request_user_input`} (`wire_response_block.tool_name`) | `record.question_asked` (`toolCallId` = `tool_use_id`) | `needs-you-asked` | `needs_you{asked}` — authoritative + durable | resolution set: id unresolved |
| 2 | any other `tool_use` block present | `record.tool_use` (status only — the wire fold does NOT write `pendingToolCallIds`; the transcript's own prompt tool_use rows supply the ids) | `running-tools` | `active.running_tool` onset | resolution set: NO id of the exchange resolved |
| 3 | `wire_exchange.response_error IS NOT NULL` OR `stop_reason = 'refusal'` | `record.transcript_error` (`reason` `"wire:response-error"` / `"refused-turn"`) | `stalled` (hard overlay) | anomaly — supplementary | cold start only |
| 4 | otherwise (finalized, no tool work: Claude `end_turn`/`max_tokens`; Codex status via `codex/protocol.py:codex_response_status_reason`) | `record.assistant_turn_ended` | `idle` | `idle` | cold start only |
| — | `response_id IS NULL` (request-only row) | nothing | — | — | — |

Not derivable by design: `gated{permission|plan_review|auth}` (client-side),
mid-turn `reasoning`/`generating` (transcript-owned), `terminal{done|error}`
(lifecycle-owned).

askToolNames is extracted once (owner:
`packages/activity/src/adapters/harnessRegistry.ts`) and
`adapters/transcriptRecords.ts` (`claudeRow`/`codexRow`) consumes it — the
literals live inline there today and this PR must not mint a third copy.

## 3. Admission: a causal resolution contract (no clocks, no cursor, no migration)

### 3.1 Why neither timestamp nor `wire_seq` can work

The wire write is asynchronous (§1 step 2), so a candidate can be a FRESH row
(never applied — any wire-internal cursor passes it) that is causally STALE
(the transcript already recorded the outcome's resolution). Wall-clock keys
fail because `created_at` is the delayed transaction's start time (architect
HIGH 1). A `wire_seq GENERATED ALWAYS AS IDENTITY` column gives true wire
commit order but decides nothing about transcript progress — it cannot refuse
the delayed ask whose answer was already applied. The only shared, durable,
replay-deterministic vocabulary across the two planes is the **tool-call id**:
wire `wire_response_block.tool_use_id` = transcript `toolCallId` (Claude block
id, Codex `call_id` — same provider ids on both planes).

### 3.2 The rules

The context gains one derived field, rebuilt deterministically by transcript
replay (so it is durable-equivalent — the event store is the persistence):

- `resolvedToolCallIds: ReadonlySet<string>` — `foldToolResult` and
  `foldToolError` add their `toolCallId`. This includes user answers to asks
  AND interrupts: Claude Code journals `"[Request interrupted by user for tool
  use]"` `tool_result` rows for abandoned calls (verified on real transcripts
  in `~/.claude/projects/`); Codex emits `function_call_output` /
  `turn_aborted`. Growth is bounded by the run's tool calls; process-resident
  actors make this acceptable (documented; no cap in v1).

Admission per candidate:

- **asked(X):** admit iff `X ∉ resolvedToolCallIds`. Answer, interrupt, or
  error on X — whenever committed, in whatever order the wire row lands —
  refuses re-assertion. Persistent across passes by construction (context
  state, not batch state): a later empty reconcile re-derives the candidate
  and refuses it again (closes architect HIGH 2). The snapshot being
  latest-only closes supersession by newer exchanges.
- **running-tools(ids):** admit iff NO id of the exchange ∈
  `resolvedToolCallIds`. Any resolved id proves the harness progressed past
  the handoff; the transcript then owns the state.
- **idle / anomaly:** admit iff the run has NO applied record-stream event
  (`recordSessionId === null`, the cold-start predicate). Rationale: unlike
  the ask row, Claude and Codex journal turn-end and tool rows promptly, so
  whenever ANY transcript evidence exists it is strictly fresher for these
  states; the wire's unique value for them is exactly the transcript-absent
  window (cold start, empty or unreadable transcript). This refuses every
  delayed-write and stale-idle ordering unconditionally — no cross-plane turn
  anchor exists for a tool-less Claude exchange (`turn_index` is NULL for
  Claude), so the conservative rule is the honest one. All four states remain
  surfaced per locked decision (b); idle/anomaly are supplementary and scoped
  to where they add signal.

Accepted residual edge (documented, self-healing): an ask abandoned with NO
journaled interrupt row would re-assert until the next finalize supersedes it.
Real transcript data shows the interrupt row IS written; if the builder finds
a counterexample, extend resolution marking to `foldTurnOpen` in the same PR.

### 3.3 Baseline preservation and retraction (closes architect MEDIUM E7 and its rev-2 follow-up)

The rev-2 follow-up finding: reusing the transcript folds verbatim lets a wire
assertion overwrite `lastActiveStatus` with the asserted status itself
(`foldQuestionAsked` sets `lastActiveStatus: "needs-you-asked"`), leaving
retraction nothing to restore to. The fix is structural, not a second
snapshot: **wire events never write the transcript baseline.**

- A `stream:"wire"` event routes to `foldWireAsserted(context, event, status)`:
  it applies `status` through `markApplied` and sets
  `wireAssertedExchangeId = exchange_id`, but does NOT touch
  `lastActiveStatus` or `pendingToolCallIds`. Those two fields remain written
  exclusively by transcript folds, i.e. they are at all times the pure
  record-stream derivation.
- `wireAssertedExchangeId` clears whenever a transcript-stream event changes
  status (the transcript has taken ownership back).
- **Retraction restore target — recompute, not retain (the option that cannot
  drift):** `wire.retracted` restores
  `pendingToolCallIds.length > 0 ? "running-tools" : lastActiveStatus` — the
  existing `statusAfterUsageRecord` derivation family over inputs only the
  record stream writes. A retained pre-assertion snapshot was rejected
  because it drifts: transcript events that do not change status (late
  `tool_use` rows growing `pendingToolCallIds`, usage) can invalidate a
  retained value while leaving it in place; a recomputation over
  transcript-owned fields is correct by construction at retraction time.

Mechanics: today's producer deletes only provisional exchanges (never stored),
so a stored-row deletion is currently unreachable — but the NOTIFY exists and
the contract must not strand state. On any reconcile pass, if the current
status is wire-owned (`wireAssertedExchangeId !== null`) and the snapshot no
longer yields an admissible candidate from that exchange (row deleted,
superseded by an inadmissible row, or absent), the service sends
**`wire.retracted`** — one new event type with guarded transitions from
`needs-you-asked`, `running-tools`, `idle`, and `stalled`, covered by
`runActivityMachineGraph.test.ts`. Revision 1's "zero machine-table changes"
claim stays withdrawn.

Baseline preservation also fixes a latent rev-2 defect beyond retraction: a
usage-driven stall restore (`statusAfterUsageRecord`) during a wire-asserted
status would otherwise have restored INTO the wire status via the polluted
`lastActiveStatus`. Accepted cosmetic edge: a silence stall from a
wire-asserted `running-tools` reports `stalledFrom` as the transcript baseline
(e.g. `reasoning`) for the seconds until the transcript's own tool rows land.

### 3.4 Precedence law (unchanged in spirit, now causal)

- Transcript owns intra-turn progression; `record.*` transcript events keep
  their cursor dedupe, are never admission-guarded, and always apply.
- Wire owns turn-outcome facts, admitted only by §3.2. Reconcile order stays:
  lifecycle `run-started` → record batch → wire snapshot step → `run-exited`.
- Lifecycle owns terminal; `exited` is final and drops everything.
- Tool identity is the cross-plane bridge; `pendingToolCallIds` converges via
  `addUnique` / `pendingAfterToolResult` with no extra machinery.

### 3.5 Worked cases (every one is a red-first test in §6)

- **E1 live ask:** finalize with ask block; transcript has only mid-turn rows
  (Claude defers the ask row — cm 019f49cd). Snapshot → asked(X), X
  unresolved → admitted → `needs-you-asked` live.
- **E2 restart while pending:** fresh ingestion; record replay ends mid-turn;
  X unresolved → admitted from reconcile alone.
- **E3 delayed async write (architect's counterexample):** answer
  `tool_result(X)` applies (X ∈ resolved) BEFORE the queued wire row commits;
  the late NOTIFY's reconcile derives asked(X) → refused. No clock involved.
- **E4 stale idle:** transcript applied turn N+1 activity; delayed idle
  candidate for N → refused by cold-start predicate (records exist).
- **E5 tailer-lag flip-back:** ask admitted; the ask turn's own late mid-turn
  rows apply and flip status to `reasoning`; next pass re-derives asked(X), X
  still unresolved → re-admitted. Self-healing survives the rework.
- **E6 answered then empty reconciles:** X ∈ resolved is context state — a
  second, third, empty-batch reconcile refuses the unchanged candidate every
  time. No timestamp equality exists to exploit.
- **E7 deletion retraction:** admitted ask, then `wire_exchange_deleted` (row
  gone) → next pass finds status wire-owned with no admissible candidate →
  `wire.retracted` → transcript-derived state restored, `needs_you` cleared.
- **E8 subagent isolation:** `track_role = 'subagent'` rows excluded in SQL.

## 4. Read surface scope

Ships in PR-3: `readWireSnapshotForRun` only — the live signal and the durable
read path are the same reconcile loop. Deferred to its own future spec: the
owner-scoped wire BROWSE surface (lists, manifests, blob hydration; blocker
noted: `wire_exchange` has no `owner` column — join vs column decided there).

## 5. Commit slicing (one PR, five commits)

1. **contracts + parse:** `pgContracts.ts` consts, `ports.ts`
   `WireExchangePayload`, `parseTmEventsPayload` cases — red-first parse tests
   (well-formed, malformed ignored).
2. **reader:** `readWireSnapshotForRun` SQL + narrow snapshot DTO (NOT
   `ActivityRecord`: its `sessionId` is required, `wire_exchange.session_id`
   nullable) + `askToolNames` extraction consumed by `transcriptRecords.ts` —
   pg-backed reader tests.
3. **domain:** `stream:"wire"` discriminator + `resolvedToolCallIds` +
   `wireAssertedExchangeId` context fields + `foldWireAsserted` (baseline
   preservation: wire events never write `lastActiveStatus` or
   `pendingToolCallIds`) + `wire.retracted` event and its four transitions —
   domain unit tests for §3.2 admission (each rule), E5 re-admission, E6
   persistence, baseline non-pollution, retraction recompute targets (both
   variants: empty and non-empty `pendingToolCallIds`), and double-assert
   idempotency; `runActivityMachineGraph.test.ts` updated.
4. **ingestion:** reconcile snapshot step (admission + retraction dispatch),
   telemetry counters (admitted / refused / retracted) — service tests with a
   fake store, including the E3 delayed-write interleaving.
5. **projection wiring + acceptance:** pg integration tests T1–T12 (§6).

Every commit gates on §7 verbatim (full suite; no targeted-filter shortcuts;
judge background gate runs by output content, not piped exit codes).

## 6. Tests — user-observable end state, red-first

Every test asserts the projected `ActivityWireRun.status` / `needs_you`
payload (what `RunVitalsStrip` renders) or the machine snapshot the projection
derives from — never an intermediate mapping. **Each newly protected behavior
must be observed RED before its commit lands** — T1, T2, T4, T5, T6, T8, T9,
T10, T11, T12 all fail on main; T3 and T7 pin boundaries introduced by this
PR.

- **T1 (E1) live ask:** seed mid-turn transcript rows (NO ask row) + finalized
  ask wire row; NOTIFY → projects `needs-you-asked` +
  `needs_you {kind:"asked"}`. On main it projects `reasoning` ("Thinking").
- **T2 (E2) survives restart:** same seed, FRESH `ActivityIngestion` →
  reconcile alone projects `needs-you-asked`.
- **T3 (E6 boundary) answered stays cleared:** from T1, apply the answer rows
  (`question-asked` + `tool_result(X)`) → projects `reasoning`; then force TWO
  further reconciles with EMPTY record batches against the unchanged snapshot
  → still `reasoning`, `needs_you` null both times.
- **T4 running-tools:** wire row with a Bash `tool_use` (`stop_reason=
  'tool_use'`) on a cold-start-free run with X unresolved → projects
  `running-tools`; transcript `tool-use` replay adds no duplicate pending id;
  `tool_result` → `reasoning`.
- **T5 cold-start idle:** run with zero transcript rows + `end_turn` wire row
  → projects `idle` from reconcile alone.
- **T6 cold-start anomaly:** `response_error` row (and separately
  `stop_reason='refusal'`) on an empty-transcript run → projects `stalled`
  with the reason on the context.
- **T7 (E4) stale idle refused:** transcript rows for turn N+1 applied →
  idle/anomaly candidates refused (cold-start predicate false); projection
  stays `reasoning`.
- **T8 (E3) delayed async write:** apply the answer `tool_result(X)` FIRST,
  then insert the ask wire row and NOTIFY (simulating the late commit) →
  projection stays `reasoning`, never flashes asked.
- **T9 (E5) tailer-lag self-heal:** admit ask; apply the ask turn's late
  mid-turn rows (status flips to `reasoning`); next reconcile → projects
  `needs-you-asked` again.
- **T10 (E7) deletion retraction:** two variants, both asserting the restored
  projection is EXACTLY the pre-wire transcript state. (a) Seed transcript to
  `reasoning`, admit the wire ask (projects `needs-you-asked`), delete the
  wire row + `wire_exchange_deleted` NOTIFY → projects `reasoning` with
  `needs_you` null and the transcript-derived `since_ts` semantics. (b) Same
  with an unresolved transcript `tool-use` pending → restores
  `running-tools`, proving the recompute reads the record-stream baseline,
  not a retained snapshot.
- **T11 double-assert idempotency:** same admitted snapshot twice →
  byte-identical projected run (`since_ts` unmoved).
- **T12 (E8) isolation:** subagent-track ask → primary tier unchanged; wire
  steps never advance `RunIngestionEntry.watermark`.

## 7. Gates, verbatim

```
cd api && just check && just test
pnpm --filter @tm/shell test
```
