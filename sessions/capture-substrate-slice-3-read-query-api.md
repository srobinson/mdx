---
title: Capture Substrate Slice 3 — Read / Query API
type: sessions
tags: [backend, capture-substrate, sqlite, tier-2, slice-3, transport-matters, moe, fastapi]
summary: Pure-SQL read surface (search/timeline/pivot/diff/raw) + /api/index FastAPI router over captured wire rows; dual MoE sign-off at 45b2dc9.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Capture Substrate Slice 3 — Read / Query API

Warroom MoE. Author = backend-engineer (`:3.1`); reviewer = Codex (`:3.2`); orchestrator = `:2.1`.
Branch `feat/capture-slice-3-read-query-api`, tip **45b2dc9**, off main (slices 1+2 merged @ #18/#19).
Dual clean sign-off. Pull/query surface only — live-tail push is §9 (slice 7).

## Summary

A small pure-SQL read surface (`index/queries.py`) + a FastAPI router (`/api/index`) over the
captured wire rows (spec §8). Search/timeline/raw work fully now; pivot/diff are wire-only until
slice 4 lands transcripts.

## API Contract

- **`index/queries.py`** (pure reads): `search_blocks(conn, q, *, filters, mode, limit, offset)`
  (two-phase FTS5; `occurrence`/`block` modes; AND-combined filters over a unified occurrence
  view `exchange_block UNION ALL turn_block`), `get_block_bodies`, `list_sessions`,
  `session_timeline(conn, session_id, *, stream, with_bodies, seq_from, seq_to)`, `session_pivot`,
  `session_diff`, `exchange_raw_ref` (raises `KeyError` if unknown).
- **`index/models.py`**: frozen `BlockHit/BlockBody/TimelineBlock/TimelineEntry/Correspondence/
  SessionDiff/RawRef/SearchFilters/SessionFilters`.
- **`/api/index`** (`api/v1/index_routes.py`, registered in `router.py`): `POST /search`
  (`{q, filters, mode, limit, offset, expand_ids}` → `{hits, bodies}`), `POST /blocks`,
  `GET /sessions`, `GET /sessions/{id}/timeline|pivot|diff`, `GET /exchanges/{id}/raw?part=`.

## Load-bearing decisions (for slices 4-8)

- **Read connection (§8.1):** `db.connect(read_only=True)` = `query_only=ON` reader (NOT
  `mode=ro` — avoids read-only-WAL lock pitfalls), `check_same_thread=False` because the
  read-only dependency + the **sync** route handler run on FastAPI threadpool workers (sequential,
  per-request, never shared). Under WAL a reader never blocks the writer.
- **Route handlers are sync `def`** (reviewer BLOCKER): FastAPI offloads sync handlers to its
  threadpool, so the blocking SQLite reads + `Path.exists` stay off the event loop. `async def`
  handlers would run on the loop and block it. The read connection is injected via `Depends`
  (`_read_connection`), which also lets tests override it to a temp db.
- **Block-mode search** wraps the FTS query in a `WITH ... AS MATERIALIZED` CTE so bm25/snippet
  run before `GROUP BY` (SQLite would otherwise flatten the subquery and reject the aux functions
  in the aggregate context).
- **Occurrence view UNIONs both edge tables**; the transcript side is empty until slice 4 → search/
  timeline/pivot/diff return wire-only gracefully (no special-casing).
- **pivot/diff are wire-only today by design** (`session_diff` buckets everything `wire_only`,
  `session_pivot` empty). Slice 4 makes the cross-stream DIFF meaningful.
- **Raw fetch streams tier-1 bytes** (`FileResponse`); tier-2 stores no raw bytes. `exchange_raw_ref`
  resolves `wire_exchange.raw_dir` → `DiskStorageLayout().artifact_paths`. Missing exchange/file → 404.
- **Ruff per-file ignore `TC003` only** on `index_routes.py`: FastAPI evaluates route/dependency
  annotations at runtime (`get_type_hints`), so `sqlite3`/`Iterator`/`Literal` stay runtime imports.

## Review Outcome

One reviewer BLOCKER (valid): the 7 handlers were `async def`, blocking the event loop on sync
SQLite + FS. Fixed @ 45b2dc9 (sync `def` → threadpool; dropped the ASYNC240 ignore). Two further
bugs were found + fixed in my own TDD before pushing: cross-thread sqlite (FastAPI threadpool→loop;
`check_same_thread=False`) and `bm25`-under-`GROUP BY` (MATERIALIZED CTE). `just ci` green, 1056 passed.

## Open Items

- Slice 4 (claude transcript + tailer) populates `transcript_turn`/`turn_block`, making the
  occurrence view's transcript side non-empty and the §8.4 pivot/diff cross-stream meaningful; it
  also triggers the slice-2 `session_id`/`seq` backfill on previously-uncorrelated wire exchanges.
- A tiny read-connection pool (§8.1 mentions "or borrows from a tiny read pool") is a future
  optimization; slice-3 opens one short-lived reader per request.
