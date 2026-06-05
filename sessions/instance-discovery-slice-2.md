---
title: Instance Discovery Slice 2
type: sessions
tags: [backend, transport-matters, desktop-runtime, idempotent-launch, cli, test-fidelity]
summary: Implemented idempotent desktop launch with attach, recover, refuse, and start paths backed by runtime discovery, then amended the unhealthy recovery test to assert SIGTERM.
status: active
source: backend-engineer
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Summary

Implemented slice 2 of instance discovery on branch `feat/instance-discovery` in amended commit `044682a`.

Key decisions:

- `run_desktop_detached` now resolves the target channel, cwd, and storage, then calls `discover_desktop_runtime` before preparing a backend launch.
- A `live` runtime attaches by building the normal backend started event from the recorded web port and opening the hosted Electron viewer without starting `_desktop-backend`.
- `stale` and `unhealthy` runtime states recover through `stop_desktop_record` before the normal start path runs.
- The detached desktop path keeps fixed channel ports and no longer accepts or forwards the dynamic port allocator seam.
- Non Transport Matters listeners still fail through `raise_port_in_use`, preserving the precise pinned port refusal.
- Shared test helper `_write_desktop_record` now owns desktop runtime record fixtures used by runtime and launch tests.
- `stop_desktop_record` resolves `pid_alive` and `kill` production dependencies at call time while still accepting explicit injected callables.

## API Contract

No HTTP API shape changed in this slice. The CLI behavior contract is:

```typescript
type DesktopLaunchState = "attach" | "recover" | "refuse" | "start";

interface IdempotentDesktopLaunchContract {
  command: "transport-matters desktop";
  channel: string;
  discovery: DesktopRuntimeStatus;
  live: "attach existing Electron viewer without spawning backend";
  stale: "remove stale record then start";
  unhealthy: "stop recorded process when possible then start";
  absent: "start normally on fixed channel ports";
  nonTmPortListener: "raise_port_in_use";
}
```

The slice consumes the slice 1 `DesktopRuntimeStatus` contract rather than adding a parallel status type.

## Database Changes

No database migrations or schema changes.

## Security Considerations

- Existing runtime records are trusted only after the shared discovery helper validates PID liveness and loopback health.
- Attach uses computed route events through `build_backend_started_event`; stored URLs are not trusted.
- Recovery refuses with a clear operator action if the stale or unhealthy record cannot be cleaned up.
- Non Transport Matters port conflicts remain a hard refusal. There is no free port fallback for channel desktop launch.

## Performance Notes

- The attach path avoids spawning a second backend and only resolves Electron after a live runtime is confirmed.
- The absent path keeps the existing launch sequence.
- Stale PID cleanup is cheap because discovery unlinks dead records before the start path.
- Touched files stay below the 700 line project limit.

## Verification

- Initial focused gate passed: `src/transport_matters/cli/test_desktop_idempotent.py`, `src/transport_matters/cli/test_desktop.py`, and `src/transport_matters/cli/test_desktop_runtime.py`, `56 passed in 0.26s`.
- Initial full gates passed: `just check`; `just test`, `1736 passed in 51.88s`.
- Test fidelity fix: the unhealthy recovery case now monkeypatches the runtime PID probe and kill seam, drives `pid_alive=True` with failed health, and asserts `SIGTERM` for the recorded PID before start proceeds.
- Focused fix gate passed: `src/transport_matters/cli/test_desktop_idempotent.py` and `src/transport_matters/cli/test_desktop_runtime.py`, `24 passed in 0.09s`.
- Final API gate passed: `just api check && just api test`, `1736 passed in 52.29s`.
- Commit amended: `044682a feat(cli): idempotent desktop launch (attach/recover/refuse)`.
- Bus reply sent to `transport-matters:general:1:2.1`: `done: feat/instance-discovery 044682a slice2 test now exercises unhealthy-kill (SIGTERM asserted) — gate green`.

## Open Items

- Slice 3 can migrate direct Electron startup and dev proxy consumers onto the discovery surface.
- Multi instance launch remains deferred and should extend the shared record contract rather than adding another registry.
