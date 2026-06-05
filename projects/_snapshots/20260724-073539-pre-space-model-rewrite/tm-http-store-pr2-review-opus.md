# PR #259 review — wire-store PR-2 (write path, ships dark)

**Branch:** `wire-store-pr2-write-path` · **head:** `deb25b0` · **base:** `main`
**Reviewer:** Opus 4.8 (contract-weight, read-only) · **CI:** 9/9 green · **tree:** pristine (`git status --porcelain` empty at `deb25b0`)
**Spec:** `~/.mdx/projects/tm-http-store-spec.md` §8 PR-2 + DDL + §4 · **Lenses:** code-review (8 angle) + code-hygiene · **Emphasis:** adversarial dedup/observer correctness

## Verdict

**Clean signoff.** Zero correctness defects on any real path. The dedup engine, replay-convergence,
delete tolerance, observer isolation, dual-path registration, and dark-ship boundary all hold under
adversarial reading and are pinned by tests. Three LOW hygiene/latent notes below, none blocking.

## Verification matrix (brief items 1–6)

| Ask | Result | Evidence |
|---|---|---|
| (1) `canonical_json` deterministic; stamps stripped BEFORE hashing; both `input_item_raw*` dropped | PASS | `canonicalization.canonical_json` sorts mapping keys (`_canonical_mapping` iterates `sorted(value)`) so identical bodies hash identically. `wire_normalization._strip_stamps` removes `cache_control`+`tm_wire_index` from every `provider_data` (message, per-block, system_part, tool_def) into `position_meta` before `_component` hashes; `normalize_system_part` strips top-level `cache_hint` too. `normalize_request.request_extras` filters `STRIPPED_REQUEST_EXTRAS_KEYS = (input_item_raw, input_item_raw_stamped)`. Stamp model is exhaustive: in `ir.py` `cache_control` lives only inside `provider_data`, never as a top-level block field. `test_wire_normalization::test_fixture_prefix_dedups_completely` proves real Codex-fallback prefixes hash-identically turn-over-turn; `test_dedup_yield_on_real_fallback_turns` bounds new-blob+extras bytes ≤4% so any leak into hash OR extras fails CI. |
| (2) replay-convergence: same exchange twice → one row set | PASS | `wire_store.write_wire_exchange` is insert-if-absent for blobs (`UPSERT_WIRE_BLOB_SQL ON CONFLICT DO NOTHING`) and sets, upserts the exchange by PK, and DELETEs+reinserts manifests/blocks; whole body runs in the caller's single `conn.transaction()` (`writer.submit_wire_exchange`). `test_replayed_finalize_converges_to_identical_state` asserts `_wire_state == snapshot` and `second.stats.new_blob_bytes == 0`. |
| (3) observer preserves per-subscriber isolation; registered on BOTH launch paths | PASS | `wire_store_observer.on_exchange` is fire-and-forget (`asyncio.run_coroutine_threadsafe`, Future discarded); its only synchronous work (`resolve_run`, `WireExchangeWrite(...)`) runs inside PR-1's `emit_to_index` per-sink try/except, so a raise is isolated and cannot starve the cursor sink or the capture path. It does not swallow peers or re-raise, so it does not defeat `_fan_out`. `SessionWriter.submit_wire_exchange` additionally wraps its own body and routes every failure through `_record_wire_failure` (counts+logs, never raises). `addon_runtime._start_session_capture` registers `wire_sink`/`wire_deleted_sink` UNCONDITIONALLY, and both `load_capture_runtime` and `load_shared_capture_runtime` call `_start_session_capture`, so both launch paths get the observer. Loop identity verified: the `loop` handed to `make_wire_store_sinks` is the same `loop` the `SessionWriter` is pinned to, so `_require_target_loop` never trips. Covered by `test_write_failure_is_counted_and_non_throwing`, PR-1 `test_failing_subscriber_does_not_stop_peers`, and `test_shared_capture_runtime_populates_wire_store_from_emitted_exchange`. |
| (4) `submit_wire_exchange_deleted` tolerates never-written ids; no orphaned blobs | PASS | `delete_wire_exchange` returns `bool(rowcount)`; a missing row yields `deleted=False`, `ok=True`, and no notify. The exchange DELETE CASCADEs manifests/blocks (FK `ON DELETE CASCADE`) but never touches `wire_blob`/`wire_component_set`; reclamation is the reference-driven `sweep_wire_store` GC. `test_deleted_tolerates_never_written_exchange`, `test_deleted_removes_exchange_rows_and_keeps_blobs` (`blobs_after == blobs_before`), and `test_gc_sweeps_only_unreferenced_rows`. |
| (5) ships DARK (no reader/API) | PASS | `git diff --stat` touches only migration 0008, `addon_runtime`, `cli/db_cmd` (manual `wire-gc`), `session/{wire_*, writer, dao_statements, migrate}`, `wire_store_observer`, and fixtures/tests. No `api/v1` route, no `www`/canvas bundle, no `pgContracts.ts` (wire_contracts.py notes the TS mirror lands PR-3). |
| (6) tree pristine | PASS | `git status --porcelain` empty at `deb25b0`; review performed read-only. |

