# Final independent review — @tm/activity slice 2 (ingestion + projection)

> **RESOLUTION UPDATE (same day, same reviewer, on Stuart's ask):** all 3 majors
> and all 7 minors fixed on `feat/activity-slice-2-ingestion` in 9 commits
> (`bf5e8e3..56d3943`). Fix map:
> M1 → `6ea21ff` (record stream totally ordered by session start; (sessionId,
> seq) cursor; machine cursor re-scopes on rotation; turn_open handled in
> running-tools and abandons pending tools; dead pre-pivot iterables deleted;
> proven live + replay against real pg).
> M2 → `1bfd942` (requestId-keyed usage fold counts a repeated key once).
> M3 → `8e81f0c` (listener onConnected after every LISTEN → reconcile all
> materialized runs; reads of materialized runs re-arm the loop).
> m1 → `39b68e3`, m2+m3 → `a54f85e`, m4 → `8d28bc0` (+ re-entrant request
> coverage), m5 → `a2c06ed`, m6 → `bf5e8e3`, m7 → `56d3943`, typo → in `6ea21ff`.
> Observations fixed opportunistically: dead RecordSource/RunLifecycleSource
> iterables deleted; ports.ts subSeq comment corrected. Left as recorded:
> materialize() deadline (slice 3), post-exit tailer-lag tail, unparented-
> subagent window (capture plane), CI unused POSTGRES_DB, pg test DB leak on
> hard-kill. Spec §7.1 wants a one-line amendment: the record watermark is now
> a (sessionId, seq) cursor over the session-start total order.
> Gates: `just check` + `just test` green; pg integration suite additionally
> run against a real local Postgres 18 (8/8) including new rotation and
> clock-skew cases. PR #198 CI green on the fix push (all 7 checks).
>
> **CROSS-REVIEW (codex, same day):** codex independently reviewed the 10 fix
> commits and raised 1 minor (a54f85e: identity-only run.started routed through
> markApplied and rewound lastEventTs to the older launch ts, skewing the
> silence timeout's stalled-since anchor). Fixed in `dedd0b0`
> (markAppliedIdentity: identity + lifecycle cursor only, timing untouched;
> test pins distinct timestamps). Codex reverified: no further findings.

Reviewer: Claude Fable (third model family, no prior-round context by design).
Branch: `feat/activity-slice-2-ingestion`, HEAD `80ee8e1`, PR #198. Diff reviewed: `git diff main...HEAD` (36 files, +3256/-692).
Gates run first-hand: `just check` exit 0; `pnpm --filter @tm/activity test` exit 0 (97 passed, 6 skipped — the pg integration suite, env-gated as designed).
Contract: spec §7.1/§5.3/§6.1/§3/§8; cm decisions 019f2bd0 (reconcile pivot), 019f2aaf (subagents-out / primary-session B), 019f2a79; scout map.

Verdict: **3 major, 7 minor. Design: SOUND** (the reconcile-loop design itself holds; the majors are contract gaps at its seams, all fixable inside the design).

---

## Major

### M1. One run can hold multiple primary sessions; the run-global watermark and single record cursor then permanently hide the newest session's records
- Severity: major
- Where: `packages/activity/src/adapters/postgresRecords.ts` `PRIMARY_SESSION_FILTER` + `RECORDS_BY_RUN_AFTER_SQL` (`seq > $2` across sessions); `packages/activity/src/service/activityIngestion.ts` `RunIngestionEntry.watermark`; `packages/activity/src/domain/runActivityContext.ts` `seqCursors.record`.
- Mechanism (verified in capture-plane code, not hypothesized): `api/src/transport_matters/addon_runtime.py` `_make_exchange_cursor_sink.register` binds ANY new native session id seen on the run's wire to the SAME `run_id`, with `parent_session_id` taken from launch fields (normally null). Claude Code `/clear` mid-run mints a new session id in the same process → a second session row with `parent_session_id IS NULL` in the same run. The slice's discriminator ("subagent iff parent points to a session in the same run") classifies BOTH sessions as primary. Codex mid-run rollout rotation has the same exposure.
- Failure scenario: run's first session reaches seq N (watermark = N, machine record cursor = N). User `/clear`s and keeps working. The successor session's records restart at seq 0; `readRecordsForRunAfter(runId, N)` filters them out (`seq > N`), and the machine's single record cursor would drop them anyway. The run's status freezes, then goes `stalled` on timeout while the agent is actively working; post-/clear prompts, messages, and usage never reach the read model. Independently, a full replay (restart) interleaves the two sessions by `ORDER BY session_id, seq` — uuid sort order, not chronology — so even rematerialization can end with `lastMessage`/status taken from the OLD session.
- Note: the resume/fork edge the design DID target is handled correctly (parent-in-a-prior-run stays primary; `pgIntegration.test.ts` "continuation session" test proves it). The gap is same-run rotation, which the discriminator cannot see because "not a child in this run" is not the same predicate as "the run's one primary session".
- Fix direction (design decision needed, options in ascending blast radius): (a) capture plane parents the rotated session like a continuation (`parent_session_id` = prior session) so the existing filter excludes it — but then post-/clear activity is invisible by design, which is wrong too; (b) scope the stream to the LATEST primary session (e.g. by `started_at`) and reset watermark + machine record cursor on session change; (c) per-session cursors/watermark (`Record<sessionId, …>`) — the Option-A shape STEP-0 rejected for blast radius. (b) fits the v1 "headline status" semantics best.

### M2. Claude Code writes the same request's usage on every content-block row; the parser emits one `usage` record per row, so `total_usage` over-counts 2-4x
- Severity: major
- Where: `packages/activity/src/adapters/transcriptRecords.ts` `claudeActivityRecords` (unconditional `records.add("usage", …)` per assistant row with `message.usage`); folded by `packages/activity/src/domain/usage.ts` `addUsage`.
- Evidence (first-hand, this machine): a real Claude Code transcript (`~/.claude/projects/...jsonl`) shows one `requestId` (`req_011CcgyYSVAiWbEysijs8wXK`) across 4 assistant rows with 4 DISTINCT uuids (so 4 distinct store rows at 4 distinct seqs) each carrying IDENTICAL `message.usage` (input 2, cache_read 80813, output 1458). Sampled duplication factors in one session: 2x, 3x, 4x. Every multi-block response (thinking + text + tool_use — the normal agentic shape) duplicates.
- Failure scenario: each duplicate row is a distinct seq, so the machine's (seq, subSeq) dedupe correctly treats them as new events and `addUsage` sums the same request 2-4 times. §3's "monotonic usage accumulation" is monotonic but wrong; the spend/usage rollup — one of the three things Activity exists to project — is inflated by roughly the average blocks-per-response. `contextTokens` is NOT affected (window value overwritten with identical numbers).
- The fixture corpus (`fixtures/claude/claude-code-transcript.json`) contains no duplicated `requestId`, so no test can catch this.
- Fix direction: dedupe usage by `requestId` at the parser/reader boundary (e.g. carry `requestId` on the usage record and let the fold replace-rather-than-add when the id repeats), pinned by a fixture with a real duplicated-requestId pair.

### M3. Lost NOTIFYs have no resync path for materialized runs: no reconnect hook, and reads of an already-materialized run never trigger reconcile
- Severity: major (borderline; compound of three verified facts)
- Where: `packages/activity/src/adapters/tmEvents.ts` `TmEventsHandlers` (no reconnected/re-listen hook); `packages/activity/src/service/activityIngestion.ts` `materialize` (early `return entry.actor` without `loop.request()`); pg NOTIFY is not durable across connections.
- Failure scenario: the listener drops (pg restart, network blip) and reconnects 250ms later. NOTIFYs fired in the gap are gone. For a MATERIALIZED run whose gap-events were its last (run exits, or agent asks a question and waits): no later NOTIFY ever arrives, `materialize()` returns the stale actor on every subsequent read, and the projection shows a live status forever — a missed `needs-you` is precisely the product's core signal, and a missed `run-exited` shows `stalled` (from timeout) instead of `exited`. The store has the truth the whole time; nothing rereads it. §7.1's own principle ("a transient error can never strand a run") is honored on the read side but not on the trigger side.
- The pg integration test "recovers a missed NOTIFY" only proves recovery when a LATER notify arrives — the self-healing case, not the stranding case.
- Fix direction (either largely closes it; both are small): (a) listener exposes an onConnected/onReconnected hook; ingestion responds by `loop.request()` for every materialized run (bounded tail reads, cheap); (b) `materialize()` on an already-materialized run also fires `loop.request()` (read-time self-heal, one indexed tail query per read).

---

## Minor

### m1. Lifecycle seq is minted from `ORDER BY ts` first; a start/exit timestamp inversion mints `run-exited` a LOWER seq than `run-started`, and the machine then drops the exit forever
- Where: `packages/activity/src/adapters/postgresRecords.ts` `LIFECYCLE_BY_RUN_SQL` (`row_number() OVER (ORDER BY ts, CASE event_type …)`).
- Scenario: clock skew or a backwards NTP step between the launch-registration write and the teardown write makes `exited.ts < started.ts`. The window function then orders exited first (seq 0, started seq 1); `reconcile` applies started (lifecycle cursor → 1), and the exit (seq 0) fails `isNewEvent` on every pass — run never terminal until stall timeout, `exitReason` lost. The table has at most two rows keyed `(run_id, event_type)`; ordering by the event-type CASE alone (started=0 < exited=1) is strictly safer and loses nothing.

### m2. A late `run.started` is only handled in the `starting` state; a run whose records applied first can never acquire identity
- Where: `packages/activity/src/domain/runActivityMachine.ts` (only `states.starting.on["run.started"]` exists).
- Scenario: a run materialized with no `run-started` row yet (lifecycle write failed/lagged, or a pre-slice-1 historical run reached via direct `run(runId)`) applies records and leaves `starting`; when the started fact later appears, every state except `starting` drops it, so `harness`/`launchKind`/`runId`/`workspaceId` stay null in the projection permanently. Cheap fix: handle `run.started` in every non-final state as a context-only apply (no status change), or seed identity at reconcile time when the actor's context lacks it.

### m3. `needs-you` drops `record.assistant_turn_ended` (and `tool_result`), so a second consecutive assistant message never updates `lastMessage`
- Where: `packages/activity/src/domain/runActivityMachine.ts` `states["needs-you"].on` (no `assistant_turn_ended` / `question_asked` / `tool_result` handlers).
- Scenario: assistant ends a turn (needs-you), then emits another end_turn message without an intervening user record. The second event has no transition, `markApplied` never runs, and §5.3's "last_message overwritten" misses the newest agent text (also its ts never stamps `lastEventTs`). Low frequency, but it is a silent read-model staleness on exactly the field the operator reads. A self-transition with `reenter: false` and the apply action closes it.

### m4. `ReconcileLoop.drive` assumes `onError` and `backoff` never throw; if either does, the drive promise rejects with `running` non-null — the run is stranded exactly the way the loop exists to prevent, plus an unhandled rejection
- Where: `packages/activity/src/service/reconcileLoop.ts` `drive` catch block (`this.onError?.(error)` and `await this.backoff(attempt)` outside any guard).
- Scenario: an injected backoff rejects (or a future telemetry sink throws): `drive()` rejects, `this.running` stays set forever, every future `request()` no-ops, `settled()` waiters hang, and Node surfaces an unhandled rejection (default: process crash). Current production wiring (console.warn + setTimeout) won't throw, so this is defensive — but the class is the correctness backbone and its contract comment promises "never strand a run". Wrap both calls.

### m5. Single-barrel boundary check silently skips a root package with no `exports` map — fail-open for the one case where every internal file becomes importable
- Where: `www/packages/shell/src/testSupport/importGraphBoundary.test.ts` `rootPackageExports()` (`.filter((entry) => entry.exports !== null)`); `packageExportsMap` returns null when the manifest has no `exports` field.
- Scenario: a future `packages/*` package ships without an `exports` map (or the map is deleted); Node exposes all files, and the single-barrel test never sees the package — it greens. The internal-reach-in tests are also hardcoded to activity+common only. One-line strengthen: assert every root package HAS an exports map (treat null as an offender). (Verified independently; surfaced by the removed-behavior audit agent.)
- Note: for packages WITH a map the check is genuinely fail-closed across string/object/types-only/wildcard second-barrel forms, and auto-covers future packages via `readdirSync`.

### m6. `runActivityMachine.test.ts` crossed the 700-line hard limit in this slice (687 → 766)
- Where: `packages/activity/src/domain/runActivityMachine.test.ts`.
- The user-level CLAUDE.md refactoring threshold is a hard limit ("no 'it fits the pattern so it's fine'"). The slice's own pivot honored it for the machine source (710 → 402 via context/usage extraction) but pushed the test file past it. The §5.3 overview describe-block added here is a natural extraction seam (it tests `runActivityContext` folds more than the graph).

### m7. Four contract clauses have no failing test (mutation-survivable), and one pg test's comment claims a dedupe it does not exercise
- Where: `packages/activity/src/pgIntegration.test.ts` "dedupes overlap" test; `packages/activity/src/service/activityIngestion.test.ts` fakes; `packages/activity/src/service/reconcileLoop.test.ts`.
- Specifics (each verified against the code):
  1. The pg "overlapping notify" test's comment says "seq 0 is deduped", but `reconcile()` reads `readRecordsForRunAfter(runId, watermark=0)` so seq 0 is never re-read — the WATERMARK filters it, the machine's (seq, subSeq) cursor never fires. No service or integration test hands the actor an already-consumed record seq; the §6.1 composite-cursor idempotence is proven only by `sameRowDedupe.test.ts`'s manual double-send at the machine layer.
  2. The watermark-monotonicity guard (`if (record.seq > entry.watermark)`, activityIngestion.ts) could become an unconditional assignment and every test still passes — all fakes pre-filter `seq > afterSeq`, so a stale seq is structurally unfeedable.
  3. The documented fail-fast materialization path (initial `readLifecycleForRun` throw → `materialize()` rejects, nothing published, later retry succeeds) has no test; both throw tests fail only the reconcile-window reads.
  4. `ReconcileLoop.request()`'s documented "safe to call from within the task itself" re-entrancy has zero coverage, and no ingestion-layer fake ever models two records sharing one seq (subSeq > 0), so the watermark×subSeq interaction is untested outside the pure machine.
- Cost: these are the exact clauses the next refactor is most likely to break silently. One test commit closes all four. (Surfaced by the test-audit agent; each specific re-verified first-hand.)

---

## Observations (not defects, recorded for slice 3 / the record)

- Post-exit tail records: a record committed after the pass that applies `run-exited` (tailer flush lag) is dropped by the final state — spec-compliant ("exited is terminal"), costs at most the last flush of overview/rollup. Within-pass ordering (records before exit) already minimizes it.
- `materialize()` has no deadline: a permanently unreachable store retries forever and the returned promise never settles. Spec-intended (retry owns failures; telemetry surfaces it), but slice 3's HTTP handler must bound its own wait.
- Transient unparented subagent sessions: a child session created first by the wire-exchange sink carries `parent_session_id` NULL until subagent discovery parents it (`session` upsert COALESCE). In that window its records pass the primary filter on a young run. Plausible, unproven ordering; worth one capture-plane look if status flaps appear near Task-tool spawns.
- `RecordSource.records()` / `RunLifecycleSource.lifecycle()` async iterables (and `readRecordsForRun`) have no non-test consumers after the pivot — the old replay path's surface. Either delete (CLAUDE.md: delete the old path completely) or keep deliberately as the slice-3 read seam; today it is neither used nor marked.
- `ports.ts` `ActivityRecord.subSeq` doc comment: "never reminds the store's seq column" — typo for "re-mints"; garbles a contract comment.
- CI product-plane job: `POSTGRES_DB: transport_matters` is created but the test URL targets `/postgres`; works (the suite creates its own throwaway database), the created DB is just unused.
- pgIntegration teardown swallows a failed `DROP DATABASE` and there is no startup sweep of prior `tm_activity_it_*` databases, so a hard-killed run leaks one uniquely-named DB on an opt-in dev's pg. No collision risk (UUID names), pure accumulation.
- Test quality overall is strong: the pg integration harness is exemplary (throwaway database per run, `DROP … WITH (FORCE)` teardown, fail-closed reachability probe at module load, real `pg_notify` end-to-end, real parser in the loop, primary-filter + continuation-edge coverage). `sameRowDedupe` proves both same-row multi-fact application and whole-row replay idempotence. The machine's model-based test now also asserts the context.status mirror across all reachable states.

## Design soundness

The pivot landed where it should. One primitive (per-run `ReconcileLoop`) owns catch-up, retry, and convergence; NOTIFYs are pure triggers; the store is the only buffer; idempotence lives in the domain cursor where the spec put it; and the loop's synchronous consume-trigger/clear-running discipline is correct under JS's single-threaded model (a trigger landing mid-pass forces another pass — verified in code and covered by tests). The adapters are thin, the translator sits in service/ keeping the domain pure (verified: domain/ imports nothing but itself), and the projection is a pure fold over actor snapshots. I found no accidental complexity to remove — this is close to the minimum design that satisfies §7.1, and I would not simplify further. The three majors are seam contracts, not architecture: M1 is the primary-session predicate being weaker than the uniqueness the cursor/watermark rest on, M2 is a wire-reality fact about Claude transcripts the parser doesn't yet know, M3 is trigger-channel durability being assumed rather than reconciled. All three fix inside the existing design without adding a mechanism class. Design: SOUND.
