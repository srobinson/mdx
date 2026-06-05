# S5 review: prompt verb + B1 causal damping (Fable)

Full-slice review of `controlplane-s5-prompt` at `5b3222336666806f276ba3872e18563255c2a49a`
(one commit off main `3dfa33e`). Tree verified pristine (`git status --porcelain` empty) before
and after the review. No repo writes by me or any subagent (finders ran as read-only Explore
agents). Method: full 3262-line diff read end to end firsthand, plus 8 independent finder
angles and firsthand verification of every surviving candidate against the current files.

Gates observed firsthand at 5b32223:

- `just check`: ruff format 509 unchanged, ruff check "All checks passed!", mypy clean on 509
  files, all three www typecheck targets clean.
- `just test` (full gate, fail-fast: desktop, shell, common, contract, activity, runtime JS
  suites then api pytest): pytest `2085 passed` (up 62 from S4's 2023, consistent with the new
  test files reaching the suite).

## Verdict

**review: issue.** The crux holds and every brief question lands, but the slice introduces
one plausible correctness edge on the state_changed axis plus a set of confirmed craftsmanship
minors (DRY and dead code) that the house rules do not allow to ride.

## 1. B1 correctness: HOLDS UNDER THE RACE

Mechanism verified line by line in `causality.py` and `watch.py`:

- **State-at-write binding** works as specified. `mark_delivery` sets
  `remaining_completions = 1` for `idle`, `2` for `working`/`unknown`
  (`causality.py::mark_delivery`), and repeated deliveries extend via
  `max(minimum, existing + 1)` with ancestry union. `consume_turn` decrements per completed
  turn, retiring the entry at zero.
- **Transitivity**: `mark_delivery` folds the actor's `_latest_turn` ancestry and the actor's
  own pending ancestry into the target's set, so A→B→C→A and A↔B cycles carry the full set;
  `consume_turn` clears `_latest_turn` when a turn has no pending entry, so a genuinely human
  turn resets the chain. Unit-tested (`test_causality.py`, two- and three-run cycles, mid-turn
  propagation).
- **needs_you is never suppressed**: in `_record_activity_delta` only the `state_changed`
  branch carries the ancestry guard; the `needs_you` branch has none, and
  `test_actuated_state_change_is_suppressed_but_needs_you_always_surfaces` pins the behavior
  (suppressed reasoning delta, delivered needs_you from the same actuated turn).
- **No suppress-forever**: pending entries drain on completions or expire at TTL 300s
  (`_current_pending` prunes at exactly `now - marked_at >= ttl_s`, boundary tested);
  `_latest_turn` is TTL-bounded the same way. `test_expired_pending_ancestry_does_not_suppress_a_later_human_turn` covers expiry.
- **Integration test exercises the working-at-delivery case**:
  `test_reciprocal_watch_loop_delivers_once_each_then_goes_silent` is parametrized over
  `state_at_write in {idle, working}` and, in the working case, publishes second turns for
  both runs and asserts the delivery count stays at 2. It drives the full engine path
  (hub publish → durable reread → ledger consume → suppression → flush → FakeGateway) with
  `delivery_states` threading the acceptance state through the real `_flush_serialized`
  mark. This answers the brief's crux question directly.
- **The single ledger is shared**: `main.py` creates one `CausalAncestryLedger` and passes it
  to both `ControlPlaneWatchEngine` and `ControlPlaneService` — prompt marks and watch
  consumes on the same instance (cross-file traced; no second ledger anywhere).
- **Escape analysis**: every under-tag interleaving I could construct (projection lag showing
  idle for a just-started turn; a human turn draining the counter before the induced turn;
  Esc flipping the projection before the post-settle sample) yields at most one escaped
  nudge, and the escaped delivery itself re-arms the peer's pending entry before the peer's
  induced turn can complete, so the loop damps within one hop. That is the adjudicated
  one-miss envelope, not beyond it.

**One interleaving found beyond the analyzed set** (finding 1 below, state_changed axis only):
suppression for `state_changed` peeks `active_ancestry` (pending only), while the wire signal
consumes pending. If the wire NOTIFY→LISTEN path beats the SSE delta for the induced turn's
final working→idle transition, that delta escapes damping toward a reciprocal state_changed
watcher. It cannot restore a sustained loop (each escape re-arms the peer, so persistence
requires losing the race on every hop, and the turn-start delta of the next hop is always
suppressed), but it is a real gap the ledger's own data can close: `consume_turn` already
records the consumed ancestry in `_latest_turn`; `active_ancestry` (or a state-changed-scoped
variant with a short grace window, seconds not the 300s TTL) could consult it. PLAUSIBLE,
medium-low.