## Adversarial dedup notes (all resolved to correct)

- **Folded-set variance (`_ensure_component_set`).** Set identity hashes member *hashes* only (stamp-independent); when a set's stored member `position_meta` differs from the incoming set (first-writer-wins), it mints `fold_member_meta_into_set_hash` covering the metas and points the exchange there. Traced three-exchange convergence: two exchanges with identical metas resolve to the same folded hash, so dedup survives variance. `position_meta` round-trips through jsonb as order-independent dicts / scalar stamps, so the `stored == ours` compare is stable; a false mismatch would only mint a redundant set, never corrupt.
- **Response bodies are stored inline** (`wire_response_block.body`), not content-addressed. Intentional (responses don't repeat across turns like request prefixes) and consistent with the blob-GC predicate, which counts only set-members and request-message manifests.
- **request_extras / sampling / request_metadata** are per-exchange columns, not deduped; extras bloat is bounded by the ≤4% dedup-yield test.

## Findings (LOW; hygiene/latent, non-blocking)

### LOW 1 (latent, robustness) — `addon_runtime._start_session_capture` sink registration is append-only
PR-1 replaced replace-semantics with append + clear-all; PR-2 now registers three sinks per call
(`wire_sink`, `wire_deleted_sink` unconditionally, cursor sink conditionally). Safe today: one capture
runtime per process, torn down by `clear_exchange_sinks` (which clears both registries). If a second
capture ever starts in-process without an intervening clear, sinks accumulate and each exchange
double-writes; the writes are idempotent so state stays correct, but the fan-out is wasted. This is the
PR-1 Note-1 hazard amplified by two more registrants; a one-line idempotent-append or dedup-on-register
closes it when a genuine second capture arrives.

### LOW 2 (DRY) — `writer.submit_wire_exchange` / `submit_wire_exchange_deleted`
Both share the `_ensure_open` → `pool.connection() + conn.transaction()` → conditional `pg_notify` →
`WireExchangeCommitResult` → `except → _record_wire_failure` skeleton. A private
`_wire_txn(exchange_id, run_id, body)` taking the in-transaction closure would collapse the duplication;
bodies differ enough (write vs delete + delete-gated notify) that this is a craftsmanship fold-in, not a blocker.

### LOW 3 (watch, hygiene) — `addon_runtime.py` at 654/700
PR-2 added +8 lines; the PR-3 read path composes more here. The detached run-lifecycle-event cluster
(`_running_loop`, `_emit/_schedule/_drain/_consume/_release` run-lifecycle helpers) is the pre-emptive
extraction seam to a `run_lifecycle_events.py` adapter — carried forward from the PR-1 hygiene map, touches
nothing the read path edits. Not part of PR-2; do it before the file crosses 700.

## Acceptance (spec §8 PR-2)
- 6 wire tables + CHECK-constrained vocabulary from `wire_contracts` — met (migration 0008, `sql_text_values` guards apostrophes).
- content-addressed dedup with stamp stripping — met (see item 1).
- additive `SessionWriter.submit_wire_exchange`/`_deleted`, best-effort per §7.1 — met (`_record_wire_failure`).
- wire_store_observer as 2nd ExchangeSink subscriber, both launch paths — met (see item 3).
- `db wire-gc` reference-driven sweep — met (`sweep_wire_store`, `test_gc_sweeps_only_unreferenced_rows`).
- ships dark — met (see item 5).
