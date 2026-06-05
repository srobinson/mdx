---
title: Littleorgans Issue 41 typed launch contract
type: design
tags: [littleorgans, issue-41, session, runtime, launch-attachment]
summary: Complete Runtime spawn requests carry one optional redacted attachment from Session persistence through Runtime receipt.
status: active
project: littleorgans
confidence: high
created: 2026-08-17
updated: 2026-08-17
related: [littleorgans-issue41-typed-launch-contract-synthesis, littleorgans-launch-attachment-contract, littleorgans-issue41-typed-launch-flow]
---

<!-- markdownlint-disable-next-line MD025 -->
# Issue 41 typed launch contract

## Caller usage

Session prepares one typed launch, converts it once, persists a clone in
Transaction A, and moves the original request into the Runtime port. The clone
gives persistence and execution equal values without a second construction.

```rust
let id = SessionId::new();
let launch = spawn_launch(id, &request, agent_config.as_ref())?;
let runtime_request = runtime_spawn_request(launch);

let intent = PendingSpawnIntent::new(
    IntentId::new(),
    runtime_request.clone(),
    SessionDraft::new(&draft_session),
);

self.begin_spawn_intent(context, &request, &intent).await?;

let spawned = match self.runtime.spawn(runtime_request).await {
    Ok(spawned) => spawned,
    Err(error) => {
        let failure = runtime_spawn_failure(&error);
        self.abort_spawn_intent(id, &failure).await?;
        anyhow::bail!("runtime spawn failed: {failure}");
    }
};
```

Issue 41 has no Transport producer. Production `spawn_launch` sets
`launch_attachment` to `None`. Adapter and persistence tests construct `Some`
with one shared Session fixture. No Session protocol field, Transport port,
Schedule type, or child delivery path enters this change.

The first Transport slice may set `Some` after Identity authorization and
before complete request construction and Transaction A. That later slice must
resolve its own authorization and transaction ordering. Issue 41 carries the
field without producing it.

Adjacent Session callers keep ids and signals typed across the private port:

```rust
let capture = self
    .runtime
    .capture(session.id, request.scrollback_lines)
    .await?;

let signal = request
    .signal
    .parse::<RuntimeSignal>()
    .context("invalid runtime signal")?;
let exit = self
    .runtime
    .terminate(id, signal, Duration::from_secs(request.grace_secs))
    .await?;

let result = self
    .runtime
    .nudge(recipient_id, message, mode, timeout_ms)
    .await?;
let to = recipient_id.to_string();
```

The nudge response formats `to`. Formatting no longer feeds the Runtime port.

## Problem

At `8c211cb767554a3435ba6bfb8f27689473f9ce8c`, Session already constructs a
typed Runtime `SpawnRequest` before Transaction A and stores it as
`spawn_request_json`. The handler then formats the id and passes untyped launch
pieces through `RuntimePort`. Each adapter parses the id and constructs another
Runtime request. Target text is also parsed for shell resume and again during
request conversion. Capture, termination, nudge, and child exit repeat typed to
string to typed conversions.

Issue 41 adds one opaque launch attachment. Its persisted and executed values
must remain equal. The attachment value must remain absent from logs and from
every child launch representation.

## Exact types

### Published Runtime types

`LaunchAttachment` stays beside `SpawnRequest` in
`crates/lilo-rm-core/src/types/spawn.rs`.

```rust
use std::fmt::{self, Debug, Formatter};

use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Clone, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct LaunchAttachment {
    pub kind: String,
    pub version: u32,
    pub value: Value,
}

impl Debug for LaunchAttachment {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("LaunchAttachment")
            .field("kind", &self.kind)
            .field("version", &self.version)
            .field("value", &"[REDACTED]")
            .finish()
    }
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct SpawnRequest {
    pub session_id: SessionId,
    pub runtime: RuntimeKind,
    #[serde(default)]
    pub isolation: IsolationPolicy,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub image: Option<String>,
    #[serde(default)]
    pub env: Vec<LaunchEnv>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub mounts: Vec<MountSpec>,
    pub cwd: PathBuf,
    pub target: SpawnTarget,
    #[serde(default, skip_serializing_if = "is_false")]
    pub force: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub shell_resume: Option<ShellResume>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub launch_attachment: Option<LaunchAttachment>,
}
```

