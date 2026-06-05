---
title: Littleorgans launch payload Runtime scout
type: projects
tags: [littleorgans, issue-35, issue-41, session, runtime, launch-payload]
summary: Source trace of the current Session to Runtime launch path and the persistence, recovery, compatibility, and test seams that constrain Issues 35 and 41
status: active
project: littleorgans
confidence: high
created: 2026-08-16
updated: 2026-08-16
---

# Littleorgans launch payload Runtime scout

## Scope and evidence

This report traces the implemented Session to Runtime launch path needed to
decide GitHub Issue #35 and prepare the later Issue #41 change.

The source was read at `main` commit
`5ace7db89dac7fe875edd626bf6222202f70b340`. `git status --short` was empty
before and after the scout. The scout changed no repository file. It did not
run tests because the original scope was read only.

Issue #35 asks the project to lock one optional opaque launch envelope,
ownership of its contents, compatibility with old pending intent JSON, and
the distinction between provider traffic capture and `lilo capture`. Issue
#41 then migrates the typed Session to Runtime contract and threads the chosen
payload through both Runtime adapters.

## Components found

| Component | Symbol and path | Current responsibility |
| --- | --- | --- |
| Root command router | `Cli::run` in `crates/lilo/src/cli.rs` | Routes `lilo run` and `lilo create session` to the Session application. Raw `lilo runtime spawn` follows a separate Runtime path. |
| Session CLI launch entry | `spawn_session` in `internal/session/app/src/cli/run.rs` | Resolves the namespace and directory, captures caller environment and shell resume data, constructs the Session `SpawnRequest`, and sends `SessionRpc::Spawn`. |
| Session wire request | `SpawnRequest` in `internal/session/core/src/proto/spawn.rs` | Carries user and Session input such as runtime, role, workspace, target text, environment, mounts, labels, and force. It has no `SessionId` and no opaque launch payload. |
| Session socket boundary | `send_request` in `internal/session/daemon/src/socket.rs` and `LilodRpc` in `internal/wire/src/lib.rs` | Serializes the Session request as `LilodRpc::Session` on the composed daemon socket. |
| Session dispatch | `DaemonState::handle_direct` in `internal/session/daemon/src/handler/dispatch.rs` | Dispatches `SessionRpc::Spawn` to `DaemonState::spawn`. |
| Session launch coordinator | `DaemonState::spawn` in `internal/session/daemon/src/handler/spawn.rs` | Mints `SessionId`, normalizes the request, resolves agent configuration, constructs `SpawnLaunch`, constructs the Runtime request, records Transaction A, calls Runtime, and completes Transaction B. |
| Internal launch command | `SpawnLaunch` in `internal/session/driver/src/driver.rs` | Carries the current Session execution values into `RuntimePort`. Its target is still text. It has no payload. |
| Shared Runtime mapper | `runtime_spawn_request` in `internal/session/driver/src/conv.rs` | Converts one `SpawnLaunch` into the Runtime `SpawnRequest`. Both Runtime adapters call this function. |
| Runtime port | `RuntimePort` in `internal/session/driver/src/port.rs` | Defines the Session owned execution interface. Spawn and several other methods still accept identifiers and signals as text. |
| In process adapter | `InProcessRuntime::spawn` in `internal/session/driver/src/in_process.rs` | Parses the textual `SessionId`, calls `runtime_spawn_request`, and invokes `RuntimeService::spawn` directly. |
| Socket adapter | `RtmdDriver::spawn` in `internal/session/driver/src/rtmd.rs` | Parses the textual `SessionId`, calls `runtime_spawn_request`, and invokes `RuntimeClient::spawn`. |
| Runtime wire request | `SpawnRequest` in `crates/lilo-rm-core/src/types/spawn.rs` | Carries the typed `SessionId`, typed `SpawnTarget`, runtime, isolation, environment, mounts, working directory, force, and shell resume data. It has no opaque launch payload. |
| Runtime client | `RuntimeClient::spawn` and `request_on_stream` in `crates/lilo-rm-client/src/lib.rs` | Wraps the Runtime request in `RuntimeRpc::Spawn` and `LilodRpc::Runtime`, then writes one JSON line to the socket. |
| Pending intent model | `PendingSpawnIntent` and `SessionSpawnIntent` in `internal/session/store/src/postgres/spawn_intents.rs` | Hold the Runtime `SpawnRequest` and Session draft used by the two transaction launch protocol and startup recovery. |
| Pending intent repository | `insert_pending_spawn_intent_with`, `list_pending_spawn_intents`, and `intent_from_row` in `internal/session/store/src/postgres/spawn_intents.rs` | Serializes the Runtime request to `spawn_request_json` and deserializes it during pending intent recovery. |
| Runtime domain entry | `RuntimeService::spawn` and `spawn_domain` in `internal/runtime/daemon/src/api.rs` | Runs preflight, builds a `LaunchSpec`, chooses a host or Docker backend, starts the shim, waits for `ShimReady`, and records Runtime lifecycle evidence. |
| Runtime launcher | `RuntimeLauncher::launch_spec` in `crates/lilo-rm-core/src/launcher.rs` and `BinaryLauncher` in `internal/runtime/launchers/src/lib.rs` | Converts the Runtime request into the command, environment, working directory, and shell resume values that form `LaunchSpec`. |
| Shim handoff | `SpawnCoordinator`, `launch_shim`, and `request_launch` in `internal/runtime/daemon/src/server/spawn.rs` and `internal/runtime/daemon/src/shim_socket.rs` | Holds `LaunchSpec` in memory while the shim starts. The shim retrieves that spec through `RuntimeRpc::ShimLaunch`. |
| Existing capture command | `DaemonState::capture` in `internal/session/daemon/src/handler/sessions.rs` and `CaptureRequest` in `crates/lilo-rm-core/src/capture.rs` | Resolves a Session and asks Runtime for a tmux pane snapshot. This is the current meaning of `lilo capture`. |

