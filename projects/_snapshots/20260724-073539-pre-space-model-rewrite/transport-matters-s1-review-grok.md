# S1 review — PR#300 `feat/s1-provider-condition-signal` @ `ab34662b`

**Range:** `main..ab34662b` (`506e0409..ab34662b`)
**Tree:** pristine at review start and before verdict
**Spec:** `~/.mdx/projects/transport-matters-spec-s1-rejection-signal.md`
**Verdict:** **issue** — 1 major, 1 minor

## Summary

S1 lands the provider-condition producer end to end: wire classification, live-status kinds + sticky durable projection, activity machine/contract mirrors, delivery resolution (bound + unbound), watch envelope, migration `0025_provider_condition_kinds` (29 chars, CHECK widen, head pin). Most load-bearing checks hold under direct code trace. One production mismatch against the spec's episode contract remains open, and the test that claims rearm is a false green for it.

## Load-bearing checks

| # | Check | Result |
|---|--------|--------|
| 1 | BOUNDARY: provider-condition reasons disjoint from `HARNESS_REJECTION_PROMPT_REASONS`; zero drift on those reasons | **PASS** |
| 2 | ONE-GENERATION: codex handshake rejection reuses persisted exchange id; prod emission test fails if missing/divergent | **PASS** |
| 3 | LAUNCHER WAKE: 401/429 resolve unbound + bound deliveries with reason; cursorless result does not raise | **PASS** |
| 4 | STICKINESS: survives finalize/restart; `submit_wire_exchange` close preserves sticky kinds | **PASS** |
| 5 | REARM: 401→success→401 and 429→success→429 re-fire after episode close | **FAIL** (see Major 1) |
| 6 | Migration 0025 CHECK DDL + revision id ≤32 | **PASS** (slug len 29; mirrors 0011) |
| 7 | General correctness / ripple | See minor |

### 1. BOUNDARY — PASS

- `provider_conditions.PROVIDER_CONDITIONS` owns the literals; `prompt_models.PROVIDER_CONDITION_PROMPT_REASONS = frozenset(PROVIDER_CONDITIONS)` is a third set, explicitly documented as disjoint from operational + harness-rejection vocabularies.
- `HARNESS_REJECTION_PROMPT_REASONS` remains `{"harness_rejected_prompt"}` only; drift emitter still gates on that allowlist alone (`harnesses/drift_emitter.py`).
- Tests: `test_provider_condition_reasons_are_disjoint_from_the_drift_vocabulary`, `test_provider_condition_receipts_never_emit_drift` (param over the condition set). No path mints harness-rejection evidence from a condition reason.

### 2. ONE-GENERATION — PASS

- `persist_codex_handshake_failure` returns `CodexHandshakeFailure(run_id, exchange_id, status_code)` with the same `exchange_id` written to storage.
- `handle_response` threads that identity into `live_status.observe_codex_handshake_rejection(..., exchange_id=failure.exchange_id, ...)`.
- `_offer_condition` uses `generation=exchange_id`.
- Prod-path test `test_handshake_rejection_emits_auth_condition_on_the_persisted_identity` drives `handle_response` (not a faked handoff), asserts `row.generation == persisted_exchange_id` and a single live row. Would fail if emission were dropped or a second id were minted.

### 3. LAUNCHER WAKE — PASS

- `_provider_condition(target)` reads `needs_you.kind` against `PROVIDER_CONDITIONS`.
- Bound active-prompt branch finishes `needs_you` with `reason=condition` (ab34662b fix for bound-delivery-lost-reason).
- Separate loop resolves open deliveries that never bound a prompt cursor when `condition is not None` (handshake reject case).
- `_result`: range raise limited to `state == "completed"`; `needs_you` without cursors returns reason with null range (no raise).
- Tests: unbound parametrized auth/usage; bound `auth_required` asserts reason.

### 4. STICKINESS — PASS

- Observer: same-generation stop / `flow_abort` early-returns so the failed flow cannot erase the sticky row (`_offer`).
- Durable: `CLOSE_RUN_LIVE_STATUS_GENERATION_SQL` sets `kind = CASE WHEN kind IN (sticky) THEN kind ELSE NULL END, closed = true` — not an unconditional clear.
- `submit_wire_exchange` still calls close on finalize; stickiness is in the SQL, not a skipped call.
- Test: `test_provider_condition_kind_survives_the_generation_close` asserts closed + `kind=auth_required`.
- Activity plane: provider-condition states mirror asked (no stall timer); wireCandidate treats condition rows as sticky truth; canvas labels land for both statuses.

