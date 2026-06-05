---
title: Terminal Pane Backend Hardening
type: sessions
tags: [backend, transport-matters, api, websocket, security, terminal, pty]
summary: Hardened the terminal PTY WebSocket origin gate, moved the route to /api/terminal, and restored Ctrl C signal delivery.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented PR #60 backend review and follow-up runtime fixes on `feat/transcript-terminal-pane`.

- Changed the terminal WebSocket route from `/api/v1/terminal` to `/api/terminal`.
- Added a loopback Host precondition before terminal Origin validation.
- Restored Ctrl C delivery for foreground terminal jobs when the backend parent process ignores SIGINT.
- Pushed commits `64f05dc` and `a8467a8` and replied on the bus with the fixed SHA values.

## API Contract

```ts
// WebSocket
// WS /api/terminal?cols=80&rows=24

interface TerminalConnectQuery {
  cols?: number; // integer, default 80, min 1, max 500
  rows?: number; // integer, default 24, min 1, max 200
}

interface TerminalOriginPolicy {
  requiredOriginHeader: true;
  requiredHost: "localhost:<web_port>" | "127.0.0.1:<web_port>" | "[::1]:<web_port>";
  allowedWhen: "host-is-loopback-and-origin-is-same-origin" | "host-is-loopback-and-origin-is-configured-cors-origin";
  rejectCode: 1008;
}

type TerminalInputFrame = ArrayBuffer;
type TerminalOutputFrame = ArrayBuffer;

interface TerminalResizeFrame {
  type: "resize";
  cols: number;
  rows: number;
}
```

The WebSocket handshake is rejected with close code `1008` before `accept()` when the request Host is not loopback on `settings.web_port`, when the Origin header is missing or invalid, or when Origin is neither same origin nor configured as an allowed CORS origin.

Binary input frames are forwarded to the PTY master. Control bytes such as `0x03` must reach the PTY line discipline so foreground child jobs receive SIGINT.

## Database Changes

None.

## Security Considerations

The original same origin branch trusted the user controlled Host header. That allowed a DNS rebinding shape where `Host` and `Origin` matched a non loopback attacker host while the TCP connection reached the loopback service.

The fix parses Host with `urlsplit`, rejects malformed values, rejects userinfo, path, query, and fragment, requires the configured web port, then allows only `localhost`, `127.0.0.1`, and `::1`. Only after that loopback Host check does the endpoint compare Origin against same origin or configured CORS origins.

## Performance Notes

No query or database path changed. Host and Origin validation is constant time per WebSocket handshake. PTY child setup adds only process spawn time work: `setsid`, `TIOCSCTTY`, foreground process group setup, and signal disposition resets before `exec`.

## Verification

Origin and route fix:

- Focused regression before fix: `api/.venv/bin/python -m pytest api/src/transport_matters/api/v1/test_terminal.py --tb=short` failed because `/api/terminal` was not mounted.
- Focused regression after fix: `api/.venv/bin/python -m pytest api/src/transport_matters/api/v1/test_terminal.py --tb=short`, 7 passed.
- Full API gate: `cd api && just ci`, ruff format check passed, ruff check passed, mypy passed, migration smoke 6 passed, pytest 1244 passed, exit 0.

Ctrl C fix:

- Reproduction before fix: `api/.venv/bin/python -m pytest api/src/transport_matters/api/v1/test_terminal.py::test_terminal_ctrl_c_interrupts_foreground_child_when_parent_ignores_sigint --tb=short`, 1 failed, output only `^C`.
- Focused regression after fix: same test, 1 passed.
- Terminal API tests after fix: `api/.venv/bin/python -m pytest api/src/transport_matters/api/v1/test_terminal.py --tb=short`, 8 passed.
- Full API gate after fix: `cd api && just ci`, ruff format check passed, ruff check passed, mypy passed, migration smoke 6 passed, pytest 1245 passed, exit 0.

## Open Items

Frontend was already updated to `/api/terminal` and confirmed to send Ctrl C as one binary frame `0x03`. No additional frontend change was required for the Ctrl C fix.
