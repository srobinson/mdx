# Slice 8b-i — own the transcript: snapshot the CLI transcript into tier-1 at capture

**Goal:** make tier-1 a COMPLETE source of truth for the **transcript** stream. Today tier-1 holds
only the wire (`request.raw`/`response.raw`/`index.jsonl`); the transcript lives ONLY in the CLI's own
file (`~/.claude/projects/.../*.jsonl`, `~/.codex/sessions/.../rollout-*.jsonl`), which the CLI or the
user can GC. When that file is gone, a tier-2 rebuild loses the entire transcript half (the wire↔
transcript DIFF collapses to wire-only). Fix: **tee a byte-faithful copy of every consumed transcript
record into tier-1 at capture**, so rebuild replays TM's OWNED bytes regardless of CLI retention,
`--home-dir`, `source_descriptor`, or `locate`.

**Depends on:** 4b (tailer), 5b/5c (managed-mint), 8a (`iter_run_dirs` enumerates run dirs).
**Unblocks:** 8b-ii (home_dir descriptor + durable owned facts — MUST land AFTER this; it bumps
`ADAPTERS_VERSION` → drop+rebuild, which needs the snapshot to rebuild from), 8c (backfill/rebuild/
reconcile replay from the snapshot). **Branch:** off current `main`.

## HARD scope line (do ONLY this)

This slice ONLY snapshots the transcript to tier-1. It does **NOT**: change the live read source (the
tailer still byte-tails the CLI file and tees a copy); add `home_dir` to the descriptor (8b-ii); bump
`ADAPTERS_VERSION` (8b-ii); build backfill/rebuild/reconcile (8c). If you trip on those, FLAG, don't build.

## Build

1. **New tier-1 per-session transcript slot** under the run dir (`storage_root`) — e.g.
   `<run_dir>/transcripts/<session_id>.jsonl` (per-session so `iter_run_dirs` + a future replay find it;
   exact name is the author's call, justify). `storage/disk_layout.py` gains the path helper.
2. **Tee the raw consumed bytes at the tailer's consumption point** — `index/tailer.py` `_poll_cursor`
   (:157-163, where `handle.read()` + `iter_complete_records(data)` produce the records) / `_ingest_record`
   (:165-182), **BEFORE `normalize`**. normalize lossily drops non-conversational records (claude
   `system`/title; codex `session_meta`/`turn_context`/`event_msg`); the snapshot must keep **ALL** raw
   records byte-faithfully so a future `normalize` change can re-derive them. Append the
   newly-consumed complete-record bytes verbatim.
3. **DAG (load-bearing, the riskiest seam):** the tailer lives in the `index` layer, which imports
   `ir`+`canonicalization` ONLY and must NOT import a `storage` write API. **Inject a snapshot-writer
   callback** into the tailer, built in `load_runtime()` closing over `storage_root`, mirroring how
   `make_index_sink` injects `storage_root`/`on_binding` (`addon_runtime.py:119-122`). NO `storage`
   import in `index/tailer.py`; `storage` never imports `index`.
4. **Off the wire hot path:** the append runs in the tailer thread (sibling to the writer thread), so
   it does NOT touch the §7.1 wire hot path. Synchronous append there is fine.
5. **Idempotent on re-tail:** only newly-consumed bytes are appended (mirror the cursor `byte_offset`);
   a tailer restart / re-registration must not duplicate snapshot content.

## Invariants (must not break)

- **DAG:** NO `storage` import in `index/tailer.py` — injected callback only. (`test_private_import_
  boundary.py` + the import DAG stay green.)
- **#17 privacy:** the injected snapshot-writer is a PUBLIC callable; no cross-module `_` imports.
- **tier-1-first (§7.1):** the wire hot path is unaffected (snapshot is in the tailer thread).
- **ONE iterate path:** reuse `iter_complete_records`; no new parser.
- **Live read source unchanged:** the tailer still reads the CLI file live and tees a copy; the TM
  snapshot is the read source ONLY on the future rebuild/backfill path (8c).
- LOC ≤ 700/file, funcs ≤ 150.

## Files (RE-CONFIRM current line numbers)

`index/tailer.py` (`_poll_cursor` :157-163, `_ingest_record` :165-182, `iter_complete_records` :44-64 —
the tee point + idempotence via the cursor); `storage/disk_layout.py` (:29-73 per-exchange layout —
add the per-session transcript slot); `addon_runtime.py` (:119-122 — where `make_index_sink` is
injected at `load_runtime`; inject the snapshot-writer the same way); `index/ingest.py`
(`make_index_sink` injection pattern reference); `storage/disk.py` (atomic-write reference — note the
snapshot is an APPEND, not the exchange tmp-activate).

## Acceptance (§13; real temp dirs + a REAL run)

- A live session writes BOTH tier-2 `transcript_turn` rows AND a tier-1 transcript snapshot under the
  run dir, per-session.
- The snapshot is **byte-faithful** to the consumed transcript and INCLUDES the non-conversational
  records `normalize` drops (assert a `session_meta`/`system` record is present in the snapshot).
- **DAG:** assert/confirm `index/tailer.py` imports no `storage` write API (the boundary test stays
  green); the snapshot-writer is injected.
- **Idempotent:** re-tailing (restart from the cursor) does not duplicate snapshot bytes.
- **REAL-RUN PROOF (mandatory — capture-path change):** a real `transport-matters claude` AND a real
  `transport-matters codex` session → the tier-1 transcript snapshot exists, byte-matches the CLI
  file's consumed portion, and lands under the run dir (`iter_run_dirs` finds it). State the evidence.
- `just ci` green.

## Sequencing note (carry to 8b-ii)

Do **NOT** bump `ADAPTERS_VERSION`/`schema_version` here. 8b-ii (the `home_dir` descriptor field)
bumps the gate AFTER this lands, so the resulting drop+rebuild has the tier-1 transcript snapshot to
rebuild from. Snapshot-before-schema-bump is the load-bearing order.
