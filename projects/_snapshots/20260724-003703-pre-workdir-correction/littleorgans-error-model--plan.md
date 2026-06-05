# Bounded-Context Port Error Model (`lilo-port`) — Implementation Plan

> **For agentic workers:** cold-read warroom handoff. The authoritative contract is the design
> doc `~/.mdx/projects/littleorgans-bounded-context-port-error-model--design.md`
> (consensus-locked, dual clean sign-off). This plan sequences the work; when the two
> disagree, the design doc wins. Precise on WHAT (files, symbols, sites, acceptance);
> behavioural signposts on HOW — do not treat code sketches as line-for-line mandates.

**Goal:** Replace the runtime port's ad-hoc `DriverError` with a shared, reusable error
kernel (`lilo-port`) that makes adapter parity a type/compile guarantee instead of a
remembered convention, and migrate the runtime port onto it as the reference implementation.

**Architecture:** A new context-neutral leaf crate `internal/port` (`lilo-port`, `thiserror`
only) exposes `PortError<F>` = `Fault(F)` (per-port caller-matched contract) + opaque-by-
construction `Opaque` (provenance, unobservable to callers), plus a `ParityProof` witness
token. The runtime port aliases `RuntimeError = PortError<RuntimeFault>` and both adapters
(in-process + socket) classify through it.

**Tech stack:** Rust, `thiserror` 2.0.17 (already a workspace dep), `cargo`/`just`/`nextest`,
`fmm`. Branch off `main` @ ≥6971d57 (NOT the stale `nancy/ALP-2816` worktree). One PR for
Phase 1+2; Phase 3 (docs) folds in or trails as a small docs PR.

---

## Pre-flight

- [ ] Branch off `main`: `git worktree add ../littleorgans-worktrees/error-model -b feat/lilo-port-error-model main`. Confirm `git log -1` shows ≥`6971d57`.
- [ ] Confirm baseline green in the new worktree: `just check && just build && just test`.
- [ ] Confirm the generated-surface guard is NOT hand-patched (do not re-add an xtask fallback — `just test` builds xtask; this regressed 3× in prior workstreams). Leave `generated_surface_guard.rs` as-is on `main`.

---

## Phase 1 — EM1: the `lilo-port` kernel crate

**Files:**
- Create: `internal/port/Cargo.toml`
- Create: `internal/port/src/lib.rs` (the only source file; keep it one module, well under 700 LOC)
- Modify: root `Cargo.toml` (two edits — see Task 1.1)

### Task 1.1 — Scaffold the crate + wire the workspace (TWO manifest edits)

- [ ] Create `internal/port/Cargo.toml`: package `lilo-port`, version/edition/lints via `[package] ... workspace = true` like sibling `internal/*` crates; `[dependencies] thiserror.workspace = true`. No other deps (it must stay a dependency leaf).
- [ ] Root `Cargo.toml` edit (i): add `"internal/port"` to `[workspace] members` (it is an explicit list, not a glob — verified).
- [ ] Root `Cargo.toml` edit (ii): add to `[workspace.dependencies]`: `lilo-port = { path = "internal/port" }` so consumers use `lilo-port.workspace = true` (DRY, matches other internal crates).
- [ ] `cargo build -p lilo-port` compiles (empty lib).

### Task 1.2 — `PortError<F>` + opaque `OpaqueFault` (TDD: opacity + source-chaining)

The contract and exact shape are in design §2.1. Key invariants the implementer MUST hit:

- `PortError<F>` is a **2-variant public enum**: `Fault(F)` + `Opaque(OpaqueFault)`, both
  `#[error(transparent)]`. Callers can `match { Fault(f) => .., _ => .. }`.
- `OpaqueFault` is a **public struct over a PRIVATE enum** (`pub struct OpaqueFault(OpaqueKind)`;
  `enum OpaqueKind { Local(String), Wire(Box<dyn Error + Send + Sync>) }`). No `Local`/`Wire`
  visible to callers.
- **`source()` MUST chain to the wire error.** Use `#[error(transparent)]` on `OpaqueFault` +
  `#[source]` on the `Wire` field (the naive `#[error("{0}")]` newtype drops `source()` —
  verified in consensus). `Local` has no source.
- Constructors: `impl<F> PortError<F> { pub fn local(impl Display) -> Self; pub fn wire(impl Error + Send + Sync + 'static) -> Self }` delegating to private `OpaqueFault::local`/`wire`. **No `#[from]`** (orphan-illegal at consumers; would swallow `F`).

