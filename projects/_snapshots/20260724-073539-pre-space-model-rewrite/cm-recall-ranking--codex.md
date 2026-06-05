---
title: cm recall ranking and shadow canary design
type: project
tags: [context-matters, recall, ranking, shadow-canary]
summary: Deterministic priority ranking plus observe only canary for cx_recall.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---
# cm recall ranking and shadow canary design
## 1. Proposed ranking model
Choose deterministic lexicographic ranking.
Rationale: cm fields are ordinal policy signals, not calibrated numeric signals. `EntryKind`, `Confidence`, and manual `priority` already express ordering semantics in `crates/cm-core/src/types/entry.rs::EntryKind`, `Confidence`, and `EntryMeta`. A weighted score would invent weights, require normalising an unbounded `priority: i32`, and borrow Vellum signals cm does not have. The canary should measure a clear policy change before any blended score is considered.
Kind tiers, highest first:
```text
feedback    7  direct correction from user or reviewer
preference  6  durable user or project preference
decision    5  architectural or product decision
lesson      4  mistake prevention and learned rule
pattern     3  reusable implementation or workflow pattern
fact        2  verified information
reference   1  pointer to external material
observation 0  general note
```
Confidence tiers:
```text
high   2
medium 1
none   1  default to medium to avoid demoting old entries with no metadata
low    0
```
Priority:
```text
priority = entry.meta.priority.unwrap_or(0)
higher i32 wins
```
Final rank key, descending unless noted:
```rust
fn priority_key(row: &RecallRow) -> PriorityKey {
    PriorityKey {
        kind_rank: kind_rank(row.entry.kind),
        confidence_rank: confidence_rank(row.entry.meta.as_ref()),
        priority: row.entry.meta.as_ref().and_then(|m| m.priority).unwrap_or(0),
        scope_depth: row.entry.scope_path.depth(),
    }
}
fn compare_rows(a: &RecallRow, b: &RecallRow) -> Ordering {
    priority_key(b).cmp(&priority_key(a))
        // Search rows only. SQLite FTS5 rank is lower when better.
        .then_with(|| compare_fts_rank(a.score, b.score))
        .then_with(|| b.entry.updated_at.cmp(&a.entry.updated_at))
        .then_with(|| b.entry.id.as_bytes().cmp(a.entry.id.as_bytes()))
}
```
`scope_depth` stays in the key to preserve ancestor walk intent, but it no longer lets a low value local observation outrank a global feedback correction. `updated_at` remains only a recency tiebreaker, matching the constraint that recency should not become a standalone feature.
## 2. Where it lands
Core, pure policy:
- `crates/cm-core/src/types/entry.rs::EntryKind` gets `recall_rank()`.
- `crates/cm-core/src/types/entry.rs::Confidence` gets `recall_rank()`.
- Optional helper in new `crates/cm-core/src/ranking.rs::priority_components` extracts confidence and priority from `EntryMeta` without I/O.
Capability orchestration:
- New `crates/cm-capabilities/src/recall/ranking.rs::rank_priority_rows` sorts `Vec<RecallRow>` with the model above.
- New `crates/cm-capabilities/src/recall/ranking.rs::rank_legacy_rows` preserves today's behavior for served results and canary comparison.
- `crates/cm-capabilities/src/recall.rs::recall_inner` splits current `post_filter_rows` into `filter_rows`, `rank_legacy_rows`, and `rank_priority_rows`.
- `crates/cm-capabilities/src/recall.rs::apply_token_budget` is applied separately to old and shadow rows so the diff reflects what each model would expose.
Store adapters:
- `crates/cm-store/src/sqlite/query.rs::CmStore::do_resolve_context` remains the no query candidate source.
- `crates/cm-store/src/sqlite/query.rs::CmStore::do_search_ancestor_walk` remains the FTS candidate source.
- `crates/cm-core/src/store.rs::ContextStore` gets a default no op `record_recall_rank_canary(record)` method.
- `CmStore` overrides that method and writes to the canary table.
## 3. FTS versus non FTS interaction
Apply the same priority model to every `cx_recall` route after candidate generation.
- `crates/cm-capabilities/src/recall/routing.rs::route_query` still chooses the candidate set.
- `Search` routing still uses the FTS tier cascade from `route_search` and `try_search_tier`.
- FTS rank becomes a tiebreaker after kind, confidence, priority, and scope depth.
- `cx_search` remains the content ranked BM25 surface for users who want pure text relevance.
This treats `cx_recall` as priority context retrieval with optional query narrowing. It avoids two incompatible meanings for recall. The canary should report diffs by `RecallRouting` so Search specific behavior can be judged separately.
## 4. Back compatibility and migration impact
Ranking needs no schema migration. It reads existing `kind`, `meta.confidence`, `meta.priority`, `scope_path`, and `updated_at` fields from `Entry`.
The canary needs an additive table because `crates/cm-store/migrations/005_mutations.sql` records write mutations only, and `MutationAction` has no retrieval event. Overloading it would mix read telemetry into an audit log.
Proposed table:
```sql
CREATE TABLE recall_rank_canaries (
    id                       TEXT PRIMARY KEY,
    timestamp                TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    model_version            TEXT NOT NULL,
    scope_path               TEXT,
    routing                  TEXT NOT NULL,
    tier                     TEXT,
    query_hash               TEXT,
    query_len                INTEGER NOT NULL,
    limit_requested          INTEGER NOT NULL,
    max_tokens               INTEGER,
    candidates_before_filter INTEGER NOT NULL,
    old_ids                  TEXT NOT NULL,
    new_ids                  TEXT NOT NULL,
    top_k                    INTEGER NOT NULL,
    top_k_overlap            REAL NOT NULL,
    spearman                 REAL,
    mean_abs_position_delta  REAL,
    position_deltas          TEXT NOT NULL,
    duration_ms              INTEGER NOT NULL
);
CREATE INDEX idx_recall_rank_canaries_timestamp ON recall_rank_canaries(timestamp);
CREATE INDEX idx_recall_rank_canaries_scope ON recall_rank_canaries(scope_path);
CREATE INDEX idx_recall_rank_canaries_routing ON recall_rank_canaries(routing);
```
No raw query, title, body, or snippet is logged. `query_hash` is BLAKE3 over the sanitized query string. Rollback is `DROP TABLE recall_rank_canaries` plus indexes.
Canary mode preserves the response schema and served ordering. A future live flip changes ordering only, acceptable for this pre release repo and still flag gated.
## 5. Shadow canary
Trigger point:
1. `recall_inner` resolves scope and obtains `raw_rows` through `route_query`.
2. `filter_rows` applies kind and tag filters without sorting or truncation.
3. Clone filtered rows.
4. Run legacy ranking and token budget for the served result.
5. Run priority ranking and the same token budget for the shadow result.
6. Compute diff.
7. Best effort insert through `ContextStore::record_recall_rank_canary`.
8. Return the legacy result exactly.
Gate:
```text
CM_RECALL_RANKING_SHADOW=1       enables logging, serves legacy
CM_RECALL_RANKING_MODEL=v1        records model version, default v1
```
Unset or invalid flags fail closed. Logging failure emits a warning and never fails recall.
Diff metrics:
```text
k = min(20, max(old_ids.len(), new_ids.len()))
top_k_overlap = |old[0..k] ∩ new[0..k]| / k
spearman = rank correlation over ids present in both lists, null when fewer than 2
position_deltas = [{ id, old_pos, new_pos, delta }] over union(old[0..k], new[0..k])
mean_abs_position_delta = mean(abs(delta)) over common ids
```
Storage uses IDs only. That lets cm web expand entries through existing entry APIs when an operator needs context.
cm web surface:
- Add `crates/cm-web/src/api/recall_canaries.rs::list_recall_canaries`.
- Register it in `crates/cm-web/src/api/mod.rs::router` at `/recall-canaries`.
- Add generated TypeScript type and hook next to the existing API client.
- Add `RecallCanaryPanel` to the dashboard near `crates/cm-web/frontend/src/components/RecentActivity.tsx::RecentActivity`.
- Show recent rows, top 1 changed rate, average top K overlap, mean absolute delta, and filters for routing, scope, and model version.
- Link each ID in old and new order to the existing entry detail route.
## 6. Test plan
Unit tests:
- `EntryKind::recall_rank` covers every `EntryKind` variant.
- `Confidence::recall_rank` covers high, medium, low, and missing metadata.
- `rank_priority_rows` proves kind beats confidence, confidence beats priority, priority beats scope depth, scope depth beats recency, and ID gives deterministic final order.
- FTS rows prove lower raw FTS score only breaks ties after priority keys.
Capability tests:
- Existing scope order tests in `crates/cm-capabilities/tests/recall_scope_order_tests.rs` get updated to assert the new policy deliberately.
- New recall ranking tests seed mixed kind, confidence, priority, and scope entries through `store` and assert `recall` order.
- Search route test seeds same query terms with different metadata and proves `Search` routing uses priority ordering while retaining `RecallRow.score`.
- Token budget test proves old and shadow budget application can produce different logged IDs without changing the served IDs.
Store and migration tests:
- Migration creates `recall_rank_canaries` and indexes.
- `CmStore::record_recall_rank_canary` writes valid JSON arrays and rejects no valid canary shape.
- Logging failure path returns the original recall result.
cm web tests:
- API parity test for `/api/recall-canaries` filtering and limit clamping.
- Frontend hook renders empty, loading, and populated canary states.
Commands:
```sh
just check
just test
just build
```
## 7. Slice plan
1. Pure ranking slice: add rank helpers and priority ranking tests. No served behavior change.
2. Shadow canary slice: add table, store method, flag, diff computation, and logging. Served result remains legacy.
3. cm web slice: add API endpoint, generated client type, dashboard panel, and parity tests.
4. Live flip slice: after canary review, add `CM_RECALL_RANKING_LIVE=1`, serve priority ranking, and keep canary comparing legacy versus live for one release window.
## 8. Risks and least sure point
Risk: Search users may expect BM25 to dominate `cx_recall(query=...)`. Mitigation: `cx_search` remains BM25 first, canary metrics are split by routing, and live serving is separately gated.
Risk: Existing entries without confidence are common. Treating missing confidence as medium keeps the first rollout from becoming a metadata completeness audit.
Risk: Canary logging on every recall can grow. Mitigation: flag off by default, timestamp index, and later retention by count or age if data volume proves high.
Least sure: the Search branch should probably use priority ranking after FTS candidate generation, but the candidate window may need widening to expose high priority rows below the old top N. The first canary should compare ranking over the current candidate set to isolate ranking behavior before changing fetch limits.
## 9. Evidence read
- `~/.mdx/research/vellum-ai-vellum-assistant-cm-deepdive.md`
- `crates/cm-store/src/sqlite/query.rs::CmStore::do_resolve_context`
- `crates/cm-store/src/sqlite/query.rs::CmStore::do_search_ancestor_walk`
- `crates/cm-capabilities/src/recall.rs::recall_inner`
- `crates/cm-capabilities/src/recall.rs::post_filter_rows`
- `crates/cm-capabilities/src/recall/routing.rs::route_query`
- `crates/cm-capabilities/src/recall/routing.rs::try_search_tier`
- `crates/cm-capabilities/src/projection/mod.rs::RecallRow`
- `crates/cm-core/src/types/entry.rs::EntryKind`
- `crates/cm-core/src/types/entry.rs::Confidence`
- `crates/cm-core/src/types/entry.rs::EntryMeta`
- `crates/cm-core/src/store.rs::ContextStore`
- `crates/cm-capabilities/src/validation.rs::MetaInput`
- `crates/cm-capabilities/src/store.rs::store`
- `crates/cm-store/migrations/001_initial_schema.sql`
- `crates/cm-store/migrations/005_mutations.sql`
- `crates/cm-web/src/api/mod.rs::router`
- `crates/cm-web/src/api/mutations.rs::list_mutations`
