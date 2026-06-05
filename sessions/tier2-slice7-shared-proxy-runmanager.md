---
title: Tier 2 Slice 7 Shared Proxy RunManager Integration
type: sessions
tags: [backend, tier2, shared-proxy, run-manager]
summary: Integrated API managed canvas runs with the Tier 2 shared proxy manager.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Tier 2 Slice 7 shared proxy integration for API managed canvas runs on branch `feat/tier2-slice7-runmanager-integration`, commit `29d1235`, PR #137.

Key decisions:

- FastAPI lifespan now owns a `SharedProxyManager` on `app.state` and starts it only after the Postgres session store is live, because shared transcript capture requires database configuration.
- `RunManager` routes external web runtime captured runs through shared proxy preparation while retaining the embedded per run proxy path for Context A and native launches.
- Shared proxy subprocess registration now binds each run to shared capture state, transcript cursor registration, per run transcript snapshots, and override snapshots.
- API run scoped override mutations synchronously forward snapshots to the shared proxy manager and roll back local state if forwarding fails.
- Long runtime paths use a short `/tmp` control socket path to avoid Unix domain socket path limits.

## API Contract

No new public endpoints were added.

Affected existing surfaces:

```typescript
// POST /v1/runs
// Existing request and response shapes are preserved.
// When runtime config selects the external web runtime, API managed runs now bind
// to the shared proxy instead of starting a per run mitmdump process.

// PATCH /api/overrides
// DELETE /api/overrides
// POST /api/overrides/toggle
// Existing request and response shapes are preserved.
// For registered run scopes, the API forwards the full override snapshot to the
// shared proxy before returning success.
```

Consistent error behavior remains route owned. Shared proxy listener failures are mapped to existing machine readable run launch errors such as `bind_conflict` and `proxy_start_timeout`.

## Database Changes

No schema changes and no migrations.

The shared proxy core reuses the existing `SessionWriter`, owned native session facts, and transcript tailer cursor paths. It does not introduce new tables or indexes.

## Security Considerations

- External web runtime runs fail closed unless owned session metadata is present.
- Override forwarding is synchronous for registered run scopes, preventing the API from reporting a local override state that the shared proxy did not receive.
- Shared proxy startup waits for a live session store, avoiding a partially initialized capture process without durable session writes.
- Short control socket paths are process specific and remain protected by the existing control server directory mode and socket permissions.

## Performance Notes

- API managed canvas runs now share one supervised proxy subprocess instead of starting one mitmdump process per run.
- Binding registration and override forwarding are control channel calls with bounded request timeouts.
- Transcript snapshot writers are mapped by run id and session id, so snapshot writes remain per run and do not scan unrelated runs.

Verification:

- `cd api && just check`
- `cd api && just test`
- Full result: 1521 tests passed in 43.81 seconds.

## Open Items

- The shared proxy manager remains in process memory. It rehydrates live API side bindings after subprocess restart, but bindings do not survive API restart.
- Future slices can expose shared proxy health in the API health or diagnostics surface.
