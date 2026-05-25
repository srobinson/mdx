---
title: littleorgans — Runtime Port Boundary (Option D)
type: design-spec
status: consensus-locked — Claude + Codex clean sign-off (round 1, 2026-05-29)
date: 2026-05-29
author: Claude (superpowers brainstorming), hardened by MoE peer-consensus (Claude + Codex codebase-analyst)
governing: ~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md (rev03 D2, rev07 R11)
scope: internal/session, internal/runtime composed-daemon boundary; v0.8.0
---

# Runtime Port Boundary — Option D

> **Round-1 consensus (2026-05-29).** Both analyst panes independently verified the
> design against the live tree and signed off conditional on one merged 5-item set,
> applied below: (1) WS1 extracts a real runtime spawn domain method + exposes
> post-commit event publication; (2) §3 split into two labeled surfaces with a
> port→domain mapping; (3) §4 audit corrected to a door+domain split; (4) §3.1
> deletion list expanded to every composed self-dialer; (5) WS2 widened to all seven
> runtime-access sites. The earlier "event_log dedup-drop" item was **withdrawn** — it
> is correct backpressure, not a defect (UUIDv7 keys make every transition unique).

## 1. Problem

The composed `lilod` daemon is its own socket client. `SessionService` holds the
in-process `Arc<RuntimeService>` (`compose.rs:84` → `handler/state.rs:14`) yet its
background work reaches the runtime by dialling the daemon's own unix socket — and one
path (`spawn`) reaches it by RPC-ing itself in-process.

### 1.1 Verified consequences (adversarial pass + MoE consensus, 2026-05-29)

Confirmed real:

- **Loopback (seven composed sites).** Reaper `lifecycle.rs:40`; event watcher
  `events.rs:47` (and the `CursorExpired` reconcile at `events.rs:115`); reconcile
  status `reconcile.rs:18`; session `doctor` `polish.rs:138`; `capture` and
  `terminate` `sessions.rs:50,112`; `terminate_all` `service.rs:108` (stub at
  `server.rs:62`). Plus **`spawn`** `spawn.rs:71`, which is in-process but via
  `handle_rpc(RuntimeRpc::Spawn)` + authz — the Option-C "RPC to yourself" tax, not a
  socket dial, but still a path that must be collapsed to a direct domain call.
- **Shutdown ordering.** Background tasks tick through `runtime.shutdown()`,
  `remove_socket_file`, and `db.close()` (`compose.rs:123-142`); `SessionService::drop`
  aborts them only at service drop. session-matters did this correctly:
  `drop(events); drop(lifecycle); driver.terminate_all()` **before** teardown
  (`sm-daemon/src/server.rs:45-47`).
- **Authz "no bypass" violation.** 7 `SessionRpc` verbs dispatched without the
  identity context (`handler/dispatch.rs:49,51,54,57,69,71,80`). `NamespaceCreate` is a
  real unprivileged **mutation**; `List`, `NamespaceGet`, `NamespaceList`, `MailCheck`,
  `MailStopCheck`, `Wait` are read-only info leaks. The runtime RPC path **is** gated
  (`authorize_runtime_rpc`, runtime `handler.rs:133`).
- **Spawn recovery gaps (partial, vs rev07 R11).** Tx-B failure does not abort the
  intent inline (orphan window if the daemon then crashes); if `abort_spawn_intent`
  dies between the intent UPDATE and the lifecycle DELETE, a `Forking` lifecycle is
  stranded forever (reconcile scans only `pending`).

Refuted / withdrawn (not in scope): event_log lost-wakeup (correct
notified-before-check, `event_log.rs:201-207`); **event_log dedup-drop** (withdrawn —
`from_event` keys on `(session_id, {Running|Terminated|Lost})`; UUIDv7 makes each
transition unique, so skipping `notify` on a genuine duplicate is correct backpressure,
not data loss); cursor off-by-one; runtime `shutdown()` hang (reconcile task is
signal-responsive; test < 100ms); `subscribe_shutdown` late-subscriber loss (real
caller subscribes before any send); shim reap-on-shutdown (e68c301 works,
test-validated); partial-init socket leak (`prepare_socket` clears stale sockets
pre-bind); double-signal drain wedge.

Minor / YAGNI at single-operator local scale: unbounded connection accept, unbounded
mail/selector growth. Deferred, logged, not fixed in v0.8.0.

