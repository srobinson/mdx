---
title: Littleorgans Issue 41 typed launch flow
type: research
tags: [littleorgans, issue-41, session, runtime, launch-attachment]
summary: Grounding of the current Session to Runtime launch flow and the exact Issue 41 migration boundary at repository commit 8c211cb.
status: active
project: littleorgans
confidence: high
created: 2026-08-17
updated: 2026-08-17
---

<!-- markdownlint-disable MD013 -->

## Overview

This report grounds Issue 41, "Keep launch values typed and add the opaque
payload," against repository commit
`8c211cb767554a3435ba6bfb8f27689473f9ce8c`. The checkout matched that commit
and was clean when checked. Issue 41 was open and its controlling decision,
Issue 35, was closed on 2026-08-17.

The current Session path already creates a typed Runtime `SpawnRequest` before
Transaction A. It then persists a clone, discards that request as the execution
value, converts `SessionId` back to text, and lets each Runtime adapter rebuild
the request. The same internal port accepts textual targets and signals. Issue
41 removes those text conversions and adds one optional `LaunchAttachment` to
the private Session launch carrier and the public Runtime request.

The governing contract places `LaunchAttachment` in `lilo-rm-core`. Its exact
fields are `kind: String`, `version: u32`, and `value: serde_json::Value`.
Session, future Schedule, and Runtime may deserialize and copy the outer
object. Transport alone interprets it. Runtime receives it on `SpawnRequest`
through `RuntimeService::spawn` and does not copy it into `LaunchSpec`, the
shim, child arguments, child environment, or files.

This is implementation grounding. The report labels current source facts,
locked requirements, and recommendations separately.

### Evidence basis

- Repository commit: `8c211cb767554a3435ba6bfb8f27689473f9ce8c`
- Current issue: `https://github.com/littleorgans/littleorgans/issues/41`
- Controlling decision: `https://github.com/littleorgans/littleorgans/issues/35`
- Governing contract: `docs/architecture/system.md:63-115`
- Session contract: `docs/architecture/session.md:45-72`, `:156-179`
- Supplied type and caller analysis:
  `/Users/alphab/.mdx/TMP/pstack/issue41-launch-attachment/how-types-gpt.md`
- Supplied adapter and persistence analysis:
  `/Users/alphab/.mdx/TMP/pstack/issue41-launch-attachment/how-adapters-grok.md`
- Runtime and Session source at the pinned commit

No runtime test was run for this research pass. The final section records the
implementation verification surface.

## Key Concepts

| Concept | Current owner | Meaning at the baseline | Issue 41 disposition |
| --- | --- | --- | --- |
| `SessionId` | Published `lilo-common` | Typed UUIDv4 join key | Use throughout the internal port, adapters, callers, and `ChildExit` |
| `SpawnTarget` | Published `lilo-rm-core` | Validated headless or tmux target | Use in `SpawnLaunch`; parse Session text once before the port |
| `RuntimeSignal` | Published `lilo-rm-core` | Typed HUP, INT, TERM, or KILL | Use in `RuntimePort::terminate` and both adapters |
| `LaunchAttachment` | Docs only at this baseline | Locked versioned envelope with opaque JSON value | Add to `lilo-rm-core` beside Runtime spawn types |
| Session `SpawnRequest` | Private `lilo-session-core` | External CLI, MCP, and Session RPC request; `target` remains text | Keep unchanged and attachment free |
| `SpawnLaunch` | Private `lilo-session-driver` | Session prepared process values; target is currently text | Use `SpawnTarget` and `Option<LaunchAttachment>` |
| Runtime `SpawnRequest` | Published `lilo-rm-core` | Complete Runtime wire and domain request | Add optional `launch_attachment` with locked serde behavior |
| `runtime_spawn_request` | Private `lilo-session-driver` | Converts Session launch values to Runtime request and parses target | Retain as one infallible typed conversion |
| `RuntimePort` | Private `lilo-session-driver` | Session execution interface | Remove textual ids and signals from all methods |
| `InProcessRuntime` | Private Session driver | Production adapter to composed `RuntimeService` | Forward typed values without parsing |
| `RtmdDriver` | Private Session driver | Socket and conformance adapter through `RuntimeClient` | Match the typed port in inherent and trait methods |
| `ChildExit` | Private Session driver | Session view of terminal Runtime evidence; id is currently text | Carry `SessionId` |
| `PendingSpawnIntent` | Private Session store | Holds complete Runtime request and Session draft | Reuse unchanged; the request gains the field |
| `spawn_request_json` | Existing Postgres column | Durable Runtime request for the two transaction protocol | Reuse without a migration or second column |
| `RuntimeService::spawn` | Private Runtime daemon | Domain receipt for the complete Runtime request | Remain the last attachment carrying boundary |
| `LaunchSpec` | Published `lilo-rm-core` | Concrete argv, env, cwd, and shell resume data | Keep attachment free |