### 5. REARM / episode — FAIL (Major 1)

Spec: one signal per run per condition; episode closes only on a subsequent successful terminal turn; then rearm. Required test: second 401 in the same episode emits nothing; 401→success→401 re-fires (same for 429).

Production:

```python
# live_status_observer._offer_condition
if self._sticky_by_run.get(run_id) == (condition, generation):
    return
```

Dedup is **exact (condition, generation)**. A later failed turn with a fresh provisional exchange id (same condition, no success yet) re-emits and overwrites sticky. That violates "second 401 in the same episode emits nothing."

The success-close path in `_offer` (pop sticky on terminal, non-`flow_abort`, other generation) is coherent with the intended rearm, but is unreachable as the gate for re-fire because generation change alone already re-fires.

Test gap / false green: `test_provider_condition_dedups_within_an_episode_and_rearms_on_a_new_turn` comments "401 -> success -> 401" then fires `gen-b` 401 with **no success terminal between**. It passes under the buggy equality and never exercises success-mediated rearm. No 429 rearm coverage either.

Fix shape (not applied; review-only): treat sticky as open episode on **condition alone** for the run (`sticky[0] == condition` → suppress); keep generation for identity/same-flow stop protection; only emit again after sticky is popped by a genuine later-turn success terminal. Replace the false-green test with: (1) 401 gen-a emit; (2) 401 gen-b no success → still one row; (3) successful terminal gen-success; (4) 401 gen-c → second row. Parametrize 429.

### 6. Migration 0025 — PASS

- Revision id `0025_provider_condition_kinds` length 29 (≤32).
- `down_revision = 0024_drop_observation_identity` (main head at review; S2-independent).
- Drop + re-add named CHECK with widened set; downgrade nulls condition kinds then restores previous set — same pattern as `0011_run_live_status_asked`.
- `EXPECTED_MIGRATION_HEAD_REVISION` + roundtrip walk step updated.

### 7. Other traces

- Shared `CODEX_AUTH_REJECTED_STATUSES` used by diagnostics + classifier.
- Anthropic header-time classification via `observe_response_status` before optional stream tap; non-condition statuses no-op.
- Codex `usage_limit_reached` documented follow-up in `classify_provider_response_status` (no guessed frame).
- Contract/activity/Python mirrors + `test_type_mirrors` status and needs_you kind pins.
- CONTROLPLANE.md / OBSERVATION-PLAN needs_you definitions updated for provider conditions + cursorless resolution.
- Canvas `RunVitalsStrip` labels: "Login needed" / "Usage limit".

## Issues

### Issue 1 — Severity: major

- File: `api/src/transport_matters/live_status_observer.py` (`_offer_condition` sticky equality)
- Also: `api/src/transport_matters/test_live_status_observer.py` (`test_provider_condition_dedups_within_an_episode_and_rearms_on_a_new_turn`)
- Description: Episode dedup keys on `(condition, generation)`, so a second failed turn in the same unresolved condition episode (new generation, no intervening success) re-emits. Spec requires one signal per run per condition until a successful terminal closes the episode. The named rearm test documents success-mediated rearm but never inserts a success, so it is a false green for the required contract; 429 rearm is untested.
- Suggestion: Dedup open episodes by condition for the run; rearm only after sticky pop on later-generation successful terminal (existing `_offer` branch). Rewrite the test as emit → same-episode second fail suppressed → success → re-fire; cover both conditions.
- Status: open

### Issue 2 — Severity: minor

- File: `api/src/transport_matters/codex/test_transport_lifecycle.py` (`test_handshake_rejection_emits_auth_condition_on_the_persisted_identity`)
- Description: Prod-path one-generation identity is proven for upgrade 401 only. Codex auth rejection is 401 **and** 403 (`CODEX_AUTH_REJECTED_STATUSES`); 403 is covered for diagnostics/persist elsewhere but not for the live signal identity assertion.
- Suggestion: Parametrize the prod emission test on `(401, 403)`.
- Status: open

## Not issues (checked)

- Bound delivery reason loss (ab34662b): fixed; tested.
- Cursorless `_result` raise: scoped to `completed` only.
- Unconditional kind clear on finalize: sticky CASE keeps condition kinds.
- Drift vocabulary pollution: structural + receipt tests.
- Migration slug length / head chain: correct for this branch vs current main.

## Counts

- major: 1
- minor: 1
- nits: 0
