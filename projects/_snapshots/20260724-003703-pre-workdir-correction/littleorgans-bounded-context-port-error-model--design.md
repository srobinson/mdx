---
title: littleorgans — Bounded-Context Port Error Model (Shared Kernel)
type: design-spec
status: consensus-locked — Claude + Codex dual CLEAN sign-off (2026-05-29)
date: 2026-05-29
author: Claude (superpowers brainstorming), hardened by MoE peer-consensus (Claude + Codex codebase-analyst)
governing: ~/.mdx/projects/littleorgans-runtime-port-boundary--design.md §5 §5.1; NOTES/bounded-context-port-error-model.md
scope: internal/session/driver (runtime port = reference impl) + a new shared kernel crate; v0.8.0
supersedes-concern: design §5.1 DEFERRED item; NOTES/bounded-context-port-error-model.md; cm 019e73c2
---

# Bounded-Context Port Error Model — Shared Kernel

> The runtime port (Option D) is the first bounded-context port. schedule / orchestrate /
> workflow will each add their own. This design fixes the one informal step in the port
> pattern — error parity across the in-process and wire adapters — **before the second
> port copies the informal version**. Stuart, 2026-05-29: "design it right, elegant";
> "Full design."
>
> **Round-1 consensus (2026-05-29).** Both analyst panes (Claude + Codex) independently
> verified the draft against `main` @ 6971d57 and signed off conditional on one merged
> 8-item set, applied below: (1) `OpaqueFault` made opaque-by-construction; (2) the
> `#[from] ClientError` ergonomic dropped (orphan-illegal) for explicit `wire` mapping; (3)
> the parity "proof" softened to a compile-time tripwire + reviewed dual-adapter proof, with
> a `ParityProof` token closing the hollow-arm gap; (4) dead `CaptureFailed` deleted +
> per-variant classification; (5) wire-payload birth rule for future faults; (6) §3 leaf-vs-
> context-neutral framing corrected; (7) EM2 blast radius enumerated; (8) EM1 manifest made
> two explicit edits.

## 1. Problem

A bounded-context port exposes a domain capability behind a trait with two adapters: an
**in-process** adapter (composed daemon, direct domain call) and a **wire** adapter
(socket, serialized RPC). A shared conformance suite proves the two adapters behave
identically. Error handling is the one place that proof is currently held together by
convention rather than construction, and the failure mode compounds with each new port.

### 1.1 Verified current state (runtime port, `main` @ 6971d57)

`RuntimePort` methods return `Result<T, DriverError>`
(`internal/session/driver/src/port.rs:15-53`). `DriverError`
(`internal/session/driver/src/driver.rs:41-69`, 10 variants) splits into distinct *kinds*,
and the distinction is the entire problem (classify **per variant** — the old enum is not
uniformly any one kind):

1. **Port-minted preconditions (true input contract)** — `InvalidSignal` (`conv.rs:173`),
   `InvalidSessionId` (`conv.rs:169`), `InvalidTarget` (`conv.rs:35`). Minted by shared
   `conv::parse_*` / request-mapping helpers **before** either transport runs (both adapters
   call them at the top of each method). Transport-independent by construction; a caller may
   legitimately branch on them (bad-input vs downstream-failure).
2. **Semantic, caller-matched** — exactly one today: `SpawnConflict { kind, message }`.
   In-process reaches it via `Ok(SpawnOutcome::Conflict)` → `conv::spawn_outcome` → `Err`
   (`conv.rs:55-60`); the socket reaches it via `Err(ClientError::SpawnConflict)` →
   `rtmd::spawn_error` (`rtmd.rs:162-167`). **Both route through the same
   `conv::spawn_conflict`** (`conv.rs:176-181`), so the variant is identical across
   transports. The one caller that branches on it is `runtime_spawn_failure`
   (`handler/spawn.rs:371-378`). Conformance pins parity:
   `runtime_ports_spawn_conflict_error_variant_matches` + `assert_spawn_conflict_eq`
   (`tests/port_conformance.rs:144,454-471`).
3. **Mapping / invariant residue + provenance catch-alls (no caller matches)** —
   `UnknownRuntimeVariant` (conversion residue, constructed independently in BOTH adapters:
   `conv.rs:94`, `in_process.rs:126`, `rtmd.rs:110`) and `MissingRuntimePid`
   (lifecycle→exit derivation, `conv.rs:193`), plus the divergent catch-alls `Runtime(String)`
   (in-process `domain_error`) vs `Client(ClientError)` (socket `#[from]`, `driver.rs:44`). The
   **same logical failure** arrives differently by transport. Benign **only because no caller
   matches any of them** (verified: zero external match-site for
   `UnknownRuntimeVariant`/`MissingRuntimePid`).

