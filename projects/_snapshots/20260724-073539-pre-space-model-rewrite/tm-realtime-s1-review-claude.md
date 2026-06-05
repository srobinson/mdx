---
title: PR #262 adversarial review — realtime slice 1 (live-status store + generation fence)
type: review-findings
reviewer: claude
pr: 262
branch: realtime-slice1-live-status-store
head: c8de2d80a2ff5011910353137ff1ec4cb436785f
spec: ~/.mdx/projects/tm-realtime-spec.md (Slice 1, §3.1/§3.2, §7 row 1)
date: 2026-07-10
verdict: 1 MINOR, 0 MAJOR, 0 BLOCKER
---

# Verdict

One MINOR (test-scaffolding duplication). No blockers, no majors. The fence is
correct, the frozen plane is proven untouched, the slice lands dark, and the
gate is green. Every claim below was verified against source at head
`c8de2d8`, not the diff text. Working tree confirmed pristine before and after
review; all mutation experiments ran in a scratchpad clone, never in the repo.

# 1. Fence correctness — CONFIRMED, mutation-tested

**Guarded upsert** (`UPSERT_RUN_LIVE_STATUS_SQL`,
`session/dao_statements.py`): `ON CONFLICT (run_id) DO UPDATE SET ...
closed = false ... WHERE NOT (run_live_status.closed AND
run_live_status.generation = EXCLUDED.generation) RETURNING run_id`. Matches
spec §3.1 exactly. Applied-detection is sound: a predicate-rejected DO UPDATE
returns no row, so `AsyncSessionDao.upsert_run_live_status` reports
`applied=False` and `submit_run_live_status` skips the NOTIFY.

**Finalize close** (`CLOSE_RUN_LIVE_STATUS_GENERATION_SQL`): `SET kind = NULL,
closed = true WHERE run_id = $1 AND generation = $2`, executed inside
`submit_wire_exchange`'s commit closure, guarded by
`write.track_role != WIRE_TRACK_ROLE_SUBAGENT`, keyed on the new
`WireExchangeWrite.generation`, never `exchange_id`. Transaction scoping
verified at source: the closure runs under `_commit_wire_raising`, which wraps
`write_wire_exchange` + close + wire NOTIFY in one `conn.transaction()`
(`session/writer.py`). No separate live-status NOTIFY for the close, per spec.
The ForeignKeyViolation retry path re-runs the closure; the close is
idempotent under replay (same run_id + generation match).

**Mutation testing** (scratchpad clone of head, original venv, PYTHONPATH
shadowing; each mutation reverted after its run). Baseline: all 5 fence tests
pass. Then:

| Mutation | Expected red test | Result |
|---|---|---|
| Remove upsert `WHERE NOT (closed AND generation = EXCLUDED.generation)` | `test_closed_generation_straggler_is_rejected_and_new_generation_reopens` | FAILED ✓ |
| Drop `AND generation = %(generation)s` from the close | `test_slow_finalize_cannot_close_the_next_generation` | FAILED ✓ |
| Remove the subagent track-role guard | `test_subagent_finalize_cannot_close_the_parent_live_status` | FAILED ✓ |
| Observer sends `generation=entry.id` (i.e. close keyed on reminted exchange id) | both fallback tests (`test_http_readback_fallback_closes_the_original_live_generation`, `test_codex_finalize_fallback_closes_the_original_live_generation`) | both FAILED ✓ |

All four guards are load-bearing; no tautologies. The straggler test also
asserts the row content (closed=true, kind=None, seq unchanged), not just the
`applied` flag, and the reopen leg asserts `closed=false` under the new
generation. The atomicity test
(`test_finalize_write_and_generation_close_roll_back_together`) proves a
failed NOTIFY rolls back both the `wire_exchange` row and the close.

**Fallback threading**: both fallback tests are end-to-end through the real
seam (provisional persist → tier-1 delete → finalize remints a new uuid →
sink → `WireStoreObserver.on_exchange` → `submit_wire_exchange`), and assert
the row closed under the ORIGINAL provisional generation while
`entries[0].id != original_generation`. That drives the actual
`artifacts.generation or entry.id` threading, as the M4 mutation confirms.

**Missing cases**: none material for slice 1.
- An older-generation (F ≠ closed G) straggler would reopen the row; this is
  by design — the spec rules it out via the producer's per-run serialized
  latest-wins slot (§3.1/§4.3, lands slice 3) and absorbs residue via
  admit-once (§5.2). Not a slice-1 defect.
- Not tested: a rejected straggler fires no NOTIFY (code does the right thing
  via `if applied:`). A spurious doorbell would be harmless; observation only.

# 2. Frozen plane — CONFIRMED

