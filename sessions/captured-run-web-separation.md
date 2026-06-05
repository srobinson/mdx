---
title: Captured Run Web Separation
type: sessions
tags: [backend, captured-run, web-runtime, desktop]
summary: Split capture and web runtime so desktop captured Claude panes run capture only while CLI web stays in process.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

## Summary

Implemented the captured run web separation fix on `fix/captured-run-web-separation`.

Key decisions:

- `CaptureRuntime` owns HTTP capture, token counting, session writing, and transcript tailing.
- `WebRuntime` owns the embedded FastAPI server.
- `transport-matters claude` keeps embedded web in the same addon process so breakpoint, override, and auth state remain in memory with the proxy addon.
- Desktop captured Claude panes request external web runtime, pass no web port, and run as nested capture only for v1.
- Nested panes omit the inspector system prompt because they do not expose breakpoint or override controls yet.

## API Contract

No public REST contract changed.

Internal captured run launch contract changed:

```typescript
type CapturedRunWebRuntime = "embedded" | "external";

interface CapturedRunRequest {
  directory: string;
  proxyPort?: number;
  webPort?: number | null;
  webRuntime: CapturedRunWebRuntime;
}

interface CapturedRunSpawnSpec {
  proxyPort: number;
  webPort?: number | null;
}
```

Desktop captured terminal uses:

```typescript
{
  webPort: null,
  webRuntime: "external"
}
```

The spawned Claude client still receives `ANTHROPIC_BASE_URL` pointing at the live proxy port.

## Database Changes

No schema or migration changes.

Regression coverage verifies capture works with the web server off by persisting an exchange, committing session rows, and observing `pg_notify` through `SessionWriter` and `SessionEventListener`.

## Security Considerations

The CLI control plane remains in process with the mitmdump addon. This preserves existing auth, breakpoint, and override state boundaries instead of creating a cross process control channel.

Desktop nested captured panes are read only capture v1. They do not expose breakpoint or override controls until the future server managed run manager owns cross process control.

## Performance Notes

No new long running sidecar is started for desktop nested captured panes. They allocate only a proxy port in capture only mode, which removes the failing nested web sidecar and avoids extra uvicorn startup work.

Line count limits held:

- `api/src/transport_matters/cli/launch_runtime.py`: 700 lines
- `api/src/transport_matters/cli/runner.py`: 700 lines
- `api/src/transport_matters/captured_run.py`: 649 lines

## Verification

- `cd api && just ci`: 1269 passed
- `git diff --check`: passed
- Existing CLI tests were not edited.
- Existing `/api/terminal` tests were not edited.
- API to CLI import boundary passed.
- CLI embedded web arm, pause, release regression passed.
- Captured run external web regression passed, including no web port and proxy targeted `ANTHROPIC_BASE_URL`.
- User verified the local captured Claude pane smoke: no live `ConnectionRefused` after the fix.

PR: https://github.com/littleorgans/transport-matters/pull/65
Commit: `17e4040`

## Open Items

- Future Plan B run manager should own cross process control for nested desktop panes before breakpoint or override controls are exposed there.