- [ ] **Test first** (`internal/port/src/lib.rs` `#[cfg(test)]`). Define a local fault type — `PortError<F>` only impls `Error` when `F: Error`, so `PortError<()>` has NO `source()`:
  - `#[derive(Debug, thiserror::Error)] #[error("test fault")] struct TestFault;`
  - `opaque_wire_preserves_source`: `PortError::<TestFault>::wire(io_error)`; assert `err.source().is_some()` and the chain reaches the inner error.
  - `opaque_local_has_no_source`: `PortError::<TestFault>::local("boom")`; assert `source().is_none()` and `Display` == "boom".
  - `display_delegates`: `Display` of a `Fault`/`Opaque` matches the inner.
  - (Opacity is enforced structurally — `OpaqueKind` private — so a "cannot match local-vs-wire" test is a compile-time fact, not a runtime assert; add a doc-comment noting this.)
- [ ] Run: `cargo test -p lilo-port` → the source tests FAIL (no impl yet).
- [ ] Implement `PortError<F>`, `OpaqueFault`, `OpaqueKind`, ctors per design §2.1.
- [ ] Run: `cargo test -p lilo-port` → PASS.

### Task 1.3 — `ParityProof` token + `prove_eq` comparator (TDD)

Contract in design §2.2. Invariants:
- `pub struct ParityProof(())` — private field ⇒ unconstructable except via `prove_eq`.
- `pub fn prove_eq<E: PartialEq + Debug>(direct: E, via_socket: E) -> ParityProof` —
  `assert_eq!` then return `ParityProof(())`.
- **Plain `pub`, NOT `#[cfg(test)]`** — `driver/tests/port_conformance.rs` is a SEPARATE crate that sees only `lilo-port`'s normal public API (cfg(test)-gating → "not found in lilo_port"). The kernel's own unit tests (Task 1.2) stay `#[cfg(test)]`.

- [ ] **Test first**: `prove_eq_returns_proof_on_equal` (equal inputs → returns, no panic);
  `prove_eq_panics_on_mismatch` (`#[should_panic]`).
- [ ] Run → FAIL.
- [ ] Implement `ParityProof` + `prove_eq`.
- [ ] Run → PASS.

### Task 1.4 — Phase 1 gate

- [ ] `cargo build -p lilo-port && cargo test -p lilo-port` green.
- [ ] `lilo-port`'s dependency tree contains only `thiserror` (no context crate): `cargo tree -p lilo-port` — confirm it is a true leaf.
- [ ] Commit: `feat(port): add lilo-port error kernel (PortError, OpaqueFault, ParityProof)`.

---

## Phase 2 — EM2: migrate the runtime port onto `lilo-port` (reference impl)

**Files (all under `internal/session/`):**
- Modify: `driver/Cargo.toml` (add `lilo-port.workspace = true`)
- Modify: `driver/src/driver.rs` (delete `DriverError`; define `pub RuntimeFault` + `RuntimeError` alias)
- Modify: `driver/src/lib.rs:15` (re-export: replace `DriverError` with `RuntimeError` + `RuntimeFault`, surfacing `lilo_port::{PortError, OpaqueFault}` as needed — this is the public error surface the daemon imports, so the daemon needs NO direct `lilo-port` dep)
- Modify: `driver/src/in_process.rs` (`domain_error` → `RuntimeError::local`)
- Modify: `driver/src/rtmd.rs` (explicit `RuntimeError::wire` at the named sites)
- Modify: `driver/src/conv.rs` (return `RuntimeError`; `spawn_conflict` → `Fault`; precondition ctors → `Fault`; residue ctors → `Opaque::Local`)
- Modify: `driver/tests/port_conformance.rs` (re-home `assert_spawn_conflict_eq` → `assert_fault_parity` returning `ParityProof`)
- Modify: `daemon/src/handler/spawn.rs` (`:371` match arm → `RuntimeFault::SpawnConflict`)
- Modify (compile-fix blast radius — REPRESENTATIVE; authoritative per-variant mapping in Task 2.6, `git grep DriverError → ZERO` is the gate): `daemon/src/events.rs` (~214/424), `daemon/tests/handler/spawn_recovery.rs` (166/236/244/289/307/313), `daemon/src/handler/spawn/tests.rs` (282/396)

The mapping table is design §4. Verified classification (design §1.1):
- **`RuntimeFault` (derive `PartialEq + Debug`; `SpawnConflictKind` too):** `SpawnConflict { kind, message }`, `InvalidSignal`, `InvalidSessionId`, `InvalidTarget`.
- **`Opaque::Local` (no caller matches):** `UnknownRuntimeVariant`, `MissingRuntimePid`, in-process domain residue.
- **`Opaque::Wire`:** the socket `ClientError` (explicit, no `#[from]`).
- **DELETE:** `CaptureFailed` (dead), `Unsupported` (test-mock only).

### Task 2.1 — Define `RuntimeFault` + `RuntimeError`; delete `DriverError`

