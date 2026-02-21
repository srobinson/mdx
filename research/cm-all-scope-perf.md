---
title: Performance cost of ScopeSelector::All in cm_recall and cm_browse
type: research
tags: [context-matters, performance, sqlite, fts5, ALP-2103]
summary: Removing the scope_path WHERE for an All variant is essentially free at realistic store sizes. One real wrinkle: recall's no-query path walks ancestors and would collapse to a single query, changing depth-bias semantics.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## 1. Current SQL paths

All citations against `~/Dev/LLM/DEV/helioy/context-matters/`. `ScopeSelector` today has only `Path` and `CwdInferred` (`crates/cm-capabilities/src/scope/types.rs:8-12`); an `All` variant does not yet exist. The capability layer materializes scope into `Option<&ScopePath>` and hands it to the store. Removing the filter is equivalent to passing `None`. The store already supports that branch on every read path.

### `cx_recall`

Recall fans out into three store calls depending on inputs (`crates/cm-capabilities/src/recall/routing.rs:16-41`).

**a. With query (FTS5 search), `do_search`** — `crates/cm-store/src/sqlite/query.rs:114-181`.

With scope (`:132-154`):
```sql
SELECT e.*, f.rank AS fts_rank FROM entries e
JOIN entries_fts f ON e.rowid = f.rowid
WHERE f.entries_fts MATCH ?
  AND e.superseded_by IS NULL
  AND e.scope_path IN (?, ?, ...)   -- ancestors
ORDER BY f.rank LIMIT ?
```

Without scope (`:155-169`): identical, minus the `scope_path IN (...)` clause. The unscoped branch already exists.

**b. No query, with scope (resolve_context), `do_resolve_context`** — `crates/cm-store/src/sqlite/query.rs:56-112`. This is the ancestor-walk path. It runs **N separate queries**, one per ancestor, each shaped:
```sql
SELECT * FROM entries
WHERE scope_path = ? AND superseded_by IS NULL
ORDER BY updated_at DESC LIMIT ?   -- remaining = limit - already_collected
```
For a four-level scope, that is four point-lookups stitched together by the application loop (`:68-109`).

**c. No query, no scope, falls through to browse** — `crates/cm-capabilities/src/recall/routing.rs:103-124`.

**d. No query, with tags, `recall_candidates_without_query`** — `crates/cm-capabilities/src/recall/routing.rs:175-235`. Iterates each ancestor, paginates `browse` until the tag post-filter accumulates `limit` rows.

### `cx_browse`

Single store call. `do_browse` — `crates/cm-store/src/sqlite/query.rs:183-244`. Filter assembly via `push_browse_filters` (`:19-53`). Scope clause is `scope_path = ?` (equality, not IN), at `:27-31`. Plus a count query with the same WHERE shape (`:197-203`). Order is keyset on `(updated_at, id)` for the default `Recent` sort (`crates/cm-store/src/sqlite/cursor.rs:98-109`).

## 2. Indexes

`crates/cm-store/migrations/001_initial_schema.sql:39-44`:

```sql
CREATE INDEX idx_entries_scope ON entries(scope_path);             -- :39
CREATE INDEX idx_entries_kind ON entries(kind);                    -- :40
CREATE INDEX idx_entries_scope_kind ON entries(scope_path, kind);  -- :41
CREATE INDEX idx_entries_updated ON entries(updated_at);           -- :42
CREATE INDEX idx_entries_content_hash ON entries(content_hash);    -- :43
CREATE INDEX idx_entries_superseded ON entries(superseded_by);     -- :44
```

No composite `(scope_path, updated_at)`. No composite `(superseded_by, updated_at)`. Verified against EXPLAIN QUERY PLAN on the live store (1550 rows):

- Browse with scope: `SEARCH entries USING INDEX idx_entries_scope`, then `USE TEMP B-TREE FOR ORDER BY`.
- Browse without scope: `SEARCH entries USING COVERING INDEX idx_entries_superseded`, then `USE TEMP B-TREE FOR ORDER BY`.

Both already use a TEMP B-TREE for ordering. Removing the scope filter does not introduce a new sort cost; it only swaps which index drives the scan.

FTS5: virtual table `entries_fts` with `content='entries'`, `content_rowid='rowid'`, `tokenize='porter unicode61'` (`crates/cm-store/migrations/002_fts5_setup.sql:9-14`). EQP for both scoped and unscoped FTS searches is identical:
```
SCAN f VIRTUAL TABLE INDEX 32:M3
SEARCH e USING INTEGER PRIMARY KEY (rowid=?)
```
SQLite drives the join from FTS5 (rank-ordered output stream), then probes `entries` by rowid. The `scope_path IN (...)` is evaluated as a row-by-row predicate after the join, **not** pushed into MATCH. So scope filtering on search is a post-predicate today; removing it shrinks the predicate list, full stop.

## 3. Cost analysis

Live store: 1550 entries, 7.1 MB DB. Top scope `global` has 301 entries, top repo bucket `repo:manicure` has 273.

