---
title: PR #264 adversarial review — realtime slice 3 (live producer on the frozen capture plane)
type: review-findings
reviewer: claude
pr: 264
branch: realtime-slice3-producer-emit
head: 91ed6e8f8417815280f7f0beba85d21c88d0e456
spec: ~/.mdx/projects/tm-realtime-spec.md (§4.3, §4.4 red tests 1-9, §7 row 3)
date: 2026-07-11
verdict: 1 MAJOR, 2 MINOR, 0 BLOCKER
reverify: CLEAN at d0ccb6daf9317948aa8ab5f8d94c9d58349c8e77 (see Delta re-verification)
---

# Verdict

The frozen plane is intact and mutation-proven: byte identity, exception
isolation, non-blocking scheduling, Tier-1 manifest parity, subagent skip,
abort terminal, and the server-frames-only guard all have load-bearing red
tests. The MAJOR is producer-side: the observer's per-run tap-order guard
permanently mutes the active turn's live facts when a concurrent same-run
parent-role flow installs a newer tap — demonstrated with a red test in a
scratchpad clone and grounded in Stuart's real captures, which contain
exactly this concurrency. Two MINORs: the HTTP handler's generation-stamp
wiring survives the full suite when deliberately broken, and the pool budget
was not extended for the new per-run write lanes. Tree pristine before and
after; all mutations ran in a scratchpad clone.

# MAJOR 1 — concurrent parent-role flow permanently mutes the active turn

`LiveStatusObserver._offer` drops any fact whose tap `order` is below
`_active_order_by_run[run_id]`, and `_install_tap` unconditionally bumps the
active order on every install. That guard is what makes the shipped
`test_late_old_generation_abort_cannot_supersede_new_turn` pass, but it
suppresses ALL facts from any older tap, not just late aborts, and nothing
ever restores an older tap's standing.

