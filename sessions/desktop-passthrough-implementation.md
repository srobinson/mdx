---
title: Desktop Passthrough Implementation
type: sessions
tags: [backend, transport-matters, desktop, captured-run, security]
summary: Implemented trusted desktop passthrough forwarding for nested Claude and Codex captured panes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented desktop passthrough forwarding for nested captured panes in PR #70 on branch `feat/desktop-passthrough` at commit `eaaa902`.

Key decisions:

- The desktop command remains the trust boundary. It captures Typer `--` passthrough args once and forwards them through typed launch state.
- Passthrough reaches the API process through a Settings and env channel: `Settings.default_client_passthrough` backed by `TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH`.
- Captured pane spawn stays provider neutral. `_prepare_captured_agent_run()` reads Settings and passes the default passthrough into `CapturedRunRequest.passthrough`, then existing Claude and Codex launch profiles build the client argv.
- No WebSocket or query parameter was added for passthrough.

## API Contract

No public endpoint shape changed.

Existing WebSocket endpoints remain:

```typescript
// Existing provider specific route
// WS /api/captured-runs/claude/terminal?cols=<int>&rows=<int>&cwd=<string | omitted>

// Existing provider parametric route
// WS /api/captured-runs/{cli}/terminal?cols=<int>&rows=<int>&cwd=<string | omitted>
type CapturedRunCli = "claude" | "codex";
```

Security invariant:

```typescript
// Not supported. Do not add this.
interface RejectedCapturedTerminalQuery {
  passthrough?: never;
}
```

Internal settings contract:

```typescript
interface RuntimeSettings {
  defaultClientPassthrough: string[]; // env JSON from TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH
}
```

Internal launch env contract:

```typescript
interface LaunchEnv {
  TRANSPORT_MATTERS_DEFAULT_CLIENT_PASSTHROUGH?: string; // JSON encoded string[]
}
```

## Database Changes

None.

No migrations were added or changed.

## Security Considerations

- Passthrough is sourced only from the operator controlled desktop launch path.
- The API WebSocket route still accepts only the existing `cols`, `rows`, and `cwd` query inputs.
- Tests assert captured terminal routes do not declare a passthrough parameter.
- The env payload is JSON encoded to preserve argv tokens without shell interpolation.

## Performance Notes

- No database query or request path performance impact.
- Runtime overhead is limited to serializing a small list of strings into launch env and parsing it once through Settings.

## Verification

Observed passing:

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/test_config.py src/transport_matters/cli/test_desktop.py src/transport_matters/api/v1/test_captured_terminal_provider_routes.py src/transport_matters/test_captured_run_web_separation.py src/transport_matters/cli/test_start_passthrough.py
# 41 passed in 0.23s
```

```bash
cd api && .venv/bin/python -m pytest src/transport_matters/api/test_import_boundary.py src/transport_matters/cli/test_codex.py src/transport_matters/cli/test_start_passthrough.py src/transport_matters/cli/test_desktop.py src/transport_matters/cli/test_captured_run.py src/transport_matters/test_captured_run_web_separation.py src/transport_matters/api/v1/test_captured_terminal_provider_routes.py
# 49 passed in 0.50s
```

```bash
cd api && just ci
# ruff format check passed
# ruff check passed
# mypy passed
# migration smoke passed, 6 passed
# full pytest passed, 1289 passed in 23.82s
```

Also observed:

```bash
git diff --check
# no output
```

## Open Items

None for this slice.
