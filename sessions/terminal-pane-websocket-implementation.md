---
title: Terminal Pane WebSocket Implementation
type: sessions
tags: [backend, transport-matters, api, websocket, terminal, pty]
summary: Implemented and hardened the backend PTY WebSocket endpoint for terminal panes, including dev-origin integration and Ctrl-C job control.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented the backend terminal pane endpoint on branch `feat/transcript-terminal-pane` and hardened it through follow-up fixes.

Key commits:

1. `d3bb6539616ec68f50e357a08b7b6587aea7cdac`: initial backend PTY WebSocket.
2. `05a692d`: accepted the frontend dev origin on port 5175.
3. `64f05dc`: hardened the terminal WebSocket origin gate.
4. `a8467a8`: restored Ctrl-C delivery by fixing PTY job control.

The backend now exposes one WebSocket terminal endpoint at `WS /api/terminal`. Each socket owns one PTY, one interactive shell child process, and deterministic teardown.

A typed contract was written to `~/.mdx/design/transport-matters-terminal-pane-api.md` before implementation. The original contract used `/api/v1/terminal`; the lockstep route was later simplified to `/api/terminal`.

## API Contract

```typescript
// WebSocket
// WS /api/terminal?cols=80&rows=24

interface TerminalConnectQuery {
  cols?: number; // integer, default 80, range 1..500
  rows?: number; // integer, default 24, range 1..200
}

type TerminalInputFrame = ArrayBuffer;
type TerminalOutputFrame = ArrayBuffer;

interface TerminalResizeFrame {
  type: "resize";
  cols: number;
  rows: number;
}
```

Binary client frames are written to PTY stdin. PTY output is sent to the client as binary frames. Text frames are reserved for control messages. The implemented control message is `resize`, which applies `TIOCSWINSZ`.

## Database Changes

None.

## Security Considerations

The endpoint validates the WebSocket `Origin` header before accepting the connection. Accepted origins are exact configured CORS origins and trusted loopback same-origin browser origins for the backend host. Missing, malformed, non-loopback, or mismatched origins are rejected with policy code `1008`.

Commit `05a692d` added `http://localhost:5175` to default `Settings.cors_origins` because the frontend dev server runs on port 5175 and the Vite proxy uses `changeOrigin: true`, which rewrites backend `Host` while preserving browser `Origin`.

The terminal endpoint remains a local command execution surface. Origin plus loopback is acceptable only for this pre-release local workflow. Wider support should add a stronger local capability or auth gate before treating this as broadly safe.

Each WebSocket owns a child process group. Disconnect or child exit terminates the child process group and closes the PTY master fd.

## Performance Notes

PTY reads are driven by `loop.add_reader`, so blocking reads do not stall the event loop. Client writes use `asyncio.to_thread` for full write completion. Terminal frame payloads stay raw bytes with no JSON wrapping on the hot path.

## Job Control Fix

The frontend proved Ctrl-C reached the backend as a single binary `0x03` frame. The remaining failure was backend PTY job control.

The fix in `a8467a8` changed child setup from `start_new_session=True` alone to an explicit child preparation function that:

1. Calls `setsid()`.
2. Claims the PTY slave as the controlling terminal with `ioctl(TIOCSCTTY)`.
3. Sets the PTY foreground process group with `tcsetpgrp()`.
4. Resets terminal child signal handlers to defaults before exec.

This lets the kernel line discipline deliver SIGINT to the foreground process group when byte `0x03` is written to the PTY.

## Verification

Observed passing gates:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_terminal.py::test_terminal_ctrl_c_interrupts_foreground_child_when_parent_ignores_sigint -q
# 1 passed

cd api && .venv/bin/python -m pytest src/transport_matters/api/v1/test_terminal.py -q
# 8 passed

cd api && just ci
# 1245 passed
```

Live verification after `a8467a8`:

```bash
# Python websockets client connected to ws://localhost:8788/api/terminal?cols=80&rows=24
# with Origin: http://localhost:5175.
# It launched a foreground Python sleep probe, waited for TM_READY,
# sent byte 0x03, and observed TM_INTERRUPTED.
```

Human verification from the frontend terminal pane: Ctrl-C now works perfectly.

Test coverage in `api/src/transport_matters/api/v1/test_terminal.py` now covers:

1. WebSocket connects and `printf hi` output is received.
2. Resize text frame applies the requested PTY winsize.
3. WebSocket disconnect kills the child process and closes the PTY master fd.
4. Ctrl-C interrupts a foreground child process even when the backend parent ignores SIGINT.
5. Origin mismatch is rejected before an accepted terminal session.
6. Non-loopback hosts are rejected even when origin matches.
7. Configured frontend dev origin `http://localhost:5175` is accepted through the proxied backend host.
8. Same-origin loopback IP is accepted.

## Open Items

Native Windows support remains planned work. The current backend PTY path is POSIX only. WSL should work when the backend runs inside WSL. Native Windows needs a platform adapter using ConPTY, Windows process-tree cleanup, Windows-compatible pipe IO, shell selection, resize handling, control key verification, and CI smoke coverage.