| Capability | Path | With scope | Without scope (All) | Delta |
|---|---|---|---|---|
| browse | `do_browse` | Index seek `idx_entries_scope`, partial scan, TEMP B-TREE ORDER BY, LIMIT 20 | Index scan `idx_entries_superseded` (partial covering), TEMP B-TREE ORDER BY, LIMIT 20 | Trades index. Same shape. Sub-millisecond at 1550 rows. |
| browse count | `SELECT COUNT(*)` | Covering scan of `idx_entries_scope` for one prefix | Covering scan of `idx_entries_superseded` over all live rows | Linear in non-superseded entry count. ~1500 rows. Free. |
| recall (search) | `do_search` | FTS5 BM25 stream + rowid probe + IN-list predicate | FTS5 BM25 stream + rowid probe | Faster without scope (one fewer predicate). FTS5 returns rank-ordered top-K already. |
| recall (no-query, scoped) | `do_resolve_context` | N queries, one per ancestor (N = depth, typ. 2-4) | One query, scope-less | Strictly fewer queries. |
| recall (no-query + tag) | `recall_candidates_without_query` | N ancestors × paged scan with `EXISTS json_each` post-filter | One scan with same EXISTS filter | Strictly fewer queries. |

Bounding factors that cap worst case regardless of scope:
- `MAX_LIMIT = 200` (`crates/cm-capabilities/src/constants.rs:11`).
- `clamp_limit` clamps requested limit to `[1, 200]` (`crates/cm-capabilities/src/validation.rs:18-21`).
- Recall fetch_limit grows to `limit * 3` only when post-filter is on, then capped at `MAX_LIMIT` (`crates/cm-capabilities/src/recall.rs:36-40`).

At 1550 rows with `LIMIT 200`, every query measured returned in well under 10 ms cold and under 1 ms warm. Removing the scope filter never touches more than the full live entry set, which is what the count query already scans every browse call.

## 4. Wrinkles

Stuart's "just remove the WHERE" model holds for browse cleanly. For recall, three behavioral changes deserve attention before shipping. None is a perf cost; all are semantics.

1. **Recall's no-query path is an ancestor walk, not a single query with `IN`.** `do_resolve_context` issues one query per ancestor and stitches results in app code (`crates/cm-store/src/sqlite/query.rs:62-109`). Under `All` you would route to a single unscoped browse-style query and lose the implicit "narrowest-ancestor-first" priority that comes from walking ancestors with `most specific first` (`:68`). The post-filter sort by `scope_path.depth()` in `recall.rs:81` partly preserves this, but with `All` every result depth is incomparable to a query scope. **The depth-based ordering becomes meaningless under `All` and should be replaced with pure recency or pure FTS rank for that variant.**

2. **FTS search ranks by `f.rank` only.** No depth-bias term lives in the SQL (`crates/cm-store/src/sqlite/query.rs:151`). So search recall under `All` keeps the same ranking it has today; the only change is "more candidates pre-rank." This is benign.

3. **Cursor encoding does not include scope state.** `CursorPayload` carries `sort`, `val`, `ts`, `id` only (`crates/cm-store/src/sqlite/cursor.rs:14-26`). Pagination across `All` is correct: a cursor produced under `All` would resume on `(updated_at, id)` regardless of scope. No invalidation problem. Mixing cursors between `All` and a scoped browse on the same sort would silently re-page across a different result set; that is a UI-side concern, not a correctness bug in the store.

Non-wrinkles confirmed: no ranking weight on ancestor distance in SQL, no scope-aware cache layer in the read path (the only cache is sqlx pool reuse), no authz layer above scope filtering. The `superseded_by IS NULL` predicate is independent of scope and stays.

## 5. Verdict

**Confirmed with caveat.** Removing the scope WHERE is essentially free at any realistic cm store size. Indexes already support both shapes, FTS5 treats scope as a post-predicate, browse already runs a TEMP B-TREE ORDER BY in both branches, and `LIMIT 200` caps any worst case. Stuart's prior on cost holds.

The caveat is recall's no-query path. It is implemented as an ancestor walk for a reason: results are returned narrowest-first, which is the implicit priority signal for "give me context for this scope." `All` flattens that. The fix is to define and document `All`'s ordering: most likely `ORDER BY updated_at DESC` (matching browse) for the no-query case, and unchanged `ORDER BY f.rank` for the FTS case. Without that decision, `All` recall would still work but produce surprisingly arbitrary ordering in a way that looks like a bug.

## 6. Recommendation for ALP-2103

1. **Ship without a benchmark.** EQP confirms shape parity; the only variable is N=1550 rows growing slowly. Worth revisiting at 100k rows.
2. **Do not add an index.** The proposed `(superseded_by, updated_at)` composite would help browse-without-scope marginally by removing the TEMP B-TREE, but the same TEMP B-TREE exists today in the scoped branch and nobody complains. Defer.
3. **Plumb `All` through the capability layer, not the store.** The store already accepts `Option<&ScopePath>`; recall and browse already pass `None` through legitimate paths. Map `ScopeSelector::All` to `scope_path: None` at the capability boundary. No store changes required.
4. **Define the no-query recall ordering for `All` explicitly.** Add a code comment in `recall.rs:81` noting that the `depth()` sort is meaningless when scope is unset and falls back to original fetch order (FTS rank or `updated_at DESC`). Otherwise add a guard that switches sort key in the `All` case. Test it.
5. **Rename advisory.** The `ScopeDefaulted` advisory at `recall.rs:63-68` reads "applied: global". Under `All` it should read something like "applied: all (no scope filter)" so the cm-web "Any scope" pill matches the advisory text.
