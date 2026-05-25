---
title: littleorgans Port Error Model Design Review
type: research
tags: [littleorgans, rust, port-error-model, runtime-port, design-review]
summary: Final re-read confirmed the applied fixes and Codex signed off cleanly on the littleorgans bounded context port error model design.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-29
updated: 2026-05-29
---

## Executive Summary

The proposed shared `PortError<F>` model is directionally correct for littleorgans bounded context ports: semantic faults should be separated from downstream provenance, and `internal/port` is the right unpublished Shared Kernel home. The design needs corrections before clean sign off because the current sketch does not actually hide `OpaqueFault` internals, cannot preserve `#[from] ClientError` with a type alias under Rust orphan rules, and overstates what an exhaustive conformance match proves.

## Project Metadata

- Language: Rust, workspace edition 2024, `rust-version = "1.95"` in `Cargo.toml`.
- Workspace size: fmm reports 364 indexed files and 47,590 LOC.
- Relevant crates: `internal/session/driver`, `internal/session/daemon`, `crates/lilo-rm-client`, `crates/lilo-rm-core`, existing foundational internal crates `internal/wire` and `internal/db`.
- Build system: Cargo workspace orchestrated by the root `justfile` and Moon. This review ran a targeted Cargo test, not the full closeout gate.
- fmm state: `.fmm.db` exists and `fmm validate` reported all 364 files indexed and up to date on `main` at `6971d57`.

## Architecture

The runtime port is the first bounded context port and sits in `internal/session/driver`.

- `RuntimePort` currently returns `Result<T, DriverError>` through the `RuntimePortFuture` alias in `internal/session/driver/src/port.rs:15-53`.
- `DriverError` is defined in `internal/session/driver/src/driver.rs:42-69`. Its current variants mix input validation, semantic caller matched errors, transport client errors, local runtime errors, and mapping residues.
- The in process adapter maps domain failures through `InProcessRuntime::domain_error` to `DriverError::Runtime(String)` in `internal/session/driver/src/in_process.rs:43-45`.
- The socket adapter maps non conflict `ClientError` values through `DriverError::Client` in `internal/session/driver/src/rtmd.rs:162-167`.
- `SpawnConflict` is the one confirmed semantic caller matched error today. Both adapters route it through `conv::spawn_conflict` in `internal/session/driver/src/conv.rs:176-181`, and `runtime_spawn_failure` is the production caller that matches it in `internal/session/daemon/src/handler/spawn.rs:371-378`.
- The conformance suite pins current spawn conflict parity in `internal/session/driver/tests/port_conformance.rs:144-165` and compares payloads in `internal/session/driver/tests/port_conformance.rs:454-471`.

The proposed `internal/port` crate fits the existing internal root pattern. `internal/wire` and `internal/db` are existing unpublished workspace members at the root of `internal/`, while `crates/` holds published or consumer facing crates.

## Key Patterns

1. **Semantic fault plus opaque provenance is the right core split.** The runtime port already demonstrates why: caller matched `SpawnConflict` must be identical across in process and socket adapters, while downstream residues only need displayable failure text and source chaining.
2. **Shared classifiers are the real parity mechanism.** The safe current path is `SpawnOutcome::Conflict` or `ClientError::SpawnConflict` into the same `conv::spawn_conflict` helper, not the enum variant by itself.
3. **Conformance tests are necessary but must be concrete.** A no wildcard match creates a compiler review point, but each arm must drive both adapters with the same trigger. An empty arm would compile while proving nothing.
4. **Rust aliases do not create ownership for conversion traits.** `type RuntimeError = PortError<RuntimeFault>` cannot own `From<ClientError>`, so socket conversion must use explicit helpers or a local newtype.

## Detailed Findings

### 1. `OpaqueFault` is not opaque as sketched

The design sketch exposes `OpaqueFault` as a public enum with public variants in `~/.mdx/projects/littleorgans-bounded-context-port-error-model--design.md:100-113`, then claims callers structurally cannot extract anything beyond `Display` or `source()` in lines 119-121 and acceptance lines 242-243.

That claim does not hold in Rust. Callers can pattern match public enum variants:

```rust
match error {
    PortError::Opaque(OpaqueFault::Wire(_)) => { /* transport branch */ }
    PortError::Opaque(OpaqueFault::Local(_)) => { /* local branch */ }
    _ => {}
}
```

Required design change: make `OpaqueFault` a public struct over a private enum, with constructors such as `OpaqueFault::local`, `OpaqueFault::wire`, `PortError::local`, and `PortError::wire`. Implement `Display` and `Error::source` manually. Callers may match `PortError::Opaque(_)`, but they cannot branch on local versus wire provenance.

### 2. `RuntimeError = PortError<RuntimeFault>` cannot preserve `#[from] ClientError`

The design says the socket `#[from] ClientError` path should become `Opaque::Wire(Box::new(e))` in `~/.mdx/projects/littleorgans-bounded-context-port-error-model--design.md:194-196`. With the proposed alias, the session driver cannot implement this as `From<ClientError> for RuntimeError`.

