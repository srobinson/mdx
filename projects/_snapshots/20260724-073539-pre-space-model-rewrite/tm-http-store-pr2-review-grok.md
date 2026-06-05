# Wire-store PR-2 review (Grok) — PR #259

| Field | Value |
|-------|--------|
| PR | #259 |
| Branch | `wire-store-pr2-write-path` |
| Head | `deb25b0e3c348c7efaa825ddfcf1d31e9e906c93` |
| Spec | `~/.mdx/projects/tm-http-store-spec.md` §8 PR-2 + DDL (§2) + §4 (+ §3/§7 for write-path support) |
| Lenses | code-review (correctness, confidence-gated) + code-hygiene (sizing, DRY, boundaries) |
| Emphasis | broad correctness + hygiene |
| Tree | pristine at review (`git status --porcelain` empty) |
| CI | 9/9 SUCCESS on head |
| Verdict | **clean / sign-off** |

## Scope checked

Write path only, ships dark:

- migration `0008_wire_store` (6 wire tables)
- `session/wire_contracts.py`, `session/wire_normalization.py`, `session/wire_store.py`
- additive `SessionWriter.submit_wire_exchange` / `submit_wire_exchange_deleted`
- notify-helper extraction (`_typed_notify_payload`)
- top-level `wire_store_observer.make_wire_store_sinks` registered in `addon_runtime._start_session_capture`
- `db wire-gc` → `sweep_wire_store`
- fixtures + focused tests

Not in scope (correctly absent): reader, gateway, `@tm/activity` `pgContracts`, product API surfaces, frozen-plane rework beyond the PR-1 composition line.

## VERIFY matrix

| # | Check | Result |
|---|--------|--------|
| 1 | `wire_store_observer` not under `storage/`; holds `SessionWriter` cleanly; `storage` never imports `session` | **Pass.** Module is `api/src/transport_matters/wire_store_observer.py` (composition plane). Runtime imports: `session.wire_store.WireExchangeWrite`, `workspace.workspace_id`. `SessionWriter` / sink types only under `TYPE_CHECKING`. Storage import scan clean. |
| 2 | GC detects orphaned blobs/sets; never deletes live-referenced rows | **Pass.** `DELETE_ORPHANED_WIRE_SET_MEMBERS_SQL` / `DELETE_ORPHANED_WIRE_SETS_SQL` key off exchange FKs (`system_set_hash` / `tools_set_hash`); `DELETE_UNREFERENCED_WIRE_BLOBS_SQL` requires absence from both `wire_component_set_member` and `wire_request_message`. Order: members → sets → blobs. `test_gc_sweeps_only_unreferenced_rows` keeps shared sets/blobs after deleting one of two exchanges; only after both deletes does GC clear. CLI `db wire-gc` exercises the same path. |
| 3 | No reinvention vs SessionWriter / migration helpers | **Pass.** UPSERT shape mirrors artifact idiom (`ON CONFLICT DO NOTHING RETURNING`). Notify DRY: `_notify_payload`, `_run_lifecycle_notify_payload`, wire write/delete all call `_typed_notify_payload`. Loop pin extracted to `_require_target_loop`. Migration CHECK literals use shared `migrate.sql_text_values` + `wire_contracts` constants. |
| 4 | No file past sizing thresholds | **Pass.** New modules all ≪700: observer 86, contracts 36, normalization 218, wire_store 312, migration 150. Touched existing: `writer.py` 532, `addon_runtime.py` 654, `dao_statements.py` 560. No function over ~150 LOC in the write path. |
| 5 | Ships DARK | **Pass.** Diff is api-only; no `www/`, `packages/`, gateway, or `pgContracts` changes. NOTIFY payloads exist for PR-3 but nothing consumes them yet. |
| 6 | Migration 0008 + writer + observer internally consistent | **Pass.** DDL matches contracts + SQL statements column-for-column. Observer maps `IndexEntry`/`ExchangeArtifacts` → `WireExchangeWrite` (session_id from IR metadata, track fields, codex turn_index, raw byte length). Writer one-shot complete insert + delete/reinsert manifests/blocks; deleted is CASCADE + notify-only-if-row-went-away. |
| 7 | Tree pristine | **Pass.** Clean porcelain at `deb25b0` before verdict. |

## Correctness notes (acceptance-aligned)

- **Normalization §3:** stamp strip for `cache_control` / `tm_wire_index` into `position_meta`; `cache_hint` on system parts; `input_item_raw` + `input_item_raw_stamped` dropped from extras; reconstruction round-trips; stamp key mirror pinned to `codex.preserved_raw.WIRE_INDEX_KEY` without session→codex import.
- **Write path §4:** finalize-once complete row; idempotent replay (`ON CONFLICT DO UPDATE` + manifest/block rewrite); best-effort failure counter; fire-and-forget via `run_coroutine_threadsafe` (cursor-sink idiom); deleted no-op for never-written provisional.
- **Meta variance §3.1:** `_ensure_component_set` first-writer-wins on members; mismatch → `fold_member_meta_into_set_hash`.
- **Dedup yield:** real Codex HTTP-fallback turns assert new blob+extras bytes ≤4% of request raw; leak of raw extras would fail.
- **Composition:** second exchange sink + deleted sink registered beside cursor sink; end-to-end `emit_to_index` / `emit_deleted` integration test populates/clears `wire_exchange`.

## Local verification

```text
# unit / pure (no DB)
test_wire_normalization.py — 13 passed

# with TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres
test_wire_writer.py — 8 passed
test_wire_store_observer.py — 5 passed
cli/test_db_cmd.py::test_db_wire_gc_sweeps_unreferenced_rows — 1 passed
```

CI backend·test SUCCESS on head covers the DB suite in CI.

## Non-blocking notes (do not block merge)

1. **Claude dedup-yield fixture not in suite.** Spec §8 PR-2 acceptance mentions a Claude fixture with the same ≤4% bound; only `codex_http_fallback` is staged and asserted. Claude stamp stripping is unit-covered; Codex is the harder cumulative case. Follow-up test asset only.
2. **Historical `_sql_text_values` remains private in migration 0007.** 0008 correctly uses shared `migrate.sql_text_values`. Do not rewrite applied migrations for cosmetics.
3. **GC wording vs implementation.** Spec §7 says “sets with no members”; code correctly treats sets as live while any exchange references them (stronger / FK-safe). Worth a one-line spec clarify later, not a code change.

## Hygiene summary

| Signal | Assessment |
|--------|------------|
| Ownership | Writer/SQL/contracts in `session/`; observer at api composition plane; storage untouched beyond PR-1 seam usage |
| Duplication | Notify payload and loop-require extracted; no parallel write path |
| Dead code | None observed |
| Boundaries | Import DAG intact (`storage` ↛ `session`) |
| Test shape | Red-first acceptance covers normalize, idempotency, delete, GC, isolation, composition, CLI |

## Issues

None at confidence ≥80.

## Verdict

**clean / sign-off.** PR-2 write path matches the locked schema, normalization, producer, and GC contracts; ships dark; sizing and DRY hold; VERIFY 1–7 pass with evidence above.
