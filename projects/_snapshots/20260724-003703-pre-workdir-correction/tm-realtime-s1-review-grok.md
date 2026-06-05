---
title: Adversarial review — PR #262 realtime slice 1 (live-status store)
type: review
tags: [transport-matters, realtime, slice-1, adversarial]
status: clean
family: grok
pr: 262
branch: realtime-slice1-live-status-store
commit: c8de2d80a2ff5011910353137ff1ec4cb436785f
base: main ef52af6
spec: ~/.mdx/projects/tm-realtime-spec.md §3, §7 slice 1
reviewed: 2026-07-10
---

# Verdict: CLEAN

Working tree pristine at review start (`git status` clean on
`realtime-slice1-live-status-store` @ `c8de2d8`). Read-only review; no source
writes. Diff inspected against slice-1 plan in `tm-realtime-spec.md` §3 / §7.
Focused reds re-run and green (DB via `TRANSPORT_MATTERS_TEST_DATABASE_URL`).

## 1. Fence correctness — PASS

### SQL implements the spec predicate

`UPSERT_RUN_LIVE_STATUS_SQL` (`dao_statements.py`):

```
ON CONFLICT (run_id) DO UPDATE SET
  generation = EXCLUDED.generation, closed = false, ...
WHERE NOT (
  run_live_status.closed
  AND run_live_status.generation = EXCLUDED.generation
)
RETURNING run_id
```

Matches §3.1 exactly (plus harmless workspace/owner columns on SET).
`upsert_run_live_status` returns `fetchone() is not None` so a WHERE-rejected
update reports `applied=False` and does not NOTIFY.

`CLOSE_RUN_LIVE_STATUS_GENERATION_SQL`:

```
UPDATE run_live_status
SET kind = NULL, closed = true, updated_at = now()
WHERE run_id = %(run_id)s AND generation = %(generation)s
```

Matches §3.2. Close is inside `submit_wire_exchange` commit, same txn as
`write_wire_exchange` + wire NOTIFY, gated by
`write.track_role != WIRE_TRACK_ROLE_SUBAGENT`.

### Close key is generation, not exchange_id

`WireExchangeWrite.generation` is required. Observer:

`generation=artifacts.generation or entry.id`

Artifact build sites stamp the stable provisional token:

| Path | generation source |
|---|---|
| HTTP provisional create | `exchange_id` (= provisional) |
| HTTP finalize main | `request_state.provisional_exchange_id` |
| HTTP remint fallback | same provisional (not cleared on finalize fail) |
| Codex provisional create | `exchange_id` |
| Codex finalize main | `provisional_exchange_id` (captured before mark) |
| Codex `_persist_codex_exchange` fallback | `state.provisional_exchange_id` |
| Codex rewrite | `exchange_id` |

Never-provisional / handshake / unparsed leave `generation=None`; observer
falls back to `entry.id` (no live facts to close).

### Reds are real (fail if guard removed)

| Case | Test | Why not a tautology |
|---|---|---|
| Closed-gen straggler is no-op | `test_closed_generation_straggler_is_rejected_and_new_generation_reopens` | Asserts `not applied`, `closed=True`, `kind=None`, `seq` stuck at 1; without WHERE, applied+kind would flip |
| New gen reopens | same test | Asserts `closed=False`, gen-2, kind running_tool |
| Slow finalize of N cannot null N+1 | `test_slow_finalize_cannot_close_the_next_generation` | Close scoped by generation; without `$2` scope, gen-new would close |
| Subagent finalize leaves parent | `test_subagent_finalize_cannot_close_the_parent_live_status` | `track_role=subagent` skips close |
| Finalize+close atomic | `test_finalize_write_and_generation_close_roll_back_together` | Notify failure rolls back wire row and leave live open |
| HTTP remint still closes original gen | `test_http_readback_fallback_closes_the_original_live_generation` | `entry.id != original`; would fail if close keyed on reminted exchange_id |
| Codex remint still closes original gen | `test_codex_finalize_fallback_closes_the_original_live_generation` | Same proof for Codex fallback |
| Observer prefers artifact gen | `test_exchange_sink_prefers_artifact_generation_over_reminted_entry_id` | write.generation stays provisional when entry.id reminted |

