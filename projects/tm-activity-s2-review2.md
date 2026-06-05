# Activity Slice 2 Review 2

Scope: full clean-eyes review of `main...feat/activity-slice-2-ingestion`.

Branch evidence:

- Branch HEAD: `1e95e80c92a3449417e0ef6c1bd4428fadeca25c`.
- Merge base with `main`: `e51efe51463ee66439f5df833236270f444f1270`.
- Commit count: `13`.
- Worktree before verdict: only `M docs/ARCHITECTURE.md`, matching the brief's unrelated dirt.
- Gates:
  - `just check`: exit 0. Biome reported warnings in unrelated canvas/inspector files; typecheck, ruff, and mypy completed cleanly.
  - `just test`: clean rerun exit 0. JS suites passed, `@tm/activity` passed `12` files / `98` tests, and API xdist reported `1805 passed`.
  - Focused real-PG Activity integration: `TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/transport_matters pnpm --filter @tm/activity exec vitest run src/pgIntegration.test.ts --reporter=verbose` passed 6 tests. A CI fail-closed probe against an unreachable PG URL failed at `src/pgIntegration.test.ts:61`, as intended.

## Findings

### 1. major: a throwing catch-up pass can permanently lose the only reconciliation trigger

Path + symbol:

- `packages/activity/src/service/activityIngestion.ts` `ActivityIngestion.applyContiguousOrPump`, `catchUp`, `pumpCatchUp`, `catchUpLifecycle`
- `packages/activity/src/service/coalescingRunner.ts` `CoalescingRunner.drain`

Evidence:

- `applyContiguousOrPump` schedules a catch-up when a live record would skip a store-only gap, then returns without applying the later event: `packages/activity/src/service/activityIngestion.ts:215`.
- `catchUp` is a single store read from `readRecordsForRunAfter` and has no retry or durable pending state: `packages/activity/src/service/activityIngestion.ts:236`.
- `pumpCatchUp` just calls that single pass: `packages/activity/src/service/activityIngestion.ts:247`.
- `CoalescingRunner.drain` consumes the queued trigger before calling the task, swallows any thrown error, and clears `running` when no later trigger arrived during the failed pass: `packages/activity/src/service/coalescingRunner.ts:39`.
- The lifecycle path has the same shape for exits during materialization: `materializeRun` clears `lifecyclePending` before `catchUpLifecycle`, and `catchUpLifecycle` swallows a read failure without rearming: `packages/activity/src/service/activityIngestion.ts:191`.

Concrete failure scenario:

1. A run is materialized with `watermark = 0`.
2. Store rows `seq=1` and `seq=2` commit, but only the NOTIFY for `seq=2` reaches Activity.
3. `applyContiguousOrPump` sees `2 > watermark + 1`, schedules the catch-up runner, and does not apply `seq=2`.
4. The store read in `catchUp` throws once due a transient PG error.
5. `CoalescingRunner.drain` swallows that throw and, because no new trigger arrived during the failed pass, clears `running` and exits.
6. If the run is now quiet, no later NOTIFY exists to re-trigger the pass. The actor remains stuck at watermark `0` even though committed rows `1` and `2` are in the store.

That violates the review contract: "every committed record is eventually applied" and "materialization converges", specifically under a throwing catch-up pass. The same one-shot failure exists for a `run-exited` row that commits during the materialization window: if the post-publish lifecycle reread fails once, `lifecyclePending` has already been cleared and the actor can stay non-terminal with no further lifecycle NOTIFY.

Expected shape:

Keep a per-run reconciliation pending state until the store read succeeds. A failed pass should either leave the runner queued, schedule retry/backoff, or expose a single retrying reconcile loop that owns both record and lifecycle catch-up. The buffer should stay a fast path, never the only remembered trigger.

### 2. minor: malformed and unrecognized record handling is not counted and logged at the ingestion boundary

Path + symbol:

- `packages/activity/src/adapters/transcriptRecords.ts` `activityRecordsFromPgEvent`
- `packages/activity/src/adapters/postgresRecords.ts` `activityRecordsFromRows`, `pgActivityEventRecordFromRow`, `runLifecycleFactFromRow`
- `packages/activity/src/service/activityIngestion.ts` `ActivityIngestion.stats`

Evidence:

- Unknown harnesses increment an in-memory per-harness map, but there is no logger and no aggregate ingestion stat: `packages/activity/src/adapters/transcriptRecords.ts:24`.
- Malformed raw records and unrecognized record payloads return `[]` silently in the parser paths, for example invalid Claude raw at `packages/activity/src/adapters/transcriptRecords.ts:38` and invalid Codex raw at `packages/activity/src/adapters/transcriptRecords.ts:80`.
- `PostgresActivityReader` maps rows with throwing coercions and does not isolate a bad row from the rest of the batch: `packages/activity/src/adapters/postgresRecords.ts:144`.
- `ActivityIngestion.stats()` reports only run and buffer overflow counts, not skipped or malformed records: `packages/activity/src/service/activityIngestion.ts:107`.

Concrete failure scenario:

A future Codex rollout record or malformed transcript row lands in the event table. Activity skips it by returning no records, but neither the listener nor ingestion can report a skipped-record count, and no log line records the bad row. The status may remain stale, while `stats()` still reports only buffer state. This misses §8's contract that malformed or unrecognized records are skipped, counted, and logged, and it leaves `transport-matters doctor` with no dropped-record source for this slice.

Expected shape:

Put skip accounting and logging at the reader/parser boundary, then surface aggregate counters through the service stats. The parser can still be conservative and keep current status, but bad input needs visible telemetry.

### 3. minor: the slice expands a secondary external import surface

Path + symbol:

- `packages/activity/src/server/index.ts` server barrel
- Contract source: `docs/ARCHITECTURE.md` "Canonical context package"; `packages/AGENTS.md` "One import surface per package"

Evidence:

- The architecture says `src/index.ts` is "the only import path for other packages" and the boundary rule is that other packages import only `src/index.ts`: `docs/ARCHITECTURE.md:53`.
- The package guide repeats that every package exposes exactly one entrypoint, `src/index.ts`, declared in the exports map: `packages/AGENTS.md:42`.
- This slice adds service and projection exports to `src/server/index.ts`: `RunActivityProjection`, `WorkspaceActivityProjections`, `ActivityIngestion`, `activityRecordToEvent`, `runLifecycleFactToEvent`, and `RunActor`: `packages/activity/src/server/index.ts:26`.

Concrete failure scenario:

Because `@tm/activity/server` already exists as an exported subpath, these new exports make Activity's service and actor internals externally importable through a second package surface. The current boundary test checks that no external source imports Activity internals; it does not fail closed when the package itself exposes another public barrel. Future packages can bind to `@tm/activity/server` and bypass the single-surface contract.

Expected shape:

Keep the server-specific runtime wiring internal until slice 3 creates the actual server surface, or route all exported service/projection types through `src/index.ts` and remove the second public barrel from the package export map.

### 4. minor: `runActivityMachine.ts` crosses the hard file-size guardrail

Path + symbol:

- `packages/activity/src/domain/runActivityMachine.ts` module

Evidence:

- The file was 622 lines on `main` and is 710 lines at this branch head.
- The slice adds same-row dedupe, status mirroring, §5.3 projection fields, and context token helpers directly to the machine module.
- Project instructions set a hard limit: new files under 700 LOC, and files over 700 LOC must be refactored before adding meaningful code.

Concrete failure scenario:

The central domain machine is now over the guardrail before slice 3 adds HTTP, SSE, and read-surface behavior. The added projection vocabulary and helper logic are coherent, but leaving all of it in the machine file makes the next change start from a policy violation and increases the chance that future status or projection edits continue to accumulate in one module.

Expected shape:

Extract pure vocabulary and helper functions that are not the state graph itself, for example usage/window-token helpers, applied-event cursor helpers, or projection/read-model vocabulary, while keeping the transition table and invariants together.

## Design Soundness Verdict

Verdict: simplify.

The approved architecture is directionally sound: Postgres as store of truth, lazy per-run materialization, a bounded buffer as an optimization, and primary-session scoping are the right primitives for a product-plane Activity context. The implementation is more complex than it needs to be at the liveness boundary. Record catch-up, lifecycle reconciliation, dirty buffers, and the coalescing runner currently form separate mechanisms, and the retry semantics fall between them. A simpler correct shape is one per-run reconcile loop: NOTIFYs and buffer overflow only mark reconciliation needed, the loop retries bounded store reads until both record watermark and lifecycle cursor are current, and telemetry owns failures. That keeps the buffer fast path optional and makes the "store is truth" invariant explicit in one place.

## Re-review Delta: `1e95e80..7f17eb33`

Scope: five-commit delta after the first review.

