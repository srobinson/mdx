---
title: Transport Matters B6 Runs Family API Migration
type: sessions
tags: [backend, b6, runs, api, transport-matters]
summary: Migrated captured runs from legacy /api/runs to the curated /v1/runs family.
status: active
source: backend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented B6 runs family step 2 in PR #123. The captured run product API now lives at `/v1/runs`, with the legacy `/api/runs` mount removed. API vocabulary now uses terminate instead of overloaded stop language. Frontend callers use `/v1/runs` for create, terminal attach, list, and terminate operations.

Verification completed:

- `just check`
- `just test`
- `just www test-e2e`
- `just build`

## API Contract

Design contract: `/Users/alphab/.mdx/design/transport-matters-b6-runs-family-api.md`.

```typescript
type CliName = "claude" | "codex";
type RunState = "RUNNING" | "TERMINATING" | "TERMINATED" | "EXITED" | "FAILED";
type RunEndReason = "explicit" | "idle-timeout" | "shutdown" | "deploy-restart";

interface Run {
  runId: string;
  workspaceId: string;
  sessionId: string;
  cli: CliName;
  state: RunState;
  endReason?: RunEndReason;
  error?: string;
  createdAt: string;
}

interface CreateRunRequest {
  cli: CliName;
  cwd?: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
}

interface ListRunsResponse {
  items: Run[];
  nextCursor: string | null;
}
```

Implemented routes:

- `POST /v1/runs`
- `GET /v1/runs?state&limit&cursor`
- `GET /v1/runs/{runId}`
- `POST /v1/runs/{runId}/terminate`
- `WS /v1/runs/{runId}/terminal?cols&rows`

`/api/runs` is not an alias. Other `/api/*` route families remain unchanged.

## Database Changes

No schema migration was required. The runs API is process resident and backed by `RunManager`, not by a new database table.

## Security Considerations

- Existing loopback and origin checks remain in place for run creation and termination.
- The public `Run` shape omits internal ports, storage directories, native session ids, viewer state, scrollback metrics, and dead letter counts.
- Terminal interrupt is ESC byte `0x1b` over the existing websocket binary input channel. No new REST interrupt endpoint was added.
- Error responses continue to use machine readable codes.

## Performance Notes

- List pagination uses a small opaque cursor over the in memory run list.
- No database query path was added to run listing, so the run family avoids session store coupling.
- Websocket terminal attach continues to stream through the existing terminal bridge and scrollback ring.

## Open Items

- CI status should be monitored on PR #123.
- Follow up B6 session family work should use the same curated `/v1` contract discipline.
