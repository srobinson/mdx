---
title: S4 watch review (controlplane-s4-watch @ 3e66ac1)
reviewer: fable (transport-matters:general:1:2.2)
date: 2026-07-11
verdict: ISSUE — 1 blocker, 3 medium, 6 minor/low. Watch engine is correctly Python-side, skins thin, no auth bypass, no parallel stream; but the engine has no self-event exclusion (nudge→turn→nudge feedback loop) and the envelope composes agent-influenced text with no control-character neutralization.
---

# Scope

Branch `controlplane-s4-watch` at 3e66ac1 (single commit "feat(controlplane): add watch subscriptions", 22 files +1963/−32). Diff `git diff main...controlplane-s4-watch`. Spec: CONTROLPLANE.md "Watch (push)" + locked design (~/.mdx/projects/tm-controlplane-design-fable.md, Tension 3). Method: full firsthand diff read + 8 parallel finder angles (line-scan, removed-behavior, cross-file tracer, DRY, simplification/efficiency, altitude, conventions, security), all load-bearing claims re-verified firsthand against watch.py, envelope.py, listen.py, run_proxy.py, RunManager.ts, activityRouter.ts, sse.py. Gates observed green firsthand: pytest src 1999 passed (Postgres suite included), ruff format/check + mypy clean on 497 files, @tm/runtime vitest 160/160. Tree pristine at 3e66ac1.

# Brief conformance (the six focus areas)

1. **Event source: PASS.** No parallel stream. `state_changed`/`needs_you` ride the existing `GET /v1/workspaces/{id}/activity/stream` SSE via a new `stream_workspace_activity` on the existing `RunRouteProxy`; `turn_completed` rides the existing tm_events LISTEN via typed `WireExchangeSignal` parsing in `session/listen.py` (one hub, no second LISTEN connection). Replay fences on both sources: first SSE snapshot sets the baseline without emitting; wire baseline is a DB-clock cursor + `seen_exchanges` dedup; both fences unit-tested (`test_double_subscribe_is_idempotent_and_replay_fences_both_sources`, `test_reconnect_snapshot_emits_only_status_changes_since_the_prior_baseline`, `test_listener_reconnect_rereads_durable_turn_once`). No watch-engine logic leaked into the gateway; the scout-observe gateway-hosted note is correctly superseded.
2. **Damping: PASS mechanically, one blocker in event mapping (F1).** Per-watcher `OrderedDict[(kind, run_id) → WatchFact]` coalesce buffer, one flush task per watcher, minimum-interval flush, burst→one line. Window-boundary event lands in the next nudge (tested). Latest-wins per (kind, run) — two turns by one run in a window deliver only the latest turn number, by design (nudge carries references, watcher pulls content).
3. **RunManager.nudge: PASS.** Genuinely fire-and-forget (`boolean`, no receipt), funnels through the same `run.session.write` as interactive input (no alternate PTY path), dead/missing run → `false` → 404 → Python removes the watcher (tested both layers). Envelope prefix composed only in Python (`envelope.py`); the TS side only validates and appends `\r`.
4. **Subscriptions: PASS.** In-memory beside the registry, `aclose()` wired into lifespan before gateway teardown. Unwatch idempotent + audited, double-subscribe `changed=False`, watcher-exit and watcher-already-ended cleanup, dead-target removal after first failed delivery — each tested. One registration/teardown race found (F3).
5. **Skins: PASS.** REST watch/unwatch and MCP tools are branch-free delegators via `invoke_control_plane` (AST test widened to 5/10 delegators); watch and unwatch both write `control_plane_action` audit rows on every outcome incl. invalid/not-found; envelope mirror-tested across skins (`test_watch_envelope_is_identical_across_both_skins`).
6. **DRY/dead code/size: mostly PASS.** watch.py 651 LOC (<700), largest function ~101 lines. Findings F6/F8/F9 below are the DRY exceptions.

