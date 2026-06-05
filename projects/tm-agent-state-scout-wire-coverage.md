# Scout — wire-plane coverage of the canonical agent-state model (PR-3 scope)

Scout & Plan pass mapping how the merged wire store (PR-1 #258 + PR-2 #259, main
`157f781`) can surface the FULL canonical agent-state model versus today's
transcript-driven `runActivityMachine`. Citations are file + symbol. Tree
pristine at `157f781` throughout.

Canonical model: `active{reasoning|generating|running_tool}` ·
`needs_you{gated{permission|plan_review|auth}|asked{question}}` · `idle` ·
`terminal{done|error}`. TM overlays `starting`/`stalled` are noted where relevant.

**Headline: the producer side is DONE and shipping dark.** Every signal PR-3
needs is already persisted and NOTIFYed by main: `SessionWriter.submit_wire_exchange`
commits the exchange (with `stop_reason`, `response_error`, `track_role`, `ts`)
plus `wire_response_block` rows (`block_type`, `tool_use_id`, `tool_name` — with
a partial index `wire_response_tool_ix` built for exactly the ask query), then
fires a `wire_exchange` / `wire_exchange_deleted` NOTIFY on `tm_events` carrying
`run_id`/`exchange_id`/workspace/owner. `parseTmEventsPayload` currently returns
`undefined` for those types, which is why it ships dark. PR-3 is therefore a
**pure product-plane slice** (packages/activity only; zero frozen-plane edits;
one optional additive migration, see D1).

Coverage summary: the wire authoritatively and durably surfaces
`needs_you{asked}`, and surfaces `idle` and `running_tool` onset live at
finalize; `gated{permission|plan_review|auth}` is confirmed wire-impossible;
mid-turn `reasoning`/`generating` and `terminal{done|error}` stay with the
transcript and lifecycle planes.

## 1. State coverage matrix

| Canonical state | Wire-surfaceable? | Wire-IR signal | Timing | Authority vs transcript derivation |
|---|---|---|---|---|
| `active.reasoning` | Retrospective only | `ThinkingBlock` rows (`wire_response_block.block_type='thinking'`) | At finalize, when the turn is already over | **Redundant.** Transcript journals Claude thinking rows and Codex `reasoning` response_items progressively mid-turn (`transcriptRecords.ts:claudeRow`/`codexRow`); the wire learns them only after the fact. Recommend emitting nothing (see §5). |
| `active.generating` | Retrospective only | `TextBlock` rows (`block_type='text'`) | At finalize | **Redundant**, same reasoning. |
| `active.running_tool` | **Yes, live onset** | `stop_reason='tool_use'` (Claude, `adapters/anthropic.py` SSE fold) / Codex status via `response_parser.py:_response_stop_reason` → `codex_response_status_reason`, plus non-ask `tool_use` blocks | At finalize — the turn ended handing tool calls to the harness, so finalize IS the moment the run enters tool execution | **Supplementary live, authoritative for restart.** Transcript's `tool-use` rows land near-simultaneously when journaled; but only the wire row proves it after a gateway restart (reconcile). Caveat: wire cannot distinguish running from permission-gated (see `gated`). |
| `needs_you.asked` | **Yes, live + durable** | `ToolUseBlock` with `tool_name` ∈ {`AskUserQuestion`, `request_user_input`} on the finalized response (`wire_response_block.tool_name`, pre-indexed by `wire_response_tool_ix`) | At finalize = ask time | **Authoritative.** The transcript structurally cannot carry it live: Claude Code defers journaling the AskUserQuestion assistant row until answered (cm 019f49cd, verified on real run 2239c60f). This is the state PR-3 exists for. |
| `needs_you.gated.permission` | **No — confirmed** | none | — | The approval decision is client-side between turns. The wire sees the `tool_use` finalize, then silence until the post-approval NEXT request (which already embeds the `tool_result`). Allowlist/permission-mode state never crosses the provider wire; Codex approval events are harness-protocol, excluded even from rollouts (`codex-rs/rollout/src/policy.rs`, cm 019f4920). A finalize with pending non-ask tools is `running_tool` OR gated — wire-indistinguishable. Stays Slice 2 (Codex structured) / Slice 3 (Claude PTY). |
| `needs_you.gated.plan_review` | Heuristic only — do not ship | `ToolUseBlock(name="ExitPlanMode")` is wire-visible | At finalize | The block proves a plan was presented, not that the client is gating (auto-accept modes approve without a prompt, client-side). At best a low-confidence hint for the gate slice; deriving canonical `gated` from it would fabricate certainty the wire does not have. |
| `needs_you.gated.auth` | **No — confirmed** | none | — | Auth flows (OAuth, `gcloud auth login`, API-key errors surfaced in-terminal) never traverse the captured provider path as state; nothing to read. |
| `idle` | **Yes, live** | `stop_reason` ∈ {`end_turn`, `max_tokens`} (Claude) / Codex completed status | At finalize = exactly turn end | **Redundant live** (transcript `turn-end` from the same stop_reason arrives promptly) but **authoritative for restart**: a fresh reconcile can prove idle from the last stored exchange with no in-memory history. |
| `terminal.done` / `terminal.error` | **No** | none | — | Process exit is lifecycle-plane (`run_lifecycle_event` via the launch path, `RunLifecyclePayload`). The wire never sees process death; the last exchange looks identical whether the process is alive-idle or exited. `run.exited` stays lifecycle-only. |
| Turn anomaly (feeds `stalled` overlay) | Supplementary | `stop_reason='refusal'` / `wire_exchange.response_error` (provider error object, `wire_store.py:_response_error`) | At finalize | Transcript already maps refusal via `CLAUDE_STOP_REASON_OUTCOMES` → `transcript-error`; the wire adds durability and catches provider errors the harness may not journal. Same fold target, idempotent. |
| `starting` (TM overlay) | No | Request-side visibility would need a provisional-time fire; the sink contract is single-fire-at-finalize (spec §4) | — | Transcript `turn-open` covers it. |