## 2. Locked intent this honours

- synthesis **rev03 D2**: "an in-process `RuntimeRpc`-shaped runtime service boundary
  (today's wire is the seam; **in-process it becomes a direct trait call**)";
  "**identity gating fronts every `lilod.sock` RPC** … no bypass."
- synthesis **rev07 R11**: Tx-A/spawn/Tx-B spine with phase-aware recovery via
  `session_spawn_intents`, and **d9 JSONL appended after the SQLite commit from
  committed state** (never commit authority). We do not change the spine; we close the
  recovery holes and preserve the post-commit publish contract.
- session-matters precedent: the session depended on a `SpawnDriver` **trait**
  (`Arc<dyn SpawnDriver>`, `sm-driver/src/driver.rs:92`) with `RtmdDriver` as one socket
  impl. The monorepo import flattened this to a concrete `Arc<RtmdDriver>`. Option D
  restores the port and adds the in-process adapter.

The synthesis is guidelines, not contract (Stuart, 2026-05-29). D honours rev03's
*intent* (no socket / no self-RPC in-process) while improving on its letter: the
session depends on a **domain port**, not on the wire enum.

## 3. Decision — Option D (hexagonal port over a real runtime domain API)

Rejected alternatives: **A** (one RpC-shaped method) abstracts the transport not the
capability; **B** (restore `SpawnDriver` verbatim) keeps the RpC seam implicit and risks
impl drift; **C** (transport trait + handle) treats `handle_rpc` as immovable and keeps
the "RPC to yourself" tax. **D inverts the dependency:** `handle_rpc` is the runtime's
RPC *front controller*, not its interface; the domain it dispatches into already exists
inside the runtime, merely private — except `spawn`, which must be **extracted** from
`handler.rs:135-173` (preflight, launcher dispatch, ShimReady wait, `record_running`).

**Two labeled surfaces, with an explicit port→domain mapping (this is what makes R1
enforceable):**

```
                      external lilo CLI clients
                                 │  unix socket (RuntimeRpc on the wire)
                                 ▼
   ┌──────────────────────────────────────────────────────────────┐
   │  WIRE ADAPTER: handle_rpc                                       │
   │  deserialize → authorize_runtime_rpc (+ decision audit, incl    │  (trust door)
   │  Deny/Error) → call domain API → serialize                      │
   └─────────────────────────────┬────────────────────────────────┘
                                 │ direct calls
   ┌─────────────────────────────▼────────────────────────────────┐
   │  RUNTIME DOMAIN API   (RUNTIME vocabulary, curated)            │
   │  spawn · subscribe_events · status · kill_runtime ·            │  (the core)
   │  kill_by_pid · nudge_runtime · capture · doctor ·              │
   │  append_event · drain_shims                                    │
   │  + state-change audit for mutating verbs (principal-threaded)  │
   └─────────────────────────────▲────────────────────────────────┘
              port→domain mapping │ (in-process adapter)
   ┌─────────────────────────────┴────────────────────────────────┐
   │  SESSION PORT: trait RuntimePort   (SESSION vocabulary)        │
   │  spawn · reap_exited · watch_events · status · terminate ·     │
   │  terminate_all · capture · doctor · publish_committed_event    │
   │   ├─ InProcessRuntime → maps each verb onto the domain API     │
   │   └─ RtmdDriver(socket) → serializes onto RuntimeRpc (split/v2)│
   └────────────────────────────────────────────────────────────────┘
   mapping:  reap_exited            = status + terminal-exit derivation
             terminate              = kill_runtime
             watch_events           = subscribe_events
             publish_committed_event= append_event   (post Tx-B, rev07 d9)
```

- **Runtime domain API** speaks runtime words; it is a curated, reviewed contract, not
  "everything `pub`." `spawn` is extracted into it; the rest are already-delegated
  `ServerState` methods made deliberately public.
- **`handle_rpc` demoted to one adapter** over that API. External clients enter here;
  this is where `authorize_runtime_rpc` and the **decision audit (incl. Deny/Error)**
  live (the trust boundary).
- **`RuntimePort`** speaks session words; the in-process adapter maps each port verb
  onto the domain API (no RPC enum, no serialization, no socket, no self-`handle_rpc`).
  The watcher's reconnect/backoff/cursor-expiry-on-disconnect machine **deletes itself**.
  The socket `RtmdDriver` keeps the same mapping over the wire for split/v2.
- **Shared conformance suite** runs both adapters against identical assertions → no
  drift.

This is the K8s shape the synthesis locked: kubelet has an internal API, the
apiserver-facing RPC is one adapter over it, co-located callers use the API directly.

### 3.1 Cleanliness mandate — delete the old path

This implementation **removes as much as it adds**; the experts enumerate orphaned code
per workstream. CLAUDE.md: delete old paths during migrations; no parallel
implementations; DRY, zero tolerance. The end state has **no socket dial and no
self-`handle_rpc`** for any composed runtime access.

Confirmed deletions / migrations (verified against the tree):

- `events.rs`: per-iteration `RuntimeClient::new`, `EventWatcher` connect,
  reconnect/backoff (`BACKOFF_*`, `next_backoff`), disconnect-driven cursor handling,
  and the `events.rs:115` `CursorExpired` socket reconcile. Keep event application +
  the genuine `CursorExpired` reconcile via the in-process API.
- `lifecycle.rs`: the `state.driver.reap_exited()` socket path; the `eprintln!`s.
- `reconcile.rs:18`: `RuntimeClient::status` self-dial → domain `status`.
- `polish.rs:138`: session `doctor` `RuntimeClient::doctor` self-dial → port `doctor`.
- `sessions.rs:50,112`: `driver.capture` / `driver.terminate` self-dials → port verbs.
- `spawn.rs:71`: `handle_rpc(RuntimeRpc::Spawn)` → direct domain `spawn`.
- `service.rs:108` / `server.rs:62`: resolve the `terminate_all` live stub via the port.
- `handler/state.rs` + builders + tests: remove `driver: Arc<RtmdDriver>` and **all
  `rtmd_socket_path` uses** once composed access leaves the socket.
- `driver/rtmd.rs`: delete `probe_session` and `validate_target` (zero composed callers,
  confirmed) or justify them in the socket-adapter conformance suite only. The socket
  adapter retains only what split/v2 needs; no dead verbs "for later."
- `RuntimeService`/`handle_rpc`: no duplicated dispatch once `handle_rpc` is a thin
  adapter over the domain API — API and wire path share one implementation.

Rule: if a verb exists on both the in-process adapter and `RtmdDriver`, its
verb→behaviour mapping lives in **one** place (the domain API or a shared helper). A
workstream that leaves a parallel runtime-access path is not complete.

## 4. Authz / audit placement (REVISED 2026-05-29 — Stuart's "no new audit type" + KISS)

Audit is emitted **by** the authz call: `IdentityClient.authorize` (`client.rs:51-61`)
and `authorize_in_tx` (`client.rs:63-85`) write an `AuditDecision` row. `AuditRow` is the
identity context's **authorization-decision** record (`decision`, `policy_id`,
`evaluation_trace`, `denial_reason`); a state change is not a decision, so forcing one in
would be a bounded-context leak. v1 therefore adds **no new audit type** —
`AuditRow`/`AuditDecision` stay frozen. The model is two pre-existing facts, kept
distinct:

- **Authorization decision** — owned by identity, written at every trust **door**
  (`handle_rpc` for runtime; the `SessionRpc` dispatch for session). WS4's gate makes the
  session door no-bypass, so every verb is decision-audited there, including
  `Deny`/`Error`.
- **Operational state change** — owned by runtime/session, written to the **event log**
  (`append_event`, `EventLog`). It already exists and is not the audit trail.

The spawn "audit regression" an earlier draft feared is **illusory**: composed
spawn/kill/nudge are already authorized and decision-audited at the **session** door
(`begin_spawn_intent → authorize_in_tx`; `delete_one → authorize(Kill)`;
`nudge_one → authorize(Nudge)`) before reaching runtime. The runtime-door audit for those
is **redundant**, so de-RPC'ing them onto the in-process port (WS4 C2) **removes a
double-audit, not a real one** — de-dup by construction, no "state-change" row required.

Self-initiated mutations (reaper, recovery-kill, reconcile) act as the daemon itself with
no principal and no door; they are operational and belong in the event log, not the
security audit. External/diagnostic callers (`lilo runtime spawn`) still enter the
runtime wire door, which keeps its decision audit. A durable, tamper-evident trail of
*effects* (vs decisions) is an enterprise/compliance posture, **deferred to v2**; if
built it is a runtime-context audit event, not a borrowed identity `AuditRow`.

