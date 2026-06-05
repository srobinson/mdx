---
title: Recall shadow canary implementation
type: sessions
tags: [backend, context-matters, recall, ranking, shadow-canary]
summary: Implemented observe-only recall ranking shadow canary logging for context-matters.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented slice 2 of the recall ranking rollout on branch `feat/recall-shadow-canary`, latest commit `49f7d8b`, PR #82.

Key decisions:

- Legacy mode keeps the existing served behavior and avoids canary work. Review fix `49f7d8b` moved `Instant::now()` into the shadow and live arm so legacy mode avoids canary timer overhead.
- Shadow mode fetches the oversampled candidate window, computes legacy and priority ordering, serves the legacy window, and logs the diff best effort.
- Live mode serves priority ordering and still logs the legacy versus priority diff.
- Shadow rows store IDs and hashed queries only. No raw query, title, body, or snippet is persisted.
- Diff metrics use effective k = `min(requested_k, max(old_len, new_len))` so underfilled unchanged recalls report `topk_overlap = 1.0`.

## API Contract

No public API endpoint was added in this slice.

Internal store contract added in `cm-core`:

```rust
async fn log_recall_shadow(&self, record: RecallShadowRecord) -> Result<(), CmError>
```

`ContextStore` provides a default no-op implementation. `CmStore` overrides it with SQLite persistence.

## Database Changes

Added migration `crates/cm-store/migrations/006_recall_shadow.sql`.

Table: `recall_shadow`

Important columns:

- `id`, UUID v7 text primary key
- `ts`, default current timestamp
- `scope_path`
- `query_hash`, BLAKE3 hash of sanitized query, null for scope walks
- `query_len`
- `routing`, `tier`, `k`, `candidate_count`
- `top1_changed`, `topk_overlap`, `footrule`, `mean_abs_position_delta`
- `position_deltas`, `old_ids`, `new_ids`, JSON text
- `window_truncated`
- `ranking_version`
- `duration_ms`

Indexes added on `ts`, `top1_changed`, `routing`, and `scope_path`.

## Security Considerations

- The canary table stores only entry IDs, query hashes, query length, metrics, and routing metadata.
- Raw query text is never stored.
- Entry titles, bodies, and snippets are never stored in canary rows.
- Canary writes are best effort. Insert failures are logged with `tracing::warn` and never fail recall.

## Performance Notes

- Legacy mode has no canary logging path and no canary timer setup after the fix round.
- Shadow and live modes reuse the existing in-memory candidate vector and do not issue a second recall query.
- Ranking active modes oversample candidates with the existing factor of 3, capped at `MAX_LIMIT`.
- Token budgets are applied separately to legacy and priority orderings before diff metrics are persisted.

## Verification

Passed on `49f7d8b`:

- `cargo clippy --workspace --all-targets -- -D warnings`
- `just test`, 785 tests passed

Previously passed on the initial slice commit:

- `just build`

Focused coverage added for:

- Shadow mode serves legacy order and writes exactly one row.
- Known divergence records `top1_changed`, `topk_overlap`, `footrule`, and position deltas.
- Underfilled unchanged recall reports `topk_overlap = 1.0` and `top1_changed = false`.
- Oversampled priority promotion marks `window_truncated`.
- Dropped `recall_shadow` table does not fail recall.
- Migration creates `recall_shadow` plus required indexes.

## Open Items

- cm-web surfacing remains slice 3.
- Live promotion should wait for shadow data review.
- A SQL-level ranking pushdown remains deferred unless canary data shows oversampling is insufficient.