Failure scenario, from real capture evidence (run `71d0469e`, workspace
`dev-helioy-transport-matters`): Claude Code fires a utility call
(`4f6ef081`: 1.3k system chars, 0 tools, 16 output tokens — title/topic
detection) and the main agent turn (`97ea5c41`: 21 tools, tool_use stop)
94 ms apart on the same run. I verified the utility request carries
`"stream": true` and its response is SSE, so BOTH flows are tap-eligible,
and both are classified `track_role="parent"` (verified in the Tier-1
`entry.json`s; `TrackManager._assign_request` routes signatureless,
resultless requests to the run's parent track). Tap install order is
response-headers order — a race. When the utility flow's headers land
second, its tap takes the active order; the main turn's facts are then
dropped for the entire remainder of its stream, the utility's terminal
writes `kind=NULL`, its finalize closes the row, and the main turn's own
finalize close is a generation-mismatch no-op. The live plane is dark or
stale for a full turn — the exact failure class this redesign exists to fix
(PR-3 sat on Thinking for 35 s).

Proven red in the clone: install main tap, then utility tap; utility streams
and terminates; main then transitions reasoning→generating. Zero rows with
the main generation ever reach the writer — `rows seen: [('gen-util', None)]`.

The mute is purely observer-side: slice 1's `UPSERT_RUN_LIVE_STATUS_SQL`
would happily let the main turn's different-generation facts reopen the
closed row (`WHERE NOT (closed AND generation = EXCLUDED.generation)`), so
the plane would self-heal at the next transition if the facts were allowed
through. Spec §4.3 only requires that a teardown abort "can never clobber a
newer turn's open state" — it does not ask for muting live content facts.
Minimal fix shape: apply the order guard to teardown/terminal facts only
(preserving the shipped red test), and let mid-stream content facts through
latest-wins so concurrent flows converge and the row reopens. A red test
mirroring my demo belongs in the PR.

# MINOR 1 — HTTP generation-stamp wiring is unpinned (mutation survives full suite)

`handle_response_headers` correctly passes
`generation=request_state.provisional_exchange_id` into `start_http_flow`
(read-verified; the id is set in `handle_http_request` before response
headers on all paths). But no test drives `handle_response_headers` with an
observer attached: every existing caller passes no `live_status`, and the
observer tests mint generations directly. Mutation G (stamp
`generation=request_state.run_id` instead) survived the FULL api suite —
1920 passed, 0 failed. This stamp is the fence token: mis-stamped, slice 1's
finalize close never matches and live rows are never closed, silently, in
production only. The Codex side IS pinned
(`test_codex_handler_feeds_only_server_frames` asserts
`generation == "generation-handler"`); the HTTP side needs the equivalent —
one test driving `handle_response_headers` with a real `RequestFlowState`
asserting the tap's facts carry the provisional exchange id.

# MINOR 2 — pool budget not extended for per-run live-write lanes

Spec §4.3 pins live writes to "one connection, matching the existing cap
noted in addon_runtime.py". The implementation serializes writes per run
(one in-flight per `_RunLane`) but has no cross-run cap:
`_SESSION_POOL_AUX_CONNECTION_RESERVE` is still 2 (one aux + wire-store's
one), its comment unamended, and dispatcher shards are still sized
`max_size - 2`. On a dedicated proxy (one run) the posture matches the spec;
on the shared proxy N concurrent runs draw up to N pool connections the
budget does not reserve, contending with dispatcher shards (durable plane)
for connections. Fix is either a shared single write slot across lanes
(the WireStoreObserver semaphore idiom, one connection total) or an explicit
reserve bump with the comment updated.

# Frozen-plane integrity — CONFIRMED, mutation-tested (§4.4 reds 1-9)

1. **Exact byte pass-through:** `capture_chunk` appends to the buffer first,
   invokes the hook inside `try/except Exception` (log once per flow via
   `hook_failed`, never re-raise), returns the exact chunk object.
   `test_response_tee_accumulates_and_passes_chunks_through` asserts `is`
   identity per chunk plus buffer equality, with a hook installed. Mutations
   A1 (withhold: `return b""`) and A2 (copy: `return bytes(bytearray(chunk))`)
   both FAILED it. (First attempt `return bytes(chunk)` is a CPython no-op —
   `bytes(b) is b` — discounted, not a survivor.)
2. **No exception leakage:** a hook raising on every chunk leaves forwarding,
   accumulation, and `restore_streamed_response` untouched. Mutation B
   (delete the try/except) FAILED the isolation test — not a tautology.
3. **Non-blocking:** the tap does reframe+classify+slot update only;
   `test_observer_schedules_without_running_writer_io_on_capture_thread`
   stubs `run_coroutine_threadsafe` and asserts one scheduling, zero writer
   calls. `_offer` takes a `threading.Lock` briefly; no awaits or I/O on the
   capture thread.
4. **Tier-1 manifest:** `test_live_tap_preserves_complete_tier1_manifest_and_bytes`
   compares the COMPLETE file snapshot (tapped vs no-tap baseline) through
   real `install_response_tee` + `DiskStorageBackend.persist_exchange`.
   Deviation noted: spec red 4 named extending
   `test_streamed_provisional_finalize_matches_buffered_response`; the PR
   added this equivalent-or-stronger test instead (full manifest + bytes).
   `complete_file_snapshot` was deduped into `storage/test_exchange_support.py`
   and the slice-1 test now shares it (DRY ✓).
5. **ExchangeSink untouched:** the observer never imports or registers on
   `exchange_sink`; live emissions use their own scheduled path. Structural,
   verified by import inspection.
6. **Import boundary:** observer is composition-level (constructed in
   `_start_session_capture` beside `WireStoreObserver`); storage imports
   nothing new; `test_private_import_boundary` in the passing gate.
7. **Subagent skip is producer-side:** `_install_tap` returns None for
   `track_role == WIRE_TRACK_ROLE_SUBAGENT`; parametrized red test; mutation
   C (drop the check) FAILED exactly the subagent case.
8. **Abort terminal:** `finish_flow` is wired in `finally` on `response`,
   `websocket_end`, and `error` hooks of BOTH addons (dedicated and shared
   proxy); emits `kind=None, provider_event="flow_abort", terminal=True` at
   `last_seq+1` only when the stream lacked a terminal. Mutation D (skip the
   emit) FAILED the pg-integration abort test;
   `test_addon_error_hook_emits_abort_terminal` drives the real addon hook.
9. **Identity-incomplete skip:** absent run_id, absent generation, or a
   binding without working_dir → no tap, no write, no raise (parametrized).

Out-of-order within-turn deltas converge under the serialized slot
(`test_latest_wins_slot_converges_out_of_order_deltas`), and the deferred
stop is superseded by an immediately following start while a write is in
flight (`test_deferred_stop_is_superseded_by_immediate_next_block`).
Observation: with an idle lane the stop deferral is one event-loop tick
(`await asyncio.sleep(0)`), a narrower window than the in-flight slot cycle;
same-chunk stop→start is already coalesced by the slice-2 classifier, so
the residual flicker window is cross-chunk with an idle lane only.

# Producer correctness — CONFIRMED except MAJOR 1

- **Mid-turn:** facts are offered per transition from the chunk tap, written
  by per-run drain loops; the pg test proves a live row exists with the
  correct generation while the stream is open (`closed=False` after abort).
- **Generation stamping:** HTTP taps stamp
  `RequestFlowState.provisional_exchange_id` (set in the request hook before
  response headers, both main and breakpoint paths); Codex WS stamps
  `state.provisional_exchange_id` read BEFORE the terminal-finalize and
  turn-rotation blocks, so terminal facts carry the closing turn's
  generation and pre-provisional frames are skipped (no tap without a
  generation). Coverage gap on the HTTP wiring is MINOR 1.
- **Deferred stop:** present; terminals and aborts bypass deferral
  (`fact.kind is None and not fact.terminal` is the only deferred shape).
- **Abort path:** Esc / network drop / upstream 5xx all funnel through the
  `error` hook or teardown; the abort routes through the same slot; a stale
  tap's abort cannot clobber a newer turn (shipped red test, and the guard
  drops it by order).
