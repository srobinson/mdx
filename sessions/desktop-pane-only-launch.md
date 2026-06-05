---
title: Desktop Pane Only Launch Implementation
type: sessions
tags: [backend, desktop, launch, transport-matters]
summary: Desktop startup now launches only the backend server and Electron viewer, with fail-fast session-store preflight before serving.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Slice A for pane only desktop launch on branch `feat/desktop-pane-only-launch`, PR #140.

Commits:

- `0c53a1c`: Desktop startup launches a backend server and Electron viewer only. Agent processes start later through captured panes.
- `6c6c4e6`: Desktop backend server launch now runs session store preflight before serving.

Key decisions:

- `transport-matters desktop` no longer calls `run_start`, `run_codex`, or a local TTY captured run path.
- Python desktop launch resolves a backend server plan, starts `transport_matters.main.create_app` on the selected web port, and opens a hosted Electron viewer after readiness.
- A hidden `_desktop-backend` command is the internal server entrypoint used by Electron owned backend children.
- `serve_desktop_backend()` applies the desktop backend environment, then calls `preflight_session_store_or_exit()` before importing Uvicorn or calling `create_app()`.
- Electron backend startup no longer selects `claude` or `codex`; it launches `_desktop-backend` only.
- Existing desktop CLI provider flags and passthrough remain accepted as no-ops for the next slice.

## API Contract

No public HTTP API contract changed.

Internal desktop backend command:

```text
transport-matters _desktop-backend --work-dir <path> --web-port <port> --proxy-port <port> --storage-dir <path> [--debug]
```

Desktop boot event emitted by Python hosted launch:

```typescript
interface DesktopBackendStartedEvent {
  type: "transport_matters.backend_started";
  cwd: string;
  workspace: {
    slug: string;
    hash: string;
  };
  webPort: number;
  baseUrl: string;
  routeUrl: string;
  storageDir: string;
}
```

Removed from this boot event: `agent`, `proxyPort`, `runId`, and `homeDir`.

## Database Changes

None.

## Security Considerations

- Desktop backend environment construction strips stale launch scoped identity fields before creating the backend app: run id, CLI, agent home, owned transcript fields, resume and launch fields, and default client passthrough.
- Backend server binding remains loopback only through the existing FastAPI and Uvicorn path.
- Desktop route parsing continues to allow a boot route without an initial `cli` or `runId`, so the UI does not infer an initial agent run.
- Session store preflight now hard-blocks unconfigured or unreachable database state before the desktop backend app can serve and return generic 503 responses.

## Performance Notes

- Desktop launch now starts one backend server plus Electron, instead of starting an initial provider process in the terminal.
- Electron waits for backend health before loading the hosted app in its owned backend path.
- Python hosted launch waits for the backend port before emitting the startup event and spawning Electron.
- The preflight check runs once on backend launch before server creation, matching existing Claude and Codex launch behavior.

## Verification

Latest fix round:

- `cd api && just check`
- `cd api && just test` -> 1543 passed
- `cd desktop && pnpm test` -> 7 files and 29 tests passed

Initial Slice A verification:

- `cd api && just check`
- `cd api && just test` -> 1542 passed
- `cd desktop && pnpm typecheck && pnpm test` -> 29 passed
- `cd www && pnpm test` -> 894 passed
- `cd api && uv run transport-matters desktop --print-command --web-port 9901 --proxy-port 9900`

## Open Items

- Live desktop launch smoke remains the merge gate, per orchestrator directive.
- Next slice should remove or redesign the accepted desktop provider flags, passthrough surface, and related help text.
