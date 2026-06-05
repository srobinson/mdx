---
title: Captured Claude Terminal WebSocket
type: sessions
tags: [backend, transport-matters, websocket, captured-run, terminal]
summary: Added and hardened the captured Claude terminal WebSocket endpoint over the shared captured run seam.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented C2 captured Claude terminal WebSocket support on `feat/captured-run-ws`, PR #62.

Commits:

- `901bdd4` added the initial endpoint.
- `069cfd6` completed the C2 peer review fix round.

Key decisions:

- Added `WS /api/captured-runs/claude/terminal` in `api/src/transport_matters/api/v1/captured_terminal.py`.
- Refactored the existing `/api/terminal` PTY implementation into `api/src/transport_matters/api/v1/terminal_bridge.py`.
- Promoted the terminal bridge shared surface to public names and updated route consumers away from `terminal_bridge._private` access.
- Kept `/api/terminal` behavior and tests unchanged through compatibility aliases in `terminal.py`.
- Used `prepare_captured_run(..., install_signal_handlers=False)` so the pane owns the captured run and lease lifecycle.
- Offloaded captured terminal teardown with `asyncio.to_thread` only for `install_signal_handlers=False`; if signal handlers are enabled later, teardown stays on the main thread.
- Added `default_claude_run_dependencies()` in `captured_run.py` so API and CLI callers share one concrete dependency bundle without API modules importing `transport_matters.cli*`.
- Preserved the current backend web port in captured run metadata while allowing that known current web port through launch port preflight.
- Pushed PR #62 with title `feat: add captured Claude terminal websocket`.

## API Contract

```typescript
// WebSocket
// WS /api/captured-runs/claude/terminal?cols=80&rows=24&cwd=/absolute/path

interface CapturedClaudeTerminalQuery {
  cols?: number; // default 80, min 1, max 500
  rows?: number; // default 24, min 1, max 200
  cwd?: string; // optional absolute path, defaults to settings.cwd or process cwd
}

interface CapturedRunReadyFrame {
  type: "captured-run.ready";
  runId: string;
  cwd: string;
  storageDir: string;
  proxyPort: number;
  webPort: number;
  cli: "claude";
  nativeSessionId?: string;
}

type TerminalInputFrame = ArrayBuffer;
type TerminalOutputFrame = ArrayBuffer;

interface TerminalResizeFrame {
  type: "resize";
  cols: number;
  rows: number;
}

interface CapturedRunErrorFrame {
  type: "captured-run.error";
  code:
    | "origin_not_allowed"
    | "invalid_terminal_control_frame"
    | "session_store_unavailable"
    | "launch_failed"
    | "bind_conflict";
  message: string;
}
```

Implementation notes:

- Origin and loopback Host gates run before `accept()`.
- The ready frame is sent before the PTY client is spawned, so terminal bytes cannot precede readiness metadata.
- Binary input and output use the same frame contract as `/api/terminal`.
- Resize text frames use the shared terminal control parser.
- Error frames are guarded against already disconnected peers before `send_json`.

## Database Changes

None.

The endpoint preflights session store availability through the shared dependency bundle before launching Claude. Captured run persistence remains owned by the existing `prepare_captured_run()` seam, `CapturedRunLease`, and mitmproxy addon runtime.

## Security Considerations

- Reused the hardened terminal origin gate and loopback Host validation from the shared terminal bridge.
- Added a bad Host regression for the captured route to prove DNS rebinding attempts are rejected before accept or spawn.
- Gates run before WebSocket accept, so rejected origins or hosts cannot trigger process spawn.
- The captured route no longer imports `transport_matters.cli*`; `api/src/transport_matters/api/test_import_boundary.py` AST walks every Python file under `transport_matters/api/` and rejects module level or function local CLI imports.
- The captured route does not expose public bind behavior. The reverse proxy remains loopback scoped through the existing launch runtime.
- The route rejects relative `cwd` values before launching.
- Teardown order is child PTY process group first, captured run lease second. This prevents new provider traffic before mitmdump and manifest resources are released.
- Error close reasons are bounded to the WebSocket reason byte limit.

## Performance Notes

- The PTY bridge remains event loop reader based for output and offloads blocking writes with `asyncio.to_thread`, matching the existing terminal behavior.
- Launch preparation runs through `asyncio.to_thread` because it performs filesystem checks, session preflight, proxy startup, and readiness waits.
- Captured terminal teardown no longer blocks the event loop. The blocking child process and lease cleanup runs in a worker thread when `install_signal_handlers=False`.
- If signal handler installation is ever enabled for captured pane launches, teardown must remain on the main thread because signal restoration is main thread coupled.

## Verification

Observed green gates after commit `069cfd6`:

- Targeted regression gate:
  - `PYTHONPATH="$PWD/src" uv run python -m pytest src/transport_matters/api/test_import_boundary.py src/transport_matters/api/v1/test_terminal.py src/transport_matters/api/v1/test_captured_terminal.py src/transport_matters/test_private_import_boundary.py -q`
  - `20 passed in 3.24s`
- Full API CI:
  - `cd api && just ci`
  - `ruff format --check src/`: 313 files already formatted
  - `ruff check src/`: All checks passed
  - `mypy src/`: Success, no issues in 313 source files
  - `migration-smoke`: `6 passed in 0.91s`
  - full pytest: `1262 passed in 23.31s`

Additional checks:

- `git diff --check` produced no output.
- `api/src/transport_matters/api/test_import_boundary.py` reported `violations=[]` for API to CLI imports.
- Diff touched no wire, adapter, addon, IR, override, or request pipeline files.

## Open Items

- Manual C2 proof against the desktop UI remains a follow up outside this headless backend implementation pass: open captured Claude pane, send a prompt, inspect mitmdump logs, verify Postgres session rows, close pane, and confirm process, proxy, manifest, and lock cleanup in a live desktop run.