Two Rust types share the name `SpawnRequest`. The external Session type is
`lilo_session_core::SpawnRequest`. The attachment belongs on
`lilo_rm_core::SpawnRequest`. Issue 41's phrase "Session launch request" is
resolved by the governing docs as private `SpawnLaunch`, after Session mints
the id. The external Session protocol remains unchanged.

## Complete current flow

<!-- markdownlint-disable MD029 -->

### Entry and composition

1. `lilo run`, `lilo create session`, or the agent MCP tool builds
   `lilo_session_core::SpawnRequest`. Its `target: String` defaults to
   `"headless"` in `internal/session/core/src/proto/spawn.rs:6-38`.
2. The client sends `LilodRpc::Session` to the one composed `lilod` socket.
   `internal/session/app/src/compose.rs:206-252` decodes the request and routes
   Session requests to `SessionService::handle_rpc`.
3. `SessionService::build` creates `InProcessRuntime` from the same composed
   `RuntimeService` in `internal/session/daemon/src/service.rs:68-94`.
   Production Session traffic therefore does not cross the Runtime socket.
4. `DaemonState::handle_direct` dispatches `SessionRpc::Spawn` to
   `DaemonState::spawn` in
   `internal/session/daemon/src/handler/dispatch.rs:56-72`.

### Session preparation and Transaction A

5. `DaemonState::spawn` mints `SessionId`, normalizes the namespace and
   directory, resolves agent configuration, and calls private `spawn_launch`
   in `internal/session/daemon/src/handler/spawn.rs:24-42`.
6. `spawn_launch` copies process fields, merges environment, removes caller
   supplied `LILO_AGENT_*`, and injects the Session id, role, and workspace.
   It keeps `request.target` as `String` at `spawn.rs:369-407`.
7. `shell_resume` separately attempts `request.target.parse::<SpawnTarget>()`
   at `spawn.rs:409-422`. A parse failure is ignored there and produces no
   inferred shell resume. This is the first current target parse.
8. `runtime_spawn_request(id, &launch)` constructs a typed
   `lilo_rm_core::SpawnRequest` at
   `internal/session/driver/src/conv.rs:22-39`. It parses the same target again
   and maps failure to `RuntimeFault::InvalidTarget`. This occurs before
   Transaction A, so an invalid target writes no pending intent.
9. Session builds a draft `Session` and `PendingSpawnIntent`. The intent owns a
   clone of that complete Runtime request at `handler/spawn.rs:43-68`.
10. Transaction A authorizes the spawn through Identity, inserts the pending
    intent, and inserts the Runtime `Forking` lifecycle through the shared
    Postgres transaction at `handler/spawn.rs:96-136`.

### Runtime execution

11. After Transaction A commits, the handler formats `SessionId` as text and
    calls `RuntimePort::spawn(&str, &SpawnLaunch)` at
    `handler/spawn.rs:70-79`. The Runtime request already built for the intent
    is not the value passed to the adapter.
12. `InProcessRuntime::spawn` parses the id, removes it from the terminal cache,
    calls `runtime_spawn_request` again, and passes the second Runtime request
    to `RuntimeService::spawn` at
    `internal/session/driver/src/in_process.rs:48-65`.