## 2. Prompt verb: OK

- **Director gate enforced first**: `_require_director(principal)` is the first line of
  `ControlPlaneService.prompt`, raising `forbidden`; the first director verb.
  `test_prompt_requires_a_director_grant_before_delivery` proves denial happens before any
  gateway call.
- **Partial failure is receipt data, never an exception**: per-target
  `GatewayUnavailableError`/`GatewayResponseError` are caught in `_deliver_prompt_target` and
  become failed receipts; a pre-flight `read_workspace_activity` failure becomes an
  all-failed receipt set via `_failed_prompt_result`, still audited, still returned.
  `test_prompt_reports_partial_fanout_and_audits_the_same_receipts` covers
  delivered/failed/exception in one fan-out and asserts audit outcomes mirror receipts (one
  construction, receipts → `ControlPlaneTargetOutcome`).
- **dispatch_id minted per fan-out and not load-bearing**: `self._dispatch_id_factory()` once
  per call; suppression uses run_id sets exclusively; the id appears only in the envelope
  token (`#{hex[:8]}`) and the audit row. Confirmed by grep: nothing parses it back.
- **All delivered text through `_terminal_safe_text`**: sender run_ref, sender name (160-unit
  caps), and the body (4096-unit shared budget, newline-preserving mode) all pass through it;
  `\r` and ESC/BEL are neutralized (tested with an OSC-injection title and body). Budget math
  lands exactly at 4096 UTF-16 units including the ellipsis; `_truncate_utf16` iterates per
  code point, no surrogate split. The Python budget is pinned to the runtime constant by
  `test_watch_nudge_utf16_budget_matches_the_runtime_contract` (now in test_type_mirrors.py).
- **Visibility gate**: targets outside the grant workspace fail as `run_not_found` without a
  gateway call (tested), closing cross-workspace injection with a foreign director grant.
- Spec conformance to CONTROLPLANE.md "Prompt": modes, receipts, delivered-means-PTY-accepted,
  fan-out, envelope prefix all match (the spec's `a1b2` short run ref is illustrative; the
  implementation uses the capped run_id plus the dispatch token per scout decision 5).

## 3. deliverInput primitive + S4 nudge refit: PARITY

- `RunManager.nudge` is now a thin delegator: `validRuntimeNudge` (single-line contract kept)
  then `deliverInput(mode="nudge")`. No parallel PTY-write implementation remains; break
  bytes, settle, bracketed paste, submit, and liveness live only in `deliverInput`.
- Old→new failure mapping is exact: old `liveRun` (lookup + terminal-state filter) + RUNNING +
  settle checks map to `lookup` + in-queue `state !== "RUNNING"`/`settle !== null` checks;
  terminal states are not RUNNING, and the `/nudge` route folds every failure to 404 exactly
  as S4 did. `RunManagerNudge.test.ts` asserts each typed reason at the old call sites.
- **Typed outcome is honest**: `delivered` requires `tryWrite` acceptance
  (`{status: "accepted"}`), and `PtyWriteOutcome` distinguishes closed PTYs where the old
  `write()` silently swallowed. `GatewayInputOutcome`'s model validator rejects a delivered
  outcome without `state_at_write` — no over-claim can cross the seam.
- **state_at_write threading verified end to end**: sampled by `agentStateAtWrite(runId)`
  immediately before the submitted write (after the interrupt settle, the correct instant),
  returned by both routes (202 `{accepted, state_at_write}` on /nudge, 200 typed body on
  /input), parsed by `run_proxy`, consumed by `mark_delivery` in both the watch flush and the
  prompt executor. The gateway composition root maps projection tier → acceptance state
  (active→working, idle/needs_you→idle, else unknown); default without an activity reader is
  "unknown" → 2 completions, fail-safe toward over-suppression.
- Interrupt mechanics: Esc per harness table, settle (default 100ms, injectable), liveness
  recheck after settle, bracketed-paste wrap for multiline, `\r` submit. The per-run
  `inputTail` queue makes break→settle→submit atomic against live terminal keystrokes and OSC
  responder replies (both now enqueue; the defensive `payload.slice()` is required once
  writes defer). Tested: per-harness interrupt, serialized concurrent interrupts, keystroke
  queued behind an atomic interrupt, post-settle state sampling, multiline nudge paste.
- Codex break byte: both harnesses use Esc per the scout's reading of the pinned codex TUI;
  the test encodes the assumption but no runtime verification against the pinned codex binary
  is recorded in the slice. Follow-through item, not a defect finding.