Two variants are **dead** and the migration **deletes** them (CLAUDE.md DRY), not classifies
them: `CaptureFailed` (`driver.rs:66`; zero constructors/matches repo-wide) and `Unsupported`
(`driver.rs:52`; constructed only by test mocks — `events.rs:424`,
`handler/spawn/tests.rs:396`, `tests/handler/spawn_recovery.rs:236` — which switch to
`RuntimeError::local`). That accounts for all 10 `DriverError` variants.

The wire protocol is richer than the port: `ErrorCode`
(`crates/lilo-rm-core/src/proto.rs` / `error.rs`) is a typed `#[non_exhaustive]` 10-variant
enum (`RuntimeUnavailable`, `SessionNotFound`, `TmuxPaneDead`, `LaunchFailed`, …,
`SpawnConflict`, `ProtocolMismatch`), and `RuntimeResponse::SpawnConflict(payload)` is a
first-class variant distinct from the generic `RuntimeResponse::Error(ErrorPayload)`. The
port **discards** that structure: everything except `SpawnConflict` collapses to
`Client(ClientError)` on the socket and to `Runtime(String)` on the in-process path.

### 1.2 The bug that compounds per service

Category 3 is the trap. The rule that keeps `SpawnConflict` safe — *"a new caller-matched
variant must be decoded on **both** adapters via a shared `conv` fn"* — is **remembered, not
enforced**. With one port it is one thing to remember. schedule / orchestrate / workflow
each mint their own `XxxError`: N independent chances to wire a semantically-meaningful
variant on the **wire adapter only**. On the composed (in-process) transport that same
condition flattens into `Runtime(String)`, so a caller's `match` arm **silently never
fires**. Behavior diverges by transport — exactly what the conformance suite exists to
prevent — and the divergence is invisible until someone runs the composed daemon and hits
that path. Conformance only covers what someone remembered to test.

## 2. Decision — two structural guarantees replace one convention

The reason `SpawnConflict` is safe is **not** its type; it is that both adapters feed the
**same structured payload** through **one shared function**. Generalize precisely that, and
make the two failure-prone steps hard to get wrong **by type**, not by discipline.

### 2.1 Tier the error; make provenance unobservable to callers

A shared, generic-over-one-parameter type, defined **once** in the kernel crate and reused
by every port. `OpaqueFault` is **opaque by construction** — a public struct over a private
enum — so the provenance split is invisible to callers as a type guarantee, not a rule:

```rust
/// The error contract of any bounded-context port. Stays a 2-variant PUBLIC enum so the
/// intended `match { Fault(f) => .., _ => .. }` works; the `_` arm is the ONLY thing a
/// caller can do with `Opaque`.
#[derive(Debug, thiserror::Error)]
pub enum PortError<F> {
    /// Semantic tier: the port's published, caller-matched contract.
    /// Per-port `F`. Must be identical across the in-process and wire adapters.
    #[error(transparent)]
    Fault(F),
    /// Provenance tier: "something else went wrong downstream." Caller-opaque.
    #[error(transparent)]
    Opaque(OpaqueFault),
}

impl<F> PortError<F> {
    /// In-process adapter: a domain error with no caller-matched meaning.
    pub fn local(err: impl std::fmt::Display) -> Self { Self::Opaque(OpaqueFault::local(err)) }
    /// Wire adapter: a transport error, type-erased. This is the EXPLICIT erasure point —
    /// there is no `#[from]` blanket (it would be orphan-illegal at the consumer crate and
    /// would swallow `F` into `Opaque`).
    pub fn wire(err: impl std::error::Error + Send + Sync + 'static) -> Self {
        Self::Opaque(OpaqueFault::wire(err))
    }
}

