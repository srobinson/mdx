---
title: Tier 2 Run Scoped Reads
type: sessions
tags: [backend, api, frontend, transport-matters]
summary: Implemented run scoped exchange and meta read APIs backed by run metadata.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented Tier 2 Slice 2 run scoped read surfaces for exchanges and meta data. Exchange reads resolve a target run through live `RunManager` state, current process settings, or persisted workspace manifests, then read that run's Tier 1 disk storage. Legacy global exchange routes are no longer registered. Frontend exchange queries, cache keys, SSE cache mutation, and session canvas exchange redirects carry `runId`.

Review fixes removed the dead empty exchange router, removed `include_history` from backend and frontend exchange request threading, bounded the manifest storage backend cache with an LRU, and refreshed the disk index cache when the index file changes so live run detail reads see exchanges written by a distinct proxy writer backend.

Branch: `feat/tier2-slice2-run-scoped-reads`
Head: `48b108e`
PR: `#132`

## API Contract

```typescript
// GET /v1/runs/{runId}/meta
interface RunMetaResponse {
  cwd: string;
  workspaceId: string;
  runId: string;
  harnesses: HarnessDescriptor[];
}

// GET /v1/runs/{runId}/exchanges?limit=50&offset=0&track_id=<id>
type ListRunExchangesResponse = IndexEntry[];

// GET /v1/runs/{runId}/exchanges/{exchangeId}
interface RunExchangeDetailResponse {
  entry: IndexEntry | null;
  requestIr: InternalRequest;
  requestCuratedIr: InternalRequest | null;
  requestAudit: OverrideAudit | null;
  responseIr: InternalResponse | null;
  transport: TransportArtifacts | null;
  events: CodexSemanticEvent[] | null;
  turn: CodexTurnSummary | null;
  codexDerivedArtifacts: CodexDerivedArtifactsState | null;
  transportDiagnostics: TransportDiagnostic[];
}

// GET /v1/runs/{runId}/exchanges/{exchangeId}/turn-content
interface RunTurnContentResponse {
  userText: string | null;
  responseText: string | null;
  stopReason: string | null;
}

// GET /v1/runs/{runId}/exchanges/{exchangeId}/pipeline_tokens
interface RunPipelineTokensResponse {
  tokensBefore: number | null;
  tokensAfter: number | null;
  reason?: "counter_unavailable" | "no_auth" | "artifact_missing" | "counter_failed" | "unsupported_provider" | null;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

The removed route family is `/api/exchanges*`. The legacy `/api/meta` route remains for direct process callers and initial UI bootstrapping.

## Database Changes

No database schema changes. This slice reads exchanges from per run Tier 1 disk storage rather than Postgres session tables. Existing session resource routes include `run_id` in exchange redirects so clients resolve the correct run scoped read path.

## Security Considerations

Run scoped APIs reject unknown runs with `run_not_found` and reject exchange IDs that do not belong to the requested run with `exchange_not_found`. Route parameters are URL encoded on generated links and frontend calls. Existing auth and local service assumptions are unchanged.

## Performance Notes

Run storage resolution checks live in memory runs first, then current process settings, then workspace manifests. Disk storage backends for manifest resolved storage roots are cached by resolved storage path with a bounded LRU. `DiskStorageBackend` now tracks index file mtime and size, refreshing the in memory index when another backend writes the same run storage. Frontend React Query keys include `runId` and no longer split on the removed `include_history` flag.

Verification passed:

- `cd api && uv run python -m pytest src/transport_matters/api/v1/test_exchanges_live_run_storage.py src/transport_matters/api/v1/test_run_storage.py src/transport_matters/api/v1/test_exchanges.py src/transport_matters/api/v1/test_exchanges_list.py -q`, 13 tests passed
- `cd api && just check`
- `cd api && just test`, 1463 tests passed
- `just www check`, with two pre existing `pane-dock.css` warnings
- `just www test`, 893 tests passed

## Open Items

Run scoped SSE is intentionally out of scope. The UI still connects to `/api/stream` and filters cache mutations by `runId`.