Branch evidence:

- Branch HEAD: `7f17eb33b8ba99b48185adce67ff101ff44add69`.
- Delta base: `1e95e80c92a3449417e0ef6c1bd4428fadeca25c`.
- Worktree before and after verdict: only `M docs/ARCHITECTURE.md`, matching the brief's unrelated dirt.
- `git diff --check 1e95e80..HEAD`: exit 0.
- Focused closure probes:
  - Activity focused Vitest set (`reconcileLoop`, `activityIngestion`, parser row isolation, same-row dedupe): exit 0, `5` files / `42` tests.
  - Boundary guard: exit 0, `1` file / `8` tests.
  - Package export fail-closed probe: `1e95e80` had export keys `.,./server` and `single=false`; `HEAD` has `.` and `single=true`.
  - Real-PG Activity integration: exit 0, `1` file / `6` tests.
  - CI fail-closed PG probe against unreachable Postgres: exit 1 at `src/pgIntegration.test.ts:61`, as intended.
- Required gates:
  - `just check`: exit 0. Biome reported the existing canvas/inspector warnings; desktop, shell, package typechecks, ruff, and mypy completed cleanly.
  - `just test`: exit 0. Desktop `49` tests, shell `168` files / `1240` tests, `@tm/common` `9` tests, `@tm/activity` `13` files / `102` tests, API `1805 passed`.

### Finding

#### 1. minor: known-harness unrecognized record types still skip without count or log

Path + symbol:

- `packages/activity/src/adapters/transcriptRecords.ts` `codexActivityRecords`, `claudeActivityRecords`
- `packages/activity/src/telemetry.ts` `DroppedRecordInfo`
- Contract source: `/Users/alphab/.mdx/projects/tm-activity-spec.md` §8

Evidence:

- The spec says malformed or unrecognized records are skipped, counted, and logged, and specifically says unrecognized record types should keep current status, count, and log: `/Users/alphab/.mdx/projects/tm-activity-spec.md:279` and `/Users/alphab/.mdx/projects/tm-activity-spec.md:287`.
- The delta counts unknown harnesses and malformed raw payloads, but its telemetry reason enum has no reason for an unrecognized record type: `packages/activity/src/telemetry.ts:11`.
- For Codex, `codexActivityRecords` only records a drop when `raw` or `payload` is malformed. A well-formed known-harness row with an unrecognized `raw.type` or `payload.type` falls through every branch and returns `records.items` without calling `sink.recordDropped`: `packages/activity/src/adapters/transcriptRecords.ts:97`, `packages/activity/src/adapters/transcriptRecords.ts:107`, `packages/activity/src/adapters/transcriptRecords.ts:119`, `packages/activity/src/adapters/transcriptRecords.ts:140`.
- The test added for drops covers unknown harness and malformed raw, but not a known-harness unrecognized record type: `packages/activity/src/adapters/transcriptRecords.test.ts:167`.

Concrete failure scenario:

A future Codex rollout row lands as:

```json
{ "type": "event_msg", "payload": { "type": "future_status_marker" } }
```

It is a known harness and well-formed JSON, but Activity does not recognize the record type. Current code returns `[]` and records no telemetry. Status stays conservative, which is correct, but the required dropped-record count and log are missing.

Expected shape:

Add an `unrecognized-record` drop reason and report it when a known-harness row is well-formed but no Activity record was produced because the type is outside the harness mapping. Keep intentional non-status records explicitly allow-listed so developer/system framing and other known ignored records do not become noisy drops.

### Closure Verdict

The major liveness finding is closed. `ReconcileLoop` retries thrown record reads and lifecycle rereads with backoff, does not clear reconcile-needed on failure, honors triggers that arrive during or at the completion boundary, and converges when caught up.

The reconcile design is now sound: one per-run loop, no in-memory buffer, NOTIFY only marks reconcile-needed, store reads advance a monotonic watermark, actor dedupe keeps re-reads idempotent, and lifecycle terminal state is reread in the same pass.

The server barrel finding is closed. `@tm/activity/server` is removed from the exports map, `src/server/index.ts` is gone, and the boundary guard is non-vacuous against the old export shape.

The file-size finding is closed. `runActivityMachine.ts` is `402` lines; `runActivityContext.ts` and `usage.ts` are pure, coherent extractions, while the transition table and invariants remain together.

Design verdict: sound, with one remaining minor telemetry bug in the parser boundary.