- **Codex WS:** turn rotation replaces the flow tap when the generation
  changes; a prior terminal-seen tap finishes as a no-op; an unterminated
  prior turn's teardown abort is order-dropped in favor of the new turn.

# Codex WS server-frames-only — CONFIRMED, mutation-tested

Two-level guard: the handler observes only `not message.from_client`, and
`observe_codex_payload` independently returns on `from_client` without
touching state. Mutation E (drop the handler guard) FAILED
`test_codex_handler_feeds_only_server_frames`. `codex_websocket_payload` is
a shared public helper consolidating the previous duplicated
`_payload_json(_payload_text(...))` pattern (DRY ✓, and fixes what would
otherwise be a private-import need).

# Composition / shutdown — CONFIRMED

`LiveStatusObserver` is constructed in `_start_session_capture` with the
writer, writer loop, and the same `binding_resolver` as `WireStoreObserver`
(now shared via one local, removing duplication). Injected at runtime
through `SessionCaptureRuntime`/`CaptureRuntime`/`AddonRuntime` and the
shared-proxy `SharedProxyCore` → `SharedProxyAddon(live_status=...)`;
storage imports nothing from session. `aclose` finishes remaining taps
(emitting their aborts) BEFORE setting `_closed`, then gathers all pending
futures — no in-flight write lost. Shutdown order in
`close_capture_runtime`: live status drains before the wire observer, so
the finalize generation-close remains the final authority (comment states
the intent).

# Dark scope — CONFIRMED

No TS files touched. No API/router/read surface references
`run_live_status` outside session internals and the observer. Nothing
crosses `register_exchange_sink`. Consumer admission is slice 4.

# DRY / sizing

Touched files: `live_status_observer.py` 357, `test_live_status_observer.py`
529, `addon_handlers.py` 379, `addon.py` 136, `response_stream.py` 60,
`shared_proxy/addon.py` 370, `codex/transport.py` 560. All under 700;
`session/writer.py` untouched at 643 (slice-4 watch item stands, with
`runActivityContext.ts` at 689). Reuse: slice-1 `submit_run_live_status`,
slice-2 `IncrementalSseFrames` + both classifiers consumed as-is; no third
fold; `codex_websocket_payload` and `complete_file_snapshot` are
consolidations, not copies. Observation (trivial): `_next_order_by_run` /
`_active_order_by_run` entries are never removed per run id — unbounded only
in run count per process lifetime, matching existing observer scale.