## Flow

### Normal session backed launch

1. `lilo` parses the command in `crates/lilo/src/main.rs`. `Cli::run` routes
   `lilo run` or `lilo create session` through the Session application.
2. `internal/session/app/src/cli/run.rs::spawn_session` creates the external
   Session `SpawnRequest`. It captures environment and shell resume data before
   sending `SessionRpc::Spawn` over the composed socket.
3. `DaemonState::handle_direct` dispatches the request to
   `DaemonState::spawn`.
4. Session mints `SessionId`, normalizes namespace and directory state, resolves
   agent configuration, and constructs `SpawnLaunch` with `spawn_launch`.
5. Session immediately calls `runtime_spawn_request`. The returned Runtime
   `SpawnRequest` is the durable launch representation. Session clones the same
   value into `PendingSpawnIntent` before any process side effect.
6. Transaction A authorizes the launch, inserts the pending Session spawn
   intent, and inserts Runtime `Forking` lifecycle evidence in one database
   transaction.
7. Session calls `RuntimePort::spawn` with the textual form of `SessionId` and
   `SpawnLaunch`.
8. Both adapters parse that text and call the shared `runtime_spawn_request`
   mapper again. `InProcessRuntime` passes the result directly to
   `RuntimeService::spawn`. `RtmdDriver` passes it through `RuntimeClient`,
   `RuntimeRpc::Spawn`, and `LilodRpc::Runtime` JSON serialization.
9. `spawn_domain` runs Runtime preflight. The selected launcher creates
   `LaunchSpec`. The backend prepares host or Docker execution and starts the
   shim.
10. Runtime stores `LaunchSpec` in `SpawnCoordinator`. The shim starts with a
    small bootstrap environment, connects back through `RuntimeRpc::ShimLaunch`,
    and receives the real `LaunchSpec`.
11. Runtime waits for `ShimReady`, records a Running lifecycle, and returns the
    lifecycle to Session. A session backed launch suppresses Runtime's normal
    Running event at this point.
12. Transaction B inserts the Running Session row, persists the Runtime Running
    lifecycle, and resolves the spawn intent. Session appends the Runtime
    Running event only after Transaction B commits.