## 2. Timing reality (load-bearing)

The `ExchangeSink` fires exactly once per exchange, at finalize
(`storage/exchange_sink.py:emit_to_index`; the corrected single-fire contract,
spec §4). `WireStoreObserver.on_exchange` → `SessionWriter.submit_wire_exchange`
→ commit + NOTIFY, serialized one-in-flight per store
(`wire_store_observer.py:_serialized`). So the wire plane is an **end-of-turn
oracle**: it knows how every assistant turn ended, live at the moment it ends,
and durably.

- **Finalize-knowable (live on the wire):** `asked` (ask block present),
  `running_tool` onset (`stop_reason='tool_use'`), `idle` (`end_turn`/`max_tokens`),
  turn anomaly (`refusal`/`response_error`). All are terminal facts of the turn,
  available the instant the turn closes.
- **Not wire-knowable live:** mid-turn `reasoning`→`generating`→tool streaming
  progression. There is no per-chunk product-plane stream (the SSE tee in
  `response_stream.py` is api-plane internal, reduced to name-less `ResStats`
  on the browser SSE). These remain transcript-driven — and the transcript is
  genuinely live for them (Claude journals per-content-block rows mid-turn;
  Codex journals response_items).
- **Tool completion** is wire-visible only inside the NEXT request's messages
  (the `tool_result` blocks), i.e. later than the transcript's `tool-result`
  row. The wire adds nothing there.
- **Deletions:** `wire_exchange_deleted` NOTIFY fires only when a stored row
  actually went away (`submit_wire_exchange_deleted`); for state derivation it
  is just a reconcile trigger (re-read heals).

## 3. Reuse map (re-mapped against main `157f781`)

Producer side — complete, no work:

- `storage/exchange_sink.py`: multi-subscriber registry (`register_exchange_sink`,
  `register_exchange_deleted_sink`) — the asked seam from the prior scout is MERGED.