/// Opaque downstream failure: a PUBLIC struct over a PRIVATE enum. Callers may match
/// `PortError::Opaque(_)` but CANNOT branch on local-vs-wire — that distinction is invisible
/// by construction, which is what makes "no caller branches on provenance" a type guarantee.
/// The wire error is type-erased: (a) no caller may branch on transport detail through a
/// domain port; (b) erasure keeps the kernel a true dependency leaf (it need not depend on
/// any context's wire-client crate). NOTE (verified in a temp crate): the naive
/// `#[error("{0}")]` newtype preserves Display but DROPS `Error::source()`;
/// `#[error(transparent)]` on the struct + `#[source]` on the wire field forwards both, so
/// the wire error stays in the `source()` chain for logs.
#[derive(Debug, thiserror::Error)]
#[error(transparent)] // forwards BOTH Display and source() to the inner kind
pub struct OpaqueFault(OpaqueKind);

#[derive(Debug, thiserror::Error)]
enum OpaqueKind { // PRIVATE — not nameable or matchable outside the kernel
    #[error("{0}")]
    Local(String), // no source
    #[error("{0}")]
    Wire(#[source] Box<dyn std::error::Error + Send + Sync>), // the box IS the source → chain kept
}

impl OpaqueFault {
    fn local(err: impl std::fmt::Display) -> Self { Self(OpaqueKind::Local(err.to_string())) }
    fn wire(err: impl std::error::Error + Send + Sync + 'static) -> Self {
        Self(OpaqueKind::Wire(Box::new(err)))
    }
}
```

Per port: `pub type RuntimeError = PortError<RuntimeFault>;` with
`enum RuntimeFault { SpawnConflict { kind, message }, /* + caller-matched preconditions */ }`.
Adapters never construct `Opaque` internals directly (they are private); they go through
`PortError::local` / `PortError::wire`, so `RuntimeError::wire(client_err)` is the explicit,
visible erasure point.

This is the K8s/DDD shape: the **semantic tier is the bounded-context contract**; the
**opaque tier is plumbing**. A caller can `match err { PortError::Fault(f) => …, _ => … }`,
and the `_` arm is the only thing it can do with `Opaque`, by type.

### 2.2 Make semantic parity a compile-time tripwire; the dual-adapter proof is reviewed

Honest framing first: the WS4 `authz_plan` idiom is by-construction because its match OUTPUT
is consumed in the production path (every request's decision is enforced at runtime). A
conformance `match` over `Fault` has no production consumer — its output is a test
side-effect — so an empty arm `=> {}` compiles and ships divergence. The exhaustive match is
therefore a **compile-time tripwire** (it forces an arm to *exist*), not a proof of parity.
The proof is a reviewed dual-adapter drive-and-`assert_eq`, living in the port's async
conformance body (today: `port_conformance.rs` builds both fixtures; `assert_spawn_conflict_eq`,
`:454-471`, only compares two already-obtained errors).

Close the "hollow arm" gap with a lean witness token (no macro, ~15 LOC, in `internal/port`
test-support):

```rust
/// Proof that one Fault was produced IDENTICALLY by both adapters. Its only constructor is
/// the comparator, so a Fault arm CANNOT be satisfied by `=> {}` — it must call `prove_eq`.
pub struct ParityProof(()); // private field ⇒ unconstructable except via prove_eq

pub fn prove_eq<E: PartialEq + std::fmt::Debug>(direct: E, via_socket: E) -> ParityProof {
    assert_eq!(direct, via_socket, "adapter parity violated");
    ParityProof(())
}

// in each port's conformance suite — exhaustive, and each arm MUST return a ParityProof:
fn assert_fault_parity(fault: &RuntimeFault) -> ParityProof {
    match fault {
        // each arm drives the SAME trigger through both adapters, then prove_eq(direct, socket)
        RuntimeFault::SpawnConflict { .. } => spawn_conflict_parity_case(),
        // adding a variant with `=> {}` fails to compile: the arm owes a ParityProof
    }
}
```

What this enforces, and what it does not (stated, not pretended): the token makes a hollow
arm a **compile error** — adding a `Fault` variant without invoking a real parity comparator
will not build. The **irreducible residual** is trigger-faithfulness: a developer could feed
`prove_eq` two errors from the *same* adapter. Closing that needs generated/driven enumeration
of triggers, out of scope for v1. So hollow arms are type-forbidden; trigger-faithfulness
stays a small, named, reviewed obligation. We enforce what is enforceable and name what is
not, rather than letting the exhaustive match masquerade as a parity proof.

**Birth rule for a semantic variant.** A `Fault` variant is born only as a structured payload
the domain emits AND the wire round-trips through a typed carrier — a dedicated
`RuntimeResponse` variant or an explicitly extended detail, **never** the generic
`ErrorPayload { code, message }` — classified through **one shared `conv` fn** consumed by
both adapters (the `SpawnConflict` / `conv::spawn_conflict` pattern, generalized). A condition
observable on only one transport cannot be a `Fault`; it is `Opaque`.

Net: provenance divergence is **unobservable by type** (§2.1); a missing parity case is a
**compile error** (the tripwire + `ParityProof`); the dual-adapter drive is a reviewed proof.
The one remembered convention (§1.2) is replaced by two type guarantees plus one
explicitly-scoped review obligation.

### 2.3 What we deliberately do NOT do now (KISS)

- **Do not restructure the domain's `anyhow` errors.** The domain API still returns
  `anyhow::Error`; only a variant being *promoted to caller-matched* must become a
  structured payload + typed wire carrier. Everything else legitimately lands in
  `Opaque::Local`.
- **No proc-macro / codegen.** The tripwire + `ParityProof` token is the enforcement; a
  derive macro to auto-generate the suite (and force trigger-faithfulness) is over-engineering
  for v1's variant counts. Revisit only if a port grows many semantic variants.
- **No third tier.** Caller-matched preconditions go in `Fault`; everything else is `Opaque`.
  Two tiers suffice.

## 3. Home and naming (Shared Kernel placement)

Best practice for a cross-context Shared Kernel, confirmed against the live workspace:

- It is its own crate (Rust requires it to cross crate boundaries) and should be a
  **dependency leaf** — depending on nothing context-specific, so every context can depend on
  it and none can cycle. Type-erasing the wire error (§2.1) is what lets it stay a leaf (it
  need not depend on any context's wire-client crate).
- The workspace establishes the home for **context-neutral foundational substrate at the root
  of `internal/`**: `internal/wire` and `internal/db` sit there, not under any bounded
  context. Note (verified on `main`): they are context-neutral but **not** dependency leaves —
  `lilo-wire` depends on `lilo-rm-core` + `lilo-session-core`; `lilo-db` on
  `lilo-paths` / `sqlx` / `tokio` / `anyhow`. They justify the *placement* (internal-root,
  unpublished), not a leaf precedent. `internal/port` (thiserror-only) would be the workspace's
  **first true dependency leaf**.
- `crates/` is reserved for *published* consumer surfaces (`lilo-common`, `lilo-paths`); a
  port-error kernel is not one.

**Decision:** a new unpublished crate **`internal/port`** (`lilo-port`) at the `internal/`
root, on the `internal/wire` / `internal/db` context-neutral-substrate precedent. Contents,
minimal: `PortError<F>` (+ `local`/`wire` ctors), opaque `OpaqueFault`, and the `ParityProof`
token + `prove_eq` comparator (test-support). Dependency: `thiserror` only. The port *trait*
stays per-context (it speaks the consumer's vocabulary); only the error contract +
conformance harness are shared. **Crate name LOCKED: `lilo-port`** (Stuart, 2026-05-30). It
matches the hexagonal `RuntimePort` vocabulary and the single-word `internal/<name>`
precedent. The "porting / monorepo-migration" misread was explicitly considered and rejected:
"port" here is ports-and-adapters, and the types `PortError` / `RuntimePort` carry that meaning
unambiguously (crate name ≠ type name, as with `thiserror`→`Error`).

## 4. Runtime-port migration (reference implementation)

The runtime port migrates onto the kernel as the worked example future ports copy. Delete
the old shape; no parallel paths (CLAUDE.md DRY).

| today (`DriverError`)                          | becomes                                      |
|------------------------------------------------|----------------------------------------------|
| `SpawnConflict { kind, message }`              | `RuntimeFault::SpawnConflict { … }`          |
| `InvalidSignal/InvalidSessionId/InvalidTarget` (conv::parse_*) | `RuntimeFault::*` (caller-matched preconditions) |
| `UnknownRuntimeVariant` (conversion residue), `MissingRuntimePid` (invariant residue) | `PortError::local(..)` → `Opaque::Local` (no caller matches) |
| `Runtime(String)` (in-process residue)         | `PortError::local(..)` → `Opaque::Local`     |
| `Client(ClientError)` (wire)                   | `PortError::wire(..)` → `Opaque::Wire` (explicit, no `#[from]`) |
| `CaptureFailed` (dead: 0 ctors/matches)        | **DELETED** (DRY)                            |
| `Unsupported` (test-mock only, no prod ctor)   | **DELETED**; mocks switch to `RuntimeError::local(..)` |

- `RuntimeError = PortError<RuntimeFault>` replaces `DriverError` as the port's `Result`
  error. The trait's `RuntimePortFuture<'a, T>` aliases `Result<T, RuntimeError>`.
- `conv::spawn_conflict` keeps its role (the one shared classifier); both adapters keep
  calling it → `RuntimeFault::SpawnConflict`. The in-process `domain_error` helper now yields
  `RuntimeError::local(e)`.
- **There is no `#[from] ClientError`** (orphan-illegal once the error type is the kernel's
  `PortError<_>`, and it would swallow `F` into `Opaque`). The socket adapter maps explicitly
  via `RuntimeError::wire` at the six bare-`?` `ClientError` sites
  (`rtmd.rs:70,75,103,129,134,138`) and the non-conflict arm of `spawn_error` (`rtmd.rs:165`)
  — **7 wire sites**. `doctor()` is **NOT** one: both its arms return `Ok(..)`; the `Err` arm
  (`rtmd.rs:145-149`) already builds an `Ok(degraded RuntimeDoctorReport)` via
  `conv::runtime_doctor_error` (preserving `code` + `socket_path`, which the WS6 conformance
  asserts). It stays verbatim; only `doctor()`'s return type renames via the alias.