### Persistence and recovery

`session_spawn_intents.spawn_request_json` contains the Runtime
`lilo_rm_core::SpawnRequest`. The external Session `SpawnRequest` and
`SpawnLaunch` are not persisted.

`insert_pending_spawn_intent_with` uses `serde_json::to_string` on the Runtime
request. `intent_from_row` uses `serde_json::from_str` on the stored text.
There is no intermediate compatibility codec and no schema version on the
intent row.

The daemon calls `SessionService::reconcile_pending_spawn_intents` before it
binds the composed socket. Recovery loads all pending rows and deserializes
their Runtime requests. For each valid row, it checks current Runtime status.
Recovery does not replay the stored spawn request.

Recovery completes Transaction B when Runtime already reports a Running
lifecycle. It aborts the intent when Runtime status fails, the lifecycle is
missing, or the lifecycle is not Running. A Transaction B failure during the
normal launch path terminates the started Runtime and aborts the intent. A
Transaction B failure during startup recovery leaves the intent pending so a
later daemon start can try completion again.

The repository does not delete resolved or aborted intent rows. Status updates
retain `spawn_request_json`, `session_draft_json`, and the timestamps. This
means an opaque payload stored in the intent table survives after resolution
unless a later cleanup policy removes the row.

### Old JSON missing field behavior

Serde rejects a missing struct field unless the field has a default or custom
deserializer. Existing optional Runtime request fields use
`#[serde(default, skip_serializing_if = "Option::is_none")]`. Existing
collection and boolean fields follow the same pattern with their zero values.
Tests in `crates/lilo-rm-core/tests/serde_snapshots.rs` prove both behaviors:
omitted defaulted fields decode, while omitted `cwd` and `target` fail.

The future payload field must therefore decode absence as `None`. A required
field would make a prechange pending intent fail in `intent_from_row`. Because
`list_pending_spawn_intents` collects every decoded row into one result, one
incompatible pending row would fail the whole list and stop daemon startup
before socket bind.

The Session request has a separate compatibility test in
`internal/session/core/src/proto/tests.rs`. That test proves old Session JSON
can omit fields added with serde defaults. It does not exercise the persisted
Runtime request, so Issue #41 needs a store or recovery test using literal old
`spawn_request_json`.

## Boundaries

### Session

Session owns the user request, `SessionId` creation, authorization, pending
intent, Session draft, namespace validation, and the two transaction protocol.
The current durable handoff is already the Runtime request created by
`runtime_spawn_request`.

Session is the documented future caller of Transport capture preparation. No
Transport port exists in the current source. The source therefore has no owner
that can create a capture lease today.

### Runtime port and wire

`SpawnLaunch` is the internal Session execution command. The Runtime
`SpawnRequest` is both the in process domain input and the public Runtime wire
payload. `runtime_spawn_request` is the single mapper between them. This is the
best existing seam for one unchanged payload copy.

The socket adapter adds JSON framing but does not otherwise transform the
Runtime request. The in process adapter and socket adapter converge on the
same mapper before their paths split.

### Runtime process launch

Runtime launchers receive the Runtime `SpawnRequest` and produce `LaunchSpec`.
The agent process receives `LaunchSpec`, not the original `SpawnRequest`.
`SpawnCoordinator` stores only `LaunchSpec` for the shim callback.

This creates an important decision boundary for Issue #35. "Runtime forwards
the payload unchanged" must name its endpoint. Copying the value only into the
Runtime request proves the Session to Runtime adapter handoff. Reaching the
shim or agent process requires either a payload field on `LaunchSpec` or a
domain neutral launcher conversion into command or environment data.

### Transport and Schedule

No `internal/transport` or `internal/schedule` implementation exists. The
architecture assigns payload contents and decoding to Transport. Session
attaches the value. Future Schedule records and forwards it without interpreting
provider, transcript, overlay, role, or harness semantics. Runtime executes the
result without interpreting Transport policy.

Transport Matters remains reference material. The monorepo must not import its
package boundaries, services, or launcher topology.

### Capture terminology