- `wire_store_observer.py:WireStoreObserver` — feeds finalize + deletions into the store.
- `session/writer.py:submit_wire_exchange` / `_wire_exchange_notify_payload` —
  NOTIFY-as-trigger on `tm_events` with `WIRE_EXCHANGE_PAYLOAD_TYPE = "wire_exchange"`
  and `WIRE_EXCHANGE_DELETED_PAYLOAD_TYPE = "wire_exchange_deleted"`
  (`session/wire_contracts.py`), payload `{run_id, exchange_id, workspace_slug,
  workspace_hash, owner}` — exactly the routing shape `markReconcileNeeded` needs.
- Store: `wire_exchange` (per-run indexed: `wire_exchange_run_ix (run_id, ts)`;
  `track_role` CHECK ∈ {`parent`,`subagent`} per `WIRE_TRACK_ROLES`) +
  `wire_response_block` (`tool_name` partial index) — migration
  `api/migrations/versions/0008_wire_store.py`.

Consumer side — existing owners for every PR-3 touch:

- `packages/activity/src/server/pgContracts.ts` — add the two wire payload-type
  consts + wire table/column consts (pattern in place).
- `packages/activity/src/ports.ts` — `WireExchangePayload` types joining the
  `TmEventsPayload` union; a narrow wire record DTO (see Quality item 6).
- `packages/activity/src/adapters/tmEvents.ts:parseTmEventsPayload` — two new
  cases (per-type parse-function pattern in place; malformed → `undefined`).
- `packages/activity/src/adapters/postgresRecords.ts:PostgresActivityReader` —
  new reader method over `wire_exchange` ⋈ `wire_response_block`
  (`readWireRecordsForRunAfter`), sibling to `readRecordsForRunAfter`.
- `packages/activity/src/service/activityIngestion.ts` — `ActivityStore` gains the
  wire read; `RunIngestionEntry` gains a wire watermark; `reconcile` reads the wire
  tail. `markReconcileNeeded` already routes any payload by `payload.runId` — the
  handler change is nearly nil.
- `packages/activity/src/domain/runActivityContext.ts` — `RunActivityEventStream`
  gains `"wire"`; `eventStream`/`initialSeqCursors` are module-private and extended
  in place; **folds reused unchanged** (`foldQuestionAsked`, `foldTurnIdle`,
  `foldToolUse`, `foldTranscriptError`).
- Unchanged: `runActivityMachine.ts` (with the stream-discriminator design, §5),
  `domain/wireStatus.ts:wireStatusFromMachineState`, `@tm/contract/activity`
  (`activityStatuses`, `activityStatusTier`, `needsYouForStatus` — enum already
  complete), `projections/workspaceActivity.ts`, `RunVitalsStrip.tsx` (derives
  via `activityStatusTier`), `reconcileLoop.ts`, `gatewayDeps.ts` (composition
  root unchanged in shape).

None found (searches run): no consumer of `wire_exchange` anywhere in
`packages/` (rg `wire_exchange` → wire_contracts/api only — confirms ships-dark);
no shared ask-tool-name constant (literals inline in `transcriptRecords.ts`
`claudeRow`/`codexRow` only); no existing wire-plane reader or cursor type in
`@tm/activity`. New code justified at exactly those three points.

## 4. Read surface vs live signal — one PR

Two concerns, one honest answer:

- **(a) Activity read path over the wire store** (reconcile reads the run's wire
  tail) and **(b) the live wire→state signal** (NOTIFY marks reconcile-needed)
  are **one PR — they are the same mechanism.** In this architecture the NOTIFY
  is only a trigger; the state always comes from the store read (§7.1
  store-as-data). A live signal without the read path cannot survive restart
  (the spec's headline acceptance); a read path without the NOTIFY case is not
  live. Splitting them would ship two halves of one loop. This is PR-3 exactly
  as spec §8 sizes it.
- **The general owner-scoped wire READ SURFACE** (browse persisted exchanges,
  request manifests/blob hydration, omit raw bytes — the inspector-facing
  product surface) is a **different deliverable**: new router surface, blob
  hydration, pagination, and an owner-scoping decision `wire_exchange` cannot
  answer alone (it has NO `owner` column; owner rides the NOTIFY only, so a
  browse query must join through `session`/`run_lifecycle_event` or add a
  column). No consumer exists yet. Keep it out of PR-3; spec it when a consumer
  is real (NOW.md discipline).

Proposed slice = **one PR (PR-3), five commits:** (1) contracts + payload types
+ `parseTmEventsPayload` cases, red-first parse tests; (2) reader method + SQL
(+ optional D1 migration); (3) domain `"wire"` stream/cursor; (4) ingestion wire
watermark + reconcile wiring; (5) projection wiring + the spec's acceptance
tests (live path, survives-restart, answered flow, isolation).

## 5. Composition — third "wire" stream over existing folds

Fits the prior-proposed third stream with **zero new machine states and zero new
folds**. Recommended shape: **reuse the existing `record.*` event types with an
explicit stream discriminator field** (`stream?: "wire"` on
`BaseRunActivityEvent`, read first by `eventStream()`), rather than minting
`wire.*` twin event types. The 589-line transition table in
`runActivityMachine.ts` then gains nothing; `isNewEvent` dedupes wire events on
the new `seqCursors.wire`; the session-rotation shortcut can never claim a wire
event because `eventStream()` checks the discriminator before `sessionId`
(prior scout Quality item 6).

Per-exchange derivation stays minimal — at most ONE status record per finalized
exchange, plus usage if desired later:

- ask block present → `question-asked` (wins over stop_reason; an ask turn ends
  `tool_use`).
- else `stop_reason='tool_use'` → `tool-use` (wire carries `tool_use_id` for
  `pendingToolCallIds` hygiene; the answering `tool_result` arrives on the
  transcript stream and `pendingAfterToolResult` clears it — cross-stream by
  design, ids are shared vocabulary).
- else `end_turn`/`max_tokens` → `turn-end`.
- else `refusal`/`response_error` → `transcript-error`-style anomaly.
- **No wire `reasoning`/`generating` events**: at finalize they are already
  history; the terminal record alone produces the same observable end state
  (observable-end-state testing discipline).

Override vs defer:

- `asked`: **wire wins** (live and only live source). The transcript's late
  `question-asked` (journaled on answer) replays as the existing harmless
  self-transition on `needs-you-asked`, immediately followed by the answer's
  `tool_result` → `reasoning`. Independent cursors prevent double-fire — the
  spec's answered-flow acceptance.
- `idle` / `running_tool` / anomaly: **equal claim, same fold target** — both
  planes converge on the same state; replays are idempotent. No winner needed.
- `reasoning`/`generating`: **transcript wins by omission** (wire emits nothing).
- `terminal`: **lifecycle wins by omission** (wire never emits `run.exited`).
- **The one true blind-spot conflict:** a finalize with pending non-ask tools
  projects `running-tools` while the harness may actually be permission-gated.
  The transcript is equally blind (no pending-permission row exists, cm
  019f4920), so no plane conflicts today — but when Slice-2/3 gate detection
  lands, `gated` must OVERRIDE wire-derived `running-tools` (a needs_you from a
  higher-fidelity plane outranks an optimistic active). Composition should not
  hard-code wire-wins.
- **Subagent isolation:** derive wire records only from
  `track_role IS DISTINCT FROM 'subagent'` rows (SQL-level, mirroring the
  primary-session filter in `postgresRecords.ts`) — spec acceptance names it;
  the column and CHECK vocabulary (`parent`/`subagent`) are already stored.

Wire cursor identity (the one real design gap): `wire_exchange` has no seq.
Numeric `seqCursors` wants a monotonic integer. Options:
(1) epoch-ms of `ts` — collision-prone and shaped wrong for the cursor contract;
(2) **additive `wire_seq bigint GENERATED ALWAYS AS IDENTITY` column
(recommended)** — one migration, zero writer-code change, replay-stable (the
UPSERT's `DO UPDATE` never touches it), per-run monotonic in commit order
because `WireStoreObserver._write_slot` serializes writes. See D1.

## 6. Quality map (existing wire + activity code, hygiene lenses)

1. `runActivityMachine.ts` at 589 LOC is nearing the 700 guardrail and its eight
   state blocks are near-identical transition bags (duplication signal). The
   stream-discriminator design adds zero lines; any `wire.*` twin-event design
   would duplicate ~40 transitions and must be rejected. If the gate slice later
   adds a machine state, refactor the table (shared transition-map builders)
   before adding it.
2. Naming collision, three meanings of "wire" in one package:
   `domain/wireStatus.ts` (machine→DTO mapping), `@tm/contract` "wire DTOs"
   (browser seam), and now the wire PLANE. Name new modules explicitly
   (`wireExchangeRecords.ts` adapter, `WireExchangePayload`), and say "wire
   plane" in doc comments.
3. Ask-tool literals (`"AskUserQuestion"`, `"request_user_input"`) live inline
   in `transcriptRecords.ts` and the wire reader needs the same set — extract a
   shared `askToolNames` const (natural owner: `adapters/harnessRegistry.ts`,
   which already owns harness vocabulary) before a third copy appears.
4. `RunIngestionEntry.watermark` is record-stream-specific; the wire stream
   adds a sibling cursor. Generalizing to a per-stream map is a small internal
   cleanup worth doing while touching the struct, not a new abstraction layer.
5. `wire_exchange` has no `owner` column (owner rides the NOTIFY only). Fine
   for run-scoped PR-3 reads; the future browse surface needs a join-vs-column
   decision. Flag only.
6. Do not stuff wire-derived records into `ActivityRecord`: it is already an
   optional-field bag (prior scout item 4) and its `sessionId: string` is
   required while `wire_exchange.session_id` is nullable. A narrow
   wire-record DTO (exchange_id, wire_seq, ts, kind, toolCallId?) that maps to
   the same `RunActivityEvent` types keeps the boundary clean.
7. `parseTmEventsPayload` grows to four cases — the per-type parse-function
   pattern holds; no refactor needed.
8. No dead code found in the merged wire path. The browser SSE exchange stats
   (`ResStats` → `exchangeStreamEvents.ts`) now conceptually overlaps the
   NOTIFY signal (two live finalize surfaces); not code duplication, but a
   convergence candidate for a later slice. Note only.

## 7. Plan

**PR-3 (one PR, product plane only + optional D1 migration):** commits as in §4;
red-first per spec §8 PR-3 acceptance (payload parse cases; live ask → 
`needs-you-asked` with `needs_you {kind:"asked"}`; **fresh-ingestion
reconcile-alone projects asked (the survives-restart test that fails first)**;
answered flow with no transcript regression; wire events never advance the
record watermark; subagent asks do not flip the primary tier). Assert projected
status/`needs_you` consumers read, never intermediate mappings.

**Gates, verbatim:** `cd api && just ci` (runs if D1 migration lands); repo root
`just check`; `just test` (full suite — persistence + contract-adjacent change);
`pnpm --filter @tm/shell test`. Judge background gate runs by output content,
not piped exit codes.

Decisions needed (Stuart):

- **D1 — wire cursor:** additive `wire_seq` identity column on `wire_exchange`
  (recommended; one migration, no writer change) vs a composite `(ts,
  exchange_id)` cursor with a reshaped domain cursor type (no migration, more
  domain surgery).
- **D2 — derivation breadth:** all finalize-knowable states (asked +
  running-tools + idle + anomaly; recommended — same reader row, near-zero
  marginal code, and the brief scopes PR-3 to every wire-supportable state) vs
  asked-only minimum.
- **D3 — plan_review heuristic** (`ExitPlanMode` wire block): defer to the gate
  slice (recommended) — shipping it as canonical `gated` would fabricate
  certainty the wire lacks.
