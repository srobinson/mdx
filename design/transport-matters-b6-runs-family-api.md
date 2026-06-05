# Transport Matters B6 Runs Family API Contract

Status: draft for implementation, 2026-06-16.

## Types

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
  createdAt: string; // ISO 8601
}

interface CreateRunRequest {
  cli: CliName;
  cwd?: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
  runtimeTemplate?: string; // name under ~/.agent-runtimes/runtimes/
  continueFromSessionId?: string;
  idempotencyKey?: string;
}

interface CreateRunResponse {
  run: Run;
}

interface ListRunsResponse {
  items: Run[];
  nextCursor: string | null;
}

interface GetRunResponse {
  run: Run;
}

interface TerminateRunResponse {
  run: Run;
}

interface ErrorEnvelope {
  code: string;
  message: string;
  details?: unknown;
}
```

## Routes

- `POST /v1/runs` returns `201 CreateRunResponse`.
- `POST /v1/runs?owner=local` with `continueFromSessionId` validates the parent session
  under that owner, returns `session_not_found` for missing or foreign ids, and requires
  `idempotencyKey`.
- `GET /v1/runs?state&limit&cursor` returns `ListRunsResponse`.
- `GET /v1/runs/{runId}` returns `GetRunResponse`.
- `POST /v1/runs/{runId}/terminate` returns `TerminateRunResponse`.
- `WS /v1/runs/{runId}/terminal?cols&rows` attaches to a run terminal.

`/api/runs` is not an alias. Other `/api/*` families stay on their current prefix.

## Semantics

- `terminate` kills the run. A terminated run remains addressable.
- `interrupt` is ESC, byte `0x1b`, sent on the terminal WebSocket binary channel. It is not a REST endpoint.
- `endReason` is present only when `state` is `TERMINATED`.
- `error` is present only when `state` is `FAILED`.
- Public `Run` responses omit internal ports, storage paths, native session ids, viewer state, scrollback metrics, and dead letter counts.
- Continuation is a TM internal fork, not native CLI resume. The backend carries
  `parentSessionId`, `forkedAtSeq`, `purpose=continuation`, and a thin
  `resume-context` payload through the launch-field carrier. The resume context contains
  only `{ firstUserPrompt, lastAgentMessage, transcriptRef }`, where `transcriptRef` is the
  parent Postgres `sessionId`.
- `idempotencyKey` deduplicates request retries in process. Reusing the same key returns
  the existing run without minting another child. Distinct keys can intentionally fork the
  same parent at the same point.