`lilo capture` currently means a Runtime tmux pane snapshot. Its path is
Session CLI to `SessionRpc::Capture`, Session authorization, `RuntimePort::capture`,
and Runtime's `CaptureRequest` and `PaneSnapshot` types. Provider traffic verbs
therefore belong under a future `lilo transport ...` namespace.

## Non-obvious things

1. Two public structs are named `SpawnRequest`. The Session type represents
   user intent. The Runtime type is the durable and executable request.
2. Session builds the Runtime request twice. It first creates the value stored
   in `PendingSpawnIntent`, then each Runtime adapter calls the same mapper again
   for execution. Today those values are deterministic copies. A future payload
   must come from stored `SpawnLaunch` data or another stable value so the
   persisted and executed requests cannot diverge.
3. Recovery keeps the stored Runtime request for decoding and evidence. It does
   not use that request to launch a process again.
4. Resolved and aborted intent rows remain in Postgres. Calling the table
   transient does not make payload retention transient.
5. Runtime never hands `SpawnRequest` to the agent process. The shim retrieves
   `LaunchSpec`. A shallow adapter test can pass even if the eventual Transport
   harness never receives the payload.
6. The socket JSON decoder will ignore undeclared unknown object fields under
   current serde defaults. A field that Runtime must forward needs an explicit
   typed slot. Relying on unknown field preservation would drop it.
7. Raw `lilo runtime spawn` bypasses Session intent and capture preparation. Its
   current constructors should produce an absent payload.
8. `docs/architecture/review/architecture-audit.sh` currently prints matches
   for the untyped Runtime boundary. Once Issue #41 removes every match, the raw
   `rg` command would exit with status 1 under `set -e`. The audit section must
   become an explicit failure check for reintroduced text fields.
9. `internal/session/driver/tests/port_conformance.rs` is 604 lines. It has room
   for a focused parity test but only 96 lines remain before the repository's
   700 line limit.

## Open questions

1. Does one envelope hold both the capture lease and all launch additions? The
   Issue #35 recommendation says yes. The current source provides no competing
   owner or persistence need that requires two fields.
2. What exact value representation defines "unchanged"? `serde_json::Value`
   preserves the semantic JSON value. An encoded string or raw JSON value can
   preserve a stronger representation contract. The decision must state which
   equality the tests prove.
3. Where does unchanged forwarding end for Issue #41: Runtime request,
   launcher input, `LaunchSpec`, shim, or agent process? The first Transport
   proof needs the last useful consumer named now.
4. Should the external Session `SpawnRequest` expose the field? Session can
   prepare capture only after minting `SessionId`, which happens inside
   `DaemonState::spawn`. `SpawnLaunch` is therefore the natural current
   attachment point. Issue #41 should state whether the external Session wire
   also carries an optional value for tests or future callers.
5. Can the envelope contain credentials or bearer material? Existing intent
   rows retain their JSON after resolve and abort. Issue #35 must state whether
   the stored value is safe at rest, redacted, encrypted, or subject to a new
   deletion policy.
6. Who validates `kind` and `version`? The architecture assigns payload decoding
   to Transport. Session, Schedule, and Runtime can preserve the envelope while
   rejecting only malformed outer structure.
7. Does an unknown envelope version fail capture preparation, fail launch, or
   launch without capture? The current architecture leaves capture failure
   policy open.
8. Should a Runtime wire capability or protocol version advertise the field?
   The monorepo moves crates in lockstep and has no external users, while the
   public Runtime client still has a serialized contract. Issue #35 should state
   whether absence alone is the compatibility mechanism.

## Reuse map for Issue 41

### Reuse directly

