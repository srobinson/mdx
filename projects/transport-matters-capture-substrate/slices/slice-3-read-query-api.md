# Slice 3 — Read / query API

**Goal:** make the captured rows queryable. A small **pure-SQL read surface**
(`index/queries.py`) + a FastAPI router (`/api/index`) registered in `api/v1/router.py`.
Delivers search, session timeline, the wire↔transcript pivot/diff, and raw fetch. With only
the **wire** stream present (transcript = slice 4), search/timeline/raw work fully now;
pivot/diff correctly return wire-only until slice 4 lands transcript rows.

**Depends on:** slices 1+2 (schema, blocks, `wire_exchange` rows + edges — merged @ #18/#19).
**Unblocks:** the first usable query surface; slice 4's DIFF becomes meaningful once
transcripts land.

## Read first (canonical spec)

- **§8 in full** — §8.1 read connection, §8.2 two-phase search, §8.3 timeline, §8.4
  pivot/diff, §8.5 raw fetch, §8.6 python surface, §8.7 HTTP endpoints.
- Slice-1/2 code for the tables/edges/FTS (`index/{schema,blocks,ingest}.py`).

## Files (≤700 LOC; functions ≤150)

1. `api/src/transport_matters/index/queries.py` (~300) — pure reads, each ≤150 LOC:
   `search_blocks(conn, q, *, filters, mode, limit, offset) -> list[BlockHit]`;
   `get_block_bodies(conn, ids) -> list[BlockBody]`; `list_sessions`;
   `session_timeline(conn, session_id, *, stream, with_bodies, seq_from, seq_to)`;
   `session_pivot`; `session_diff`; `exchange_raw_ref`. Result models (`BlockHit`,
   `BlockBody`, `TimelineEntry`, `Correspondence`, `SessionDiff`, `RawRef`, `SearchFilters`,
   `SessionFilters`) frozen pydantic added to `index/models.py`.
2. `api/src/transport_matters/api/v1/index_routes.py` (~180) — FastAPI router, prefix
   `/api/index`, thin wrappers over `queries.py` (§8.7 table), registered in
   `api/v1/router.py` alongside the existing routers.

## Invariants (must not break)

- **Read connection:** separate, short-lived, opened read-only + `PRAGMA query_only = ON`;
  under WAL it never blocks the writer; **pure reads only** — no writes in `queries.py` (§8.1).
- **Two-phase:** `search_blocks` returns metadata + snippet + bm25 rank (no bodies);
  `get_block_bodies` fetches bodies for chosen ids (the cm search→get discipline, §8.2).
- **Unified occurrence view** over BOTH edge tables (`exchange_block` UNION ALL
  `turn_block`). The transcript side is **empty until slice 4** — the query must return wire
  results gracefully with an empty turn side (don't break on zero transcript rows).
- **pivot/diff with wire-only data:** `session_pivot` returns no cross-stream
  correspondences and `session_diff` buckets everything `wire_only` — that is **correct, not
  a bug**; full cross-stream behavior is verified in slice 4.
- **raw fetch:** `exchange_raw_ref` returns `raw_dir` and resolves the tier-1 artifact paths
  (request/response raw); the HTTP layer streams the file; tier-2 stores **no** raw bytes
  (§8.5). Complements, does not duplicate, the existing `/api/exchanges/{id}` endpoints.
- **#17 privacy;** DAG: `queries.py` imports `index` + `ir`; `index_routes.py` is server
  layer (after `index`), may import `index` + `queries`.
- Builtins typing, pydantic v2 frozen.

## Acceptance (§13.2; real temp SQLite)

- **capture→index→search round-trip:** drive a synthetic exchange through the writer (reuse
  slice-2 ingest), `search_blocks` finds its text, `get_block_bodies` returns the body,
  `exchange_raw_ref` resolves to the tier-1 dir.
- Two-phase: metadata (snippet + rank) then bodies separately; structured filters
  (kind/stream/provider/role/section/session/run/ts/sidechain) AND-combine.
- `session_timeline` reconstructs the wire stream ordered by `seq`, with/without bodies,
  seq-range paginates.
- `session_diff` with wire-only data buckets all `wire_only`; `session_pivot` empty
  (cross-stream deferred to slice 4 — assert the wire-only shape explicitly, don't hide it).
- HTTP endpoints registered and return the §8.7 shapes.
- `just ci` green.

## Grounding (confirm current, post #16/#17)

`api/v1/router.py` — how routers register (confirm the current path + include pattern). The
existing exchanges endpoints (`GET /api/exchanges/{id}` — was `exchanges.py:160-185`, may
have drifted post #16; confirm current). Tier-1 artifact paths for raw fetch (the
`DiskStorageLayout` API slice 2 used: `DiskStorageLayout.new_exchange_dir`). FTS5 `block_fts`
+ the §8.2 occurrence-view SQL from slice 1's schema.

## Build order (TDD)

result models → `search_blocks` + `get_block_bodies` (two-phase, test round-trip + filters) →
`session_timeline` (test ordered reconstruction + pagination) → `session_pivot`/`session_diff`
(test wire-only buckets) → `exchange_raw_ref` (test tier-1 resolution) → `index_routes.py`
router + `api/v1/router.py` registration (test endpoints) → privacy/DAG.