**Auth/scope:** both skins bearer-gated (S3 machinery); cross-workspace subscribe blocked — target validated against the principal-scoped activity feed and turn reads are owner+workspace-scoped in SQL. No entitlement bypass (both current roles legitimately include watch; note N7).

# Findings

## F1 — BLOCKER: no self-event exclusion → perpetual nudge→turn→nudge feedback loop

`api/src/transport_matters/controlplane/watch.py`, `_record_completed_turn` + `_record_activity_delta`. Facts are routed to every watcher whose target events match the run — with no exclusion of the watcher's own run. A watcher subscribed to `workspace` (the flagship use case) receives `turn_completed`/`state_changed` facts about itself. Delivery writes `"{text}\r"` into the watcher's PTY (`RunManager.nudge`), which submits a prompt line and starts a turn; that turn's completion emits `turn_completed(watcher)` (and status transitions), which buffers a new self-fact, which flushes into another nudge. The loop is self-sustaining forever, paced by the flush interval + turn duration, burning provider tokens indefinitely. Even one peer event bootstraps it: peer nudge → watcher turn → self-fact → nudge → …. For `needs_you` watchers it is worse: the self-nudge line is injected as the *answer* to whatever the harness was asking. No test exercises a watcher receiving its own events. Fix: filter `fact.run_id == watcher.principal.run_id` at buffering (and add the test).

## F2 — MEDIUM (security/robustness): envelope composes agent-influenced titles with no control-character neutralization

`controlplane/envelope.py` `_format_watch_fact` interpolates `names[run_id]` — the watched run's session title, transcript-derived and watched-run-influenced — with zero sanitization. The single-line invariant lives only in the far-side TS reject (`validRuntimeNudge` blocks `[\r\n]` and >4096 only): (a) a title containing a newline gets the *entire* flush batch 400-rejected → `GatewayResponseError` → swallowed by `_flush`'s broad except → every subsequent flush containing that run is silently suppressed (watch channel blinded, log-only); (b) ESC/OSC/C0 sequences pass validation entirely and are written into the watcher's PTY stdin — terminal escape injection (ESC is the harness interrupt key; OSC-52 reaches the clipboard), and the title text itself is submitted as agent-actionable prompt content (prompt injection surface). Per the locked design the envelope has ONE owner (Python), so the invariant belongs at composition: strip/replace control characters (and cap name length) in `envelope.py`; keep the TS check as defense-in-depth. (Merged from finders C, F, H.)

## F3 — MEDIUM: feed-startup race — `_stop_unused_feeds` kills a feed whose first watcher has not registered yet

`watch.py` `watch()`: the feed is created under the lock, but the watcher is only registered after releasing the lock and awaiting readiness (up to `start_timeout_s`). `_stop_unused_feeds` derives "used" purely from registered watchers and runs on every unwatch, ended-watcher cleanup, and failed delivery — process-wide, all workspaces. Any of those firing during the readiness window pops and cancels the pending feed; the in-flight `watch()` then either (a) registers against the dead feed and returns `changed=True` while no events will ever be delivered (until some later `watch()` recreates a feed for that key), or (b) times out with a spurious `busy_gateway` on a healthy gateway. Realistic in a multi-agent warroom with watch/unwatch churn. Fix: mark the feed as pending (refcount or in-flight registrations set) so `_stop_unused_feeds` skips it, and re-check feed liveness at registration.

## F4 — MEDIUM: `liveRun` tightening silently changes existing write/resize behavior

`packages/runtime/src/service/RunManager.ts` `liveRun` went from "not in {TERMINATED, EXITED, FAILED}" to `state === "RUNNING" && settle === null`. `RuntimeRunState` includes `TERMINATING`, which the old guard allowed — so interactive `write()` and `resize()` now silently no-op during the whole settle/TERMINATING window where they previously reached the PTY. Plausibly the right semantics for nudge, but it is an unannounced behavior change on the existing interactive terminal path, bundled into the watch diff, with no test or rationale covering the write/resize regression. Either scope the settle guard to `nudge` or state and test the tightening deliberately. (Confirmed independently by three finders.)

