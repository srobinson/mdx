---
title: cm web recall shadow viewer API
type: design
tags: [backend, api, cm-web, recall-shadow]
summary: Typed contract for the read only recall shadow dashboard endpoint.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# API Contract

## GET /api/recall-shadow

Read only dashboard endpoint for recent `recall_shadow` canary rows.

### Query

```ts
interface RecallShadowQuery {
  routing?: string;
  scope_path?: string;
  top1_changed?: boolean;
  limit?: number; // default 50, clamped to 1..200
}
```

### Response

```ts
interface RecallShadowPositionDelta {
  id: string;
  old_position?: number | null;
  new_position?: number | null;
  delta: number;
}

interface RecallShadowRow {
  id: string;
  ts: string; // ISO 8601 UTC
  scope_path?: string | null;
  query_hash?: string | null;
  query_len?: number | null;
  routing: string;
  tier?: string | null;
  k: number;
  candidate_count: number;
  top1_changed: boolean;
  topk_overlap: number;
  footrule: number;
  mean_abs_position_delta: number;
  position_deltas: RecallShadowPositionDelta[];
  old_ids: string[];
  new_ids: string[];
  window_truncated: boolean;
  ranking_version: string;
  duration_ms: number;
}
```

### Error format

All validation and storage errors use the existing cm-web `ApiError` mapping.

```ts
interface ApiError {
  error: string;
}
```

### Semantics

Rows are returned newest first, ordered by `ts DESC, id DESC`.
Filters compose with AND semantics.
The handler performs only `SELECT` statements against the read pool.