## 4. Quality: scout §3 cleanups ALL LANDED; new minors introduced

- `_remove_ended_watcher`/`_remove_missing_watcher` collapsed into
  `_remove_watcher_and_unused_feeds`. ✓
- run_proxy dead `>= 500` branch removed from `deliver_watch_nudge` before the clone. ✓
- Audit writes moved outside `_registry_lock` for both watch and unwatch
  (decide-under-lock → audit-outside → recommit-under-lock). Correctness of the split
  verified: the per-watcher `_serialize_watcher` op lock serializes same-watcher
  watch/unwatch/removal, and `pending_registrations` keeps the feed alive across the audit
  window, so the commit-skip branch is reachable only at `aclose()` (moot at shutdown). New
  test `test_audit_failure_does_not_mutate_watch_registration_or_removal` pins the
  audit-failure atomicity.
- `_schedule_flush` extracted; the damping re-arm no longer re-buffers an existing fact. ✓
- Single `FakeReads`/`session_view` in `watch_test_support.py`; the test_service.py copies
  deleted. ✓
- watch.py at 689/700 (measured; headroom remains thin), service.py 417, RunManager.ts 679.
  No function over ~150 lines. No em dashes in added lines. CONTROLPLANE.md untouched and
  already authoritative for prompt/deliverInput at main.

## Findings (ranked)

```json
[
  {"file": "api/src/transport_matters/controlplane/watch.py", "line": 498, "verdict": "PLAUSIBLE", "category": "correctness", "summary": "state_changed damping peeks active_ancestry (pending) while the wire signal consumes pending, so the induced turn's trailing working-to-idle delta escapes damping when the wire NOTIFY beats the SSE delta", "failure_scenario": "A and B hold reciprocal state_changed watches; A's nudge actuates B's turn; the turn's wire commit signal consumes pending[B] before the working-to-idle activity delta arrives; active_ancestry(B) is empty so the delta is buffered and delivered to A. Escape re-arms pending[A] so persistence requires losing the race every hop (geometric damping), but the gap is real; consume_turn already stores the consumed set in _latest_turn, so a short-grace consult in the state_changed path closes it"},
  {"file": "api/src/transport_matters/controlplane/watch.py", "line": 578, "verdict": "CONFIRMED", "category": "dead-code", "summary": "The try/except around resolve_watch_names is dead (the helper swallows all exceptions internally and returns {}) and its audit reason mislabels a session-name lookup as 'causality lookup failed'", "failure_scenario": "A reader trusts that a name-lookup failure restores facts and audits delivery_failed; it never fires, and if the swallowing ever moves out of resolve_watch_names the audit will misattribute a name failure to causality, misdirecting debugging"},
  {"file": "api/src/transport_matters/api/v1/run_proxy.py", "line": 192, "verdict": "CONFIRMED", "category": "altitude", "summary": "deliver_watch_nudge hand-builds GatewayInputOutcome from payload['state_at_write'] (hardcoding status, discarding reason) while deliver_input uses model_validate, leaving two wire shapes and two parse depths for one primitive whose /nudge shape has exactly one consumer", "failure_scenario": "GatewayInputOutcome grows a field or the gateway returns a failed status on 202; the manual builder discards it and reports delivered for a nudge that did not land, while the /input path would surface it; the shared-primitive refit was supposed to prevent exactly this drift"},
  {"file": "packages/runtime/src/service/RunManager.ts", "line": 31, "verdict": "CONFIRMED", "category": "duplication", "summary": "validRuntimeInput re-implements hasTerminalControl's C0/C1 scan with one extra allow-newline clause instead of parameterizing the existing scanner", "failure_scenario": "user CLAUDE.md zero-tolerance DRY: a future terminal-safety fix (new blocked range) must be made in two loops or one input path becomes an injection gap; hasTerminalControl(text, {allowNewline}) serves both"},
  {"file": "api/src/transport_matters/controlplane/service.py", "line": 237, "verdict": "CONFIRMED", "category": "duplication", "summary": "_resolve_actor_name duplicates the sessions_for_runs to title-or-run_id lookup that this same commit extracted into watch_delivery.resolve_watch_names", "failure_scenario": "prompt-sender naming and watch-nudge naming silently diverge on the next name-policy change; resolve_watch_names(reads, principal, (run_id,)) already provides the behavior including the exception fallback"},
  {"file": "packages/activity/src/projections/workspaceActivity.ts", "line": 110, "verdict": "CONFIRMED", "category": "efficiency", "summary": "The new byRun map is written on every projection update and never evicted, adding a second unbounded per-run structure for the gateway process lifetime", "failure_scenario": "A long-lived gateway retains one Map entry per all-time run; parallels the pre-existing byWorkspace retention but widens it; evict on terminal tier alongside whatever cleanup byWorkspace eventually gets"},
  {"file": "packages/gateway/src/main.ts", "line": 155, "verdict": "CONFIRMED", "category": "test-coverage", "summary": "The tier-to-InputAcceptanceState mapping (active=working, idle/needs_you=idle, else unknown) lives as an untested closure in the composition root", "failure_scenario": "activityStatusTier gains or renames a tier; contract tests update but this hand mapping is missed silently; state_at_write feeding the causality ledger degrades (wrong completion count: escape-and-re-arm or one extra over-suppression) with no failing test"},
  {"file": "packages/runtime/src/service/RunManager.ts", "line": 397, "verdict": "CONFIRMED", "category": "efficiency", "summary": "write(), the per-message hot path for every attached viewer, now pays a buffer copy plus promise-chain allocations and a microtask deferral even when the input queue is idle", "failure_scenario": "GC pressure and added latency scaling with concurrent terminals; the queue only needs to engage while a control-plane delivery is in flight; a queue-idle fast path (synchronous write when inputTail is settled and no delivery pending) preserves the atomicity guarantee at zero steady-state cost"}
]
```