13. `RtmdDriver::spawn` performs the same id parse and request reconstruction,
    then sends `RuntimeRpc::Spawn` through `RuntimeClient` at
    `internal/session/driver/src/rtmd.rs:45-56` and
    `crates/lilo-rm-client/src/lib.rs:72-80`. This adapter is the socket and
    conformance route, not the production Session route.
14. `RuntimeService::spawn` calls `spawn_domain` at
    `internal/runtime/daemon/src/api.rs:40-47`.
15. `spawn_domain` runs preflight, derives `LaunchSpec`, lets the selected
    backend prepare it, begins the spawn, starts the backend, waits for
    `ShimReady`, and records `Running` at `api.rs:74-115`. Preflight may mutate
    concrete process request fields.
16. `RuntimeLauncher::launch_spec` copies argv, env, cwd, and shell resume only
    at `crates/lilo-rm-core/src/launcher.rs:62-89`.
    `SpawnCoordinator` stores `LaunchSpec`, keyed by `SessionId`, at
    `internal/runtime/daemon/src/server/spawn.rs:15-70`.

The current request path is:

```text
Session SpawnRequest, target String
  -> spawn_launch, target String
     -> optional target parse for inferred shell resume
  -> runtime_spawn_request parses target
  -> Runtime SpawnRequest A
     -> clone into PendingSpawnIntent and persist in Transaction A
  -> SessionId formatted as String
  -> RuntimePort
  -> adapter parses SessionId
  -> runtime_spawn_request parses target again
  -> Runtime SpawnRequest B
  -> RuntimeService::spawn
  -> LaunchSpec without request metadata
```

### Completion and failure

17. A Runtime failure aborts the pending intent and deletes the `Forking`
    lifecycle at `handler/spawn.rs:72-78`, `:237-255`.
18. A successful Runtime result supplies a `Running` lifecycle. Session derives
    the event, builds the final Session row from the stored draft and Runtime
    lifecycle, and revalidates the namespace.
19. Transaction B inserts the Session row, persists the Runtime `Running`
    lifecycle, and resolves the intent at `handler/spawn.rs:138-203`.
20. Session appends the Runtime `Running` event only after Transaction B
    commits at `handler/spawn.rs:205-209`.
21. If Transaction B fails during the ordinary spawn path, Session asks Runtime
    to terminate the orphan with textual id and `"SIGTERM"`, then marks the
    intent aborted and deletes its lifecycle at `handler/spawn.rs:212-255`.

### Exit and adjacent Runtime operations

- `terminal_child_exit` begins with typed `Lifecycle.session_id`, formats it
  into `ChildExit.session_id: String`, and `persist_child_exit` immediately
  parses it back to `SessionId` in
  `internal/session/driver/src/conv.rs:88-108` and
  `internal/session/daemon/src/lifecycle.rs:50-69`.
- Capture, delete, and nudge start with typed Session ids in their handlers,
  format them for `RuntimePort`, and let each adapter parse them again.
- Session delete accepts a textual external signal. The internal port and both
  adapters also keep it textual, then parse it to `RuntimeSignal` before the
  Runtime kill request.
- `wait_for_terminal` already takes `SessionId` and filters Runtime status with
  it in `internal/session/driver/src/port.rs:57-77`.

<!-- markdownlint-enable MD029 -->

## Exact caller and adapter inventory

### Production `RuntimePort` callers

