# WS4 — Authz "no-bypass" + audit de-dup (Option D §4)

> **For agentic workers:** this is the cold-read handoff for the WS4 warroom. Read it
> in full before touching code. The design is settled (see "Design decisions" below);
> do not re-litigate it. Implement the cards in order. Branch:
> `feat/runtime-port-authz-audit` (worktree
> `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans-worktrees/runtime-port-authz-audit`,
> off `main` @ `dec7015`).

**Goal:** Close the 7 ungated `SessionRpc` verbs so authorization is impossible to
bypass, and de-RPC the 3 spawn-lifecycle self-calls onto the existing `RuntimePort` so
composed mutations stop double-auditing and stop looping through the wire door.

**Architecture:** The session daemon's `SessionRpc` dispatch is the session bounded
context's trust door. Every verb must pass an authorization decision there. Composed
runtime access goes through the in-process `RuntimePort` (built in WS2); the runtime wire
door (`handle_rpc`) is retained only for external/diagnostic clients. Authorization +
decision audit live at each door; there is **no separate "state-change audit" type**.

**Tech stack:** Rust, tokio, sqlx/SQLite, the WS2 `RuntimePort` trait in
`internal/session/driver`.

---

## Design decisions (LOCKED — do not change)

1. **No new audit type.** `AuditRow` / `AuditDecision` (`crates/lilo-im-core/src/audit.rs`)
   are frozen. We do **not** add an `Executed` variant or restructure the row. The §4
   "domain state-change audit" idea is dropped for v1 (KISS, confirmed by Stuart).
2. **De-dup, not preserve.** Today a composed spawn writes **two** audit rows: one at the
   session door (`authorize_in_tx`, `spawn.rs:117`) and one at the runtime door
   (`authorize_runtime_rpc`, `runtime/daemon/src/handler.rs:133`) because spawn self-RPCs
   through `runtime_service.handle_rpc`. De-RPC'ing spawn onto the port removes the
   second, redundant row. The session-door row (real principal) is the system of record.
   Verified: `delete_one` (`sessions.rs:98`, `Action::Kill`), `nudge_one`
   (`messaging.rs:191`, `Action::Nudge`), spawn (`authorize_in_tx`) all decision-audit at
   the session door before reaching the port.
