---
title: Transport Matters channel stop restart slice 1
type: sessions
tags: [backend, transport-matters, channels, desktop, restart]
summary: Implemented channel stop and restart wiring for detached desktop backends.
status: active
source: backend-engineer
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

## Summary

Implemented restart slice 1 on `feat/desktop-detach` in commit `c107315`.

Key changes:

- Added `transport-matters channel stop [channel]` for detached desktop backend cleanup.
- Added `stop_desktop_record()` to terminate live recorded desktop PIDs, unlink stale records, and escalate from SIGTERM to SIGKILL after timeout.
- Wired `just channel-restart` to stop the current detached desktop before ensuring the database and launching again.
- Updated CLI help, README guidance, and channel docs.
- Added CLI and runtime unit coverage for no record, malformed record, dead PID, TERM success, KILL fallback, PID race, permission failure, and unknown channel handling.

## API Contract

CLI contract:

```text
transport-matters channel stop [channel]
```

Successful outputs:

```text
nothing running for <channel>
stopped <channel> desktop pid <pid>
```

Exit behavior:

- Exit 0 when no live desktop is recorded or when a live process is stopped.
- Exit 1 when the process cannot be signaled or the record cannot be cleaned up.
- Exit 2 for unknown channel names, matching existing channel command validation.

Restart contract:

```text
just channel-restart <channel>
```

The recipe now builds web and desktop assets, stops the detached desktop for the channel, ensures the channel database, and relaunches the desktop.

## Database Changes

No database schema changes. No migrations were added.

## Security Considerations

- Stop only uses the channel scoped desktop PID record under the resolved channel storage root.
- Malformed or stale records are removed without attempting arbitrary process signaling.
- Unknown channel names are rejected through the existing channel specification resolver.
- Permission errors while signaling or unlinking surface as command failures instead of being hidden.

## Performance Notes

- Stop polling defaults to a short bounded timeout with a small sleep interval.
- Stale record cleanup is constant time.
- The restart path avoids port conflicts by terminating the prior detached backend before relaunch.

Verification:

- `just check`, passed.
- `cd api && just ci`, passed with `1666 passed`.
- `just test`, passed, including desktop, web, and API suites.
- Live preview restart smoke, passed: first PID `82739`, second PID `83448`, no port conflict `yes`.

## Open Items

- Future restart slices can add richer operator feedback if desktop startup fails after stop.
- The stop command intentionally does not discover unmanaged desktop processes outside the channel PID record.