This is R3 made concrete. WS4 owns it.

## 5. Forward-compatibility — the reusable pattern

D is the first instance of the platform's **bounded-context port pattern**, which
schedule / orchestrate / workflow each instantiate as they land:

> A bounded context exposes a narrow **domain API** in its own vocabulary. Its wire RPC
> is **one adapter** over that API (the trust door, where authz + decision audit live).
> Co-located consumers depend on a **domain port** in the consumer's vocabulary, with an
> in-process adapter (direct call, mapped to the domain API) and a wire adapter
> (serialise). One conformance suite proves the adapters equivalent. Operational /
> state-change events sit on the domain's own event stream (origin-independent); authz
> **and decision audit** stay at the door — no separate audit type per context.

Named here so later contexts copy the shape rather than re-litigate it
("forward-compatibility contract, not metaphor").

### 5.1 Error model across ports (DEFERRED — flagged 2026-05-29, address before the 2nd service)

Each port returns a context-specific error enum (`DriverError` for runtime). Its two
adapters mint it from different provenances: the in-process adapter stringifies live
domain errors (`DriverError::Runtime(String)`), the wire adapter carries the structured
transport error (`DriverError::Client(ClientError)`). Today this is benign because the
only **caller-matched** variant is `SpawnConflict`, and both adapters decode it through
the **same `conv` helper** (`conv::spawn_conflict`), so the one error consumers branch on
is identical across transports. Everything else is `.to_string()`'d, so the provenance
split is invisible.

The risk, which compounds per service: the "a new caller-matched variant must be decoded
on **both** adapters via `conv`" rule is a **convention, not enforced**. With one service
it is one thing to remember; with schedule / orchestrate / workflow each minting their own
port error enum, it is N chances to add a semantically-meaningful variant on only the wire
path — and the bug is silent, surfacing only on the composed (in-process) transport where
the error gets flattened to `Domain(String)` and a caller's `match` arm never fires.
Behavior then diverges by transport, which is exactly what the conformance suite is meant
to prevent.

Deferred remedy to design **before the second context-port lands** (do not build per-port
ad hoc): a shared error-model convention for bounded-context ports — each port error enum
explicitly separates (a) **semantic / caller-matched** variants, unified via `conv` and
**conformance-tested on both adapters**, from (b) **opaque provenance** variants
(`Domain(String)` / `Wire(transport-error)`) that no caller branches on. Make the
"decode-on-both-paths" rule mechanical rather than remembered (shared trait / macro, or a
conformance harness that fails when a caller-matched variant is reachable on only one
adapter). Until then, every new port must add a conformance test per caller-matched
variant (the `SpawnConflict` pattern) and must not branch on provenance variants.

## 6. Workstream decomposition (each → its own writing-plans plan → moe-local-batch)

- **WS1 — Runtime domain API.** **Extract** a runtime `spawn` domain method from
  `handler.rs:135-173` (preflight, launcher dispatch, ShimReady wait, `record_running`);
  curate + expose the rest (`status`, `kill_runtime`, `kill_by_pid`, `nudge_runtime`,
  `capture`, `doctor`, `drain_shims`); add `subscribe_events(since)` over the existing
  `EventAppender`/`EventLog::events_since_or_wait` (same cursor + Notify semantics as the
  wire path); expose `append_event` for post-commit publication. Demote `handle_rpc` to a
  thin adapter over the API. *Warroom.*
- **WS2 — Session RuntimePort + in-process adapter (all composed access).** Define
  `trait RuntimePort` (session vocabulary) + the port→domain mapping; `InProcessRuntime`
  adapter; migrate **all seven** composed runtime-access sites off the socket and off
  `handle_rpc`: reaper (`lifecycle.rs`), watcher + `CursorExpired` reconcile (`events.rs`),
  reconcile status (`reconcile.rs`), `doctor` (`polish.rs`), `capture` + `terminate`
  (`sessions.rs`), `terminate_all` (`service.rs`/`server.rs`), and `spawn`
  (`spawn.rs`: `handle_rpc` → direct domain). Share the lifecycle→`ChildExit` derivation
  (DRY with `RtmdDriver`). Keep `RtmdDriver` as the socket adapter; delete dead
  `probe_session`/`validate_target`. **May split into WS2a (reaper/watcher/reconcile) +
  WS2b (doctor/capture/terminate/terminate_all/spawn de-RPC)** given the site count and
  the 700-LOC/150-LOC limits. *Warroom.*