The new request field stays last. Present requests preserve the existing field
order before the attachment. Absent writers preserve the current JSON shape.
The attachment outer object rejects unknown members. The request keeps its
current unknown field behavior. `value` remains uninterpreted JSON.

`crates/lilo-rm-core/src/types.rs` and `src/lib.rs` reexport
`LaunchAttachment`. There is no constructor, validation error, opaque JSON
wrapper, version helper, or type in `lilo-common`. Transport will own attachment
meaning.

`lilo_rm_core::ErrorCode::InvalidTarget` remains unchanged. Runtime owns that
occupancy and target validation code.

### Private Session types

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SpawnLaunch {
    pub session_id: SessionId,
    pub runtime: lilo_session_core::RuntimeKind,
    pub isolation: IsolationPolicy,
    pub image: Option<String>,
    pub cwd: PathBuf,
    pub target: SpawnTarget,
    pub env: Vec<LaunchEnv>,
    pub mounts: Vec<MountSpec>,
    pub shell_resume: Option<ShellResume>,
    pub force: bool,
    pub launch_attachment: Option<LaunchAttachment>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChildExit {
    pub session_id: SessionId,
    pub runtime_pid: u32,
    pub exit_code: Option<i32>,
    pub transcript_path: Option<PathBuf>,
}

#[derive(Debug, PartialEq, Eq, Error)]
pub enum RuntimeFault {
    #[error("{message}")]
    SpawnConflict {
        kind: SpawnConflictKind,
        message: String,
    },
}
```

`SpawnLaunch.session_id` binds the id used for `LILO_AGENT_SESSION_ID` to the
id in the Runtime request. `SpawnLaunch.target` carries the one parsed target
used by shell resume inference and Runtime execution. The private port can no
longer receive malformed ids, targets, or signals.

Only the Session driver parse faults leave `RuntimeFault`:
`InvalidSessionId`, `InvalidTarget`, and `InvalidSignal`. Runtime error codes,
including `lilo_rm_core::ErrorCode::InvalidTarget`, stay intact.

## Exact signatures

### Session preparation and conversion

```rust
fn spawn_launch(
    id: SessionId,
    request: &lilo_session_core::SpawnRequest,
    agent_config: Option<&ResolvedAgentConfig>,
) -> Result<SpawnLaunch, SpawnTargetParseError>;

fn shell_resume(
    request: &lilo_session_core::SpawnRequest,
    target: &SpawnTarget,
    cwd: &Path,
) -> Option<ShellResume>;

pub fn runtime_spawn_request(launch: SpawnLaunch) -> RuntimeSpawnRequest;
```

`spawn_launch` calls `SpawnTarget::from_str` once. It returns the existing
`SpawnTargetParseError` directly. A fresh Session error type adds no value.
Invalid targets fail before Transaction A. `shell_resume` accepts the parsed
target. `runtime_spawn_request` is infallible and moves every owned field into
the complete Runtime request.

### Runtime port

```rust
pub type RuntimePortFuture<'a, T> =
    Pin<Box<dyn Future<Output = Result<T, RuntimeError>> + Send + 'a>>;

pub trait RuntimePort: Send + Sync {
    fn spawn(
        &self,
        request: RuntimeSpawnRequest,
    ) -> RuntimePortFuture<'_, SpawnedProcess>;

    fn reap_exited(&self) -> RuntimePortFuture<'_, Vec<ChildExit>>;

    fn capture(
        &self,
        session_id: SessionId,
        scrollback_lines: Option<u32>,
    ) -> RuntimePortFuture<'_, CaptureResult>;

    fn terminate(
        &self,
        session_id: SessionId,
        signal: RuntimeSignal,
        grace: Duration,
    ) -> RuntimePortFuture<'_, Option<ChildExit>>;

    fn nudge<'a>(
        &'a self,
        session_id: SessionId,
        content: &'a str,
        mode: NudgeMode,
        timeout_ms: Option<u64>,
    ) -> RuntimePortFuture<'a, NudgeResult>;

    fn status(
        &self,
        filter: StatusFilter,
    ) -> RuntimePortFuture<'_, Vec<Lifecycle>>;

    fn poll_events(
        &self,
        request: EventsRequest,
    ) -> RuntimePortFuture<'_, EventBatch>;

    fn doctor(&self) -> RuntimePortFuture<'_, RuntimeDoctorReport>;

    fn terminate_all(&self);
}
```

Spawn transfers one complete request. The selected adapter owns it until it
moves the request into the unchanged `RuntimeService::spawn` or
`RuntimeClient::spawn` API.

### Adapter implementations

`InProcessRuntime` keeps terminal deduplication, domain execution, and error
mapping:

```rust
fn spawn(
    &self,
    request: RuntimeSpawnRequest,
) -> RuntimePortFuture<'_, SpawnedProcess> {
    Box::pin(async move {
        self.locked_terminal_sessions().remove(&request.session_id);
        let outcome = self
            .runtime
            .spawn(request)
            .await
            .map_err(Self::domain_error)?;
        spawn_outcome(outcome)
    })
}
```

`RtmdDriver` implements `RuntimePort` directly:

```rust
fn spawn(
    &self,
    request: RuntimeSpawnRequest,
) -> RuntimePortFuture<'_, SpawnedProcess> {
    Box::pin(async move {
        self.locked_terminal_sessions().remove(&request.session_id);
        let payload = self.client.spawn(request).await.map_err(spawn_error)?;
        spawned_process(payload)
    })
}
```

Delete the inherent `RtmdDriver` methods for `spawn`, `capture`,
`reap_exited`, `terminate`, `nudge`, `status`, `poll_events`, and `doctor`.
Their trait wrappers duplicate the same interface. Keep inherent construction
and inspection methods such as `new` and `client`.

### Typed Session boundaries

Parse the external delete signal once before selected sessions are processed:

```rust
let signal = request
    .signal
    .parse::<RuntimeSignal>()
    .context("invalid runtime signal")?;