- `handler/spawn.rs:371 runtime_spawn_failure` updates its one match arm to
  `RuntimeFault::SpawnConflict`. `assert_spawn_conflict_eq` becomes the `SpawnConflict` arm of
  `assert_fault_parity`, returning a `ParityProof`.
- `ClientError: Send + Sync + 'static` is confirmed (io::Error / ProtocolError / ErrorCode /
  String / Box<SpawnConflictPayload> / &'static str are all `Send + Sync`), so erasure into
  `Box<dyn Error + Send + Sync>` holds.

## 5. Forward-compatibility — how port 2..N adopts it

A new bounded-context port (schedule / orchestrate / workflow):

1. `type XxxError = PortError<XxxFault>;` — define only the semantic `XxxFault` enum.
2. In-process adapter: domain residue → `XxxError::local(..)`; caller-matched conditions →
   `XxxFault::*` via a shared `conv` classifier fed by a structured payload.
3. Wire adapter: transport error → `XxxError::wire(..)`; caller-matched conditions → the
   **same** `conv` classifier fed by the round-tripped typed carrier (the §2.2 birth rule).
4. Conformance: `assert_fault_parity(&XxxFault) -> ParityProof` with an exhaustive match — the
   tripwire forces an arm per variant, and the `ParityProof` return forbids hollow arms.
5. Callers never branch on `Opaque` (and structurally cannot, beyond `Display`/`source()`).

This replaces the design §5.1 deferred remedy and the
`NOTES/bounded-context-port-error-model.md` "until then" stopgap with an enforced mechanism.

## 6. Workstreams

- **EM1 — Kernel crate.** Create `internal/port` (`lilo-port`): `PortError<F>` (+ `local`/
  `wire` ctors), opaque `OpaqueFault` (public struct over private `OpaqueKind`), and the
  `ParityProof` token + `prove_eq` comparator (test-support). Dependency: `thiserror` only.
  **Two explicit manifest edits** (root `Cargo.toml` `members` is an explicit list, not a
  glob): (i) add `internal/port` to `members`; (ii) add
  `[workspace.dependencies] lilo-port = { path = "internal/port" }` so the driver consumes it
  via `workspace = true` (DRY; `thiserror` is already a workspace dep, 2.0.17). Tests:
  `Display`/`source()` chaining, opacity (no public local-vs-wire match), `prove_eq`.
- **EM2 — Runtime-port migration (reference impl).** Replace `DriverError` with
  `RuntimeError = PortError<RuntimeFault>` per §4; in-process adapter → `RuntimeError::local`;
  socket adapter → explicit `RuntimeError::wire` at the 6 `?` sites + `spawn_error`
  non-conflict arm (**7 wire sites**; `doctor()`'s `Err` arm stays a degraded `Ok` report, NOT
  wire-mapped — see §4); `conv::spawn_conflict` → `Fault`; precondition ctors → `Fault`,
  residue (`UnknownRuntimeVariant`/`MissingRuntimePid`) → `Opaque::Local`. **Delete** the old
  `DriverError` enum (incl. dead `CaptureFailed` + test-mock-only `Unsupported`) and the
  `Runtime`/`Client` split; **re-export `RuntimeError` + `pub RuntimeFault` from
  `driver/src/lib.rs:15`** (the surface the daemon imports — daemon needs no direct `lilo-port`
  dep). Update the one match (`handler/spawn.rs:371`) to
  `RuntimeError::Fault(RuntimeFault::SpawnConflict ..)`. **Blast radius beyond the driver crate
  (line list REPRESENTATIVE; `git grep DriverError → ZERO` is the completeness gate), mapped
  PER VARIANT:** `Runtime`→`local` (`events.rs ~214`, `spawn_recovery.rs 166/289/307/313`);
  `Unsupported`→`local` (`events.rs:424`, `spawn_recovery.rs:236`, `spawn/tests.rs:396`);
  `InvalidSessionId`→`Fault` (`spawn_recovery.rs:244`, `spawn/tests.rs:282`); plus mechanical
  `DriverError`→`RuntimeError` renames in imports/sigs. Re-home
  `assert_spawn_conflict_eq` into `assert_fault_parity`'s `SpawnConflict` arm. **`RuntimeFault`
  (and `SpawnConflictKind`) must derive `PartialEq + Debug`** so `prove_eq` can compare by `==`
  (today's `assert_spawn_conflict_eq` destructures, so `DriverError` lacks `PartialEq`). `fmm
  generate && fmm validate` after moves.
- **EM3 — Docs/lesson truth-up.** Resolve design §5.1 (point to this doc, mark enforced),
  retire the `NOTES/` stopgap, update the LESSONS entry from "flag and track" to "enforced by
  `lilo-port`."

Ordering: EM1 → EM2 → EM3. EM1+EM2 are one coherent change (the kernel is meaningless without
its first consumer); land them in one PR unless size forces a split.

## 7. Acceptance

- `internal/port` builds, is a workspace member + a `[workspace.dependencies]` entry, depends
  only on `thiserror`, and is a true dependency leaf (no context crate in its tree).
- Runtime port returns `PortError<RuntimeFault>`; `DriverError` and its `Runtime`/`Client`
  split are **deleted**; dead `CaptureFailed` is gone (0 refs). No parallel path; fmm dead-code
  sweep clean for touched modules.
- A caller cannot branch on provenance: `OpaqueKind` is private, so no `match` on local-vs-wire
  is nameable outside the kernel (structural, not by-convention); `Display`/`source()` still
  work.
- `assert_fault_parity` is exhaustive (no `_`) AND each arm returns a `ParityProof` from
  `prove_eq`; a dummy `RuntimeFault` variant with a hollow `=> {}` arm fails to compile (assert
  in review, then revert the dummy).
- The existing dual-adapter conformance (`spawn_conflict` parity, status/doctor/poll_events
  shapes) stays green through the rename.
- `just check && just build && just test`; `fmm generate && fmm validate` after moves.

## 8. Risks

- **R1 — Over-abstraction.** A shared error kernel could grow into a junk drawer. Mitigation:
  the kernel holds ONLY the two-tier type + the `ParityProof` helper; the port trait and `conv`
  classifiers stay per-context. Reviewed as a contract.
- **R2 — Type-erasure hides a genuinely-needed wire signal.** If some caller truly needs a
  transport fact (e.g. "daemon unavailable, retry"), erasure blocks it. Mitigation: that is a
  transport concern that must not cross a domain port; a retry policy belongs in the adapter,
  not the caller. Revisit only with a concrete caller.
- **R3 — `Send + Sync + 'static` bound on erased wire errors.** Any future port's wire error
  must satisfy it. Mitigation: it is the standard bound for `anyhow` / `Box<dyn Error>`
  interop; assert per port at adoption (§5 step 3).
- **R4 — Parity residual (trigger-faithfulness).** The tripwire + `ParityProof` forbid hollow
  arms but cannot force the trigger to faithfully exercise both adapters. Mitigation: named
  per-variant parity cases + review; codegen deferred (§2.2/§2.3).

## 9. Process

superpowers brainstorming (done, with Stuart) → **MoE peer-consensus** (Claude + Codex
codebase-analyst: dual conditional sign-off → 2 re-read fixes (classification + source) +
1 bonus (dead `Unsupported`) applied → dual CLEAN sign-off, 2026-05-29) → superpowers writing-plans → warroom execution (Codex implements, Claude reviews,
one PR for EM1+EM2, EM3 folded or a small docs PR). Branch off `main` (not the stale
`nancy/ALP-2816` worktree).
