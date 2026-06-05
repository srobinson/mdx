---
title: Recall shadow viewer implementation
type: sessions
tags: [backend, cm-web, recall-shadow, dashboard, review-fix]
summary: Implemented the read only recall shadow canary viewer with backend aggregate metrics.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented Slice 3 for cm-web on branch `feat/recall-shadow-viewer`, PR #87. Initial commit `c882a03` added a read only recall shadow canary viewer. Follow up commit `465e3ea` moved aggregate metrics to the backend so the dashboard summary covers all matching `recall_shadow` rows, while the visible list remains the recent drill down window.

Key decisions:

- Keep the endpoint read only.
- Return one response object with backend `summary` plus clamped `rows`.
- Share filter construction between list and summary SQL to prevent divergent semantics.
- Generate ts-rs contracts for both `RecallShadowResponse` and `RecallShadowSummary`.

## API Contract

`GET /api/recall-shadow`

Query parameters:

```ts
interface RecallShadowQuery {
  routing?: string;
  scope_path?: string;
  top1_changed?: boolean;
  limit?: number;
}
```

Response:

```ts
interface RecallShadowSummary {
  total: number;
  divergence_rate: number;
  avg_topk_overlap: number;
  avg_footrule: number;
}

interface RecallShadowResponse {
  summary: RecallShadowSummary;
  rows: RecallShadowRow[];
}
```

`limit` defaults to 50 at the API boundary and is clamped to `1..200`. It affects only the recent `rows` drill down. `summary` aggregates across all matching rows for the same filters. Rows are ordered by `ts DESC, id DESC`. Filters compose with AND semantics.

## Database Changes

No migration was added. The implementation reads the existing `recall_shadow` table from migration 006.

The SQLite adapter now exposes:

- `list_recall_shadow(&RecallShadowListFilter)` for the clamped recent row window.
- `recall_shadow_summary(&RecallShadowListFilter)` for full filtered aggregate metrics.

## Security Considerations

The endpoint is read only. SQL uses `sqlx::QueryBuilder` bind parameters for all user supplied filters. The handler reuses the existing cm-web `ApiError` mapping.

## Performance Notes

The row query remains bounded to at most 200 results. Summary aggregation scans the filtered row set and uses existing indexes on `routing`, `scope_path`, `top1_changed`, and `ts` where applicable. The frontend requests 8 rows for the panel drill down and uses backend metrics for totals, divergence rate, average top K overlap, and average footrule.

Verification run before pushing `465e3ea`:

```sh
cargo clippy --workspace --all-targets -- -D warnings
just test
just build
just web-check
```

Additional focused proof:

```sh
cargo test -p cm-web recall_shadow --test parity --test frontend_recall_shadow_contract
```

## Open Items

The frontend tests are source level contracts because cm-web currently relies on TypeScript typechecking rather than a JS test runner. Add a React test runner if future dashboard work needs DOM level interaction assertions.