self.collect_target_sessions(&request.selector, |id| {
    self.delete_one(context, &request, id, signal)
})
.await?;
```

This placement rejects a bad signal before authorization or termination of any
selected session. Transaction B cleanup uses `RuntimeSignal::Term`. Capture,
nudge, and termination pass `SessionId` values directly. `persist_child_exit`
uses `child_exit.session_id` without parsing.

## Module map

<!-- markdownlint-disable MD013 -->

| Concern | Existing module | Change |
| --- | --- | --- |
| Attachment type and serde | `crates/lilo-rm-core/src/types/spawn.rs` | Add `LaunchAttachment`, manual redacted `Debug`, and the optional request field. |
| Runtime exports | `crates/lilo-rm-core/src/types.rs`, `src/lib.rs` | Reexport `LaunchAttachment`. |
| Runtime error code | `crates/lilo-rm-core/src/error.rs` | Keep `ErrorCode::InvalidTarget` unchanged. |
| Child delivery boundary | `crates/lilo-rm-core/src/launcher.rs` | Keep the attachment out of `LaunchSpec`; add a negative proof. |
| Private Session launch data | `internal/session/driver/src/driver.rs` | Type the id, target, exit id, and attachment. Remove only the three Session parse faults. |
| Session to Runtime conversion | `internal/session/driver/src/conv.rs` | Consume `SpawnLaunch`; remove id, target, and signal parsers. |
| Session Runtime interface | `internal/session/driver/src/port.rs` | Accept one owned Runtime spawn request and typed adjacent arguments. |
| In process adapter | `internal/session/driver/src/in_process.rs` | Forward the owned request without reconstruction. |
| Socket adapter | `internal/session/driver/src/rtmd.rs` | Forward through `RuntimeClient`; delete duplicate inherent verbs. |
| Session launch owner | `internal/session/daemon/src/handler/spawn.rs` | Parse target once, build once, persist a clone, execute the original. Production attachment remains `None`. |
| Other Session callers | `handler/sessions.rs`, `handler/messaging.rs`, `lifecycle.rs` | Remove string formatting and parsing at the internal boundary. |
| Durable intent | `internal/session/store/src/postgres/spawn_intents.rs` | Reuse `spawn_request_json`; add old, attached, malformed, and retained JSON proofs. |
| Runtime CLI | `internal/runtime/app/src/cli/spawn.rs` | Set `launch_attachment: None`; add no CLI flag. |
| Shared Session test value | `internal/session/test_support.rs` | Add one nontrivial attachment fixture with a redaction sentinel. |
| Typed boundary guard | `docs/architecture/review/architecture-audit.sh` | Reject restored string boundaries, adapter reconstruction, and child delivery. |

<!-- markdownlint-enable MD013 -->

The trait compile wave includes these five test doubles:

- `PollErrorThenBatchRuntimePort` in `internal/session/daemon/src/events.rs`
- `StaticStatusRuntimePort` in
  `internal/session/daemon/src/handler/spawn/tests.rs`
- `FaultingRuntimePort` in
  `internal/session/daemon/tests/handler/spawn_recovery.rs`
- `ConcurrentNudgeRuntimePort` in
  `internal/session/daemon/tests/mail_notify_concurrency.rs`
- `RecordingRuntimePort` in
  `internal/session/daemon/tests/mail_safety.rs`

Delete the local `parse_session_id` beside `FaultingRuntimePort`. Delete
`internal/session/driver/tests/port_conformance.rs::spawn_request`, which is a
second request builder inside the tests.

No new crate, production module, store column, Transport producer, Schedule
type, Session protocol field, child protocol field, environment key, or
protocol version belongs in Issue 41.

## Migration and deletion sequence

1. Add `LaunchAttachment`, manual redacted `Debug`, request serde, and exports.
   Add `launch_attachment: None` to every Runtime request literal, including
   `internal/runtime/app/src/cli/spawn.rs`. Add no CLI flag.
2. Change `SpawnLaunch.session_id`, `SpawnLaunch.target`,
   `SpawnLaunch.launch_attachment`, and `ChildExit.session_id`. Parse the target
   once in `spawn_launch` with the existing `SpawnTargetParseError`. Make
   `runtime_spawn_request` infallible, consuming, and complete.
3. Change `RuntimePort` in one compile wave. Update both adapters and all five
   named doubles. Delete the duplicate inherent `RtmdDriver` verbs. Delete the
   conformance request builder and the recovery double's local id parser.
4. Migrate every caller. Persist `runtime_request.clone()` in Transaction A and
   move `runtime_request` into `RuntimePort::spawn`. Pass typed ids and signals
   through capture, delete, nudge, cleanup, and child exit persistence. Parse a
   delete signal once before iterating selections.
5. Delete `parse_session_id`, `parse_runtime_signal`, obsolete `FromStr` and
   `RuntimeSpawnTarget` imports, string port parameters, adapter calls to
   `runtime_spawn_request`, response formatting used for Runtime calls, and
   malformed values injected through the former typed port seam.
6. Delete only `RuntimeFault::InvalidSessionId`,
   `RuntimeFault::InvalidTarget`, and `RuntimeFault::InvalidSignal` from the
   Session driver. Preserve `lilo_rm_core::ErrorCode::InvalidTarget` and all
   other Runtime validation and occupancy errors.
7. Add serde, redaction, adapter parity, old JSON recovery, malformed row,
   absent production behavior, and architecture audit proofs. A malformed
   present attachment must fail closed. No fallback decoder maps it to `None`.
8. Run focused packages, ignored Postgres contracts, the fail closed audit,
   `fmm generate && fmm validate`, the root gate, and `git diff --check` on the
   implementation tree.

No deprecated overload, compatibility trait, feature flag, serde alias, or
parallel builder remains.

## Tests and proof

### Core serde and redaction

Run `cargo test -p lilo-rm-core`.

Use an explicit sentinel in every value disclosure proof:

```rust
const ATTACHMENT_VALUE_SENTINEL_41: &str =
    "ATTACHMENT_VALUE_SENTINEL_41";