No missing fence case from the slice-1 plan. Cross-generation in-flight
serialization is a producer/slot concern (§4.3, slice 3); store fence does not
need a seq comparison operator.

## 2. Frozen plane — PASS

- `ExchangeArtifacts.generation: str | None = None` only; comment pins
  in-memory sink metadata.
- `IndexEntry` untouched (no generation field).
- Disk `_write_exchange_files` is field-by-field; never serializes generation.
- `test_generation_envelope_preserves_complete_tier1_manifest_and_bytes` compares
  full recursive file path→bytes maps baseline vs with generation; asserts
  `restored.generation is None` on readback.
- `test_list_response_excludes_in_memory_sink_generation` asserts list payload
  equals `entry.model_dump(mode="json")` and `"generation" not in response`.
- Storage package has zero imports of `transport_matters.session`.
- Capture-plane delta is +8 lines total across `exchange_recorder.py`,
  `codex/exchange.py`, `storage/base.py` (plus derivation signature plumbing);
  `emit_to_index` remains best-effort/non-blocking.

## 3. Migration — PASS

- `0009_run_live_status` revises `0008_wire_store` (correct next).
- Schema matches §3.1 column-for-column (`generation`, `closed`, `seq`,
  nullable `kind` CHECK, workspace/owner, `updated_at`).
- Style mirrors `0008` (contracts constants + `sql_text_values` + raw
  `op.execute`).
- `downgrade` drops table; new empty table → no data-loss risk.
- `test_migrate` helpers assert present/absent column set and nullability.

## 4. Scope (dark) — PASS

Slice-1 inventory only (Python / api). No `packages/` or `www/` changes.

Absent (correctly deferred):

- `LiveStatusObserver`, tee `on_chunk`, classifier, reframer (slice 2/3)
- `readLiveStatusForRun`, admission, machine folds (slice 4)
- empty-at-spawn SQL (slice 5)

Present and dark:

- `submit_run_live_status` + identity-only `run_live_status` NOTIFY
- finalize generation-close
- generation threading on in-memory envelope

Existing activity listener already ignores unknown payload types
(`tmEvents.test.ts`: "ignores unknown payload types"), so the new doorbell is
safe while no consumer admits it.

## 5. DRY / sizing — PASS

- Contracts: `live_status_contracts.py` follows wire/lifecycle pattern.
- Shared test builder: `live_status_test_support.make_run_live_status`.
- `WIRE_TRACK_ROLE_SUBAGENT` extracted once in `wire_contracts`.
- DAO row params reuse `model_dump` + `strip_decoded_nuls` like lifecycle.
- Writer notify payload via existing `_typed_notify_payload`.
- Touched files under 700-line hard limit (writer 643, dao_statements 599,
  test_wire_writer 552). No function near 150-line blowout from this slice.

## Evidence (tests re-run this review)

```
test_closed_generation_straggler_is_rejected_and_new_generation_reopens  PASS
test_slow_finalize_cannot_close_the_next_generation                      PASS
test_subagent_finalize_cannot_close_the_parent_live_status               PASS
test_finalize_write_and_generation_close_roll_back_together              PASS
test_live_status_write_persists_and_notifies                             PASS
test_http_readback_fallback_closes_the_original_live_generation          PASS
test_codex_finalize_fallback_closes_the_original_live_generation         PASS
test_generation_envelope_preserves_complete_tier1_manifest_and_bytes     PASS
test_exchange_sink_prefers_artifact_generation_over_reminted_entry_id    PASS
test_list_response_excludes_in_memory_sink_generation                    PASS
```

## Findings

None. No BLOCKER / MAJOR / MINOR.
