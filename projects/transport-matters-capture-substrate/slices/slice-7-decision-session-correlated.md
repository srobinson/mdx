# Slice 7 — DECISION: build `session_correlated` now, or defer it?

**This is a decision review, not a build.** Adversarially verify the claim below against current
`main`, then reach consensus: **BUILD** `session_correlated` now (with scope) or **DEFER** it (with the
exact condition that would revive it). The codex §15-risk-2 doc-comment fix happens **regardless** —
scope it too.

## Background

Slice 7 = "live-tail completion." Already shipped: the `transcript_turn` SSE event + the
writer-thread→event-loop `loop.call_soon_threadsafe` bridge (4b, `writer.py:192-201`). The opencode
Pull-poll path (§9.3) is parked with slice 6. So slice 7's only open feature is the
**`session_correlated`** SSE event (spec §9.4): fire when a `wire_exchange` row captured with
`session_id = NULL` is later **backfilled** with a session id, so the §8.4 pivot/diff/timeline view
refreshes. It is **entirely absent from code** today (spec/README only).

## The claim to adversarially verify (orchestrator's analysis)

> **Managed-mint (5b/5c) closed the window that produced a NULL→session_id backfill, so
> `session_correlated` has no producer in the current claude+codex flow. It would fire on a transition
> that no longer occurs. Therefore: ship the doc fix, DEFER the event until external-adoption or a
> read-back provider (opencode) actually creates the transition AND a consumer needs the refresh.**

### Code-grounded evidence (confirm or refute each)

1. `bind_exchange` returns `None` (→ `wire_exchange.session_id` NULL) **iff**
   `artifacts.request_ir.metadata.session_id is None` or `run_id is None` (`ingest.py:110-112`). So a
   row is NULL exactly when the captured request carries **no session id on the wire**.
2. Managed conversational turns carry the id on frame 1 — claude `metadata.session_id` = injected
   uuid (5c), codex = thread uuid (5b) — so they correlate at first write and are **never NULL**.
3. The only NULL rows are codex **non-conversational** frames (`request_kind:memory` +
   window-handshake), which have **no session at all** → they stay NULL **permanently** (no session
   exists to backfill them from).
4. The backfill is the COALESCE upsert (`ingest.py:314-334`): it fills a NULL row only when **the
   same `exchange_id` is upserted again, that time carrying a session id it lacked at first capture**.
   That is the **read-back-relearn** flow (pre-5b codex learned its thread uuid from a later frame and
   re-correlated earlier exchanges). Managed-mint owns the id at launch → that re-learn step is gone.
5. The transcript/tailer side never backfills `wire_exchange.session_id` (it upserts the `session`
   row + `transcript_turn` rows only). So there is no other backfill producer.

**Conclusion under test:** no current code path produces a NULL→non-NULL `wire_exchange.session_id`
transition in the managed claude+codex flow ⇒ `session_correlated` has no trigger ⇒ defer.

## Questions for the panel (independent, then converge)

1. **Refute or confirm the claim.** Find ANY current-`main` path that still produces a NULL→non-NULL
   `wire_exchange.session_id` transition in the managed claude+codex flow (a re-upsert with a newly
   available id; a provisional→final seam that changes the binding; a correlation pass you can cite).
   If you find one, the event has a producer and the analysis is wrong — cite file:line.
2. **Build-anyway value vs YAGNI.** Even if it has no producer today, is there a defensible reason to
   build it now (forward-compat for external-adoption/opencode), or is that an event with no producer
   AND no consumer (no UI), i.e. premature? Weigh against the repo's no-backcompat / simplicity-first
   stance.
3. **Does deferring break anything?** Do the permanently-NULL codex phantom rows need any signal for
   §8.4 correctness, or are they correctly inert (uncorrelated, excluded from pivot/diff by design)?
4. **Codex §15-risk-2 doc fix (regardless):** `adapters/codex.py:62-66`. Current tail implies a
   single "frame-1 phantom"; reality = `request_kind:memory` + window-handshake frames, **several per
   session**, no session id, stay pending. Confirm the exact corrected wording.

## Output

A consensus **recommendation**: BUILD (with scope + why the producer exists) or DEFER (with the exact
revival condition + where to record the deferral: spec §9.4 + README + LEDGER). Adversarial discipline:
find ≥1 substantive hole in the analysis or positively justify "confirmed." You propose + reach
consensus; the **orchestrator applies** (doc fix + spec/README/LEDGER notes, or the build brief if
BUILD wins). Dual sign-off with the exact phrases.
