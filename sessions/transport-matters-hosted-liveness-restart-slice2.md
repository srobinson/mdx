---
title: Transport Matters hosted liveness restart slice 2
type: sessions
tags: [backend, transport-matters, desktop, channels, restart]
summary: Implemented hosted Electron liveness polling so stale detached desktop windows close after backend loss.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented restart slice 2 on branch `feat/desktop-detach` in commit `5aaddb1`.

The desktop health probe is now shared. `desktop/src/backendHealth.ts:isBackendHealthy` is exported and owns one fetch plus AbortController timeout path. `waitForBackendHealth` reuses it for startup readiness without duplicating fetch or abort logic.

`desktop/src/main.ts:registerHostedDesktopLifecycle` now derives the backend health URL from `options.routeUrl`, registers liveness polling for each hosted window, starts only after the first `did-finish-load`, self schedules non overlapping probes every 1000 ms, resets on successful probes, closes the window after 3 consecutive failures, and clears pending timeouts on `closed`.

## API Contract

No HTTP API contract changed.

Internal TypeScript contract additions:

```typescript
interface BackendHealthProbeOptions {
  fetchHealth?: FetchBackendHealth;
  timeoutMs?: number;
}

interface BackendHealthOptions {
  fetchHealth?: FetchBackendHealth;
  intervalMs?: number;
  probeTimeoutMs?: number;
  timeoutMs?: number;
  webPort: number;
}

type HostedBackendHealthProbe = (healthUrl: string) => Promise<boolean>;
```

`HostedDesktopLifecycleOptions` accepts `probeBackendHealth` for deterministic tests. Production uses `isBackendHealthy` with the default 750 ms probe timeout.

## Database Changes

None.

## Security Considerations

No new external input surface was added. The hosted liveness URL is derived from the already supplied hosted route URL. Invalid or portless URLs skip liveness polling and leave initial load failure handling to the existing hosted window policy.

The probe uses AbortController timeout handling so a stalled backend does not leave a hanging fetch or overlapping liveness checks.

## Performance Notes

Polling starts only after a successful hosted load. Probes are non overlapping and spaced by 1000 ms after each probe settles. The failure debounce requires 3 consecutive failures, so transient backend blips do not close the window.

Observed gates:

- `cd desktop && pnpm exec vitest run src/backendHealth.test.ts src/main.test.ts`: 2 files, 20 tests passed.
- `cd desktop && just check`: 8 files, 39 tests passed.
- Root `just check`: passed. Existing www `!important` warnings remained.
- Root `just test`: desktop 39 passed, www 989 passed, API 1666 passed in 48.70 s.
- `cd desktop && just package-smoke`: passed with `status: main-window-created`.
- Live smoke: two `just channel-restart preview` runs. Preview backend changed from PID `14194` to `14960`; no port conflict was found. The first new Electron main process `14290` had no renderer child after the second restart, while the second Electron process `15012` retained a renderer child, consistent with the stale hosted window closing on macOS.

## Open Items

Older preview Electron windows launched before this slice do not have the new liveness behavior. They may remain open until manually closed.