| Existing owner | Reuse |
| --- | --- |
| `crates/lilo-rm-core/src/types/spawn.rs` | Define the one domain neutral envelope beside Runtime `SpawnRequest`, or in a small sibling module reexported by `types.rs` and `lib.rs`. `lilo-rm-core` already depends on `serde_json`. No equivalent launch envelope exists in the workspace. |
| `internal/session/driver/src/driver.rs::SpawnLaunch` | Add one optional field using the shared envelope type. This keeps Session and Runtime from declaring duplicate payload structs. |
| `internal/session/driver/src/conv.rs::runtime_spawn_request` | Copy the optional field once. Both adapters already reuse this mapper. |
| `internal/session/daemon/src/handler/spawn.rs::spawn_launch` | Attach the stable optional value at the point where Session has minted `SessionId` and resolved agent configuration. |
| `internal/session/store/src/postgres/spawn_intents.rs` | Keep the current serializer and column. Adding the field to Runtime `SpawnRequest` automatically persists it in `spawn_request_json`. No migration is needed for an optional field. |
| `crates/lilo-rm-core/src/launcher.rs::RuntimeLauncher::launch_spec` | Use this only if Issue #35 requires the payload to reach `LaunchSpec` or the agent process. Keep provider interpretation out of Runtime. |
| `internal/runtime/daemon/src/server/spawn.rs::SpawnCoordinator` | Existing in memory `LaunchSpec` handoff can carry the value to the shim if `LaunchSpec` gains the shared optional field. |

### Migrate in the same change

Issue #41 already calls for typed `SessionId`, typed `SpawnTarget`, typed
Runtime signals, typed `ChildExit.session_id`, and deletion of the replaced
text API. The payload should travel in that same mapper migration. Retaining a
second payload mapper or compatibility wrapper would violate the repository's
DRY rule and the issue's same wave migration requirement.

All Runtime `SpawnRequest` and `SpawnLaunch` struct literals will need an
explicit absent value unless the implementation introduces a deliberate
constructor or default pattern. Raw Runtime CLI, examples, preflight tests,
launcher tests, Session daemon fixtures, and adapter fixtures are the main
literal groups.

## Quality map for Issue 41

| Proof | Best current location | Required assertion |
| --- | --- | --- |
| Envelope serde | `crates/lilo-rm-core/tests/serde_snapshots.rs` | Absent decodes to `None`; present kind, version, and opaque value round trip with the equality promised by Issue #35. |
| Session wire compatibility | `internal/session/core/src/proto/tests.rs` | Old Session spawn JSON remains valid if the external Session request gains the field. |
| Stored old JSON compatibility | `internal/session/store/src/postgres/spawn_intents.rs` tests | Insert literal prechange `spawn_request_json`, list pending intents, and assert the decoded payload is absent. This must test the real row decoder. |
| Recovery with old and new rows | `internal/session/daemon/src/service.rs` or `internal/session/daemon/src/handler/spawn/tests.rs` | Startup reconciliation completes old and new pending intents without replaying spawn or losing the payload value. |
| Shared mapper equality | `internal/session/driver/src/conv.rs` tests | `runtime_spawn_request` preserves the envelope exactly while completing the typed target and identifier migration. |
| Socket forwarding | `internal/session/driver/tests/rtmd_spawn.rs` | The `LilodRpc::Runtime(RuntimeRpc::Spawn)` observed by the mock server contains the exact envelope. |
| Adapter parity | `internal/session/driver/tests/port_conformance.rs` | In process and socket adapters receive the same typed launch command and produce the same Runtime request behavior. |
| Runtime launch endpoint | `internal/runtime/launchers/tests/conformance.rs` and shim launch tests | If the decision names the shim or process as the endpoint, prove `LaunchSpec` preserves the same envelope through `RuntimeRpc::ShimLaunch`. |
| Normal absent behavior | Existing Session spawn contract and Runtime integration tests | A launch with no payload keeps current command, environment, lifecycle, intent, and event behavior. |
| Architecture regression guard | `docs/architecture/review/architecture-audit.sh` | Fail when textual `SessionId`, textual `SpawnTarget`, duplicate payload types, or a provider specific Runtime field returns. |
| Full repository gate | Root `justfile` | Run `just check && just build && just test` after the implementation. Run the focused Issue #41 commands first for faster diagnosis. |

The focused commands named by Issue #41 remain the right acceptance set:

```sh
cargo test -p lilo-session-driver
cargo test -p lilo-session-driver --test port_conformance -- --ignored
cargo test -p lilo-integration-tests --test session_spawn_contract -- --ignored
just check && just build && just test
```

The implementation should also run the amended architecture audit. A generated
navigation refresh is necessary only if the change moves files, changes
workspace manifests, or refreshes generated surfaces.

## Files read

### Governance and decisions

- `AGENTS.md`
- `~/.mdx/_schema.md`
- GitHub Issue #35, `Lock the launch payload and capture terminology`
- GitHub Issue #41, `Keep launch values typed and add the opaque payload`
- `docs/architecture/system.md`
- `docs/architecture/session.md`
- `docs/architecture/runtime.md`
- `docs/architecture/schedule.md`
- `docs/architecture/transport.md`
- `docs/architecture/review/README.md`
- `docs/architecture/review/component-flow.md`
- `docs/architecture/review/data-boundaries.md`
- `docs/architecture/review/data-boundaries-findings.md`
- `docs/architecture/review/doc-code-drift.md`
- `docs/architecture/review/architecture-audit.sh`
- `NOTES/transport-integration.md`

### CLI and Session

- `crates/lilo/src/main.rs`
- `crates/lilo/src/cli.rs`
- `internal/session/app/src/cli/run.rs`
- `internal/session/app/src/cli/client.rs`
- `internal/session/app/src/compose.rs`
- `internal/session/app/src/cli/capture.rs`
- `internal/session/core/src/proto/spawn.rs`
- `internal/session/core/src/proto/tests.rs`
- `internal/session/daemon/src/socket.rs`
- `internal/session/daemon/src/handler/dispatch.rs`
- `internal/session/daemon/src/handler/spawn.rs`
- `internal/session/daemon/src/handler/spawn/tests.rs`
- `internal/session/daemon/src/handler/sessions.rs`
- `internal/session/daemon/src/service.rs`
- `internal/session/daemon/tests/handler/spawn_recovery.rs`
- `internal/session/store/src/postgres/spawn_intents.rs`
- `internal/session/driver/src/lib.rs`
- `internal/session/driver/src/driver.rs`
- `internal/session/driver/src/port.rs`
- `internal/session/driver/src/conv.rs`
- `internal/session/driver/src/in_process.rs`
- `internal/session/driver/src/rtmd.rs`
- `internal/session/driver/tests/rtmd_spawn.rs`
- `internal/session/driver/tests/port_conformance.rs`

### Runtime and persistence

- `internal/db/migrations/0001_unified_schema.sql`
- `crates/lilo-rm-core/Cargo.toml`
- `crates/lilo-rm-core/src/types/spawn.rs`
- `crates/lilo-rm-core/src/launcher.rs`
- `crates/lilo-rm-core/src/proto.rs`
- `crates/lilo-rm-core/src/capture.rs`
- `crates/lilo-rm-core/tests/serde_snapshots.rs`
- `crates/lilo-rm-client/src/lib.rs`
- `internal/wire/src/lib.rs`
- `internal/runtime/app/src/cli/spawn.rs`
- `internal/runtime/daemon/src/api.rs`
- `internal/runtime/daemon/src/service.rs`
- `internal/runtime/daemon/src/handler.rs`
- `internal/runtime/daemon/src/server.rs`
- `internal/runtime/daemon/src/server/state.rs`
- `internal/runtime/daemon/src/server/spawn.rs`
- `internal/runtime/daemon/src/backend.rs`
- `internal/runtime/daemon/src/shim_socket.rs`
- `internal/runtime/launchers/src/lib.rs`
- `internal/runtime/launchers/src/claude.rs`
- `internal/runtime/launchers/src/codex.rs`
- `internal/runtime/launchers/tests/conformance.rs`

## Best source evidence

The five most useful paths for the future change are:

1. `internal/session/daemon/src/handler/spawn.rs`
2. `internal/session/store/src/postgres/spawn_intents.rs`
3. `internal/session/driver/src/conv.rs`
4. `crates/lilo-rm-core/src/types/spawn.rs`
5. `internal/session/driver/tests/rtmd_spawn.rs`
