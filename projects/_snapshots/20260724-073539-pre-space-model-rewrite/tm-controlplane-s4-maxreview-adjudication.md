---
title: S4 max-review adjudication (controlplane-s4-watch @ 7054d43)
adjudicator: fable (transport-matters:general:1:2.3)
date: 2026-07-12
verdict: 7 confirmed / 1 refuted. In-S4-scope B1, B2, M1, Med1, Med2 (M2 split). Pre-existing M3, M2 substrate, B3 adapter behavior. Severity — B1 agree Blocker (upgraded from my delta-verify design note), B2 down to Medium, B3 refuted as defect, M1 low-medium, M2 low.
---

Every claim below re-verified firsthand at 7054d43 (tree pristine). File and symbol citations follow the repo convention.

## B1 — reciprocal watch cycle (A→B→A nudge/turn loop)

**CONFIRMED. IN-S4-SCOPE. Severity: AGREE Blocker (I upgrade my own earlier call).**
`_target_events` (watch.py) excludes only `watcher.principal.run_id == run_id`. Two agents in one workspace who both register a `workspace` watch (or watch each other's runs) mutually excite: A's turn buffers a fact for B, B's PTY receives the envelope as a submitted prompt, B's harness runs a turn, B's `turn_completed`/`state_changed` buffer facts for A, indefinitely. Damping paces the loop (flush interval + turn duration) but nothing terminates it; each cycle burns real provider tokens on both sides and pollutes both transcripts. I flagged this in my delta-verify reply as a residual S5-scope design note; adjudicating honestly, that was too lenient. The dynamics are identical to the F1 self-loop the correction round treated as a blocker — it merely needs two participants, and multi-watcher workspaces are the flagship scenario. S5's receipt primitive does not fix watch-only deployments, and nothing in the product detects or prevents cycles (registration-time cycle detection cannot even see workspace-target cycles). Introduced at 3e66ac1, untouched by 7054d43. Candidate fixes are design-level: suppress fact emission for turns caused by a watch nudge (loop tagging), per-watcher-pair cool-down, or constraining watch to one actuating watcher per workspace until receipts land.

## B2 — unkeyed nudge POST retried after ambiguous loss → duplicate submission

**CONFIRMED. IN-S4-SCOPE (introduced by the 7054d43 correction). Severity: ADJUST Blocker → MEDIUM.**
Verified: `RunRouteProxy` uses `httpx.AsyncClient(timeout=10.0)` (run_proxy.py) and the correction broadened the guard to `except httpx.RequestError → GatewayUnavailableError`, which includes `ReadTimeout` and `RemoteProtocolError` — failures that can occur *after* the gateway has accepted the POST and written to the PTY. `_flush` (watch.py) reacts to `GatewayUnavailableError` by restoring the facts (`_restore_failed_facts`) for a damped retry with no idempotency key, so an accepted-but-unreported delivery is submitted to the watcher's PTY twice. Real, and new in the correction (base dropped the batch, at-most-once). Medium, not blocker: each duplicate requires a fresh ambiguous-loss window on loopback HTTP (slow/blocked gateway event loop, restart mid-response), retries are damped, and the consequence is a duplicated informational line plus one redundant turn — no unbounded amplification. Clean fix without a key: only retain-and-retry on `httpx.ConnectError` (provably no side effect); treat response-phase losses as ambiguous and drop-with-audit like `delivery_rejected`. An envelope batch id honored by the gateway is the fuller alternative.

## B3 — nudge returns true after suppressed PTY write

**REFUTED as a defect (mechanism real). Adapter behavior PRE-EXISTING; nudge semantics IN-S4 per the design lock. Severity: LOW note, not Blocker.**
Verified: `NodePtySession.write` (NodePtyAdapter.ts) returns silently when `disposed || exitEvent !== null` and swallows `isTerminalGoneError` (EIO/EBADF); `RunManager.nudge` then returns true → 202 → Python consumes the facts. But the locked design makes nudge explicitly fire-and-forget with the resultful receipt deferred to S5, so "202 ≠ bytes read by the agent" is the specified contract, and the only silent-drop cases are a dead or dying recipient — the exact party the lost notifications were for. The next delivery attempt returns 404/false and removes the watcher (`watcher_missing` audit, tested). Consuming facts destined for a dead watcher is moot, not a loss. If S5 receipts land, this window closes for free.

## M1 — transaction-start created_at as commit watermark

**CONFIRMED. IN-S4-SCOPE. Severity: ADJUST to LOW-MEDIUM.**
Verified: `wire_exchange.created_at timestamptz NOT NULL DEFAULT now()` (migrations/versions/0008_wire_store.py) — `now()` is transaction start, and `GET_COMPLETED_WIRE_TURNS_FOR_OWNER_SQL` fences on `created_at >= cursor` while `_catch_up_wire` advances the cursor to the max `created_at` seen. A writer transaction in flight during a cursor advance commits with a below-cursor timestamp; if its NOTIFY is also lost (connection drop — queue overflow no longer loses, it degrades to catch-up), the turn is permanently invisible to watch. Double fault, narrow window, and the blast radius is one missed *notification* — the durable store and observe surfaces are unaffected. In-S4 (the cursor mechanism is S4's; the correction's opportunistic advance widens exposure slightly). Proportionate fix: subtract a small overlap margin when advancing the cursor (the bounded dedupe already absorbs re-reads), or fence on a `pg_snapshot` xmin instead of the clock.

## M2 — NOTIFY on idempotent upsert replays vs bounded process-local dedupe

**CONFIRMED mechanism. Scope SPLIT: unconditional NOTIFY is PRE-EXISTING (157f781, wire-store PR-2, on main); the false-turn_completed exposure via the 2048-entry dedupe is IN-S4. Severity: ADJUST to LOW.**
Verified: `SessionWriter.submit_wire_exchange` (writer.py) notifies on every commit with no inserted-vs-replayed gate, and `_remember_exchange` (watch.py) is the only guard, bounded FIFO 2048 per feed. However the sole non-test caller of `submit_wire_exchange` is the live finalize path (`WireStoreObserver.on_exchange`); there is no bulk backfill caller today. Triggering a false `turn_completed` therefore requires the *same exchange* to be re-finalized more than 2048 workspace turns after first commit — rare, and the consequence is one stale notification line. Flag as a landmine: the day a backfill or repair path batch-re-submits exchanges, it will spray stale nudges at every watcher. Cheap hardening when that day comes: gate the NOTIFY on rows actually inserted / response newly set, or have the consumer drop signals older than the feed cursor.

## M3 — parse-dependent completion (unparseable responses invisible to watch)

**CONFIRMED as a coverage gap. PRE-EXISTING substrate. Severity: agree LOW-MEDIUM, as a substrate note, not an S4 defect.**
Verified: `ExchangeArtifacts.response_ir: InternalResponse | None` (storage/base.py, predates the namespace rename) is None whenever the response IR artifact was never produced; `WireStoreObserver.on_exchange` passes it through, so a wire-complete but unparseable response yields `has_response=False` in the NOTIFY and a NULL `response_id` in the row — invisible to both the live path (requires `has_response`) and replay (`response_id IS NOT NULL`). But this is the wire store's own definition of completion, established in PR-2/PR-3; observe and timeline treat the same exchange as response-less. S4's predicate is consistent with its substrate. The defect, if any, lives in the parse/persist path and should be tracked there.

## Med1 — unwatch leaves removed-target facts buffered

**CONFIRMED. IN-S4-SCOPE (base, missed by my review too). Severity: agree MINOR.**
Verified in watch.py `_unwatch_serialized`: it pops the target from `watcher.targets` (and removes the watcher only when no targets remain) but never purges `watcher.buffer`, and `_flush` does not re-check targets. Facts already coalesced for the removed target are delivered after a successful unwatch — one late notification, a semantic wart. Fix: purge non-matching `(kind, run_id)` entries on unwatch, or filter the buffer against `_target_events` at flush.

## Med2 — createRuntimeRouter crosses the ~150-line function cap

**CONFIRMED. IN-S4-SCOPE (3e66ac1 added the nudge route; the correction did not touch the file). Severity: agree MINOR hygiene.**
Measured firsthand: `createRuntimeRouter` (runtimeRouter.ts) is 136 lines at main and 153 at 7054d43, matching the reviewer's numbers, against the user CLAUDE.md guardrail "If a function grows past ~150 lines, break it up". Route-handler extraction is the natural seam.

## Tally

Confirmed 7 (B1, B2, M1, M2, M3, Med1, Med2), refuted 1 (B3, as a defect — the mechanism is real but design-conformant and its loss cases are moot). In-S4-scope: B1, B2, M1, Med1, Med2, plus M2's consumer-side exposure. Pre-existing: M3, M2's writer-side NOTIFY behavior, B3's adapter suppression. Severity deltas vs the max reviewer: B1 agree (Blocker — an honest upgrade of my earlier S5-note call), B2 Blocker→Medium, B3 Blocker→refuted/low, M1 →low-medium, M2 →low, M3/Med1/Med2 agree.
