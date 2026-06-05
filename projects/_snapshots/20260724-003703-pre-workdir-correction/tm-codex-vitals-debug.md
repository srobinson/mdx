# Codex vitals root-cause debug (claude family) — F1 stuck "Responding", F2 "0 tok"

Read-only investigation on branch `codex-live-asked-producer`. Grounded in the real Codex-40 run
`a2e44b3e-3828-47bf-a8e6-e07653a1282c` (started 11:17, 6 turns, last turn 11:19:22, workspace
`dev-helioy-transport-matters/ecd9b0df`) plus the live Postgres store (`localhost:55432/transport_matters`).
The capturing runtime is an editable install of this repo; the run's mitmdump proxy (pid 64680) started
11:17 and executed the PR1 working tree.

**Note on tree state:** the checkout was NOT pristine at investigation start. It sat on
`codex-live-asked-producer` with PR1's changes uncommitted (the builder's in-flight work); mid-investigation
the builder committed them as `ace6647 feat(activity): emit live Codex asked status`, after which the tree is
clean. I made no writes; the diff content I analyzed is identical before and after the commit.

## Verdict

- **F1** (chip stays "Responding" after the final message, never returns to Idle): pre-existing, **PR1=no**.
- **F2** ("0 tok" despite real usage on every turn): pre-existing, **PR1=no**.
- Both share one root: **the Codex status/usage markers never cross the Activity reader boundary**, and the
  live plane that would otherwise cover the gap **never produces a single row for Codex websocket runs**.

## Ground truth from the captured bytes and stores

- Final turn `67490685` transport.json (35 ws frames): text deltas frames 9–30, then
  `response.completed` frame 34 with **full usage** (`input_tokens: 25647`, `cached_tokens: 24320`,
  `output_tokens: 66`, `total_tokens: 25713`). The wire truth is complete.
- index.jsonl (tier-1 finalize plane): every turn carries real usage (in 9.6k–25.6k, out up to 187,
  cache_read up to 24.3k). Wire parsing is not the drop point.
- `wire_exchange` in pg: all 6 exchanges finalized, `stop_reason = completed`, no errors.
- `run_live_status` in pg: **zero rows for this run — ever** (no delete path exists for that table, so none
  were written). All 9 rows in the table are Anthropic (`message_stop`/`message_delta` provider events),
  proving the observer writes fine when it gets a run identity.
- `event` table: the transcript has both missing signals — seq 47 `event_msg token_count` with
  `last_token_usage {input 25647, output 66, total 25713}`, and seq 48 `event_msg task_complete`. **Both are
  stored with `kind = 'meta'`.** The assistant message (seq 46, `response_item message`) is `kind = 'turn'`.
- Run log (`logs/mitmdump.log`, 1238 lines): no live-status warnings or exceptions. Every guard that can
  decline the live tap is silent by design.

## F1 — generating never retracted at Codex `response.completed`

The chip's "Responding" is set by the **record plane**: the assistant `message` response_item (seq 46,
`kind='turn'`) maps to a `generating` record via `transcriptRecords.ts codexRow`. Nothing ever moves the
machine off it, because all three retraction paths are dead for Codex:

1. **Live plane is dead for Codex websocket runs (the load-bearing defect).**
   `addon_handlers.handle_codex_websocket_message` passes
   `run_id=getattr(request_state, "run_id", None)` to `LiveStatusObserver.observe_codex_payload`. That flow
   state is captured at WS INIT by `request_pipeline.capture_codex_initial_request_ir`, which calls
   `capture_request_flow_state` **without `run_id`** (defaults None). The correct value is computed three
   lines later in the same WS INIT block (`run_id = binding.run_id ...`, `addon_handlers` turn-rotation path)
   and used for `run_pipeline`, but is never written back into flow state, and
   `update_request_flow_state` has no run_id field. So every `observe_codex_payload` call carries
   `run_id=None` and `LiveStatusObserver._install_tap` silently declines (`not run_id` guard). Result:
   no live `generating` row, and no live terminal at `response.completed` — the classifier support exists
   (`codex_terminal_status` maps `response.completed` → terminal; `CodexLiveClassifier._feed_one` emits the
   kind=null stop) but is unreachable. Contrast: the HTTP path (`addon_handlers.handle_http_request`) does
   pass `run_id = binding.run_id` into `capture_request_flow_state`, which is why Anthropic rows exist.