- [ ] In `driver/src/driver.rs`: add `lilo-port` dep; define `pub enum RuntimeFault { SpawnConflict { kind: SpawnConflictKind, message: String }, InvalidSignal(String), InvalidSessionId(String), InvalidTarget(String) }` with `#[derive(Debug, PartialEq, thiserror::Error)]` and the existing `#[error(...)]` messages. `SpawnConflictKind` ALREADY derives `Clone,Copy,Debug,Eq,PartialEq` (lilo-rm-core `proto.rs:135` — **verify, do NOT edit the published crate**), so `RuntimeFault` derives `PartialEq + Debug` cleanly. `RuntimeFault` must be `pub` (the daemon matches it).
- [ ] `pub type RuntimeError = PortError<RuntimeFault>;`
- [ ] Delete `enum DriverError` entirely (incl. `CaptureFailed`, `Unsupported`, `Runtime`, `Client`).
- [ ] Update the `RuntimePort` trait's `RuntimePortFuture<'a, T>` alias (`port.rs`) to `Result<T, RuntimeError>`.
- [ ] (Will not compile until 2.2–2.4 land — expected.)

### Task 2.2 — `conv.rs`: classify into the two tiers

- [ ] `parse_session_id`/`parse_runtime_signal`/`runtime_spawn_request` precondition errors → `RuntimeFault::{InvalidSessionId,InvalidSignal,InvalidTarget}` wrapped as `PortError::Fault(..)`.
- [ ] `spawn_conflict(payload)` → `PortError::Fault(RuntimeFault::SpawnConflict { .. })` (still the ONE shared classifier both adapters call).
- [ ] `UnknownRuntimeVariant` (conv.rs:94) and `MissingRuntimePid` (conv.rs:193) residue → `PortError::local(..)`, reproducing the EXACT current `#[error]` message text (`Opaque::Local` passes Display through; verify no test asserts these strings via `git grep`).
- [ ] All `conv` fns that returned `Result<_, DriverError>` now return `Result<_, RuntimeError>`.

### Task 2.3 — In-process adapter (`in_process.rs`)

- [ ] `domain_error(e)` helper → `RuntimeError::local(e)` (was `DriverError::Runtime(e.to_string())`).
- [ ] The `UnknownRuntimeVariant` construction at `in_process.rs:126` → `RuntimeError::local(..)`.
- [ ] Method signatures return `RuntimeError`.

### Task 2.4 — Socket adapter (`rtmd.rs`): explicit `wire` mapping (NO `#[from]`)

- [ ] Confirm `ClientError: std::error::Error + Send + Sync + 'static` (the `wire` bound; design R3) — true today, compile-confirm.
- [ ] Replace the six bare `?`-on-`ClientError` sites (`rtmd.rs:70,75,103,129,134,138`) with `.map_err(RuntimeError::wire)?`.
- [ ] `spawn_error`: keep the `ClientError::SpawnConflict(payload) => conv::spawn_conflict(..)` arm (→ `Fault`); the non-conflict arm → `RuntimeError::wire(other)` (`rtmd.rs:165`).
- [ ] **Doctor `Err` arm (`rtmd.rs:145-149`) stays VERBATIM** — both `doctor()` arms return `Ok(..)`; the `Err` arm already builds `Ok(conv::runtime_doctor_error(code, msg, socket_path))` (a degraded `RuntimeDoctorReport`, NOT a port error). Do NOT wire-map it — that regresses `runtime_ports_doctor_shapes_match_*` (asserts `socket_path.is_some()`) + the conv unit test. Only `doctor()`'s return type renames via the alias. → **7 wire sites total** (6 `?` + spawn_error arm).
- [ ] `UnknownRuntimeVariant` at `rtmd.rs:110` → `RuntimeError::local(..)`.

### Task 2.5 — Conformance: `assert_fault_parity` returning `ParityProof`

- [ ] In `driver/tests/port_conformance.rs`: the existing async test obtains the `Fault` from BOTH adapters for each trigger, THEN calls an exhaustive-match comparator returning `ParityProof` — e.g. `fn parity(direct: &RuntimeFault, socket: &RuntimeFault) -> ParityProof { match direct { /* one arm per variant, NO `_` */ RuntimeFault::SpawnConflict{..} => lilo_port::prove_eq(direct, socket), .. } }`, called after both errors are available (or an `async fn` per-variant case if a variant needs its own trigger); name it `assert_fault_parity` per design §4/§7. The exhaustive match (no `_`) is the tripwire; `prove_eq` is the proof. Re-home `assert_spawn_conflict_eq`'s comparison into the `SpawnConflict` path. **All 4 `RuntimeFault` arms must be driven with REAL triggers through BOTH adapters** — the 3 preconditions via bad session_id/signal/target at method entry — then `prove_eq`; do NOT stub precondition arms (a stubbed arm degenerates the tripwire into the R4 residual the reviewer will check in diff review).
- [ ] Keep the existing `runtime_ports_*_shapes_match` (status/doctor/poll_events) tests green through the rename; `socket_path` None/Some provenance assertions unchanged.
- [ ] **Tripwire test (assert-then-revert):** temporarily add a dummy `RuntimeFault` variant with a hollow `=> {}` arm; confirm `cargo test -p lilo-session-driver --test port_conformance` FAILS TO COMPILE (the arm owes a `ParityProof`); revert. Record the observation in the PR.