| Method | Caller | Current text conversion or behavior |
| --- | --- | --- |
| `spawn` | `internal/session/daemon/src/handler/spawn.rs:70-79` | Formats minted `SessionId`; passes `SpawnLaunch` |
| `capture` | `internal/session/daemon/src/handler/sessions.rs:31-58` | Formats stored `session.id` |
| `terminate` | Session delete in `handler/sessions.rs:91-130` | Formats id; passes external signal text |
| `terminate` | Failed Transaction B cleanup in `handler/spawn.rs:212-234` | Formats id; passes `"SIGTERM"` |
| `nudge` | `internal/session/daemon/src/handler/messaging.rs:161-182` | Formats recipient id; retains the same text for response output |
| `reap_exited` | `internal/session/daemon/src/lifecycle.rs:36-47` | Signature unchanged; returned `ChildExit` must become typed |
| `status` | Pending intent startup reconcile in `handler/spawn.rs:257-323` | Already typed through `StatusFilter` |
| `status` | General reconcile in `internal/session/daemon/src/reconcile.rs:13-20` | Already typed |
| `status` | Expired event cursor reconcile in `internal/session/daemon/src/events.rs:94-100` | Already typed |
| `status` | `wait_for_terminal` in `internal/session/driver/src/port.rs:57-77` | Already typed |
| `poll_events` | Runtime event loop in `internal/session/daemon/src/events.rs:33-58` | Unchanged |
| `doctor` | `internal/session/daemon/src/polish.rs:123-133` | Unchanged |
| `terminate_all` | `SessionService::drop` in `internal/session/daemon/src/service.rs:124-129` | Unchanged |

### `RuntimePort` implementations

Production and conformance adapters:

- `InProcessRuntime`, `internal/session/driver/src/in_process.rs:48-182`
- `RtmdDriver`, `internal/session/driver/src/rtmd.rs:193-250`

Test doubles that must migrate in the same compile wave:

- `PollErrorThenBatchRuntimePort`,
  `internal/session/daemon/src/events.rs:152-217`
- `StaticStatusRuntimePort`,
  `internal/session/daemon/src/handler/spawn/tests.rs:241-328`
- `FaultingRuntimePort`,
  `internal/session/daemon/tests/handler/spawn_recovery.rs:117-239`
- `ConcurrentNudgeRuntimePort`,
  `internal/session/daemon/tests/mail_notify_concurrency.rs:70-161`
- `RecordingRuntimePort`,
  `internal/session/daemon/tests/mail_safety.rs:549-623`

`RtmdDriver` also exposes inherent `spawn`, `capture`, `terminate`, `nudge`,
`status`, `poll_events`, and `doctor` methods at `rtmd.rs:45-176`. Those methods
must change with the trait. Leaving textual inherent overloads would preserve
the replaced API.

Direct adapter calls that must compile against the new signatures live in:

- `internal/session/driver/tests/port_conformance.rs:29-307`
- `internal/session/driver/tests/rtmd_spawn.rs:72-88`
- `internal/session/driver/tests/rtmd_nudge.rs:14-44`

### Runtime `SpawnRequest` construction inventory

Adding a required Rust field makes the migration compile visible. Every Runtime
`SpawnRequest` literal must name `launch_attachment`. Ordinary Runtime paths and
fixtures use `None`. Attachment forwarding tests use one shared nontrivial
fixture.

Published protocol and client coverage:

- `crates/lilo-rm-core/tests/serde_snapshots.rs:27`, `:413`, `:431`
- `crates/lilo-rm-client/tests/typed_helpers.rs:162-175`

Runtime source and fixtures:

- `internal/runtime/app/src/cli/spawn.rs:66-78`
- `internal/runtime/app/examples/support/spawn.rs:20`
- `internal/runtime/app/tests/common/harness.rs:512-533`
- `internal/runtime/launchers/src/lib.rs:73-84`
- `internal/runtime/launchers/tests/conformance.rs:54-66`
- `internal/runtime/daemon/src/doctor.rs:45-56`
- `internal/runtime/daemon/src/backend.rs:197-210`
- `internal/runtime/daemon/src/docker_preflight.rs:319-332`
- `internal/runtime/daemon/src/handler/tests.rs:182-195`
- `internal/runtime/daemon/src/api.rs:629-642`
- `internal/runtime/daemon/src/shim_socket.rs:303-318`
- `internal/runtime/daemon/src/spawn_preflight/tests/helpers.rs:113-142`
- `internal/runtime/daemon/src/spawn_preflight/tests/mounts.rs:409-422`

Session bridge and persistence fixtures:

- `internal/session/driver/src/conv.rs:22-39`
- `internal/session/driver/tests/port_conformance.rs:558-571`
- `internal/session/store/src/postgres/spawn_intents.rs:491-506`
- `internal/session/daemon/src/service.rs:272-286`
- `tests/integration/src/lib.rs:102-114`

