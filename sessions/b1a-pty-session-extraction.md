---
title: B1a PTY Session Primitive Extraction
type: sessions
tags: [backend, transport-matters, pty, terminal, captured-terminal]
summary: Extracted PTY process and file descriptor primitives into a package root seam for the run manager path.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented B1a for Transport Matters. The PTY process and file descriptor primitive cohort now lives in `api/src/transport_matters/pty_session.py`. `api/v1/terminal_bridge.py` now keeps the WebSocket bridge, origin checks, resize parsing, and close helpers, while re-exporting moved primitives for compatibility. `terminal.py` and `captured_terminal.py` now import PTY primitives from the package root seam.

Branch: `feat/b1a-pty-session`
Commit: `75d57e7`
PR: `https://github.com/littleorgans/transport-matters/pull/71`

## API Contract

No endpoint contract changes.

Existing WebSocket routes remain unchanged:

```typescript
// WS /api/terminal
// WS /api/captured-runs/claude/terminal
// WS /api/captured-runs/{cli}/terminal
```

Existing terminal control frame contract remains unchanged:

```typescript
interface TerminalResizeFrame {
  type: "resize";
  cols: number;
  rows: number;
}
```

Captured terminal ready and error frames remain unchanged.

## Database Changes

None. This was a behavior preserving module extraction with no schema, migration, or index changes.

## Security Considerations

Origin checks and loopback host validation remain in `terminal_bridge.py` and were not changed. Captured terminal launch behavior remains nested capture only, with no nested web control plane. The new `pty_session.py` seam imports only standard library modules and has a subprocess import regression to guard against future import cycles.

## Performance Notes

No expected runtime performance change. PTY spawn, resize, write, termination, and file descriptor close logic were moved without algorithmic changes. Existing terminal and captured terminal tests cover byte flow, resize flow, Ctrl C job control, disconnect cleanup, and launch failure paths.

Verification observed:

- `cd api && uv run python -m pytest src/transport_matters/api/v1/test_terminal.py src/transport_matters/api/v1/test_captured_terminal.py src/transport_matters/api/v1/test_captured_terminal_provider_routes.py src/transport_matters/api/v1/test_captured_terminal_web_separation.py src/transport_matters/api/test_import_boundary.py src/transport_matters/test_private_import_boundary.py src/transport_matters/test_pty_session.py`: 29 passed.
- `cd api && just ci`: ruff format check passed, ruff check passed, mypy passed, migration smoke passed with 6 passed, full pytest passed with 1290 passed.

## Open Items

B1b can now import PTY primitives from `transport_matters.pty_session` instead of from the API route layer. Future run manager work should keep `api/` as an adapter and avoid duplicating PTY ownership or teardown paths.