### Task 2.6 — Caller + blast-radius compile fixes

- [ ] `daemon/src/handler/spawn.rs:371 runtime_spawn_failure`: match arm → `RuntimeError::Fault(RuntimeFault::SpawnConflict { kind, .. })` via the **driver re-export** (daemon depends on the driver crate, NOT on `lilo-port` directly); the `other => other.to_string()` fallthrough works on `RuntimeError` via transparent Display.
- [ ] Daemon-side construction sites — **map PER VARIANT** (line list REPRESENTATIVE; the Task 2.7 `git grep DriverError → ZERO` gate is authoritative for completeness):
  - `DriverError::Runtime(..)` → `RuntimeError::local(..)`: `events.rs` (~214), `tests/handler/spawn_recovery.rs` (166, **289, 307, 313**).
  - `DriverError::Unsupported{..}` (deleted) → `RuntimeError::local(..)`: `events.rs:424`, `tests/handler/spawn_recovery.rs:236`, `src/handler/spawn/tests.rs:396`.
  - `DriverError::InvalidSessionId(..)` → `RuntimeError::Fault(RuntimeFault::InvalidSessionId(..))` (caller-matched precondition, NOT residue): `tests/handler/spawn_recovery.rs:244`, `src/handler/spawn/tests.rs:282`.
  - Mechanical `DriverError`→`RuntimeError` renames in imports/sigs/turbofish (e.g. events.rs:133/149/219; handler/spawn.rs:13; handler/spawn/tests.rs:22; spawn_recovery.rs:14/21/151/243/281).

### Task 2.7 — Phase 2 gate

- [ ] `git grep -n "DriverError"` → ZERO hits (enum and all references deleted; no parallel path).
- [ ] `git grep -n "CaptureFailed\|DriverError::Unsupported"` → ZERO hits.
- [ ] `just check && just build && just test` green (full workspace gate).
- [ ] `fmm generate && fmm validate` clean; dead-code/glossary sweep clean for `driver`, `daemon/handler`.
- [ ] Commit: `refactor(session): migrate runtime port to lilo-port PortError<RuntimeFault>`.
- [ ] Open PR (title): `feat(port): shared bounded-context error kernel + runtime-port migration`. Body cites design doc + the parity-tripwire observation.

---

## Phase 3 — EM3: docs / lesson truth-up (folds into the PR or a small docs PR)

- [ ] `~/.mdx/projects/littleorgans-runtime-port-boundary--design.md` §5.1: replace the DEFERRED text with a pointer to this design doc, marked ENFORCED.
- [ ] `NOTES/bounded-context-port-error-model.md`: retire the "until then" stopgap; point to `lilo-port`.
- [ ] `LESSONS.md`: update the error-model entry from "flag and track" to "enforced by `lilo-port` (PortError two-tier + ParityProof)."
- [ ] cm: update decision `019e74a5` status → implemented (post-merge).

---

## Acceptance (design §7, consolidated)

- `internal/port` builds, is a workspace member + `[workspace.dependencies]` entry, `thiserror`-only, true leaf (`cargo tree`).
- Runtime port returns `PortError<RuntimeFault>`; `DriverError` + `Runtime`/`Client` split + dead `CaptureFailed`/`Unsupported` all deleted; zero parallel path.
- `source()` chains through `Opaque::Wire`; `Local` has none (Phase 1 tests).
- `assert_fault_parity` exhaustive (no `_`) + each arm returns `ParityProof`; hollow arm fails to compile (Task 2.5 assert-then-revert).
- Existing dual-adapter conformance (spawn_conflict parity, status/doctor/poll_events shapes) green through the rename.
- `just check && just build && just test`; `fmm generate && fmm validate`.

## Execution

Fresh warroom (Codex `helioy-tools:backend-engineer` implements, Claude `superpowers:code-reviewer` reviews), two-phase per the proven runtime-port pattern: design-read `D`→`S|A`, diff-review `C`→`S|B`. Orchestrator runs own `just check && just build && just test` + `git diff main..HEAD` before PR. One PR for Phase 1+2.
