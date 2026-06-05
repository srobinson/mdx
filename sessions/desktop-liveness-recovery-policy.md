---
title: Desktop Liveness Recovery Policy
type: sessions
tags: [backend, desktop, liveness, cli]
summary: Replaced destructive single probe desktop recovery with debounced health classification and explicit force restart.
status: active
source: backend-engineer
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

## Summary

Implemented branch `fix/liveness-recover-policy` at amended commit `e504ac8`. The desktop launch path now uses debounced HTTP `/health` liveness before reusing or recovering a recorded backend. PID dead records recover silently. PID alive records with all refused health connections recover only after an explicit warning. PID alive records with timeout after debounce refuse without sending a signal. Mixed non-timeout probe failures, including `[failed, refused]`, are ambiguous and refuse without killing the PID. `transport-matters desktop --force-restart` is the explicit user authorized restart path.

## API Contract

Updated the desktop runtime status state contract:

```typescript
type DesktopRuntimeState =
  | "absent"
  | "live"
  | "stale"
  | "unhealthy"
  | "not-serving"
  | "wedged";
```

`GET /v1/desktop-runtime` continues to return `GetDesktopRuntimeResponse` with the existing envelope. New machine states are discovery facts and still return HTTP 200.

## Database Changes

None.

## Security Considerations

The policy prevents silent termination of slow, ambiguous, or live desktop backends that may hold captured agents, paused breakpoints, or in flight work. Only an all-refused debounce may become `not-serving` and enter the warned recovery path. Timeout and mixed ambiguous classifications refuse and point operators to `transport-matters desktop --force-restart` and `transport-matters doctor`. The explicit force path uses the existing `stop_desktop_record` signal lifecycle.

## Performance Notes

Default liveness uses three attempts, two seconds per probe, and a short backoff. A transient timeout followed by a healthy response attaches without restart. Refused health connections remain fast because refusal returns immediately, while mixed failures avoid destructive recovery.

## Open Items

No known code gaps. The external design spec at `/Users/alphab/.mdx/projects/transport-matters-instance-discovery-spec.md` was updated to describe the new liveness and recovery policy. Verification observed: focused ambiguous mixed probe test `2 passed in 0.04s`, `cd api && just check` exited 0, root `just check` exited 0, and root `just test` completed with desktop 9 files and 46 tests passed, www 144 files and 1039 tests passed, and api 1743 passed in 52.44s.
