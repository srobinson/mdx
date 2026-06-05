---
title: Transport Matters Tailer Quarantine Visibility API
type: design
tags: [backend, transport-matters, api, quarantine]
summary: Additive read contract for exposing dead letter counts on run and session read surfaces.
status: active
source: backend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Expose operator visibility for transcript tailer quarantine by adding dead letter counts to existing read surfaces. The source of truth is `event_dead_letter`; no tailer, writer, quarantine, or migration logic changes.

## API Contract

```typescript
interface RunViewModel {
  runId: string;
  cli: "claude" | "codex";
  cwd: string;
  storageDir: string;
  proxyPort: number;
  webPort?: number | null;
  nativeSessionId?: string | null;
  deadLetterCount: number;
  state: "starting" | "running" | "stopping" | "exited" | "failed";
  viewerCount: number;
  createdAt: string;
  startedAt: string;
  updatedAt: string;
  viewerlessSince?: string | null;
  exitCode?: number | null;
  stopReason?: string | null;
  scrollbackBytes: number;
  scrollbackLimitBytes: number;
}

interface ListRunsResponse {
  runs: RunViewModel[];
}

interface GetRunResponse {
  run: RunViewModel;
}

interface SessionSummary {
  session_id: string;
  provider: string;
  cli: string | null;
  run_id: string;
  cwd: string;
  workspace_slug: string;
  workspace_hash: string;
  native_session_id: string | null;
  minted: boolean;
  source_descriptor: unknown | null;
  home_dir: string | null;
  owner: string;
  status: "active" | "completed" | "archived";
  title: string | null;
  parent_session_id: string | null;
  forked_at_seq: number | null;
  started_at: string;
  created_at: string | null;
  updated_at: string | null;
  dead_letter_count: number;
}
```

Endpoints:

- `GET /api/runs` returns `deadLetterCount` per run. Counts use one grouped `event_dead_letter GROUP BY run_id` query for all listed runs.
- `GET /api/runs/{runId}` returns `deadLetterCount` for that run.
- `GET /api/sessions` returns `dead_letter_count` per listed session. Counts use one grouped `event_dead_letter GROUP BY session_id` query for the filtered session page.

When the session store is unavailable, run routes remain available and report `deadLetterCount: 0`; session routes keep their existing `503` behavior.