Nits (record, builder's discretion): three separate 160-unit name budget constants in
envelope.py where the 4096 budget was properly aliased; `activity_by_run` dict built for a
pure membership test (a set states the intent); twin pre-flight except arms in `prompt()`
collapsible to one; sender-name lookup and envelope work spent before the visibility read
discards them on gateway failure, and the two independent awaits could gather;
`void enqueueInput(...).catch(() => {})` fire-and-forget idiom duplicated twice;
barrel exports (`DEFAULT_INPUT_INTERRUPT_SETTLE_MS`, `MAX_RUNTIME_NUDGE_CHARS`,
`validRuntimeInput`) with no external consumer; `BREAK_SEQUENCE_BY_HARNESS` keyed by harness
with identical values while per-harness knowledge otherwise lives with the harness registry;
needs_you's never-suppress rule enforced by absence of a guard (pinned by test, but a
declared suppressible-kinds set would survive refactors); InputAcceptanceState/PromptMode
literals not covered by test_type_mirrors.py the way ActivityStatusTier is.

Refuted candidates (for the record): registration commit-skip during the audit window
(feed replacement is not constructible: `pending_registrations` guards `_stop_unused_feeds`,
the reconnect loop never swaps the feed object, and the `aclose` window is moot at shutdown);
concurrent human turn draining the counter and post-settle Esc state sampling (both inside
the adjudicated one-miss envelope: every escape re-arms the peer and damps the next hop);
202-without-state_at_write version skew (gateway and API ship in one wheel, no skew surface);
write/resize reordering (PTY input vs resize ioctl ordering is not an app-level contract,
SIGWINCH is already asynchronous); OSC reply delay behind an interrupt settle (bounded 100ms
and required, since injecting a reply mid-bracketed-paste would corrupt the pasted text);
swallowed write errors on the WS path (the old throw was an unhandled exception in the socket
handler, not a client-visible signal).

## 5. Builder trust verdict (codex, this slice)

**High on the mechanism, medium on craft; delegation of sizeable scope remains reasonable
with the generalist-lens brief and this review loop retained.**

Evidence for: the crux implementation is better than the agreed design minimum in several
places (completion-counter spanning instead of pop-once, `_latest_turn` transitivity with
human-turn reset, the enqueueInput atomicity making break-settle-submit safe against live
keystrokes, the defensive payload copy that deferred writes newly require, the visibility
gate closing cross-workspace injection). Test rigor on the race surfaces is genuinely good:
the reciprocal-loop integration test covers the working-at-delivery case the objection was
about, audit-failure atomicity, post-settle state sampling, atomic interrupt queueing, and
control-char injection through a hostile session title. The audit-outside-lock refactor
preserved every serialization invariant (verified against the op-lock and
pending_registrations structure). All five scout §3 cleanups landed. Completion claims match
the hash.

Evidence against: the same component-boundary blind spot as prior slices, now in miniature —
two DRY violations against helpers created or touched in this very commit
(`_resolve_actor_name` vs the freshly extracted `resolve_watch_names`; `validRuntimeInput`
beside `hasTerminalControl`), a dead except with a mislabeled audit reason, and the /nudge
wire shape left divergent from the primitive it was refit onto. None are correctness
failures; all are the category the house rules say must not ride.
