---
title: Transport Matters CLI desktop command implementation
type: sessions
tags: [backend, transport-matters, cli, desktop, electron]
summary: Implemented the Python-primary desktop command and applied PR#40 reviewer fixes for canvas query routing and option validation.
status: active
source: backend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented `transport-matters desktop` for the session canvas PR-2 slice and applied the PR#40 review fixes.

Key decisions:

- `desktop` is a thin Typer command in `api/src/transport_matters/cli/__init__.py`.
- Launch behavior lives in `api/src/transport_matters/cli/desktop_cmd.py`.
- Claude remains the default agent. `--agent codex` selects Codex.
- Python remains primary in the terminal. The selected agent stays interactive through the existing foreground launch path.
- Electron is launched as a detached viewer after backend readiness and receives the canvas route through `TRANSPORT_MATTERS_DESKTOP_ROUTE_URL`.
- The canvas route is the frontend launch contract and carries `owner`, `workspace_hash`, `cli`, and `run_id` as query parameters.
- Omitted `--proxy-port` and `--web-port` stay as `None` until `prepare_launch`, preserving dynamic allocation and bind-retry semantics.
- Shared desktop dependency injection kwargs are centralized in one `TypedDict`-backed mapping before dispatching to Claude or Codex.

## API Contract

No HTTP endpoint was added.

CLI contract:

```typescript
type DesktopAgentKind = "claude" | "codex";

interface DesktopBackendStarted {
  type: "transport_matters.backend_started";
  agent: DesktopAgentKind;
  cwd: string;
  workspace: {
    slug: string;
    hash: string;
  };
  runId: string;
  proxyPort: number;
  webPort: number;
  baseUrl: string;
  routeUrl: string;
  storageDir: string;
  homeDir: string | null;
}
```

`routeUrl` shape:

```text
http://127.0.0.1:{webPort}/canvas?owner=local&workspace_hash={workspaceHash}&cli={agent}&run_id={runId}
```

Command surface:

- `transport-matters desktop`
- `transport-matters desktop --agent claude|codex`
- Shared launch flags: `--work-dir`, `--proxy-port`, `--web-port`, `--storage-dir`, `--home-dir`, `--debug`, `--print-command`
- Claude-only flags are rejected for `--agent codex` only when explicitly supplied on the command line.
- Codex-only flags are rejected for the default Claude agent only when explicitly supplied on the command line.
- Ambient environment values for the inactive agent are ignored during cross-agent option validation.
- Arguments after `--` pass through to the selected agent.

## Database Changes

None.

## Security Considerations

- Electron is resolved before the live launch unless `--print-command` is used.
- Electron runs detached with stdin, stdout, and stderr attached to `DEVNULL`.
- The detached viewer receives the explicit route URL rather than an unused serialized launch context blob.
- The desktop app opens only loopback hosted routes already allowed by `desktop/src/window.ts`.
- No broad environment enumeration was added.

## Performance Notes

- No extra port preallocation is done in `desktop`; this preserves the existing retry loop and avoids disabling bind-race recovery.
- Startup JSON and Electron spawn happen through an `on_backend_ready` hook after manifest write and proxy plus web readiness, before the foreground agent spawn.
- Runner helper extraction kept `run_client_children_until_outcome` below the project function-size threshold.

Verification observed:

- `cd api && .venv/bin/python -m pytest src/transport_matters/cli/test_desktop.py -q`: 7 passed.
- `cd api && .venv/bin/python -m mypy src/transport_matters/cli/desktop_cmd.py src/transport_matters/cli/__init__.py src/transport_matters/cli/test_desktop.py src/transport_matters/env_keys.py`: success, no issues.
- `cd desktop && pnpm typecheck && pnpm test`: typecheck clean, 7 files passed, 25 tests passed.
- `cd api && TRANSPORT_MATTERS_TEST_DATABASE_URL=postgresql://tm:tm@localhost:55432/postgres just ci`: ruff format/check clean, mypy clean, pytest 1154 passed.
- `git diff --check`: clean.

## Open Items

- Orchestrator owns commit and PR creation.
- Electron packaging for installed distributions may need a later packaging slice. The resolver supports repository local Electron, environment overrides, and packaged app candidates when present.