- **WS3 — Background-task lifecycle + shutdown ordering.** Start tasks after `bind`;
  stop them before `runtime.shutdown()`/socket-remove/`db.close()` (session-matters
  ordering); explicit ownership in compose/session; `eprintln!` → `tracing`. **Lands
  with WS2 in the same change, not as a separate optional PR** (current drops happen
  after teardown). *Warroom.*
- **WS4 — Authz "no bypass" + audit split (§4).** Gate all 7 `SessionRpc` verbs (choke
  point or threaded context); keep decision audit + denials at the door; add
  state-change audit at the domain for mutating verbs, principal-threaded, de-duped;
  key off verb not `Action`. *Warroom (security-sensitive).*
- **WS5 — Spawn recovery hardening.** Inline-abort on Tx-B failure; reconcile stranded
  `Forking` lifecycles whose intents are aborted/missing. Strictly within rev07 R11.
  *Small warroom or direct.*
- **WS6 — Conformance suite + acceptance tests.** Dual-adapter conformance (in-process ≡
  socket); rev03's locked `session-spawn → identity-audit → runtime-kqueue →
  session-record` ordering test; merged Stop/Ctrl-C/SIGTERM shutdown-ordering test; the
  preserved-audit assertion (in-process spawn still audited); Linux compile/behaviour
  assertion on the gated seams. *Direct.*

Ordering: WS1 → WS2(+WS3) ; WS4 and WS5 parallel after WS1 ; WS6 last. WS2 depends on
WS1 exposing `spawn`, `subscribe_events`, and `append_event`.

## 7. Linux (verify + don't-regress)

Already sound and cfg-gated: peer-creds (`SO_PEERCRED` Linux / `getpeereid` macOS,
`lilo-im-core/src/peer_creds.rs`), process-exit (`pidfd` Linux / `kqueue` macOS),
signals (`tokio::signal::unix`), build targets (linux gnu/musl listed). Constraint: the
port stays platform-agnostic; platform specifics stay behind the existing gated seams.
The in-process path **shrinks** platform surface (self-calls stop touching the socket
layer). WS6 adds a Linux assertion so this can't silently regress.

## 8. Risks

- **R1 — Runtime-surface discipline (load-bearing).** D widens the runtime's public API.
  Mitigation: the two-surface model (§3) keeps runtime vocabulary on the domain API and
  session vocabulary on the port, with an explicit mapping; `reap_exited`/`terminate_all`
  live on the **port**, never on `RuntimeService`. Review the domain API as a contract;
  the conformance suite pins behaviour.
- **R2 — Events subscription semantics.** `subscribe_events` sits over
  `EventAppender`/`EventLog::events_since_or_wait`; it must read committed state and honour
  the same cursor + Notify contract as the wire path (which bottoms out at the same
  method). Co-design with WS1.
- **R3 — Audit door↔domain split (§4).** Wrong split regresses in-process-spawn audit or
  drops denials. Resolved by §4; WS4 implements and WS6 asserts the preserved audit.

## 9. Acceptance

- rev03 locked tests: spawn-ordering and merged-shutdown-ordering integration tests.
- Boundary: **no socket dial and no self-`handle_rpc`** from any composed runtime-access
  site (assert via the in-process adapter); zero ENOENT on start/stop; clean teardown
  with no store-after-close.
- Dual-adapter conformance: in-process and socket adapters pass the same suite.
- Authz/audit: all `SessionRpc` verbs gated; decision audit incl. denials at the door;
  state-change audit at the domain for mutating verbs; in-process spawn still audited
  (no regression); d9 post-commit publish preserved.
- No orphaned code (§3.1): `fmm` dead-code / glossary sweep clean for touched modules;
  net diff **deletes** the loopback machinery (negative LOC in `events.rs`/`lifecycle.rs`);
  no second runtime-access path remains.
- `just check && just build && just test`; `fmm generate && fmm validate` after moves.
- Linux assertion green in CI.

## 10. Process

superpowers brainstorming → **peer-consensus warroom** (Claude + Codex, round-1
conditional sign-off applied here; clean re-read sign-off pending) → superpowers
writing-plans (per workstream) → moe-local-batch execution (Codex implements, Claude
reviews, one PR per workstream group).