- `generation` lives only on the in-memory `ExchangeArtifacts`
  (`storage/base.py`), optional, default None. `grep generation storage/` has
  no other hit: the disk backend (`persist_exchange` →
  `_write_exchange_files`) serializes fields individually
  (`model_dump_json` per field), never the artifacts model wholesale.
  `read_exchange` rebuilds artifacts without generation
  (asserted: `restored.generation is None`).
- `IndexEntry` untouched by the diff.
- **Complete-manifest guard**: `test_generation_envelope_preserves_complete_
  tier1_manifest_and_bytes` snapshots the ENTIRE run directory via
  `rglob` (every file path + full bytes) for a baseline persist vs a
  generation-carrying persist and asserts equality — this is the full-manifest
  guard the brief requires, not an entry.json/index.jsonl spot check. Caveat
  (observation, not a finding): the fixture populates request/response fields
  but not events/turn/transport/curated; acceptable because disk writes each
  field independently and storage has zero `generation` references outside the
  model field, so there is no alternate leak path.
- **Inspector API guard**:
  `test_list_response_excludes_in_memory_sink_generation` asserts the
  `/v1/runs/{run}/exchanges` response equals `entry.model_dump(mode="json")`
  exactly and carries no `generation` key.
- Import DAG holds: `storage` gains no `session` import; the only capture-
  plane edits are setting a field on an in-memory model at artifact build
  sites (non-blocking, best-effort posture unchanged).
- All 7 non-test `ExchangeArtifacts` build sites checked: the five
  provisional/finalize/fallback sites plus `rewrite_codex_provisional_exchange`
  set generation per spec §3.2; the two unparsed-exchange sites
  (`exchange_recorder.py` unparsed request, `codex/exchange.py` handshake
  failure) deliberately don't — never-provisional, no live facts, covered by
  the `or entry.id` fallback whose close is a no-op UPDATE. Matches the spec's
  stated posture verbatim.

# 3. Migration — CONFIRMED

`0009_run_live_status` revises `0008_wire_store` (correct next number), same
style as 0008 (constants imported from the contracts module,
`sql_text_values` for the CHECK list, raw `op.execute` DDL). New table only —
zero data-loss risk. Downgrade drops the table, matching the wire-store
pattern. `test_migrate.py` now walks head → 0008 → 0007 in both smoke tests,
asserts the full column set, types, and nullability
(`_assert_run_live_status_present/_absent`), and `_reset_to_unmigrated` drops
the new table.

# 4. Scope (dark) — CONFIRMED

- `submit_run_live_status` has zero callers in `src/` (writer definition
  only); no tee hook, no reframer, no classifier, no `LiveStatusObserver` in
  this diff — producer is slice 3.
- Zero TS/packages changes — consumer is slice 4.
- `WireExchangeWrite` is constructed in exactly one src site
  (`wire_store_observer.py`), updated; the new required field can break no
  other path.
- NOTIFY payload is identity-only (`run_id`, slugs, `owner` — no kind, no
  ts), matching §3.3.

# 5. DRY / sizing

- Good reuse: `WIRE_TRACK_ROLE_PARENT/SUBAGENT` extracted into
  `wire_contracts.py` instead of a string literal; `live_status_contracts.py`
  mirrors the `run_lifecycle_contracts.py` pattern; shared
  `make_run_live_status` builder used by all three DB test modules; migration
  reuses `sql_text_values`.
- File sizes all within limits: largest touched file is `session/writer.py`
  at 643 lines (approaching the 700 hard limit — the slice-4 era should plan
  a split before adding more).

**MINOR (the one finding):** the two fallback tests duplicate the
writer+observer harness and the row-readback assert block.
`test_exchange_recorder_http_provisional_flow.py::test_http_readback_fallback_
closes_the_original_live_generation` and
`codex/test_exchange_finalize_sink.py::test_codex_finalize_fallback_closes_
the_original_live_generation` each inline: `SessionWriter(create_async_pool(
test_db.database_url), loop=...)`, `clear_exchange_sinks()`,
`WireStoreObserver(writer, loop, None)` + `register()`, the identical
`finally: await observer.aclose(); await writer.aclose();
clear_exchange_sinks()` teardown, and a byte-identical
`SELECT generation, closed, kind FROM run_live_status WHERE run_id = ...` +
dict-equality block (~15 duplicated lines across the pair, both new in this
PR). A harness contextmanager plus a `read_live_status_row(db_url, run_id)`
helper beside `make_run_live_status` in
`session/live_status_test_support.py` would serve both.

# Gate

`cd api && just check && just test` run at head on the reviewer's machine:
exit 0, `1894 passed` (output content verified, not just exit code).
`TestDb.create()` raises when Postgres is unconfigured (no silent skip), so
the DB-backed fence tests are hard gates in CI too.