## F5 — MINOR (spec conformance): failed delivery is dropped but not audited

Locked design: "A failed watch delivery is dropped and audited, never retried into a storm." `_flush`'s exception path only `logger.exception`s and returns; the not-delivered → remove-watcher path writes no `control_plane_action` row either. Registration outcomes are thoroughly audited; delivery outcomes are not. Add an audit row on dropped delivery and on dead-watcher removal.

## F6 — MINOR (DRY): hand-rolled SSE parser beside the canonical `sse.py`

`run_proxy.py` `stream_workspace_activity` re-implements SSE record parsing over `aiter_lines()` while `transport_matters/sse.py` (`IncrementalSseFrames`, `iter_sse_data_objects`) is the established decoder used by live_status_observer, codex response_parser, and the anthropic adapter. The copy diverges: no oversized-record cap (`MAX_INCREMENTAL_SSE_TAIL_BYTES`), no `[DONE]` handling. The test is even named `..._reuses_sse_...`. Feed `IncrementalSseFrames` from `aiter_bytes()` instead.

## F7 — MINOR (leak): `seen_exchanges` grows unbounded and the wire cursor stagnates between reconnects

`_WorkspaceFeed.seen_exchanges` accretes every exchange_id for the feed's lifetime with no eviction, and `wire_cursor` only advances inside `_catch_up_wire` — so a long-lived feed grows memory monotonically with total turn count and a late reconnect replays the whole window since feed start (correct via dedup, but O(all turns)). Advance the cursor opportunistically and bound the dedup set (turns arrive time-ordered; a small window covers the reconnect overlap).

## F8 — MINOR (DRY/tenancy): bespoke ownership-scoping SQL in `completed_wire_turns_since`

`read_store.py` inlines two hand-written `EXISTS` subqueries matching owner/workspace_slug/workspace_hash, plus `_workspace_parts` as the inverse of the existing `f"{slug}/{hash}"` formatter (`SESSION_WORKSPACE_ID_SQL` / session_models), where every other read on the store delegates scoping to the DAO idiom. The tenant-isolation predicate now lives in two idioms; a future scoping fix to the central one will not reach this query.

## F9 — LOW (simplification): `SessionEventHub` grew a parallel special-cased fanout

`listen.py`: a second `(workspace, owner)`-keyed subscriber map, an `isinstance` branch in `publish`, a duplicated `put_nowait`/QueueFull loop, and a doubled `publish_catch_up`. A keyed multi-topic fanout absorbs both channels; the next NOTIFY flavor forces a third copy of the drop policy.

## F10 — LOW (efficiency/coupling): wasted per-watch gateway snapshot; unlinked cross-language caps

Every `watch()` call performs `read_workspace_activity` before checking feed existence; when the feed exists the result is discarded, and even on feed creation the stream's first snapshot overwrites it before validation reads anything — its only real job is an early health check. Separately, `MAX_WATCH_ENVELOPE_CHARS = 4000` (Python, deliberately UTF-16-counted to mirror JS `.length`) and `MAX_RUNTIME_NUDGE_CHARS = 4096` (TS) encode one contract as two unlinked constants (plus `MAX_WORKSPACE_SUMMARY_CHARS = 4000` as a third same-value budget); raising the Python cap past 4096 silently trips the F2 drop path.

# Refuted / notes