2. **Record-plane turn-end is dead code for Codex.**
   `index/adapters/codex.py CodexAdapter.normalize` skips every `event_msg` ("streaming UI events,
   duplicative of the response_items"), so `task_complete` is stored `kind='meta'`; the Activity reader
   (`postgresRecords.ts EVENT_KIND_TURN_FILTER`, from `pgContracts.ts EVENT_KIND_TURN`) reads only
   `kind='turn'`. The mapping `task_complete → turn-end` in `transcriptRecords.ts codexRow` therefore never
   executes, so `record.assistant_turn_ended` never fires and the machine cannot reach `idle`.
3. **Wire idle candidate is refused, by design.** The finalized exchange yields an `idle` candidate
   (`wireCandidateFromSnapshot`), but idle/anomaly admission requires a cold start
   (`recordSessionId === null && liveStatusObserved`, per #268); this run has a transcript session and no
   live row, so it is refused — correct behavior, since warm-run idle is supposed to come from the
   transcript turn-end that leg 2 drops. No retraction fires either (no wire/live assertion was held).

Net: `generating` persists after `response.completed` until the machine's generating silence timeout flips
it to Stalled. The observed 18s "Responding" is this window.

**PR1 relation: none.** The `observe_codex_payload` threading is slice 3 (#264); the adapter meta-skip and
reader filter predate the realtime work. PR1's asked classifier/lane changes never executed during the road
test — **which also means PR1's own producer cannot emit `asked` rows on a real Codex run until the run_id
threading is fixed; its live path is only exercisable by tests today.** The road test could not have
validated PR1's feature.

## F2 — "0 tok" despite real usage

`context_tokens`/`total_usage` in the vitals payload (`activityRouter.ts`, from
`workspaceActivity.ts` projection) are folded from the machine's `usage` record events. For Codex the only
transcript usage carrier is `event_msg token_count` — same fate as `task_complete`: stored `kind='meta'` by
`CodexAdapter.normalize`'s event_msg skip, filtered out by `EVENT_KIND_TURN_FILTER`, so the
`token_count → usage` mapping in `transcriptRecords.ts codexRow` (including its cached-share split
`codexUsage`) is dead code. Zero usage events reach the machine → `usageTotals` stays empty → "0 tok".
Claude works because its usage rides assistant transcript rows that are `kind='turn'` (`message.usage`).

**PR1 relation: none.** Pre-existing since the Codex activity mapping landed.

## Fix directions (not applied — read-only brief)

- Thread run identity into the Codex ws flow state: pass `run_id` (and ideally the track assignment already
  computed) into `capture_codex_initial_request_ir` → `capture_request_flow_state`, mirroring
  `handle_http_request`. This single seam revives the entire Codex live plane (generating, terminal
  retraction at `response.completed`, and PR1's asked producer).
- Let Codex turn-end/usage cross the reader boundary: either persist `task_complete`/`token_count` as
  `kind='turn'` in `CodexAdapter.normalize` (they are status-bearing, not duplicative for Activity), or
  widen the Activity read filter for the harness. The TS mappings in `codexRow` already exist and are
  tested; only the substrate withholds the rows.

## PR-A verification (codex-runid-threading @ f1a3042) — clean

Follow-up review of the fix for leg 1 above. The diff is 2 production files (+6/-1 effective):
`addon_handlers.handle_codex_websocket_message` moves the pre-existing
`run_id = binding.run_id if binding is not None else get_settings().run_id` line above the capture and
passes it into `capture_codex_initial_request_ir`, which grows a required keyword-only `run_id` param and
threads it into `capture_request_flow_state`. This is the exact chain diagnosed, and it REUSES the same
seam the Anthropic path uses (`handle_http_request` computes run_id with the identical expression) — the
line was literally moved, not reinvented; the keyword-only no-default param means future call sites cannot
silently omit it (single call site today).

- New end-to-end test (`test_codex_live_status_flow.py`) drives the REAL handler over redacted Codex-40
  frames into a real Postgres writer: passes at f1a3042 with 3 kind writes (reasoning, generating,
  running_tool) each polled back from the store.
- **Mutation check:** unthreading run_id (capture with `run_id=None`) makes the test fail with
  `expected live row kind='reasoning', found None` — zero rows, the exact pre-fix production state. So the
  pre-0/post-3 claim is real (3 = applied kind writes; the table itself is single-row-per-run latest-wins,
  so "3 rows in the table" would be the wrong reading).
- Adjacent suites green: 201 passed (`test_addon_http_provisional`, `test_live_status_observer`,
  `test_live_status`, full `codex/` package).
- Residual None paths, all pre-existing and shared or intended: (a) `binding is None` and
  `get_settings().run_id` unset — same residual the Anthropic path has (shared seam); (b) unparseable
  initial client frame — capture returns before flow state is written, handler clears state, that turn has
  no live rows (pre-existing unparsed-exchange path); (c) missing generation if provisional persist fails
  (pre-existing); (d) subagent track_role declines the tap (intended guard). No identity remint: run_id
  comes from the per-proxy binding at every turn rotation.

## Method note

No instrumentation was added and nothing was executed against the tree; all evidence is captured bytes
(transport.json frames), tier-1 index.jsonl, live Postgres rows, the run's mitmdump log, and static tracing
of the committed/in-flight code. Tree left untouched (clean at `ace6647`).
