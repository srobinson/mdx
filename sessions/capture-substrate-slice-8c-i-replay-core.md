---
title: Capture-substrate slice 8c-i — the replay core (rebuild tier-2 from tier-1 alone)
type: sessions
tags: [backend, transport-matters, capture-substrate, slice-8c-i, rebuild, replay, backfill, reconcile, moe]
summary: New index/rebuild.py with one DRY replay_run core + backfill/reconcile/explicit-rebuild callers that reconstruct tier-2 from tier-1 (wire artifacts + 8b-i snapshot + 8b-ii sessions.json) alone.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

Slice 8c-i delivers the payoff of the capture-substrate arc: **tier-2 (the SQLite projection) is
faithfully rebuildable from tier-1 alone** — drop the index, replay every durable run dir, and the
timelines / DIFF / pivot / correlation come back identical, *including a session whose CLI transcript
file has been deleted* (replayed from the 8b-i snapshot).

Branch `feat/capture-slice-8c-i-replay-core-backfill-reconcile` @ `6ef6e4d` (first impl `b84c942`,
off main `05abbf5`). MoE: author 3.1 (claude), reviewer 3.2 (codex). `api ci` green: 1204 passed
(ruff format + check, mypy, pytest). Awaiting 3.2 re-review → dual sign-off → 2.1 opens PR → Stuart
road-tests the killer demo before merge.

Key decisions:
- **One DRY core, three thin callers.** `replay_run(writer, run_dir)` is the only reusable core;
  `backfill` / `reconcile` / `rebuild` are ≤~15-LOC glue.
- **Reads the snapshot, never the CLI file.** Transcript replay reads
  `transcript_snapshot_path(session_id)` (the 8b-i tier-1 byte snapshot); the original CLI file may
  be gone.
- **Fully synchronous.** Deliberately did NOT reuse the async `DiskStorageBackend.read_index /
  read_exchange` — that backend owns a per-instance `ThreadPoolExecutor` with no `close()` (N run
  dirs → N stranded pools) and self-heals tier-1 mid-read (redaction / index rewrites). Replay
  instead reuses the parse **models** (`IndexEntry` / `InternalRequest` / `InternalResponse`) +
  `DiskStorageLayout` path policy with plain file I/O. Not a second parser; the model owns the parse.
- **Extracted the record→turn loop.** `tailer._ingest_record` was lifted to a module-level
  `ingest_records(records, cursor, source_path, submit)` shared verbatim by live-tail (`_poll_cursor`)
  and replay — one seam, no drift.

## API / module surface

New `index/rebuild.py` (exported from `index/__init__.py`):

```python
def replay_run(writer: IndexWriter, run_dir: RunDir) -> None        # the one reusable core
def backfill(writer: IndexWriter, workspaces_root: Path, run_id: str | None = None) -> None
def reconcile(writer: IndexWriter, conn: sqlite3.Connection, workspaces_root: Path) -> None
def rebuild(workspaces_root: Path, *, db_path: Path | None = None) -> None   # explicit drop+replay-all
```

`tailer.py` (new public seam): `ingest_records(records, cursor, source_path, submit)`.

replay_run flow per run dir (`workspaces_root/{slug}/{hash}/{run_id}/`):
1. `read_run_session_facts(root)` → owned launch facts (8b-ii).
2. WIRE: read `index.jsonl` → `IndexEntry` (de-duped by id, one-object-per-line) → per entry read
   `request.ir.json` / `response.ir.json` → `bind_exchange` → `build_wire_job` → `writer.submit`.
3. TRANSCRIPT: per owned session, reconstruct the `SessionBinding`
   (`session_id = native if minted else synth_session_id(run_id, provider, native)`,
   `decode_source_descriptor` → `FileTailSource`) → read the snapshot bytes →
   `iter_complete_records` → `ingest_records` → `build_transcript_job` → `writer.submit`.

## Database changes

None. No schema change, no `ADAPTERS_VERSION` bump (boot auto-replay is 8c-ii). Tier-1 read-only;
every tier-2 mutation flows through the single writer (orphan eviction is one atomic
delete-all-orphans + one GC job in a single per-job SAVEPOINT).

`reconcile` repairs both directions vs the durable on-disk set (`iter_run_dirs`):
- **missing OR under-counted** durable run → `replay_run` (idempotent). Under-count = de-duped
  tier-1 index count > tier-2 `wire_exchange` rows (§10.4 — a §6.3 backpressure drop).
- tier-2 `run_id` with no dir → `delete_run` + `gc_blocks`.
- the **live set** (`manifest.read_all`) is skipped in both directions.

## Security considerations

No new external surface (offline maintenance + boot-path machinery). `rebuild` is boot/offline-only
by contract (it unlinks `index.db` + WAL sidecars, which on POSIX would strand a live writer's
inode); the caller guarantees no live writer. No untrusted input — tier-1 artifacts are
self-produced; malformed durable rows are skipped + logged, not fatal.

## Performance notes

- Replay submits through the existing batched single-writer (≤64/batch); no new write path.
- `_read_exchange` computes the exchange dir via `new_exchange_dir(id, ts)` (O(1), same call as
  `build_wire_job`'s `raw_dir`) with `find_exchange_dir` fallback.
- Idempotent by construction: PK upserts (`seq` preserved via COALESCE) + identical content rehashes
  to the same `block.hash`, so a second replay adds no rows/blocks (asserted).

## Open items

- **3.2 re-review pending** → dual sign-off → PR (opened by 2.1) → Stuart road-tests the killer demo.
- `cwd` is not durably recoverable from tier-1 (§11.1) → rebuilt `session.cwd = ""`. Not load-bearing
  (correlation/diff/timeline key on session_id + block.hash + seq); `started_at` reconstructed from
  min wire `ts` for deterministic `session_pivot` ORDER.
- 8c-ii (out of scope): wire `replay_run` into the boot `schema_meta` drop path + the
  `index.rebuild.lock` flock + connection-quiescence + `load_runtime` so an `ADAPTERS_VERSION` bump
  auto-rebuilds.
- Transcript-only runs without `sessions.json` remain un-backfillable (§11.3, known limitation).