3. **Self-initiated mutations are operational, not security events.** The recovery kill
   (failed-spawn cleanup) and reconcile are the daemon acting as itself with no user
   principal. After de-RPC they pass no door and write no audit row — correct. Their trace
   belongs in the runtime event log (the kill path already emits a lifecycle/`ChildExit`
   event; verify, don't add a parallel trail).
4. **No-bypass by construction.** Gating is a single exhaustive classifier over
   `SessionRpc` with **no `_` arm**, so a future verb fails to compile until its authz is
   declared. (Cashes in the `non_exhaustive` removal from the earlier branch.)
5. **Effects trail deferred to v2.** A durable tamper-evident trail of *effects* (vs
   decisions) is an enterprise/compliance posture; out of scope for v0.8.0. If ever built,
   it is a runtime-context audit event, not a borrowed identity `AuditRow`.

---

## Verified surface (current state @ dec7015)

- **Dispatch:** `internal/session/daemon/src/handler/dispatch.rs` — `handle` (`:11`)
  special-cases `McpBridge`, delegates everything else to `handle_direct` (`:42`), which
  is the big `match` over `SessionRpc` (`:47-67`). `self.identity: Arc<IdentityClient>`.
  `RequestContext` carries `principal: Principal`.
- **7 ungated verbs** (no `&context`, no `authorize`): `List` (`:49`),
  `NamespaceCreate` (`:50`), `NamespaceGet` (`:51`), `NamespaceList` (`:52`),
  `MailCheck` (`:57`), `MailStopCheck` (`:58`), `Wait` (`:64`).
- **Already gated downstream** (keep as-is): `Spawn`, `NamespaceDelete`, `Delete`,
  `MailSend`, `MailRead`, `Nudge`, `Label`, `Logs`, `Capture`, `Doctor`, `Shutdown`.
  `McpBridge` handled in `handle` (own path).
- **`Action` enum** (`crates/lilo-im-core/src/types.rs:137-160`): `Spawn, Kill, List,
  Read, Logs, MailSend, MailRead, Nudge, Link, Doctor, Daemon, ShimCallback`. **No
  `Create`.**
- **Resources:** `ResourceSpec::default()` available; `session_resource(id)` at
  `internal/session/daemon/src/identity_client.rs:42`. **No `namespace_resource`.**
- **`DaemonState`** (`internal/session/daemon/src/handler/state.rs:10-14`): `store`,
  `runtime: Arc<dyn RuntimePort>` (`:12`), `runtime_service: Arc<RuntimeService>` (`:13`),
  `identity: Arc<IdentityClient>` (`:14`). Both runtime fields exist.
- **`RuntimePort`** (`internal/session/driver/src/port.rs`): `spawn(&str, &SpawnLaunch)
  -> SpawnedProcess` (`:19`), `terminate(&str, &str signal, Duration) -> Option<ChildExit>`
  (`:33`), `status(StatusFilter) -> Vec<Lifecycle>` (`:46`). All needed methods exist.
- **3 spawn self-calls** in `internal/session/daemon/src/handler/spawn.rs`: Spawn
  (`:71-87`, `RuntimeResponse::Spawned(payload)`), recovery Kill (`:165-177`,
  `KillRequest{Term, grace_secs:5}`), reconcile Status (`:273-287`, `StatusRequest{..}`).
  spawn.rs is the **only** composed caller of `runtime_service.handle_rpc` (tests aside).

---

## Card C1 — exhaustive authz gate (the security fix)

**Files**
- Create: `internal/session/daemon/src/handler/authz.rs`
- Modify: handler module root (the file declaring `dispatch`/`spawn`/`sessions` mods) — add `mod authz;`
- Modify: `internal/session/daemon/src/handler/dispatch.rs` (gate in `handle_direct`)

**Contract**

Add a classifier and gate every verb at the session door. New module `authz.rs`:

```rust
use lilo_im_core::Action;
use lilo_session_core::SessionRpc; // adjust path to where SessionRpc is defined

/// Where a verb's authorization decision is made.
pub(crate) enum AuthzPlan {
    /// Coarse decision at the door, before dispatch.
    AtDoor { action: Action },
    /// Verb authorizes itself after resolving its resource (in-tx / per-target).
    Downstream,
}

/// Exhaustive by design: a new `SessionRpc` variant will not compile until its
/// authorization is declared here. Do NOT add a `_` arm.
pub(crate) fn authz_plan(rpc: &SessionRpc) -> AuthzPlan {
    use AuthzPlan::{AtDoor, Downstream};
    match rpc {
        // --- newly gated reads (door-coarse) ---
        SessionRpc::List { .. } => AtDoor { action: Action::List },
        SessionRpc::NamespaceList { .. } => AtDoor { action: Action::List },
        SessionRpc::NamespaceGet { .. } => AtDoor { action: Action::Read },
        SessionRpc::MailCheck { .. } => AtDoor { action: Action::MailRead },
        SessionRpc::MailStopCheck { .. } => AtDoor { action: Action::MailRead },
        SessionRpc::Wait { .. } => AtDoor { action: Action::Read },
        // --- newly gated mutation ---
        // NamespaceCreate: symmetric with NamespaceDelete, which authorizes with
        // `Action::Kill` + `ResourceSpec::default()` (namespace.rs:93). Use the same.
        // (The namespace Action vocabulary — `Kill` labelling both create and delete —
        // is a pre-existing wart; a dedicated cleanup is carried forward, NOT bundled
        // into this security PR. Do not add a new Action variant in WS4.)
        SessionRpc::NamespaceCreate { .. } => AtDoor { action: Action::Kill },
        // --- verbs that authorize themselves downstream (unchanged) ---
        SessionRpc::Spawn { .. }
        | SessionRpc::NamespaceDelete { .. }
        | SessionRpc::Delete { .. }
        | SessionRpc::MailSend { .. }
        | SessionRpc::MailRead { .. }
        | SessionRpc::Nudge { .. }
        | SessionRpc::Label { .. }
        | SessionRpc::Logs { .. }
        | SessionRpc::Capture { .. }
        | SessionRpc::Doctor { .. }
        | SessionRpc::McpBridge { .. }
        | SessionRpc::Shutdown => Downstream,
    }
}
```

In `dispatch.rs::handle_direct`, before the existing `match request`:

```rust
if let AuthzPlan::AtDoor { action } = authz::authz_plan(&request) {
    if let Err(error) = self
        .identity
        .authorize(&context.principal, action, &ResourceSpec::default())
        .await
    {
        return response(Err(error), false);
    }
}
```

(Use `ResourceSpec::default()` at the door — no namespace/selector resource helper exists,
and the gate is coarse "may this principal do this class of action". Matches how
`shutdown` already authorizes with `ResourceSpec::default()`.)

**Why `Action::MailRead` for MailCheck/MailStopCheck and `Action::Read`/`Action::List`
for the rest:** the Action is the audit label; the stub authorizer gates on local-uid.
Pick the closest existing variant; do not invent read/view variants.

**Tests (C1)**
- Unit in `authz.rs`: assert the plan for each of the 7 newly-gated verbs is `AtDoor` and
  each downstream verb is `Downstream`. (The exhaustive match is the compile-time guard;
  this test documents intent.)
- Integration: a request from a non-local / unknown `Principal` to each of the 7 verbs
  now returns an authorization error (previously succeeded). Use the existing test
  harness in `internal/session/daemon/tests/` (see `tests/common/mod.rs`). One
  parametrized test over the 7 verbs is enough.

**Acceptance:** all 7 verbs gated; exhaustive match compiles with no `_`; full gate green.

---

## Card C2 — de-RPC the 3 spawn-lifecycle self-calls onto the port

**Files**
- Modify: `internal/session/daemon/src/handler/spawn.rs` (3 sites)

**Contract** — replace each `self.runtime_service.handle_rpc(..)` with the equivalent
`self.runtime.<method>(..)` (the WS2 port). Map request/response via the **existing**
`conv` layer + the way `InProcessRuntime` already implements these methods (read
`internal/session/driver/src/in_process.rs` and `conv.rs` to match shapes exactly — do
not invent conversions).

1. **Spawn (`:71-87`).** Replace the `RuntimeRpc::Spawn { request: runtime_request }`
   self-call returning `RuntimeResponse::Spawned(payload)` with
   `self.runtime.spawn(&session_id, &launch).await` returning
   `Result<SpawnedProcess, DriverError>`. Build the `SpawnLaunch` (session vocabulary)
   the same way `InProcessRuntime::spawn` expects; map the existing `runtime_request`
   inputs into it. Error path unchanged in spirit: on `Err`, call
   `self.abort_spawn_intent(id, &<failure string from DriverError>)` then `bail!`.
   Reuse/extend the existing `runtime_spawn_failure` helper for the `DriverError` case
   (it currently formats a `RuntimeResponse`; adapt or add a sibling for `DriverError`,
   no duplication).
2. **Recovery kill (`:165-177`).** Replace `RuntimeRpc::Kill { KillRequest{ session_id,
   signal: Term, grace_secs: 5 } }` with `self.runtime.terminate(&session_id_string,
   <signal-str for Term>, Duration::from_secs(5)).await` → `Option<ChildExit>`. Match the
   signal-string mapping the other terminate callers use (e.g. `delete_one`/reaper).
   This is self-initiated cleanup: log the outcome via `tracing`; do not add an audit row.
3. **Reconcile status (`:273-287`).** Replace `RuntimeRpc::Status { StatusRequest{
   session_id: Some(..), .. } }` with `self.runtime.status(StatusFilter{ .. }).await` →
   `Vec<Lifecycle>`. Build the `StatusFilter` for the single session id; consume the
   `Vec<Lifecycle>` where the old code consumed the `RuntimeResponse::Status` payload.

After all three: spawn.rs must no longer reference `runtime_service` or `RuntimeRpc` /
`RuntimeResponse` / `KillRequest` / `StatusRequest` / `RuntimeSignal`. Remove now-unused
imports. **Do not** remove the `runtime_service` field from `DaemonState` — the wire door
(`compose.rs`) still uses it for external clients. (If a grep proves spawn.rs was the last
in-crate reader and the field is now only read by the wire-door composition, leave it; it
is legitimately the wire door's dependency.)

**Tests (C2)**
- The existing spawn integration tests must still pass (spawn succeeds, intent committed,
  recovery on failure still kills, reconcile still observes status).
- **De-dup assertion (the §4 acceptance):** a composed spawn writes **exactly one** audit
  row (the session door's, `Action::Spawn`, real principal) — assert the runtime-door row
  is gone. Query the audit store after a composed spawn and assert count == 1 for that
  principal+action. (Before C2 it was 2.)

**Acceptance:** 3 sites on the port; no `handle_rpc`/`RuntimeRpc` in spawn.rs; composed
spawn audits once; full gate green.

---

## Card C3 — cleanup + doc truth-up (orchestrator does the doc edits)

- **Dead-code sweep:** confirm no orphaned imports/helpers after C1+C2 (`cargo build` +
  `clippy -D warnings`). If `runtime_spawn_failure` or any `RuntimeRpc` re-export became
  unused, delete it.
- **Doc revision (orchestrator, not the warroom):** edit
  `~/.mdx/projects/littleorgans-runtime-port-boundary--design.md` §4 and §5 to the
  "no new audit type" model — §4 becomes "decision audit at every door (no-bypass) +
  de-dup redundant runtime-door audit on de-RPC + self-mutations to the event log; no
  state-change audit type in v1"; §5's last sentence becomes "operational/state-change
  events sit on the domain's own event stream (origin-independent); authz + decision
  audit stay at the door." Note the effects-trail deferral to v2.
- Update HANDOVER + cm on WS4 completion.

---

## Out of scope (carry-forward)

- **WS5** — spawn-recovery hardening: inline-abort on Tx-B failure; reconcile stranded
  `Forking` lifecycles whose intents are aborted/missing. R11-bounded. (C2 only swaps the
  transport for the *existing* recovery kill; it does not change recovery semantics.)
- **WS6** — dual-adapter conformance; rev03 ordering test; merged shutdown-ordering;
  Linux assertion; tmux-capture hermeticity (ALP-2607); error-type-parity;
  poll_events socket-port loop-resilience.
- **Finer-grained read authz** (per-resolved-session resource for NamespaceGet/MailCheck/
  Wait instead of `ResourceSpec::default()`): deferred. The door gate closes the bypass;
  resource-fineness for reads is low-risk and not required for v1.
- **Type-level authorization witness** (`Authorized<Action>` token making `Downstream`
  verbs compile-enforced too): future hardening, not v1.

---

## Acceptance (WS4 whole)

1. All 7 previously-ungated verbs reject an unauthorized principal.
2. `authz_plan` is exhaustive (no `_`); adding a `SessionRpc` variant fails to compile.
3. A composed spawn produces exactly one audit row (session door).
4. spawn.rs uses only the `RuntimePort`; the runtime wire door remains for external
   clients (`compose.rs`).
5. `just check && just build && just test` green. `AuditRow`/`AuditDecision` unchanged.