External Session `SpawnRequest` literals remain outside this field sweep.

### `SpawnLaunch` and `ChildExit` construction inventory

`SpawnLaunch` literals:

- Production builder: `internal/session/daemon/src/handler/spawn.rs:369-407`
- Socket adapter coverage: `internal/session/driver/tests/rtmd_spawn.rs:72-86`
- Conformance fixture: `internal/session/driver/tests/port_conformance.rs:544-556`

`ChildExit` literals:

- Production conversion: `internal/session/driver/src/conv.rs:88-108`
- Spawn handler test double:
  `internal/session/daemon/src/handler/spawn/tests.rs:286-302`
- Recovery test double:
  `internal/session/daemon/tests/handler/spawn_recovery.rs:195-212`

## Persistence and recovery behavior

`PendingSpawnIntent` already owns the complete Runtime request. The store
serializes it with `serde_json::to_string` into
`session_spawn_intents.spawn_request_json` at
`internal/session/store/src/postgres/spawn_intents.rs:276-300`.

Status changes update status and timestamps only. Pending, resolved, and
aborted rows therefore retain `spawn_request_json` at `spawn_intents.rs:303-360`.
The locked attachment contract prohibits credentials, API keys, and bearer
secrets in the retained value.

`list_pending_spawn_intents` selects every pending row and maps all rows through
`intent_from_row` at `spawn_intents.rs:259-273`. `intent_from_row` deserializes
the entire Runtime request at `:363-374`.

The locked serde behavior is:

- Missing `launch_attachment` decodes as `None`.
- Writers omit `None`.
- A valid attachment round trips by semantic JSON value equality.
- Unknown outer attachment members fail because the attachment uses
  `deny_unknown_fields`.
- Unknown members inside `value` survive because `value` is opaque JSON.
- A present malformed attachment fails the existing row decode. Since
  `list_pending_spawn_intents` collects the whole iterator, one malformed
  pending row fails the complete list.

No table, column, migration, fallback decoder, encryption layer, or cleanup
worker belongs in Issue 41.

At daemon start, `compose.rs:128-137` calls
`SessionService::reconcile_pending_spawn_intents` before accepting socket
traffic. Reconciliation:

1. Decodes all pending intents, including the complete stored Runtime request.
2. Asks Runtime for status with typed `StatusFilter::for_session`.
3. Aborts the intent if status fails, the lifecycle is missing, or the
   lifecycle is not `Running`.
4. Completes Transaction B from the stored Session draft and observed Running
   lifecycle when Runtime is already running.
5. Leaves the intent pending if that recovery Transaction B fails, so a later
   pass can retry.

Recovery does not call `spawn` again and does not resend the stored attachment
to Runtime. It proves that old and new request JSON can be decoded and retained
through process recovery. Adapter forwarding to `RuntimeService::spawn` is a
separate proof.

## Where Things Live

| Concern | Location |
| --- | --- |
| Typed ids | `crates/lilo-common/src/id.rs` |
| Runtime spawn, target, and kill types | `crates/lilo-rm-core/src/types/spawn.rs` |
| Typed Runtime signal | `crates/lilo-rm-core/src/types/runtime.rs` |
| Public Runtime reexports | `crates/lilo-rm-core/src/types.rs`, `src/lib.rs` |
| Runtime socket request envelope | `crates/lilo-rm-core/src/proto.rs` |
| Runtime client forwarding | `crates/lilo-rm-client/src/lib.rs` |
| Process only `LaunchSpec` | `crates/lilo-rm-core/src/launcher.rs` |
| External Session spawn protocol | `internal/session/core/src/proto/spawn.rs` |
| Production composition root | `internal/session/app/src/compose.rs` |
| Session service and production adapter selection | `internal/session/daemon/src/service.rs` |
| Session spawn protocol | `internal/session/daemon/src/handler/spawn.rs` |
| Session launch carrier and error types | `internal/session/driver/src/driver.rs` |
| Session to Runtime conversion | `internal/session/driver/src/conv.rs` |
| Runtime port contract | `internal/session/driver/src/port.rs` |
| Production adapter | `internal/session/driver/src/in_process.rs` |
| Socket adapter | `internal/session/driver/src/rtmd.rs` |
| Pending intent model and JSON store | `internal/session/store/src/postgres/spawn_intents.rs` |
| Runtime domain receipt | `internal/runtime/daemon/src/api.rs` |
| Runtime spawn coordinator | `internal/runtime/daemon/src/server/spawn.rs` |
| Typed boundary audit | `docs/architecture/review/architecture-audit.sh` |
| Governing launch contract | `docs/architecture/system.md` |

