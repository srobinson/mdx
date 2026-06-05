---
title: B1b RunManager Core Implementation
type: sessions
tags: [backend, transport-matters, run-manager, pty, plan-b]
summary: Implemented and hardened the package root RunManager core for managed captured agent PTY lifecycle.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented B1b-1 as PR #72 on branch `b1b-run-manager-core`.

Commits:

- `b5f138b`: initial package root `RunManager` concurrency core.
- `49a1a06`: peer consensus fix round for the `close()` and `spawn()` race, RLock removal, and test relocation.

The slice adds `transport_matters.run_manager` as a package root concurrency core only. It does not add HTTP routes, WebSocket routes, route retirement, or request and response wire path changes.

Key decisions:

- `RunManager` owns `CapturedRunLease` plus `TerminalPty` for each managed run.
- Each run starts one continuous loop-reader drain task that remains alive with zero viewers.
- Attachments are detachable viewers, not lifecycle owners.
- Attach uses a synchronous snapshot plus queue registration section to keep replay to live ordering gapless.
- Slow viewers are detached with `retryable-overload`; the PTY drain and run continue.
- Teardown removes the loop reader before closing the PTY master and calls `CapturedRunLease.close()` as the only proxy, manifest, lock, and addon releaser.
- The manager no longer uses `threading.RLock`; await-free event loop sections protect registry, attachment, and drain state transitions.
- `spawn()` rechecks `_closed` after awaited preparation and PTY setup and before registry insertion. If `close()` wins, rollback terminates the PTY and closes the lease exactly once.

## API Contract

No public HTTP or WebSocket API was implemented in this slice.

Internal package root contract added:

```typescript
type RunState = "starting" | "running" | "stopping" | "exited" | "failed";

type CapturedRunCli = "claude" | "codex";

interface SpawnRun {
  cli: CapturedRunCli;
  cwd?: string;
  cols: number;
  rows: number;
  passthrough: string[];
  proxyPort?: number;
  webPort?: number;
  upstream?: string;
  storageDir?: string;
  homeDir?: string;
  clientBin?: string;
  clientDisabled: boolean;
  noSystemPrompt: boolean;
  debug: boolean;
  webRuntime: "embedded" | "external";
  defaultClientPassthrough: string[];
}

interface ManagedRunView {
  runId: string;
  cli: CapturedRunCli;
  cwd: string;
  state: RunState;
  createdAt: string;
  startedAt: string;
  updatedAt: string;
  viewerCount: number;
  viewerlessSince?: string;
  exitCode?: number;
  stopReason?: string;
}
```

Python surfaces added:

- `RunManager.spawn(request: SpawnRun) -> ManagedRun`
- `RunManager.get(run_id: str) -> ManagedRun`
- `RunManager.list(filters: RunFilters | None = None) -> list[ManagedRunView]`
- `RunManager.attach(...) -> AttachedTerminal`
- `RunManager.detach(run_id, attachment_id) -> None`
- `RunManager.stop(run_id, reason=...) -> ManagedRunView`
- `RunManager.close() -> None`

## Database Changes

None.

This slice is in-memory manager state only. It reuses existing captured run preparation and lease ownership. No schema, migration, index, or query changes were made.

## Security Considerations

- `run_manager.py` imports no `transport_matters.api*` modules, preserving the package root seam boundary.
- Captured CLI names are constrained to `claude` and `codex`.
- `cwd` is expanded, required to be absolute, required to exist, and required to be a directory before launch prep.
- Session store preflight still runs before captured run preparation.
- Post prepare rollback closes the lease on every failure path after proxy resources may be live.
- No public endpoint was added, so origin and loopback request gates remain a later route integration slice.

## Performance Notes

- PTY output fan out is await free per chunk.
- Attachment queues are bounded to prevent socket send backpressure from blocking PTY draining.
- Scrollback is byte bounded with a default 2 MiB cap.
- Viewer registration order determines live fan out order.
- Attach snapshot and queue registration occur without an await between them.
- Blocking teardown remains off the event loop through `asyncio.to_thread` for PTY termination, master close, and lease close.

Verification:

- Before fix, the new regression copied onto `b5f138b` failed with `Failed: DID NOT RAISE <class 'transport_matters.run_manager.RunManagerError'>`.
- `cd api && uv run python -m pytest src/transport_matters/test_run_manager.py -q`: 9 passed.
- `cd api && uv run ruff format --check src/ && uv run ruff check src/ && uv run mypy src/`: clean.
- `cd api && just ci`: 1299 passed, migration smoke 6 passed, formatting, lint, and mypy clean.
- `fmm validate || true`: all 623 indexed files up to date.
- `gh pr view 72 --json headRefName,headRefOid,url --jq ...`: PR #72 head is `b1b-run-manager-core 49a1a06`.

## Open Items

- B1b-2 should integrate `POST /api/runs`, `GET`, `WS /api/runs/{runId}/terminal`, and `DELETE /api/runs/{runId}`.
- B1b-2 should retire or reduce the pane-owned `captured_terminal.py` path without changing request and response wire capture.
- Route integration must add the origin and loopback HTTP request gate before spawn and stop.
- Future slices should add input fan in, resize plumbing, app lifespan ownership, and reconnect UI flow.
