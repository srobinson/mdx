---
title: Runtime port WS6 C2 conformance breadth
type: sessions
tags: [backend, runtime, session-driver, conformance, SpawnConflict, WS6]
summary: Added test-only dual-adapter RuntimePort conformance for status, poll_events, doctor, and SpawnConflict parity.
status: active
source: backend-engineer
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Summary

Implemented WS6 Card C2 for ALP-2816 on `feat/runtime-port-conformance`.

Commit: `6a8e00beae581fc8f48062bc96b6859938ffb3ad`

Key decisions:

- Kept the change test-only in `internal/session/driver/tests/port_conformance.rs`.
- Added cross-adapter conformance coverage for the uncovered `RuntimePort` methods: `status(StatusFilter)`, `poll_events(EventsRequest)`, and `doctor()`.
- Compared doctor on stable structural fields because `RtmdDriver` intentionally adds its socket path wrapper field while `InProcessRuntime` has no socket path.
- Added a SpawnConflict parity test proving both adapters surface `DriverError::SpawnConflict { kind, message }`.
- Refactored repeated one-shot RTMD mock read/assert/write logic into `mock_rtmd_once` so the new tests do not duplicate socket harness code.

## API Contract

No API endpoints, commands, or wire schemas changed.

Test coverage now asserts the existing internal `RuntimePort` contract across both adapters:

```rust
trait RuntimePort {
    fn status(&self, filter: StatusFilter) -> RuntimePortFuture<'_, Vec<Lifecycle>>;
    fn poll_events(&self, request: EventsRequest) -> RuntimePortFuture<'_, EventBatch>;
    fn doctor(&self) -> RuntimePortFuture<'_, RuntimeDoctorReport>;
    fn spawn<'a>(&'a self, session_id: &'a str, launch: &'a SpawnLaunch) -> RuntimePortFuture<'a, SpawnedProcess>;
}
```

The `spawn` conformance assertion focuses on the caller-matched conflict error variant:

```rust
enum DriverError {
    SpawnConflict { kind: SpawnConflictKind, message: String },
}
```

## Database Changes

None.

## Security Considerations

No auth, permission, or secret handling changed. The new tests strengthen adapter parity around runtime status, event polling, diagnostics, and conflict errors without changing runtime behavior.

## Performance Notes

No production code changed. Test helper refactoring reduces duplicated mock socket setup in the conformance test file.

## Verification

- `cargo test -p lilo-session-driver --test port_conformance -- --nocapture`: PASS, 8/8.
- `cargo fmt --all && just check && just build && just test`: PASS. `just test` reported `418 tests run: 418 passed, 0 skipped`.
- `fmm generate && fmm validate`: PASS, 364 files indexed and current.
- `git diff --check`: PASS.
- `git status --short --branch`: clean after commit.

## Open Items

- WS6 C3 remains pending: watcher-loop poll error retry and reconcile-loop per-intent error isolation.
