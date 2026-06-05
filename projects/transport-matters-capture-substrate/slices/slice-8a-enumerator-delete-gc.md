# Slice 8a — durable enumerator + delete + block GC (tier-2 maintenance, SQL-only)

**Goal:** the safe, launch-state-free half of §10 maintenance. New `index/maintenance.py` with three
pure tier-2 operations and the durable run enumerator. **No backfill, no rebuild, no reconcile —
those are 8b** (they carry the connection-quiescence + `sessions.json` rebuild-faithfulness decision).

**Depends on:** slice 1 (schema/db/FK shape + FTS trigger), slices 2-5c (ingest, run dirs). **Branch:**
off current `main`. **Scope discipline:** 8a touches ZERO launch state; if a piece needs
`owned_*`/`source_descriptor`/the launch env, it belongs in 8b — flag it, don't build it here.

## Build (new `index/maintenance.py`, budgeted ~300 LOC, §10.6)

1. **`iter_run_dirs`** (§10.1) — the **durable** run enumerator. Globs
   `default_workspaces_root()/*/*/*/index.jsonl` (`storage_roots.py:14`; layout
   `{slug}/{hash}/{run_id}/index.jsonl`, `disk_layout.py:52-53`) and yields a small
   `RunDir(root: Path, run_id: str)`. **MUST NOT** use `manifest.read_all` (`manifest.py:98-109`) —
   manifests are LIVE-only and unlink on exit, so they'd miss completed runs (the §10.1 invariant).
   This is the durable substitute every maintenance caller uses for run discovery. `run_id` is the dir
   name; confirm against `resolve_storage_dir` (`launch_runtime.py:288-299`).
2. **`delete_run(run_id)` / `delete_exchange(exchange_id)`** (§10.2) — tier-2 delete. Entities-first
   (`DELETE FROM wire_exchange`/`transcript_turn`/`session WHERE run_id=…`), edges cascade via the
   FK shape (`schema.py:118,129`). Then run (or document the caller runs) `gc_blocks`. **Decide +
   justify** (per §10.2): does `delete_run` also remove the tier-1 raw dir (`disk.py:265-308`), or is
   tier-1 deletion the caller's job and maintenance is tier-2-only? State the contract explicitly.
3. **`gc_blocks()`** (§10.3) — mark-sweep: `DELETE FROM block` where the block is referenced by
   neither `exchange_block` nor `turn_block`. Block FKs have **no cascade** (by design,
   `schema.py`), which is what makes the sweep safe. FTS eviction rides the `block_ad` AFTER DELETE
   trigger (`schema.py:144-146`) — verify it fires. Idempotent. **Cross-stream invariant:** a block
   referenced by BOTH an `exchange_block` and a `turn_block` (the §3.3 dedup linchpin) survives until
   BOTH refs are gone — the GC predicate must check both edge tables, not one.

## Invariants (must not break)

- **#17 privacy** (AST-enforced `test_private_import_boundary.py`): `maintenance.py` imports PUBLIC
  names only; keep its own helpers `_`-prefixed.
- **DAG:** `maintenance.py` may import `ir`/`canonicalization` + storage **read** APIs
  (`default_workspaces_root` `storage_roots.py:14`, `read_index`/`read_exchange` `base.py`) + the
  `index` core — but **NOT `server`**, and `storage` must never import `maintenance`.
- **Single-writer (load-bearing):** tier-2 has ONE writer (the §6 writer thread, WAL +
  busy_timeout). Maintenance mutations must go through that single-writer path (submit as
  maintenance jobs to the writer, or use the writer's connection) — NOT a second parallel write
  connection. Confirm the §10 maintenance-job pattern against `writer.py`/`db.py:63-73` and state it.
- `iter_run_dirs` is pure + durable (glob only, no manifest, no live-set filtering — filtering the
  live set is reconcile's job in 8b).
- LOC ≤ 700/file, funcs ≤ 150; builtins-only typing; Pydantic v2; IR frozen.

## Acceptance (§13.1/§13.2; real temp SQLite + seeded run dirs)

- **`iter_run_dirs`** enumerates seeded `{slug}/{hash}/{run_id}/index.jsonl` dirs durably; a run with
  NO manifest (simulating post-exit) is still found; a dir without `index.jsonl` is skipped.
- **`delete_run`** removes all tier-2 rows for the run + cascades edges; a second run's rows are
  untouched; the declared tier-1 contract (point 2) holds.
- **`delete_exchange`** removes one `wire_exchange` + its `exchange_block` edges; a block still
  referenced by another exchange/turn SURVIVES.
- **`gc_blocks`** deletes only unreferenced blocks; FK-safe; FTS row evicted; idempotent on re-run; a
  both-streams block survives until both refs are deleted (state the evidence).
- `just ci` green.

## Grounding (RE-CONFIRM current line numbers)

`index/schema.py` (FK shape :118/:129, block edge indexes :121/:132, `block_ad` FTS trigger :144-146,
`_DROP_DDL` :150-161), `index/db.py` (`transaction` :63-73), `index/writer.py` (single-writer job
pattern), `index/ingest.py` (writer-thread job convention), `storage/storage_roots.py`
(`default_workspaces_root` :14), `storage/disk_layout.py` (index.jsonl path :52-53),
`storage/manifest.py` (`read_all` :98-109 — what NOT to use), `storage/disk.py` (tier-1 delete
:265-308 — reference for the point-2 contract).

## Out of scope → 8b (do NOT build here; flag if you trip on it)

backfill (§11.2), rebuild executor + boot rebuild-lock + connection-quiescence (§10.5), reconcile
(§10.4), and the **rebuild-faithfulness decision**: `owned_source_descriptor`/`cli` live only in the
launch env, never in tier-1, so codex's owned descriptor is lost on rebuild (codex has no `locate`
fallback post-5b) → 8b decides whether to ship durable per-run `sessions.json` (§11.1). 8a must not
depend on any of this.