## Gotchas

1. The private Session port is the string layer. Runtime requests, Runtime
   status filters, and `wait_for_terminal` are already typed.
2. Target text is currently parsed three times on a successful Session launch:
   once opportunistically for shell resume, once before Transaction A, and once
   inside the selected adapter. A typed `SpawnLaunch.target` should also drive
   the shell resume decision.
3. Production uses `InProcessRuntime`. `RtmdDriver` remains required because it
   proves socket serialization and future out of process behavior.
4. The handler already builds the complete Runtime request before Transaction
   A. Passing `SessionId` plus `SpawnLaunch` to the port causes duplicate request
   construction and allows persisted and executed values to drift.
5. `RuntimeRpc`, Runtime `SpawnRequest`, `PendingSpawnIntent`, and `SpawnLaunch`
   expose nested `Debug`. A manual `LaunchAttachment` `Debug` implementation is
   the protection against logging `value` through those derives.
6. Manual `Debug` does not prove every decode error path is redacted. An error
   test with a sentinel inside `value` must prove the governing "errors never
   show value" contract before extra error mapping is added.
7. `LaunchSpec` is the structural delivery boundary. Adding the attachment to
   retain it would send metadata toward the child and violate the contract.
8. `RUNTIME_PROTOCOL_VERSION` and `LaunchAttachment.version` have different
   owners. Issue 41 does not bump the Runtime protocol or add a capability.
9. The external Session request remains text and attachment free. Raw
   `lilo runtime spawn` constructs the Runtime request directly and must set
   `launch_attachment: None` without gaining a new flag.
10. Current malformed id, target, and signal conformance tests call the textual
    `RuntimePort`. Typed signatures make those invalid values unconstructable.
    Preserve the acceptance coverage at raw socket JSON, serde, `FromStr`, or
    CLI input boundaries. Do not keep compatibility overloads.
11. `RtmdDriver` has both inherent methods and a trait implementation. Both
    signatures must migrate in the same change.
12. `architecture-audit.sh:39-44` runs a positive `rg` under `set -e`. It exits
    zero while forbidden strings exist and stops when they disappear. Issue 41
    needs an explicit forbidden pattern check whose success behavior is the
    inverse.
13. One malformed pending request prevents reconciliation of every pending
    intent. The governing contract specifies this fail closed behavior.
14. The largest direct files at the baseline are Runtime `api.rs` at 643 lines,
    the integration contract at 612, port conformance at 604, the intent store
    at 508, Runtime serde snapshots at 503, Runtime spawn types at 460, and the
    Session spawn handler at 439. Split a file before additions would cross 700
    lines. Issue 41 does not justify a speculative split below that threshold.

## Reuse Map

| Need | Existing owner | Reuse |
| --- | --- | --- |
| Optional omitted JSON field | `SpawnRequest.image` and `shell_resume` serde attributes | Apply the same attributes to `launch_attachment` |
| Typed target | `SpawnTarget` and `FromStr` | Parse once at the Session boundary and carry the value |
| Typed id | `SessionId` | Pass directly through port methods and `ChildExit` |
| Typed signal | `RuntimeSignal` | Parse external delete input once; use `Term` for internal cleanup |
| One Runtime request builder | `runtime_spawn_request` | Copy typed values and attachment without parsing |
| Dual adapter parity | `port_conformance.rs` and `rtmd_spawn.rs` | Compare complete requests through direct and socket routes |
| Durable request | `PendingSpawnIntent.spawn_request` and `spawn_request_json` | Extend existing serde only |
| Legacy missing field coverage | Existing serde tests for omitted optional fields | Add old pending JSON with no attachment key |
| Malformed row behavior | `intent_from_row` and `SpawnIntentError::Json` | Prove a present malformed attachment fails the list |
| Redacted nested logging | Manual `Debug` on the new attachment | Show kind and version; omit all of value |
| Semantic equality | `serde_json::Value: PartialEq` | Compare parsed values without lexical order requirements |
| Runtime receipt | `RuntimeService::spawn` and `spawn_domain` | Receive the complete request; keep `LaunchSpec` unchanged |
| Structural string guard | Existing `untyped_session_runtime_boundary` audit section | Convert it to a fail closed check |
| Process environment merge | Existing `upsert_launch_env` and Session `upsert_env` | Keep for typed `LILO_AGENT_*` only |

