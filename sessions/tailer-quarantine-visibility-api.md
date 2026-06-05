---
title: Tailer Quarantine Visibility API
type: sessions
tags: [backend, api, sessions, tailer, quarantine]
summary: Surfaced event_dead_letter quarantine counts on run and session read APIs with grouped DAO queries.
status: active
source: backend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented additive operator visibility for quarantined transcript tailer records in Transport Matters.

Key decisions:

- `GET /api/runs` now includes `deadLetterCount` per run.
- `GET /api/runs/{run_id}` was added and returns the same run view model with `deadLetterCount`.
- `GET /api/sessions` now includes `dead_letter_count` per session summary.
- Counts are sourced only from `event_dead_letter` through DAO methods.
- List endpoints use a single grouped query per response, avoiding N plus one lookups.
- Run routes preserve existing availability if the session store is absent by reporting zero counts.

PR: https://github.com/littleorgans/transport-matters/pull/106
Commit: `d988f17`

## API Contract

```typescript
interface RunViewModel {
  runId: string;
  cli: "claude" | "codex";
  cwd: string;
  command: string[];
  proxyPort: number;
  webPort?: number | null;
  nativeSessionId?: string | null;
  deadLetterCount: number;
  state: string;
  viewerCount: number;
  createdAt: string;
  startedAt?: string | null;
  stoppedAt?: string | null;
  exitCode?: number | null;
  error?: unknown;
}

interface ListRunsResponse {
  runs: RunViewModel[];
}

interface GetRunResponse {
  run: RunViewModel;
}

interface SessionSummary {
  session_id: string;
  owner: string;
  workspace_id: string;
  run_id?: string | null;
  native_session_id?: string | null;
  provider?: string | null;
  cli?: string | null;
  started_at: string;
  created_at?: string | null;
  updated_at?: string | null;
  dead_letter_count: number;
}
```

Endpoints:

- `GET /api/runs` returns `ListRunsResponse` with `deadLetterCount` on every run.
- `GET /api/runs/{run_id}` returns `{ run: RunViewModel }`.
- `GET /api/sessions` returns `SessionSummary[]` with `dead_letter_count` on every session.

## Database Changes

No migration was added.

Read methods added to the session store DAO layer:

- `count_dead_letters_by_run(run_ids)` groups `event_dead_letter` rows by `run_id`.
- `count_dead_letters_by_session(session_ids)` groups `event_dead_letter` rows by `session_id`.

Both sync and async DAO variants now expose the methods. SQL lives in `dao_statements.py`, not route handlers.

## Security Considerations

- No raw dead letter payloads are exposed.
- The new fields expose counts only.
- Existing route ownership behavior for sessions remains unchanged.
- Queries are parameterized and route through the existing psycopg DAO layer.
- No auth or CORS behavior changed.

## Performance Notes

- `GET /api/runs` materializes the run list once and performs one grouped count query for those run IDs.
- `GET /api/sessions` performs one grouped count query for returned session IDs.
- Empty ID lists short circuit without touching Postgres.
- Run routes do not use `RunManager` process state for count data.

Verification:

- Focused real Postgres tests: 2 passed.
- `cd api && just check`: passed.
- `cd api && just test`: 1348 passed.

## Open Items

- UI consumption is not included in this backend slice.
- No detail endpoint for listing individual dead letter records was added.
- Run routes intentionally report zero when the session store is disabled to preserve existing runtime behavior.
