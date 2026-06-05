# Evidence — vitals strip "always Thinking" + empty-at-spawn (Phase 1, facts only)

Scope per narrowed brief: A' active-state labels, B empty-at-spawn, C tools-turn
transition trace. Main `ef52af6`, tree pristine. Evidence sources: code (file +
symbol) and the dev store (`postgresql://localhost:55432/transport_matters`,
read-only), including Stuart's actual test run `437a5042` (spawned 12:53:17Z,
"Hello" turn 12:53:55–12:54:31).

**Headline: "always Thinking" is COMPUTED-BUT-TEMPORALLY-COLLAPSED, and
empty-at-spawn is a structural absence from the owner-scoped runs query.** The
label map is complete and distinct; the machine performs every transition; the
distinct statuses do reach the strip — but Claude Code journals content-block
rows only at block completion and commits them in batches, so the
running-tools and generating windows are sub-frame while all streaming time
rests in `reasoning`.

## A'. Status → label map (active states + idle)

`RunVitalsStrip.tsx:STATUS_LABELS` (www/packages/canvas/src/workbench/chrome/),
rendered at `STATUS_LABELS[vitals.status]`; `vitals.status` is the projection's
`ActivityStatus` (machine state via `wireStatusFromMachineState`, projections/
`workspaceActivity.ts:runActivityProjection`):

| Machine status | Strip label |
|---|---|
| `starting` | "Starting" |
| `reasoning` | **"Thinking"** — the ONLY status that renders "Thinking" |
| `generating` | "Responding" |
| `running-tools` | "Tools" |
| `idle` | "Idle" |
| (`stalled` / `exited`, for completeness) | "Stalled" / "Exited" |

There is no label collapse: every active state has a distinct label.

## B. Empty-at-spawn

Render condition: `RunVitalsStrip.tsx` renders `data-empty` whenever
`useRunVitalsStore.byRunId[runId]` is `undefined` (its doc comment says "empty
until the stream has a record"). `byRunId` is fed exclusively by SSE frames:
`runVitalsStore.applyFrames` ← `useWorkspaceActivityStream` ←
`GET /v1/workspaces/{id}/activity/stream` (`transport.ts:
workspaceActivityStreamUrl`).

Why a fresh pane's run is in no frame:

1. Snapshot and refresh both come from
   `WorkspaceActivityProjections.listWorkspaceActivity` →
   `PostgresActivityReader.runsForWorkspace` → `RUNS_BY_WORKSPACE_SQL`, which
   **INNER JOINs `session` ON run_id** (the `owner` gate lives on
   `session.owner`; `run_lifecycle_event` has no owner column).
2. At spawn only the lifecycle row exists:
   `capture_rpc.py:prepare_capture` → `_emit_lifecycle(RUN_STARTED)` (verified:
   `run_lifecycle_event` row for `437a5042` at `12:53:17.435`, workspace
   `dev-helioy-transport-matters/ecd9b0df`, launch_kind `canvas`). A `session`
   row is inserted only when the transcript tailer first ingests the run's
   session (the `SessionWriter` path) — i.e. at the first turn.
3. Store proof: run `44612e09` (run-started `12:32:28`, **zero turns**) has NO
   `session` row → excluded by the INNER JOIN → never appears in any snapshot
   or delta. Run `437a5042` has a session row and first event commit at
   `12:53:55.607` — it enters the stream only at its first turn.
4. The delta path is gated identically: `subscribeWorkspaceActivity`'s
   `scopedListener` drops deltas for runs not in `ownerRuns` (the last
   `listWorkspaceActivity` summary set), so even a materialized actor could not
   reach the strip before the summaries include the run.

Consequence: the `starting` → "Starting" label exists in the map but is
unreachable for a fresh pane through this pipeline; the strip is structurally
empty until the first transcript ingest creates the session row.

## C. Tools-used turn: transitions computed, windows sub-frame

Raw store evidence for `437a5042`'s turn (`event` rows, `kind='turn'`;
`ts` = the row's journal timestamp, `created_at` = Postgres commit time):

| seq | ts (journal) | created_at (commit) | row | blocks | stop_reason |
|---|---|---|---|---|---|
| 10 | 12:53:55.559 | 12:53:55.862 | user | "Hello" | |
| 19 | 12:54:08.711 | **12:54:09.548** | assistant | thinking | tool_use |
| 20 | 12:54:09.335 | **12:54:09.548** | assistant | tool_use | tool_use |
| 21 | 12:54:09.371 | **12:54:09.548** | user | tool_result | |
| 23 | 12:54:30.234 | 12:54:31.074 | assistant | text | end_turn |

Machine transitions (all computed — Slice-1 active-tier split is fully
present): `transcriptRecords.ts:claudeRow` maps thinking→`reasoning`,
tool_use→`running-tools`, tool_result→(no pending)→`reasoning`,
text→`generating`, and the SAME text row's `stop_reason=end_turn` appends
turn-end→`idle` (subSeq 0,1 on one row). Each transition that changes the
projection reaches the strip: `WorkspaceActivityProjections.run` subscribes to
the actor and `store()` emits an SSE delta per projection change
(`sameRunActivityProjection` guard) → `runVitalsStore`.

The wall-clock reality that produces "Thinking the entire time":

- **12:53:55.9 → 12:54:09.5 ("Thinking", 13.6s):** after turn-open the machine
  is `reasoning`; the thinking row's own journal ts is 12:54:08.7 — Claude Code
  writes a content-block row only when the block COMPLETES, so no row exists
  while thinking streams.
- **12:54:09.548 (one commit batch):** thinking + tool_use + tool_result all
  commit together — the tool ran in 36ms (ts 09.335 → 09.371). One reconcile
  pass folds `reasoning → running-tools → reasoning` back-to-back; the
  "Tools" delta exists for sub-frame time.
- **12:54:09.5 → 12:54:31.0 ("Thinking", 21.5s):** ZERO transcript rows while
  the final response streams; the machine rests in `reasoning` the whole time.
- **12:54:31.074:** the text row lands carrying generating AND end_turn —
  `generating → idle` fold in the same batch, so "Responding" is never
  visible; the strip flips straight to "Idle".

Wire plane (PR-3) adds nothing in this shape, correctly: exchange 1
(`stop_reason=tool_use`) finalizes into the same commit window as the
tool_result that resolves its ids, and the reconcile pass applies records
before the wire snapshot, so the wire running-tools candidate is refused by
the causal-resolution contract (`wireCandidateAdmitted`); exchange 2
(`end_turn`) corroborates the transcript's idle.

**Answer to computed-vs-collapsed:** `running_tool` and `generating` are
COMPUTED and DELIVERED, but temporally collapsed — the transcript plane
journals at completion boundaries, so the states that would show "Tools" and
"Responding" exist for milliseconds, and every streaming interval (thinking
and text generation alike) rests in `reasoning` = "Thinking". This is a
source-granularity property of the record stream, not a display-map defect
and not a missing machine transition.
