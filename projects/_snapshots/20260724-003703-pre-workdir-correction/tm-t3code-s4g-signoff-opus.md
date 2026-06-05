---
title: Sign-off findings — t3code P1 Slice 4g (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-4g, sign-off, review, continuation, idempotency, concurrency]
summary: Opus independent sign-off on 4g (rebuild continuation + idempotency on the gateway + canvas consumer). Verdict GO-WITH-FIXES. Verbatim run_continuation.py restore is clean on main; merge order confirmed. 3 must-fix + 1 confirm-delta — sharpest is a delete-on-reject race in the new TS single-flight map that can break idempotency (double spawn). First-hand on main @ 7241fff; old sources recovered from 84da72c.
status: active
source: opus (5:2.3), first-hand on main @ 7241fff
confidence: high
created: 2026-07-08
---

# 4g plan sign-off (opus) — GO-WITH-FIXES

Verified the concurrency core (idempotency single-flight) and the continuation merge fidelity
first-hand, recovering the old sources from 84da72c. The plan is sound; the risks are concentrated
in the TS re-implementation of the old Python lock-based dedup. 3 must-fix + 1 confirm-delta.

## Confirmed sound (independently verified)

- **Verbatim run_continuation.py restore is CLEAN on main @ 7241fff.** Every dependency exists
  unchanged: `AsyncSessionDao.get_session_for_owner` (async_dao.py:91),
  `get_first_turn_with_raw_for_owner` (:311), `get_latest_turn_with_raw_for_owner` (:321),
  `SessionPurpose.CONTINUATION` (models.py:24), `EventRow` with `.seq`/`.ir`/`.search_text` (:150/:163/:166).
  The 4e-d-deletion revert does not dangle.
- **Merge order confirmed.** `captured_run_context` builds `launch_fields = {**request.launch_fields,
  **runtime_home_plan.launch_fields}` (:136-138) — template fields merge OVER request. Continuation lineage
  lands in `request.launch_fields` (the base). Today no key collision (template = provenance/home;
  continuation = lineage), so lineage survives; `addon_runtime._string_launch_field(binding,
  "parent_session_id")` (:199) stamps it on the new session row via the unchanged path.
- **Error plumbing is live.** `ContinuationSessionNotFound`→404 / no-pool→503 ride the proven C1
  upstreamStatus/upstreamCode path (`replyRunManagerError` → `RunManagerError.upstreamStatus` → canvas
  detail-aware errors), live since 4e-a — the new continuation errors reuse it, not swallowed.
- **return-existing-even-terminated holds.** TS `RunManager` never evicts terminated runs from its `runs`
  Map, so `getView(runId, owner)` returns the current (terminal) view — old Python parity. Re-reading the
  view per hit gives fresh state.
- **transport.ts refactor is smaller than stated.** `createCapturedRun` has ONE real call site
  (`capturedRunStore.ts:162`); the options-object refactor is a one-site change. The coupling-400 slots into
  the existing `runtimeRouter` `invalid_request` (:59) path.
- **idempotencyKey mint-per-intent** (client `crypto.randomUUID` once per spawn intent) is correct: the
  client need not retain it; the SERVER map dedups process-lifetime; a deliberate retry mints fresh.

## Must-fix

### M1 — delete-on-reject must be identity-guarded, or a late reject breaks idempotency (double spawn)

The single-flight map must store the in-flight promise BEFORE it settles (that IS the single-flight). The
hazard the old Python lock-based `spawn` did NOT have: if the delete-on-reject runs per-caller unguarded
(each of N awaiters of the shared rejected promise does `map.delete(key)` in its catch), a LATE reject
handler can delete a FRESH entry a subsequent caller inserted after the key was first removed:

1. A(keyK)→P1 stored; P1 rejects. B(keyK) awaits P1 (still stored); P1 rejects for B too.
2. A's catch: `delete keyK` (removes P1). C(keyK)→ no key → spawns P2, stores keyK→P2.
3. B's catch runs LATE (shared P1 rejection): `delete keyK` → removes **P2**.
4. D(keyK)→ no key → spawns **P3** — a SECOND real spawn for keyK → double capture prepare, idempotency
   violated (the exact thing it exists to prevent).

Fix: attach the delete ONCE to the shared promise with an identity guard — `if (map.get(key) === entry)
map.delete(key)` — so only the entry that is still this promise is removed. Test: leader rejects, a trailing
caller inserts a fresh promise, assert the fresh entry is NOT deleted and its dedup holds.

### M2 — owner scoping needs a composite (owner, idempotencyKey) map key, not owner-in-value

The plan's `key → {owner, promise}` is a single slot per key; "different owner, same key = distinct"
requires the map key to be composite `(owner, key)`, else two owners' concurrent same-key creates collide on
one slot (one breaks the other's dedup). Client-minted randomUUID makes cross-owner collision astronomically
unlikely, but implement the composite key and keep `getView(runId, owner)` owner-scoping as the backstop (it
returns null on owner mismatch, so no cross-owner run leaks even if the map ever returned the wrong run). Add
a two-owners-same-key → two-spawns test.

### M3 — the parity contract test must assert lineage survives WITH a runtime_template applied

`captured_run_context` merges template OVER request launch_fields (verified), so template has the higher
precedence — the real risk is a template clobbering CONTINUATION lineage, not the reverse (the plan's "must
not clobber runtime-template fields" framing is backwards). Today no key collision, so lineage survives, but
the dict-equality parity test must assert the EXACT merged dict with BOTH a runtime_template AND continuation
present (not the bare continuation case), locking the invariant that `parent_session_id`/`forked_at_seq`/
`resume_context` are never clobbered if a future template introduces a colliding key.

## Confirm-delta (adopt consciously; not blocking)

- **Concurrent-caller-retry-on-leader-failure is NOT preserved.** Old Python: a concurrent same-key caller
  whose leader FAILED spawned fresh (lock released, key never recorded). New TS: all concurrent same-key
  callers share the leader's rejection; only a SUBSEQUENT (post-delete) create retries. This is arguably
  cleaner (no surprise spawn from a trailing concurrent caller), but it IS a parity delta — the plan's
  "delete-on-reject → retry spawns fresh" is true only for a subsequent create, not a concurrent one. Confirm
  acceptance (recommend accept). Also flag, as the plan does: process-lifetime map growth is unbounded =
  old parity, acceptable.

Scope discipline clean (D-g2 faithful-lineage-port honored — no --resume argv; create-path only, no session-store
schema/addon changes). D-g1 Option A (SessionPickerPane Continue) reuses an existing surface. Strong plan; the
concurrency core is the thing to get right (M1).
