# Transport Matters Tier 2 Run Scoped Reads API Contract

Status: implementation contract, 2026-06-16.

## Types

```typescript
type RunId = string;
type ExchangeId = string;

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

interface MetaResponse {
  cwd: string;
  workspace_id: string;
  run_id: RunId;
  harnesses: HarnessDescriptorResponse[];
}

type ListExchangesResponse = IndexEntry[];
type GetExchangeResponse = ExchangeDetailResponse;
type GetTurnContentResponse = TurnContentResponse;
type GetPipelineTokensResponse = PipelineTokensResponse;
```

Existing `IndexEntry`, `ExchangeDetailResponse`, `TurnContentResponse`, and `PipelineTokensResponse` payload shapes remain unchanged.

## Routes

- `GET /v1/runs/{runId}/meta` returns `MetaResponse` for that run.
- `GET /v1/runs/{runId}/exchanges?limit&offset&track_id` returns `ListExchangesResponse` scoped to `runId`.
- `GET /v1/runs/{runId}/exchanges/{exchangeId}` returns `GetExchangeResponse` only when the index entry belongs to `runId`.
- `GET /v1/runs/{runId}/exchanges/{exchangeId}/turn-content` returns `GetTurnContentResponse` only when the index entry belongs to `runId`.
- `GET /v1/runs/{runId}/exchanges/{exchangeId}/pipeline_tokens` returns `GetPipelineTokensResponse` only when the index entry belongs to `runId`.

The legacy `/api/exchanges*` routes are removed. The legacy `/api/meta` route remains for Context A and direct process callers.

## Semantics

- Run scoped reads resolve a `StorageBackend` from run metadata: first an active `RunManager` entry, then the current Context A run settings, then persisted workspace manifests.
- Exchange reads are disk artifact reads. They do not use Postgres.
- Unknown `runId` returns `404` with `run_not_found`.
- An exchange id from another run returns `404` with `exchange_not_found`.