fn launch_attachment_fixture() -> LaunchAttachment {
    LaunchAttachment {
        kind: "issue41.test".into(),
        version: 1,
        value: serde_json::json!({
            "lease": "cap_lease",
            "nested": { "z": 1, "a": 2 },
            "secret": ATTACHMENT_VALUE_SENTINEL_41,
            "mixed": [null, true, 7, { "deep": "value" }]
        }),
    }
}
```

Core tests prove:

1. Nested arrays, objects, nulls, booleans, and numbers round trip.
2. JSON object member order does not affect semantic equality.
3. Unknown attachment outer fields fail.
4. Unknown fields inside `value` survive.
5. A missing request key decodes as `None`.
6. Writers omit `None`, preserving the current Runtime request JSON.
7. A present malformed attachment fails request deserialization.
8. `LaunchAttachment`, `SpawnRequest`, and `RuntimeRpc` debug output exclude
   `ATTACHMENT_VALUE_SENTINEL_41`.
9. The deserialize error for malformed outer metadata excludes the sentinel.

Keep core tests local to the core crate. Export no fixture from
`lilo-rm-core`. Session adapter and store tests share the one fixture in
`internal/session/test_support.rs`.

### Typed port and adapter parity

Run:

```text
cargo test -p lilo-session-driver
cargo test -p lilo-session-driver --test port_conformance -- --ignored
```

Build one complete `RuntimeSpawnRequest` with the shared attachment fixture.
Clone it once for the in process call and move the original into the socket
call. The mock socket server asserts equality on the full decoded request
before returning the same conflict. Both adapter results must map to the same
typed conflict fault.

Extend `rtmd_spawn.rs` so its mock server checks the full request, including
the attachment. Tests call `RuntimePort::spawn` because the inherent method is
gone. The owned request signature and direct `RuntimeService::spawn(request)`
call prove in process forwarding. The architecture audit rejects adapter
request reconstruction.

Retain the at most once reaping test and compare typed `SessionId` values. Move
malformed id, target, and signal cases to Runtime JSON decoding, Session spawn
parsing, and Session delete parsing.

### Persistence and recovery

Run:

```text
cargo test -p lilo-session-store
cargo test -p lilo-session-daemon --test handler spawn_recovery -- --ignored
```

Seed rows with SQL so `list_pending_spawn_intents` exercises
`intent_from_row`:

1. Store literal JSON from before Issue 41 without `launch_attachment`. Assert
   `None` after decode.
2. Store the shared attachment through the normal writer. Read it back and
   assert complete request equality. Resolve and abort separate rows, then
   query retained JSON and assert the attachment remains.
3. Seed a pending row with a malformed present attachment. Assert
   `SpawnIntentError::Json`. Include the value sentinel and assert its rendered
   error excludes the sentinel.
4. Seed the old request plus a Running Runtime lifecycle. Run startup
   reconciliation. Assert Transaction B creates the Session, resolves the
   intent, and a recording port receives zero spawn calls.

### Absent production behavior

Run with the configured Postgres test database:

```text
cargo test -p lilo-integration-tests --test session_spawn_contract -- --ignored
```

Extend the existing contract to query pending intent JSON from a normal
Session launch and assert the attachment key is absent. Keep the raw Runtime
spawn assertion that Session tables remain empty. In the Runtime app mock
socket test, inspect outgoing JSON before decoding and assert the key is
absent. Transaction A, Runtime execution, Transaction B, and event ordering
remain unchanged.

### Architecture audit

The audit fails if it finds any of these patterns in the Session driver:

```text
session_id: &str
session_id: String
target: String
signal: &str
parse_session_id
parse_runtime_signal
runtime_spawn_request( inside either adapter
```

A second guard rejects `launch_attachment` in `LaunchSpec`, shim types, child
arguments, child environment, files, and Docker launch plans. Use explicit
`if rg ...; then exit 1; fi` checks so zero forbidden matches succeeds.

Restore one forbidden declaration temporarily. Run the audit and observe a
failure. Restore the clean form and observe success. This proves the guard can
detect regression.

### Line caps and final gate

The baseline line counts are:

| File | Lines |
| --- | ---: |
| `internal/runtime/daemon/src/api.rs` | 643 |
| `tests/integration/tests/session_spawn_contract.rs` | 612 |
| `internal/session/driver/tests/port_conformance.rs` | 604 |
| `internal/session/daemon/src/handler/messaging.rs` | 553 |
| `internal/session/store/src/postgres/spawn_intents.rs` | 508 |
| `crates/lilo-rm-core/tests/serde_snapshots.rs` | 503 |
| `crates/lilo-rm-core/src/types/spawn.rs` | 460 |
| `internal/session/daemon/src/handler/spawn.rs` | 439 |

Deleting the three malformed port cases should fund the attachment parity case
in `port_conformance.rs`. Measure every changed file. Extract tests before any
file exceeds 700 lines.

Final implementation proof:

```text
docs/architecture/review/architecture-audit.sh
fmm generate && fmm validate
just check && just build && just test
git diff --check
```

## Red flag screen

<!-- markdownlint-disable MD013 -->

| Red flag | Judgment |
| --- | --- |
| Shallow module | Pass. The new record stays beside `SpawnRequest`. One owned request replaces two spawn parameters and adapter construction. No `PreparedSpawn` wrapper appears. |
| Information leakage | Pass. Runtime core owns outer serde. Transport meaning stays inside `value`. Session already persists the occupant launch spec. `LaunchSpec` remains process only. |
| Temporal decomposition | Pass. Session prepares one `SpawnLaunch`, converts it once, then persistence and execution share the resulting request. |
| Pass through method | Pass after deletion. The duplicate inherent `RtmdDriver` verbs leave. Each adapter still owns terminal deduplication, domain or wire execution, and error mapping. |

<!-- markdownlint-enable MD013 -->

## Synthesis decision

Candidate A, the complete Runtime request design, is the base. It scored 25 of
25. Candidate B scored 17 of 25. A removes the observed duplicate request
construction and makes equality structural. The handler builds once, persists
a clone, and moves the original into `RuntimePort::spawn`.

The synthesis grafts all eight judge items from candidate B:

1. Delete `port_conformance.rs::spawn_request` in the same wave.
2. Delete `FaultingRuntimePort`'s local `parse_session_id`.
3. Carry the five named Runtime port doubles through the compile wave.
4. Preserve `lilo_rm_core::ErrorCode::InvalidTarget`.
5. Include `internal/runtime/app/src/cli/spawn.rs` in the literal sweep, set
   `launch_attachment: None`, and add no CLI flag.
6. Use the verified baseline line counts to enforce the 700 line limit.
7. Return the existing `SpawnTargetParseError` directly from `spawn_launch`.
8. Keep the shared attachment fixture inside Session test support. Export no
   fixture from `lilo-rm-core`.

Candidate B's typed piece spawn loses because it calls
`runtime_spawn_request` once for persistence and again for execution. A pure
helper test cannot prevent the handler from passing different pieces on the
second call. The owned request prevents that divergence.

## Tradeoffs accepted

- We accept one explicit `SpawnRequest::clone` in exchange for an independently
  owned durable intent and execution request with semantic equality.
- We accept required `launch_attachment: None` updates at Rust literals in
  exchange for compiler checked constructor coverage.
- We accept a hard decode failure for a malformed present attachment in
  exchange for preserving the storage contract and avoiding silent data loss.
- We accept no production attachment in Issue 41 in exchange for keeping
  Transport policy and authorization out of this carrying change.

## Alternatives considered

`RuntimePort::spawn(SessionId, &SpawnLaunch)` keeps Session shaped pieces on
the port. It also preserves two request constructions and exposes their pairing
to callers. Its interface hides less and permits persist versus execute drift.

A borrowed complete request extends caller lifetimes or forces an adapter
clone because both Runtime calls need owned data. Ownership transfer marks the
execution handoff directly.

A `PreparedSpawn` wrapper would bind values without hiding policy. It adds a
shallow module beside the complete request Session already owns.

Persisting `SpawnLaunch` would change the meaning of `spawn_request_json` and
break the locked occupant launch spec contract.

## Open questions and risks

- Do any nested `Debug` or serde error paths reveal attachment `value`? The
  implementation must answer with sentinel tests across core, RPC, and store
  decode paths.
- Does the architecture audit reject every child delivery representation and
  adapter reconstruction without false positives? The temporary restoration
  proof must demonstrate both failure and success.
- Do the added proofs push any measured file past 700 lines? The implementation
  must measure after each test wave and extract tests before the limit.

No product or ownership decision remains open for Issue 41. Transport
production, Identity ordering for that producer, Schedule forwarding, and
attachment delivery remain later work.

## Next implementation step

Add `LaunchAttachment`, manual redacted `Debug`, Runtime request serde, exports,
and explicit `launch_attachment: None` fields first. Core tests then let the
compiler reveal the complete constructor inventory before the port migration.