# Gate

Run at head on the reviewer's machine, judged by output content:
`cd api && just check && just test` → "All checks passed!", mypy "no issues
found in 466 source files", `1933 passed` (up 14 from slice 2's 1919).

# Delta re-verification (2026-07-11, head d0ccb6d)

One fix commit, two files (`live_status_observer.py`, its test), nothing
else touched — still dark on consumer. All three findings resolved; verified
by reading the delta and by kill-checks in a fresh scratchpad clone at the
new head, each dying on exactly its targeted test:

- **MAJOR fixed.** `_offer` now drops only `stale_terminal` facts
  (`fact.terminal and order < active`); mid-stream content facts flow
  latest-wins. New red test
  `test_concurrent_parent_flow_does_not_mute_main_content` reproduces my
  scenario (main tap first, utility second, utility streams and terminates
  via `message_stop`, main then transitions twice) and asserts the main
  generation's `["reasoning", "generating"]` rows reach the writer with the
  last row being main's. Kill-check K1 (revert to the blanket order guard)
  → that test FAILED, 14 others passed — genuinely red against the old
  implementation. The shipped
  `test_late_old_generation_abort_cannot_supersede_new_turn` passes at head
  (stale teardown aborts are terminal, still dropped). Accepted residue: a
  stale tap's genuine in-stream terminal is also dropped, so the row holds
  the last content state until the finalize generation-close — closing is
  the fence's job, sub-second window, correct row generation.
- **MINOR 1 fixed.** New
  `test_http_handler_stamps_provisional_exchange_generation` drives the real
  `handle_response_headers` with a real captured `RequestFlowState`
  (provisional id set via `update_request_flow_state`) through the real tee,
  asserting `generation == "provisional-http-generation"`. Kill-check K3
  (stamp `run_id`) → FAILED. The fence-critical stamp is now pinned.
- **MINOR 2 fixed.** All lanes now share `asyncio.Semaphore(1)` around
  `submit_run_live_status` — one pool draw total, comment states it. New
  `test_live_writes_share_one_connection_slot_across_runs` blocks the first
  write across two runs and asserts `max_in_flight == 1` through drain-out.
  Kill-check K2 (remove the slot) → FAILED. Observation only: the
  `_SESSION_POOL_AUX_CONNECTION_RESERVE` comment in `addon_runtime.py` still
  enumerates two fixed draws (aux + wire); the live slot is a third,
  bounded-at-one but unreserved — worth a comment touch-up someday, not a
  finding (the directive's "shared write slot" option is satisfied).

Sizes after delta: `live_status_observer.py` 363,
`test_live_status_observer.py` 691 — both under 700. Gate at d0ccb6d:
"All checks passed!", mypy "no issues found in 466 source files",
`1936 passed` (up 3 from the pre-fix head's 1933 — the three new tests). Tree pristine before and after; clone removed.

# Mutation / demo table

| # | Change (scratchpad clone, each reverted) | Red test | Result |
|---|---|---|---|
| DEMO | none (test added): concurrent parent flows, main installed first, utility second | main-generation rows reach writer after utility ends | FAILED — main muted, `[('gen-util', None)]` → MAJOR 1 |
| A1 | `capture_chunk` returns `b""` (withhold) | pass-through test | FAILED ✓ |
| A2 | `capture_chunk` returns a byte copy (mutate) | pass-through `is` asserts | FAILED ✓ |
| B | remove hook try/except (leak exceptions) | isolation test | FAILED ✓ |
| C | drop subagent track skip | parametrized subagent case | FAILED ✓ |
| D | `_finish_tap` never emits abort | pg abort-clears-row test | FAILED ✓ |
| E | handler feeds client frames | server-frames-only test | FAILED ✓ |
| G | stamp HTTP generation with `run_id` | FULL api suite | **1920 passed — SURVIVED** → MINOR 1 |