Reason: `From` is foreign, `PortError` is defined in the new kernel crate, and a type alias is not a nominal local type. A scratch Rust check confirmed the equivalent orphan rule failure for `impl From<std::io::Error> for Alias<Vec<Local>>`, producing E0117. A blanket `impl<E: Error> From<E> for PortError<F>` in the kernel also conflicts once `PortError<F>` implements `Error`, because it overlaps core's `impl<T> From<T> for T`.

Required design change: either:

- keep `RuntimeError = PortError<RuntimeFault>` and use explicit socket mapping, for example `.await.map_err(RuntimeError::wire)?`, with one helper to avoid duplication, or
- introduce a local `RuntimeError` newtype in `internal/session/driver` and implement `From<ClientError>` there.

The alias plus explicit helper is smaller and keeps the migration honest. It does mean updating the existing socket adapter `?` calls in `internal/session/driver/src/rtmd.rs:58-151` where `ClientError` currently flows through `DriverError::Client`.

### 3. Exhaustive `assert_fault_parity` is a review gate, not full enforcement

The design's no wildcard match in `assert_fault_parity` appears in `~/.mdx/projects/littleorgans-bounded-context-port-error-model--design.md:123-146`. It does force a source edit when `RuntimeFault` gains a variant. It does not force the new arm to drive both adapters, and a hollow arm can satisfy the compiler.

Required design change: adjust the wording from compile time proof to compiler enforced review point, then make the test harness concrete:

- each `RuntimeFault` arm must call a named parity case,
- each parity case must trigger the same condition through in process and socket fixtures,
- each case must compare the extracted `Fault`, not only string output,
- review acceptance should include a temporary dummy variant compile failure plus a read of the new arm to confirm it drives both adapters.

A stronger declaration time coupling could use a declarative macro that declares variants and parity cases together, but that may exceed v1 KISS. A proc macro is not needed.

### 4. The mapping table leaves `CaptureFailed` unresolved and over classifies old variants as preconditions

The migration table leaves `CaptureFailed(String)` as `decide` in `~/.mdx/projects/littleorgans-bounded-context-port-error-model--design.md:183-190`. fmm did not find call sites for `DriverError::CaptureFailed`, and targeted search found no production constructor. Since the design defines `Fault` as the published caller matched contract, `CaptureFailed` should be deleted unless a current caller needs to branch on it.

The design also groups `UnknownRuntimeVariant`, `Unsupported`, and `MissingRuntimePid` with preconditions in lines 35-38 and maps them to `RuntimeFault` in lines 186-187. Only `InvalidSessionId`, `InvalidSignal`, and `InvalidTarget` are true input validation preconditions in the current runtime port. `MissingRuntimePid` comes from malformed spawn payload conversion in `internal/session/driver/src/conv.rs:190-194`, and `UnknownRuntimeVariant` is emitted for unexpected downstream lifecycle or kill outcome variants in `internal/session/driver/src/conv.rs:88-105` and `internal/session/driver/src/rtmd.rs:105-113`.

Required design change: explicitly decide which old variants become public `RuntimeFault` contract and why. Non caller matched mapping or invariant residues should move to `Opaque::Local`, or the doc should justify exposing them as stable faults.

### 5. Wire promotion needs a payload rule

The design says future semantic variants should round trip via a typed `ErrorCode` plus payload in `~/.mdx/projects/littleorgans-bounded-context-port-error-model--design.md:141-143`. The current wire shape has `ErrorPayload { code, message }` only in `crates/lilo-rm-core/src/proto.rs:220-223`; spawn conflict preserves structure through the dedicated `RuntimeResponse::SpawnConflict(SpawnConflictPayload)` variant in `crates/lilo-rm-core/src/proto.rs:237-257`.

Required design change: state that a promoted semantic fault with data must be represented in the wire protocol before erasure, either as a dedicated typed response variant or as an explicitly extended error detail. The socket adapter must classify it before falling back to `RuntimeError::wire`.

## Dependencies

Critical dependencies in the reviewed path:

- `thiserror`: current `DriverError` derives `Error`; proposed `PortError<F>` and `RuntimeFault` will need the same.
- `lilo-rm-client`: owns `ClientError` in `crates/lilo-rm-client/src/lib.rs:208-239`.
- `lilo-rm-core`: owns `ErrorCode`, `RuntimeResponse`, and `SpawnConflictPayload` in `crates/lilo-rm-core/src/error.rs:6-20` and `crates/lilo-rm-core/src/proto.rs:237-257`.
- `lilo-session-driver`: owns the runtime port trait, adapters, and conversion helpers.
- `lilo-session-daemon`: contains the production spawn caller that branches on `DriverError::SpawnConflict`.

## Relevance to Helioy

This design is a contract for future littleorgans ports, including schedule, orchestrate, and workflow. Getting the opacity and conformance story right now prevents each future bounded context from inventing its own transport provenance split and caller matched error convention.

## Verification

Commands and checks run from `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`:

- `git rev-parse --abbrev-ref HEAD` returned `main`.
- `git rev-parse --short HEAD` returned `6971d57`.
- `fmm validate` reported all 364 files indexed and up to date.
- `cargo test -p lilo-session-driver --test port_conformance` passed 8 tests.
- fmm structural reads were used for `internal/session/driver/src/{driver.rs,port.rs,conv.rs,in_process.rs,rtmd.rs}`, `internal/session/driver/tests/port_conformance.rs`, `internal/session/daemon/src/handler/spawn.rs`, `crates/lilo-rm-client/src/lib.rs`, and `crates/lilo-rm-core/src/{proto.rs,error.rs}`.


## Peer Consensus Update

The Claude analyst pane independently reviewed the same live tree and converged on the five initial issues, adding three more required document fixes. Final Codex position sent on `errmodel-signoff`: **conditional sign off** if the design is revised with eight changes.

Additional agreed findings:

1. `internal/wire` and `internal/db` are context neutral internal root crates, but they are not dependency leaves. `internal/port` would be the first true `thiserror` only leaf. The placement decision is still right, but the rationale should be corrected.
2. EM2 must enumerate daemon side `DriverError` construction and match sites. Deleting `DriverError` affects `internal/session/daemon/src/events.rs`, `internal/session/daemon/src/handler/spawn/tests.rs`, and `internal/session/daemon/tests/handler/spawn_recovery.rs`, not only the driver crate and production `handler/spawn.rs`.
3. EM1 must explicitly add both root `Cargo.toml` entries: the workspace member `internal/port` and `[workspace.dependencies] lilo-port = { path = "internal/port" }`.
4. A small `ParityProof` token is worth adding to the test support helper. It prevents hollow exhaustive match arms from compiling, while the design remains honest that trigger faithfulness is still reviewed unless generation or macros are introduced.

Final conditional list sent to Nancy and the peer:

1. Make `OpaqueFault` a public struct over a private enum.
2. Drop the `#[from] ClientError` claim and specify alias plus explicit `RuntimeError::wire` mapping.
3. Reword enforcement as a compile time tripwire plus reviewed dual adapter proof, with `ParityProof` preventing hollow arms.
4. Delete dead `CaptureFailed` and classify each old `DriverError` variant accurately.
5. Add the wire payload birth rule for future semantic faults.
6. Fix the §3 leaf versus context neutral rationale.
7. Expand EM2 to daemon side construction and match sites.
8. Make EM1 manifest edits explicit.


## Final Re-read Update

Nancy applied the eight agreed conditions and requested final clean sign off. I re-read the live 370-line design document instead of relying on memory. Most conditions landed faithfully, but I flagged two remaining issues and did not emit the clean sign off yet.

1. **Stale `DriverError` classification remains in §1.1.** Lines 46-49 still classify `UnknownRuntimeVariant`, `Unsupported`, and `MissingRuntimePid` as port-minted preconditions from `conv::parse_*`. The live tree shows only `InvalidSignal`, `InvalidSessionId`, and `InvalidTarget` are true parse or input validation preconditions. `UnknownRuntimeVariant` and `MissingRuntimePid` are mapping or invariant residues, and `Unsupported` is an unsupported operation or mock path.
2. **`OpaqueFault` source chaining is promised but not implemented by the sketch.** Lines 132-149 use `#[error("{0}")] pub struct OpaqueFault(OpaqueKind);`, which preserves Display but does not forward `Error::source()`. I validated the equivalent thiserror wrapper in a temporary crate and `source()` returned `false`. The doc should either implement `Error::source` manually or use a transparent wrapper shape that forwards source while keeping `OpaqueKind` private.

All other agreed conditions appeared faithful on re-read: private `OpaqueKind`, explicit `RuntimeError::wire` mapping, `ParityProof`, dead `CaptureFailed` deletion, wire payload birth rule, corrected internal-root placement rationale, EM2 daemon-side blast radius, and explicit EM1 manifest edits.


## Clean Sign-off Update

Nancy applied the two final fixes and requested a clean sign-off. I re-read the live 382-line design document and spot-checked the claims against the tree and a temporary `thiserror` source-chain check.

Confirmed:

1. §1.1 now treats only `InvalidSignal`, `InvalidSessionId`, and `InvalidTarget` as true input preconditions.
2. `UnknownRuntimeVariant` and `MissingRuntimePid` are now mapping or invariant residue that migrate to `Opaque::Local`.
3. `Unsupported` is now deleted as test-mock only. Repo search found only the three mock construction sites named in EM2.
4. The `OpaqueFault` sketch now uses `#[error(transparent)]` on the wrapper and `#[source]` on the wire box. The temporary check showed `wire.source().is_some()` is true and local has no source.
5. The rest of the eight agreed conditions remain intact.

Clean sign-off sent to Nancy on `errmodel-signoff`:

> I sign off on the error-model design as currently filed

## Open Questions

1. No open review questions remain for the design document.
2. Implementation planning should preserve the signed-off shape: opaque `OpaqueFault`, alias plus explicit wire mapping, `ParityProof`, and deletion of dead/test-only variants.
3. Future review should verify the code implements the source-chain behavior with tests, not just the display behavior.
