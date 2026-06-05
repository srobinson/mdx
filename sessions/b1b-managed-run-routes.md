---
title: B1b Managed Run Routes
type: sessions
tags: [backend, transport-matters, run-manager, api, websocket]
summary: Implemented managed captured run routes and migrated captured terminal to a RunManager delegate.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented B1b managed run route integration in `transport-matters` on branch `b1b-routes`, commit `cf3b698`, PR #73. Follow-up cleanup commit `7e00776` removed an unreachable post-`NoReturn` assertion from run state validation.

Key decisions:

- `RunManager` is app scoped and initialized in FastAPI lifespan.
- New `/api/runs` routes own managed run spawn, list, attach, and stop.
- The old captured terminal route is now only a compatibility delegate. It spawns and attaches through `RunManager`, then stops the run on socket close to preserve old pane behavior until B3 removes it.
- The live request and response wire capture path was not touched.

## API Contract

```typescript
type CapturedRunCli = "claude" | "codex";
type RunState = "starting" | "running" | "stopping" | "exited" | "failed";

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

interface TerminalSize {
  cols: number;
  rows: number;
}

interface RunView {
  runId: string;
  cli: CapturedRunCli;
  cwd: string;
  storageDir: string;
  proxyPort: number;
  webPort?: number;
  nativeSessionId?: string;
  state: RunState;
  viewerCount: number;
  createdAt: string;
  startedAt: string;
  updatedAt: string;
  viewerlessSince?: string;
  exitCode?: number;
  stopReason?: string;
  scrollbackBytes: number;
  scrollbackLimitBytes: number;
}

interface CreateRunRequest {
  cli: string;
  cwd?: string;
  terminal?: Partial<TerminalSize>;
}

interface CreateRunResponse {
  run: RunView;
}

interface ListRunsResponse {
  runs: RunView[];
}

interface RunTerminalReadyFrame {
  type: "run.terminal.ready";
  run: RunView;
  terminal: TerminalSize;
  scrollback: {
    replayedBytes: number;
    truncated: boolean;
  };
}

interface RunTerminalScrollbackEndFrame {
  type: "run.terminal.scrollback-end";
}

interface RunTerminalErrorFrame {
  type: "run.error";
  code:
    | "run_not_found"
    | "run_not_attachable"
    | "origin_not_allowed"
    | "invalid_terminal_control_frame"
    | "attachment_overloaded";
  message: string;
  details?: unknown;
}

interface StopRunResponse {
  runId: string;
  state: "stopping" | "exited";
  stopReason: "explicit-stop";
}
```

Routes:

- `POST /api/runs` returns `201 { run }`.
- `GET /api/runs?cli=&cwd=&state=` returns `{ runs }`.
- `WS /api/runs/{runId}/terminal` sends ready, scrollback bytes, scrollback end, then live bytes. WebSocket close detaches and keeps the run alive.
- `DELETE /api/runs/{runId}` returns `{ runId, state, stopReason }` and stops the run.
- Existing `WS /api/captured-runs/{cli}/terminal` delegates to the manager and stops on close.

## Database Changes

None.

## Security Considerations

- `POST /api/runs` and `DELETE /api/runs/{runId}` require the shared loopback and origin gate before spawn or stop.
- `WS /api/runs/{runId}/terminal` and the captured compatibility route reuse the WebSocket origin gate.
- CLI allowlist is restricted to `claude` and `codex`.
- Explicit cwd must be absolute, existing, and a directory.
- Machine-readable error codes are returned for invalid cwd, unsupported CLI, session store unavailable, bind conflicts, launch failures, and missing runs.

## Performance Notes

- Run attach uses the existing continuous `RunManager` PTY drain and bounded scrollback.
- WebSocket close detaches without stopping the PTY drain for new run routes.
- Slow attachment queues are isolated from the PTY drain and receive an overload error frame.
- Query paths are in-memory only for B1b. No database reads were added.

Verification:

- `cd api && just ci`
- Result after cleanup: ruff format check passed, ruff lint passed, mypy passed, migration smoke passed, and `1305 passed` in the full pytest suite.

## Open Items

- B2 can add multi-viewer fanout beyond one attachment per socket.
- B3 should move the frontend to `/api/runs` and delete the captured terminal compatibility bridge.
- B5 can add server restart recovery for managed runs.