- **Refuted — tier-only needs_you drop:** the `previous.status == current.status` early return cannot mask a tier transition; `tier = activityStatusTier(projection.status)` is a pure function of status (activityRouter.ts), so same status ⇒ same tier.
- **Refuted — stale committed gateway bundle:** `api/src/transport_matters/gateway/main.js` is gitignored (build artifact, not in the diff or history); wheel builds regenerate it. Env caveat: `resolve_gateway_entry` prefers a local packaged bundle over workspace source, so a stale *local* build 404s the nudge route until rebuilt — environment, not this diff.
- **Note — first-frame-delta hazard:** `activity_ready` is only set by a snapshot frame; today's gateway always writes the snapshot first on connect, so this is protocol-drift exposure only. Related: strict frame validation turns any future frame-shape change into a reconnect loop + `busy_gateway` (version-skew hazard, acceptable for an in-repo pair).
- **Note — cursor clock edge:** catch-up fences on `created_at >= cursor` with dedup; a writer transaction straddling a cursor advance plus a second LISTEN drop could miss one turn (double-fault, microscopic window).
- **Note — mid-typing splice:** a nudge lands as `text\r` with no coordination with concurrent interactive input; inherent to the v1 nudge primitive — bracketed-paste discipline is the S5 prompt primitive's contract.
- **Note — unauthenticated loopback route:** `/runs/:runId/nudge` matches the existing runtimeRouter trust model (127.0.0.1 bind, owner query param, same as sibling PTY-adjacent routes). New surface, same posture; not a regression.
- **Note — entitlement gate structurally absent:** no code branches on `ControlPlaneGrantRole`; correct today (observer and director both watch), but nothing enforces a future observe-without-watch role.
- **Note — damping semantics:** latest-wins per (kind, run) means intermediate turn numbers within a window are not enumerated; consistent with "push carries references".
- **Nits:** `_parse_wire_exchange_signal(data: dict[str, Any])` adds an uncommented `Any` (api/CLAUDE.md rule; consistent with the pre-existing sibling); `GatewayActivityRun.needs_you` field is parsed but unused by the engine (declarative completeness).

# Self-audit efficacy (extra ask a)

Visibly effective on the anticipated seams: every edge the orchestrator's brief called out by name — damping window boundary, empty flush, replay fence on both sources, reconnect single-reread, dead-target delivery, double-subscribe idempotency, watcher-dies-mid-subscription, envelope cap — arrived pre-covered by tests and produced zero findings. That is a real reduction versus S1/S2, where exactly this class of enumerable edge case dominated the ~10-finding pattern. What remains is one altitude deeper: cross-component and emergent behavior (self-feedback across nudge→PTY→turn→event, sanitization across the Python/TS boundary, registration racing teardown, a shared guard's blast radius on untouched callers) — seams a checklist-style self-audit does not enumerate. Net: count did not drop (10), severity went up (first blocker of the series).

# Builder assessment (extra ask b)

**Trust: MEDIUM — down from S3's HIGH.** Craftsmanship remains excellent: correct asyncio discipline (CancelledError re-raised everywhere, self-cancel guard in `_remove_watcher`, tasks named and reaped), UTF-16 unit counting deliberately mirroring JS `.length` semantics, both replay fences genuinely tested, thin skins preserved with the AST contract test widened, spec-superseding note honored (nothing leaked into the gateway beyond the minimal primitive). But S4 is the first slice with a blocker-grade design miss, and it sits in the feature's flagship path: a workspace watch self-loops on first nudge. Together with F2 (no trust boundary on agent-influenced envelope text) and F4 (tightening a shared guard without owning the blast radius on existing callers), the pattern is design blind spots at component boundaries rather than sloppiness inside the component. Delegation guidance: continue delegating implementation-heavy slices; require an explicit "feedback/actuation loop" and "who controls this text" analysis in the pre-submit self-audit for anything that writes into an agent's input channel.

# Delta-verify (7054d43, 2026-07-12)

Fix commit "fix(controlplane): harden watch boundaries" (22 files, +968/−289). **Verdict: clean, 10/10 addressed.** Verified firsthand against the full 3e66ac1..7054d43 diff plus targeted reads of watch.py, envelope.py, RunManager.ts.