Do not reuse `LaunchEnv`, the external Session `SpawnRequest`, or
`RUNTIME_PROTOCOL_VERSION` as the attachment carrier.

## Quality Map with disposition recommendations

| Finding | Evidence | Disposition |
| --- | --- | --- |
| Persisted and executed Runtime requests are built separately | `handler/spawn.rs:41-72`; both adapters call `runtime_spawn_request` | Recommended: let `RuntimePort::spawn` accept the complete typed Runtime request by value. This exact signature is not locked by Issue 41. If typed pieces remain, add an equality proof and record why duplicate construction remains. |
| Port ids, target, signal, and exit id lose types | `port.rs:18-46`; `driver.rs:20-54`; `conv.rs:88-108`, `:171-180` | Required: migrate the complete trait, adapters, callers, and doubles in one wave. |
| Target has three parse sites | `spawn.rs:369-422`; `conv.rs:22-39`; adapter spawn methods | Required: choose one Session boundary parse and reuse the typed value for shell resume and Runtime conversion. |
| The attachment has one published cross process owner | Runtime request crosses `RuntimeRpc`; Session packages are private | Required: define and reexport `LaunchAttachment` from `lilo-rm-core`. |
| External Session request is excluded by governing docs | `system.md:87-102`; `session.md:65-72` | Keep unchanged. Add the field to private `SpawnLaunch`, not the Session protocol. |
| Attachment value may leak through nested debug | Current request and protocol derives use `Debug` | Required: manual redacted `Debug` plus a sentinel test. |
| Attachment could leak below Runtime receipt | `RuntimeLauncher::launch_spec` copies only process fields | Keep `LaunchSpec`, shim, child args, env, files, and Docker plans unchanged. Add structural assertions. |
| Old pending JSON lacks the field | Existing request shape at `8c211cb` | Required: `serde(default)` and a real recovery fixture with the key absent. |
| Malformed pending row can be silently weakened | Locked contract requires list failure | Required: prove `SpawnIntentError::Json`; do not map malformed attachment to `None`. |
| Adapter malformed tests depend on removed string API | `port_conformance.rs:192-265` | Relocate to raw wire and input decode boundaries. Delete the compatibility cases from typed port parity. |
| Obsolete Runtime fault variants may remain | `InvalidSessionId`, `InvalidTarget`, `InvalidSignal` exist for adapter parsing | Delete each variant after its last producer disappears. Do not add mappings solely to preserve it. |
| Audit currently rewards forbidden matches | `architecture-audit.sh:39-44` | Required: fail when a forbidden match exists and pass when the boundary is clean. Add a controlled restoration proof. |
| Raw Runtime spawn could accidentally acquire attachment behavior | Direct Runtime CLI literal | Keep `None`; preserve the test that raw Runtime spawn creates no Session rows. |
| Transport and Schedule have no implementation | Architecture and Issue 41 out of scope | Defer producers, provider parsing, capture policy, placement, and forwarding. Issue 41 creates the carrying seam only. |
| Tests may push large files over the hard limit | Baseline line counts in Gotchas | Measure after placement. Extract before any changed file exceeds 700 lines. |

## Deletion map

Delete or replace these items in the same migration:

- `parse_session_id` and `parse_runtime_signal` in
  `internal/session/driver/src/conv.rs:171-180`
