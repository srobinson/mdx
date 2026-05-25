---
title: Lilo Port Error Model Implementation
type: sessions
tags: [backend, rust, littleorgans, error-model, runtime-port]
summary: Implemented the shared lilo-port error kernel and migrated the session runtime port to caller-matched faults plus opaque provenance.
status: active
source: backend-engineer
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

## Summary

Implemented Phase B of the littleorgans port error model on branch `feat/lilo-port-error-model`.

- EM1 commit: `6f8298b feat(port): add lilo-port error kernel`
- EM2 commit: `5aa9eda refactor(session): migrate runtime port to lilo-port`
- In-repo lesson update: `ce030d2 docs: enforce bounded-context port error model`

Key decisions:

- Added `internal/port` as the shared authored error kernel.
- Modeled caller-matched failures as `PortError::Fault(F)`.
- Modeled local and wire provenance behind opaque `OpaqueFault` so callers cannot branch on transport origin.
- Migrated the session runtime port to `RuntimeError = PortError<RuntimeFault>`.
- Kept non caller-matched runtime failures and client or wire failures opaque.
- Added parity proof tests that force every `RuntimeFault` variant through both adapters.

## API Contract

Rust contract:

```rust
pub enum PortError<F> {
    Fault(F),
    Opaque(OpaqueFault),
}

pub struct OpaqueFault;
pub struct ParityProof(());

impl<F> PortError<F> {
    pub fn local(err: impl Display) -> Self;
    pub fn wire(err: impl Error + Send + Sync + 'static) -> Self;
}

pub fn prove_eq<E: PartialEq + Debug>(direct: E, via_socket: E) -> ParityProof;

pub enum RuntimeFault {
    InvalidSignal(String),
    InvalidSessionId(String),
    SpawnConflict { kind: SpawnConflictKind, message: String },
    InvalidTarget(String),
}

pub type RuntimeError = PortError<RuntimeFault>;
```

Runtime port behavior:

- In-process and socket adapters return caller-matched `RuntimeFault` for invalid signal, invalid session id, spawn conflict, and invalid target.
- Runtime-only failures remain opaque local failures.
- Wire or client failures remain opaque wire failures.
- Doctor socket errors still degrade into `Ok(RuntimeDoctorReport)` rather than surfacing as port errors.

## Database Changes

No schema or migration changes.

## Security Considerations

- Preserved provenance opacity. Callers can match semantic faults but cannot branch on whether an opaque failure came from local execution or a socket boundary.
- No new secrets, environment variables, socket paths, or authorization bypasses.
- Daemon auth and mutation audit paths were updated only for type names and preserved existing authorization flow.

## Performance Notes

- No new database queries, background tasks, or network calls.
- Error conversion remains synchronous and allocation-light, limited to boxed opaque error sources or local messages.
- Full workspace gates passed:
  - `just check`
  - `just build`
  - `just test`: 603 run, 603 passed, 0 skipped
  - `fmm generate`: 365 files indexed
  - `fmm validate`: 365 files current
  - `git grep` for `DriverError` or `CaptureFailed`: 0 matches

## Open Items

- No PR opened in this session.
- Future bounded-context ports should reuse `lilo-port` instead of creating transport-specific error enums.
- Keep separate parity arms when adding new caller-matched fault variants so the compile tripwire continues to catch hollow conformance arms.