- **F1 (blocker):** fixed at the single choke point — `_target_events` returns `()` when `watcher.principal.run_id == run_id`; both the activity path (`_record_activity_delta`) and the wire path (`_record_completed_turn`) route through it, and the terminal self-removal branch keeps its own explicit check. `test_workspace_watch_excludes_the_watcher_own_activity_and_turns` drives self activity delta + self wire signal to zero delivery attempts, then proves a peer batch excludes the watcher.
- **F2:** neutralization now lives at the envelope owner: `_terminal_safe_text` maps Cc/Cf/Cs/Zl/Zp to space, collapses whitespace to a single line, caps names at 160 UTF-16 units and status at 80; `_truncate_utf16` appends whole code points so no surrogate split. TS `validRuntimeNudge` widened to reject all C0 + DEL + C1 (defense-in-depth), tested both sides. The batch-blindness path is gone: `GatewayResponseError` is audited as `delivery_rejected` and dropped, not silently swallowed.
- **F3:** `pending_registrations` refcount makes `_stop_unused_feeds` skip in-flight feeds; after readiness, `_watch_serialized` re-checks feed currency + consumer-task liveness and raises busy_gateway if the feed died; a per-watcher `_WatcherOperation` lock serializes watch/unwatch/cleanup. Three race tests including cleanup-vs-registration.
- **F4:** `liveRun` restored to `TERMINAL_STATES.has` (write/resize live during TERMINATING again — tested), the strict `RUNNING && settle === null` guard scoped to `nudge` only.
- **F5:** `watch_delivery` audit rows for `delivery_failed` (transient — facts restored latest-wins for one damped retry), `delivery_rejected` (dropped), `watcher_missing` (watcher removed). CONTROLPLANE.md amended to state the damped-retry semantics, so the spec of record matches.
- **F6:** `stream_workspace_activity` feeds `IncrementalSseFrames` from `aiter_bytes`; `httpx.RequestError` broadened to transient, tested (malformed-frame + RemoteProtocolError cases).
- **F7:** dedup bounded to `MAX_WIRE_REPLAY_DEDUPE = 2_048` (OrderedDict FIFO); cursor advances opportunistically every `wire_cursor_advance_interval` (default 1_000) live exchanges, constructor-validated ≤ the dedupe window so evicted ids can never double-fire; both tested.
- **F8:** SQL moved to `controlplane_statements.GET_COMPLETED_WIRE_TURNS_FOR_OWNER_SQL` using shared `workspace_id_sql()`; ownership now joins on `session_id` with a lifecycle fallback only for unknown sessions — this additionally fixes a same-run-id cross-owner leak my finding did not name, and the new `foreign_same_run` test pins it.
- **F9 (partial by design):** duplicated QueueFull loops consolidated into `_publish_wire_signal`; overflow now drains the queue and enqueues a durable catch-up instead of dropping (loss → reread), tested. The isinstance branch remains — acceptable for a LOW.
- **F10:** the per-watch point read is deleted (`read_calls == 0` asserted); caps unified at 4_096 UTF-16 units with a cross-language mirror test.

**No regressions:** engine wholly Python-side (TS gained only input validation), replay fences intact and strengthened, nudge still a fire-and-forget boolean (the retry is Python damping-layer batching, not a receipt). Hygiene: watch.py 695 LOC (models → watch_models.py, audit → watch_audit.py), longest function 102 lines. Gates firsthand: pytest 2013 passed, ruff format/check + mypy clean on 500 files, @tm/runtime vitest 162/162. Tree pristine at 7054d43.

**Residual design note (not a defect in this fix, base behavior):** two agents watching the same workspace still mutually excite — A's turn nudges B, B's responding turn nudges A, indefinitely, since a nudge is a submitted prompt and every prompt yields a turn. Self-exclusion cannot cover cycles of length ≥ 2. Belongs in the S5 prompt/receipt design conversation (loop suppression, e.g. not emitting facts for turns caused by a watch nudge, or watcher briefing conventions).