- `std::str::FromStr` and the `RuntimeSpawnTarget` alias from `conv.rs` once the
  converter stops parsing
- `RuntimeFault::InvalidSessionId`, `InvalidTarget`, and `InvalidSignal` from
  `internal/session/driver/src/driver.rs:41-54` when no real boundary produces
  them
- Text `session_id` and `signal` parameters on `RuntimePort`
- Text parameters on `RtmdDriver` inherent methods
- Text parameters and parsing in `InProcessRuntime`
- `SpawnLaunch.target: String`
- `ChildExit.session_id: String`
- Session handler id formatting used only for spawn, capture, terminate, and
  nudge port calls
- The id parse in `persist_child_exit`
- Duplicate `runtime_spawn_request` calls inside adapters if the port accepts
  the complete Runtime request
- Port conformance cases that construct malformed ids, signals, or targets
  through the removed typed interface, after equivalent boundary tests exist
- Positive audit behavior that treats an untyped match as success

Do not add parallel string methods, deprecated overloads, `From<&str>` on the
port, feature flags, serde aliases, a generic payload alias, a second envelope,
a second persistence column, or attachment data in `LaunchEnv`.

## Verification surface

### Type, serde, and redaction

Run:

```sh
cargo test -p lilo-rm-core
```

Prove:

1. `LaunchAttachment` round trips arbitrary nested JSON.
2. Unknown outer fields fail.
3. Unknown fields inside `value` survive.
4. Runtime `SpawnRequest` omits `None` and defaults a missing key to `None`.
5. A present malformed attachment fails.
6. Semantic equality survives JSON object key reorder.
7. `Debug`, errors, CLI output, and projections contain no sentinel from
   `value`.

### Typed port and adapters

Run:

```sh
cargo test -p lilo-session-driver
cargo test -p lilo-session-driver --test port_conformance -- --ignored
```

Prove:

1. All valid calls use typed ids, target, and signal.
2. Both adapters forward an equal complete Runtime request with a nontrivial
   attachment.
3. `RtmdDriver` JSON round trip preserves semantic attachment equality.
4. In process and socket spawn conflict behavior remains equal.
5. Reaping stays at most once and `ChildExit` remains typed.
6. Malformed id, target, and signal coverage exists at raw socket or parser
   boundaries, without a string port API.

### Persistence and recovery

Run:

```sh
cargo test -p lilo-session-store
cargo test -p lilo-session-daemon --test handler spawn_recovery -- --ignored
```

Add and prove:

1. A seeded old `spawn_request_json` with no attachment key decodes as `None`
   and follows the existing recovery state rules.
2. A seeded request with a nontrivial attachment decodes with equal content and
   remains in the row through resolved or aborted status.
3. A present malformed attachment returns `SpawnIntentError::Json` from
   `list_pending_spawn_intents`.
4. Recovery does not respawn a pending intent.
5. Transaction B and event ordering remain unchanged.

### End to end absent behavior

Run with the configured Postgres test database:

```sh
cargo test -p lilo-integration-tests --test session_spawn_contract -- --ignored
```

Prove:

1. Session backed launch with no Transport producer behaves as before.
2. Two transaction persistence and event ordering remain intact.
3. Raw `lilo runtime spawn` keeps attachment absent and Session tables empty.

### Structural and repository gates

Run:

```sh
docs/architecture/review/architecture-audit.sh
fmm generate
fmm validate
just check && just build && just test
git diff --check
```

Inspect:

- No string id, target, or signal remains in
  `internal/session/driver/src` at the internal port boundary.
- Restoring one forbidden string pattern makes the architecture audit fail.
- `launch_attachment` appears on `LaunchAttachment`, private `SpawnLaunch`,
  Runtime `SpawnRequest`, conversion, persistence, and tests only.
- No attachment field or key appears in `LaunchSpec`, shim requests, child
  arguments, child environment, files, or Docker launch plans.
- Raw Runtime request JSON omits the key.
- No changed file exceeds 700 lines and no function exceeds about 150 lines.
- The final diff contains the Issue 41 migration only.

The implementation is complete only after all focused proofs and the root
`just` gate pass on the same tree.
