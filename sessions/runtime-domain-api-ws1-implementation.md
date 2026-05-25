---
title: Runtime Domain API WS1 Implementation
type: sessions
tags: [backend, runtime, api, littleorgans, ALP-2816]
summary: Implemented the WS1 in-process runtime domain API on RuntimeService and locked its public surface with an external compile guard.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented ALP-2816 WS1 across five commits on `feat/runtime-domain-api` through `6815494`.

Key decisions:

- Added in-process runtime domain verbs to `RuntimeService` so co-located callers can bypass socket self-RPC.
- Kept `handle_rpc` as the authorization door and wire adapter, with business logic delegated to domain functions.
- Extracted spawn preflight into a shared domain path used by both direct and wire spawn calls.
- Documented the curated runtime API surface on `RuntimeService` and added an external compile guard under `internal/runtime/daemon/tests/runtime_domain_api.rs`.

## API Contract

Public in-process runtime API on `RuntimeService`:

```rust
pub async fn poll_events(&self, request: EventsRequest) -> EventBatch;
pub async fn spawn(&self, request: SpawnRequest) -> anyhow::Result<SpawnOutcome>;
pub async fn status(&self, filter: StatusFilter) -> Vec<Lifecycle>;
pub async fn kill_runtime(&self, request: KillRequest) -> anyhow::Result<KillOutcome>;
pub async fn kill_by_pid(&self, request: KillByPidRequest) -> anyhow::Result<KillByPidResponse>;
pub async fn nudge_runtime(&self, request: NudgeRequest) -> anyhow::Result<NudgeResponse>;
pub async fn capture(&self, request: CaptureRequest) -> anyhow::Result<CaptureResponse>;
pub async fn doctor(&self) -> anyhow::Result<DoctorResponse>;
pub async fn append_event(&self, event: RuntimeEvent) -> anyhow::Result<RuntimeEvent>;
pub fn drain_shims(&self);
```

`SpawnOutcome` is public and carries only public `lilo_rm_core` payloads:

```rust
pub enum SpawnOutcome {
    Spawned(SpawnedPayload),
    Conflict(SpawnConflictPayload),
}
```

Session vocabulary `reap_exited`, `terminate`, `watch_events`, and `terminate_all` is not on `RuntimeService`; it belongs on the WS2 `RuntimePort` and maps onto the runtime verbs above.

## Database Changes

No schema or migration changes.

The implementation reuses existing runtime store tables and event log behavior. Spawn preflight remains before lifecycle insertion for guarded rejection paths.

## Security Considerations

- RPC authorization remains in `handle_rpc` via the existing identity door.
- Domain calls do not add a separate authorization policy in WS1; WS4 owns no-bypass and domain state-change audit follow-up.
- Direct domain methods use existing typed request validation and runtime preflight paths.
- The wire path remains `deserialize -> authorize_runtime_rpc -> domain -> wrap`.

## Performance Notes

- Direct in-process calls remove socket serialization overhead for future session co-location.
- `poll_events` uses the existing `events_since_or_wait` path with cursor and wait semantics intact.
- No additional database round trips were introduced beyond existing domain behavior.
- Final gate included `just check && just build && just test`, with 383 nextest tests passing.

## Open Items

- WS2 must introduce `RuntimePort`, `InProcessRuntime`, and session vocabulary mapping.
- WS4 must harden no-bypass authorization and audit placement for direct domain mutation paths.
- WS5 and WS6 own spawn recovery and conformance or ordering coverage.
