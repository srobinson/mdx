# Transport Matters Activity Slice 2 Review

Scope reviewed: committed branch diff only, `git diff main...feat/activity-slice-2-ingestion`.

Expected workspace dirt preserved: `M docs/ARCHITECTURE.md`.

## Verdict

Review result: issues found.

Summary: 2 major, 1 minor.

## Major Findings

### 1. Buffer overflow during materialization can permanently drop live records

Severity: major

Files:

- `packages/activity/src/service/activityIngestion.ts`
- Symbols: `ActivityIngestion.route`, `ActivityIngestion.replayAndGoLive`

Evidence:

- `route` drops a dirty buffer and ignores subsequent live events while the run has no actor: lines 113-120.
- `replayAndGoLive` snapshots lifecycle and records before publishing the actor: lines 123-125.
- After replay, it publishes the actor, clears the buffer, and unconditionally clears `dirty`: lines 146-150.

Concrete scenario:

1. A run is unmaterialized.
2. `materialize(runId)` starts and `replayAndGoLive` reads store records through sequence N.
3. While the async replay is still in flight, more than `bufferLimit` committed NOTIFY records arrive for sequence N+1 onward.
4. `route` clears the in-memory buffer and sets `entry.dirty = true`.
5. `replayAndGoLive` finishes replaying only the already-collected records, sets `entry.actor = actor`, clears `entry.dirty = false`, and drains an empty buffer.

The actor is now live but has never seen the dropped committed records. Since the actor remains materialized and `dirty` has been cleared, no later full replay repairs the projection. This violates the slice contract that buffer overflow is a correctness-safe fast-path failure: overflow should mark the run dirty and force store replay, with the store remaining the source of truth.

Required fix:

When a buffer overflows during materialization, do not publish the partially replayed actor as clean. The materialization path needs to detect dirty-after-replay and restart from the store, or loop replay until it can atomically publish a clean actor and drain a non-dirty buffer.

### 2. Multiple Activity records from one transcript row share one sequence and the machine drops all but the first

Severity: major

Files:

- `packages/activity/src/adapters/transcriptRecords.ts`
- `packages/activity/src/domain/runActivityMachine.ts`
- Symbols: `claudeActivityRecords`, `recordBuilder`, `isNewEvent`, `eventStream`, `applyUsage`

Evidence:

- A single Claude assistant row can emit an action record and a usage record. The tool/question/turn-end records are added at lines 60-72, and the usage record is added at lines 73-74.
- `recordBuilder` gives every Activity record from that raw row the same `seq`: lines 124-143, especially line 136.
- The machine dedupes all non-lifecycle events on the single `record` cursor: `isNewEvent` at lines 574-575 and `eventStream` at lines 677-679.
- Applied events advance that shared cursor to `event.seq`: lines 595-598.
- Usage updates the new overview fields at lines 277-286, including `contextTokens`.

Concrete scenario:

For a Claude assistant transcript row containing a tool use plus usage, the translator emits records like:

- `record.tool_use` with `seq = 42`
- `usage.recorded` with `seq = 42`

The tool-use event is applied first and advances the record cursor to 42. The subsequent usage event fails `event.seq > context.seqCursors.record`, so `applyUsage` never runs. The run projection then reports stale or zero `totalUsage` and `contextTokens`, even though the usage was present in the source row. The same loss can happen for `question-asked + usage` and `turn-end + usage`.

This violates the §5.3 overview field contract and the §6.1 replay/idempotency intent: distinct facts from the same persisted row must be idempotent, not discarded because they share the row sequence.

Required fix:

Give same-row Activity facts a monotonic per-record ordering that the machine can dedupe, or make dedupe aware of record identity/kind in addition to the row sequence. The fix should include a parser-to-machine test where one raw Claude row emits both an action event and usage, and the projection reflects both.

## Minor Findings

### 3. New Activity tests leave unused helpers that surface in `just check`

Severity: minor

Files:

- `packages/activity/src/pgIntegration.test.ts`
- `packages/activity/src/service/activityIngestion.test.ts`
- Symbols: `toolResultRaw`, `lifecycleDispatch`

Evidence:

- `toolResultRaw` is declared at `packages/activity/src/pgIntegration.test.ts:110` and is unused.
- `lifecycleDispatch` is declared at `packages/activity/src/service/activityIngestion.test.ts:75` and is unused.
- `just check` exited 0, but Biome emitted slice-local unused-variable warnings for both helpers.

Concrete scenario:

The branch gate passes, but the committed diff carries dead test scaffolding in the highest-blast-radius Activity slice. This makes the new integration and ingestion tests look less intentional and adds noise to future gate output.

Required fix:

Remove the unused helpers or use them in tests that cover the missing lifecycle/tool-result cases.

## Gate Evidence

- `git status --short` before review: only `M docs/ARCHITECTURE.md`.
- Reviewed branch tips:
  - `main`: `e51efe51463ee66439f5df833236270f444f1270`
  - `feat/activity-slice-2-ingestion`: `9abd8b88f641ae937b10417a8f266afeabab31e2`
- `just check`: exited 0. The gate emitted the two slice-local unused-variable warnings listed above. It also formatted `packages/activity/src/pgIntegration.test.ts`; that formatter side effect was reverted because this review is write-restricted.
- `just test`: exited 0, `1805 passed in 221.47s`.
- `git status --short` after gates and reverting the formatter side effect: only `M docs/ARCHITECTURE.md`.

## Re-verify Delta e758750

Scope reviewed: `git show e758750` only.

Result: issue found, 1 major, 0 minor.

Closed items:

- Original major 1 data loss window is closed for a single overflow during materialization. `replayAndGoLive` now replays in a compare loop, stops the partial actor, and replays from the store when `entry.dirty` is set during the store reads.
- Original major 2 is closed. `recordBuilder` preserves the store `seq` and adds `subSeq`; the machine dedupes records by `(seq, subSeq)` while leaving lifecycle dedupe on the lifecycle cursor. `sameRowDedupe.test.ts` covers same-row action plus usage and same-row two `tool_use` records with whole-row replay.
- Original minor 3 is closed. `toolResultRaw` now drives a live PG tool-result path, and `lifecycleDispatch` now drives live lifecycle routing coverage.

New major finding:

### 4. Overflow-safe materialization can livelock under sustained hot-run traffic

Severity: major

Files:

- `packages/activity/src/service/activityIngestion.ts`
- `packages/activity/src/service/activityIngestion.test.ts`
- Symbols: `ActivityIngestion.replayAndGoLive`, `recovers records dropped by a buffer overflow that happens DURING materialization`

Evidence:

- `replayAndGoLive` uses an unbounded `for (;;)` loop and resets `entry.dirty = false` before each store replay: lines 123-133.
- If any replay sees `entry.dirty`, it stops the actor and immediately retries: lines 153-157.
- The regression test covers one overflow followed by a quiet second replay: lines 225-267. It does not cover continuous arrivals that overflow every replay window.

Concrete scenario:

1. A hot run is unmaterialized.
2. A read calls `materialize(runId)`.
3. While `store.lifecycle()` and `store.records()` are being collected, live NOTIFY traffic for that run keeps exceeding `bufferLimit`.
4. Each iteration drops the fast-path buffer, sets `entry.dirty`, and then `replayAndGoLive` discards the actor and retries.
5. Since the loop only publishes after a full replay window with no overflow, a sustained hot run can keep the materialization promise pending indefinitely. As the store grows, each replay can also take longer, making another overflow more likely.

The original data-loss bug is fixed, but the new fix depends on a quiet replay window for liveness. A live read/projection for a high-volume run can hang instead of publishing a safe actor and catching up from the store.

Required fix:

Make materialization converge without requiring a no-overflow replay window, for example by publishing a safe actor with a bounded store catch-up step, tracking a durable replay watermark, or adding another deterministic catch-up mechanism that can drain live arrivals under sustained load.

Re-verify gate evidence:

- `just check`: exited 0. Activity warnings from the first review are gone; only pre-existing web warnings remained.
- `just test`: exited 0, `1805 passed in 215.12s`.
- `git status --short` after gates: only `M docs/ARCHITECTURE.md`.

## Final Re-verify Delta e758750..bc86f85

Scope reviewed: `git diff e758750..bc86f85` only, covering commits `5ca1e86` and `bc86f85`.

Result: issue found, 1 major, 0 minor.

Closed items:

- Original major 4 materialization livelock is closed for the read path. The old unbounded discard-and-retry loop is gone; `materialize()` now does one bounded store catch-up, publishes the actor, and uses a background catch-up pump. The sustained-overflow regression makes `materialize()` resolve.
- Lifecycle terminal correctness is closed for the covered materialization-window case. A lifecycle NOTIFY during materialization sets `lifecyclePending`, and post-publish `catchUpLifecycle()` re-reads the full lifecycle stream so `run-exited` reaches the actor.
- Original major 1 and major 2 are not reintroduced in the covered paths. The fast path refuses to advance over record seq gaps, store catch-up remains source-of-truth based, and composite `(seq, subSeq)` machine dedupe is unchanged.

New major finding:

### 5. Catch-up pump can lose a queued trigger at the completion boundary

Severity: major

Files:

- `packages/activity/src/service/activityIngestion.ts`
- Symbols: `ActivityIngestion.scheduleCatchUp`, `ActivityIngestion.drainCatchUp`, `ActivityIngestion.applyContiguousOrPump`

Evidence:

- `applyContiguousOrPump` depends on `scheduleCatchUp` when a live record would skip a store seq gap: lines 228-230.
- `scheduleCatchUp` only sets `entry.pumpQueued = true` when `entry.pumping !== null`: lines 251-254.
- The active pump clears `entry.pumping` in a `finally` after `drainCatchUp` resolves, without checking whether `pumpQueued` was set in that boundary window: lines 256-258.
- `drainCatchUp` exits its loop as soon as `pumpQueued` is false after a catch-up pass: lines 261-273.

Concrete scenario:

1. A live gap schedules a catch-up pump.
2. The pump awaits `readRecordsForRunAfter()`.
3. That read resolves and `drainCatchUp` resumes first. It runs a catch-up pass, sees `pumpQueued === false`, and returns.
4. Before the `.finally()` callback clears `entry.pumping`, another NOTIFY handler that was already queued in the same event-loop turn calls `scheduleCatchUp`.
5. Because `entry.pumping` is still non-null, `scheduleCatchUp` sets `entry.pumpQueued = true` and returns without starting a new pump.
6. The `finally` callback then sets `entry.pumping = null`. Final state: `pumping === null`, `pumpQueued === true`, and no catch-up is running.

That loses the trigger that should have repaired a store-only gap or post-overflow catch-up. If it was the final NOTIFY for the run, the actor can stay stale indefinitely even though the store has the missing records.

I validated the event-loop ordering with a minimal Node probe that reproduces the same state transition: `drain returning`, then an external schedule sees `pumping` still set and queues, then `finally` clears `pumping`, leaving `pumpQueued=true` with no pump.

Required fix:

Make the completion boundary re-check queued work after clearing `pumping`, or clear `pumping` before deciding whether to schedule/queue. The invariant should be: if `pumpQueued` is true and `entry.actor` still exists, a pump is either running or definitely scheduled.

Final re-verify gate evidence:

- `just check`: exited 0. Activity warnings absent; only pre-existing web warnings remained.
- `just test`: exited 0, all suites passed. Shell: `1228 passed`; common: `9 passed`; Activity: `91 passed`; API: `1805 passed`.
- `git status --short` after gates: only `M docs/ARCHITECTURE.md`.
