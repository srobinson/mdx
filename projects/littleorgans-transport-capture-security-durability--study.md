# littleorgans Transport capture security and durability study

Status: COMPLETE

## Executive verdict

littleorgans has a credible control plane foundation. Its composed daemon,
typed contracts, Postgres transaction seams, identity audit path, spawn intent
pattern, lifecycle reconciliation, isolated database fixtures, and CI gate are
worth retaining.

Transport capture does not exist in the current implementation. The workspace
has no Transport member, `LilodRpc` has only Session and Runtime variants, and
the unified schema has no capture tables. There is therefore no current capture
implementation to certify.

Governing finding: capture must be a native, fail closed `lilod` subsystem
whose durable readiness precedes every model agent spawn, with no invocation,
package, version, protocol, artifact, release, or runtime relationship to `tm`
or Transport Matters.

Several shared foundations need repair before capture uses them:

1. Bound and authenticate local RPC before allocating request sized memory.
2. Replace SessionId only shim callbacks with unforgeable launch capabilities.
3. Remove secret values from durable spawn intents and process arguments.
4. Replace or redesign the runtime JSONL event log before using its durability
   pattern.
5. Establish explicit file modes, retention, quotas, deletion, and audit outcome
   contracts.

These are pre-release changes. Compatibility should not preserve unsafe shapes.

## Audit baseline and limits

- littleorgans commit:
  `98d8928941b5b5db670ed73ed06af57f61dcfa0a`
- Pinned Transport Matters research commit, inspected with `git show` and
  `git ls-tree`: `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`
- littleorgans branch at initial inspection: `main`
- Later-only evidence: none. The clean final research checkout was `main` at
  `ed099336ebfa9e72da32ed547b29b932f077ccbd` and supplied no finding.
- Scope: read only source audit of security, privacy, durability, recovery,
  retention, audit, secret handling, isolation, and operations.
- Boundary: Transport capture is a mandatory first class littleorgans product
  capability. littleorgans will not invoke, package, port, version against, or
  depend on `tm` or Transport Matters.
- Method: static source, schema, test, workflow, and packaging inspection.
- Exclusions: no build, test, network, authentication, process launch, database
  mutation, or live fault injection was authorized.
- The littleorgans worktree already had a modification to `LESSONS.md`. It was
  preserved. Its current `LESSONS.md:18-19` records the corrected product
  boundary, but that working tree text is outside the commit named above.
- No content under the Transport Matters private notes area was read or used.

## Worker Status

No nested agents were spawned.

## Proven facts

### Foundation worth retaining

| Area | Fact | Evidence |
| --- | --- | --- |
| Composition | One `lilod` process builds a shared database, Runtime service, and Session service, reconciles pending spawn intents, then binds one socket. | `internal/session/app/src/compose.rs:run_core` |
| Wire boundary | The current daemon wire has exactly Session and Runtime variants. | `internal/wire/src/lib.rs:LilodRpc` |
| Capture absence | The workspace has no Transport member or dependency, and the unified migration has no Transport table. | `Cargo.toml:workspace.members`; `internal/db/migrations/0001_unified_schema.sql` |
| Peer identity | Unix peer credentials become a typed local UID principal. Unknown principal kinds are preserved and denied. | `crates/lilo-im-core/src/peer_creds.rs:extract`; `crates/lilo-im-core/src/types.rs:Principal`; `crates/lilo-im-core/src/audit.rs:AuditDecision::evaluate_local` |
| Transactional authorization | `authorize_in_tx` writes the authorization decision into the caller's Postgres transaction and fails closed when audit persistence fails. | `internal/identity/service/src/client.rs:IdentityClient::authorize_in_tx` |
| Spawn intent | Authorization, a pending spawn intent, and a Forking runtime lifecycle are committed together before external spawn. | `internal/session/daemon/src/handler/spawn.rs:begin_spawn_intent` |
| Spawn completion | Session, Running lifecycle, and resolved intent are committed together. A failed completion commit triggers runtime termination on the live path. | `internal/session/daemon/src/handler/spawn.rs:complete_spawn_intent` |
| Event consumption | Session applies runtime events and advances its cursor in one Postgres transaction. Poll and persistence failures retry without advancing the cursor. | `internal/session/daemon/src/events.rs:run_event_loop`; `internal/session/store/src/postgres/events.rs:apply_runtime_events_and_cursor` |
| Runtime recovery | Runtime performs startup and periodic liveness reconciliation and detects PID reuse when process start time is available. | `internal/runtime/daemon/src/reconcile.rs:reconcile_startup`; `host_lost_evidence` |
| Database safety | Database errors use a password free descriptor, SQL statement logging is disabled, and the pool has a configured ceiling and acquire timeout. | `internal/db/src/lib.rs:LiloDb::open_postgres`; `internal/db/src/config.rs:DbConfig` |
| Test isolation | Each database integration test can create, migrate, and explicitly destroy a unique Postgres database. | `internal/db/src/test_support.rs:TestDb` |
| CI | The required PR workflow runs Moon, ignored Postgres tests against a health checked service, and a binary doctor smoke test. | `.github/workflows/pr.yml:PR gate` |
| Release provenance | Cargo Dist is configured for GitHub attestations. | `Cargo.toml:workspace.metadata.dist` |

These facts support a native capture context. They do not prove capture
correctness because no capture context exists yet.

### Current littleorgans security and privacy blockers

#### Local RPC allocates before authentication

`handle_connection` reads a complete newline terminated JSON request before it
extracts peer credentials. The shared decoder uses unbounded `read_until` into
a new `Vec`. The accept loop has no connection semaphore or read deadline.

Evidence:

- `internal/session/app/src/compose.rs:handle_connection`
- `crates/lilo-rm-core/src/proto.rs:read_async_json_line`
- `internal/session/app/src/compose.rs:run_core`

A client that can reach the socket can hold connections without a newline or
send an arbitrarily large line before authorization runs. Capture traffic is
larger and more adversarial than current control requests, so this boundary
cannot be reused.

#### Same UID is full authority

Every matching local UID is allowed. Runtime shim callbacks receive the same
rule as operator calls. `ShimLaunchRequest` carries only `SessionId`, and the
reply contains `LaunchSpec`, including all environment values.

Evidence:

- `crates/lilo-im-core/src/audit.rs:AuditDecision::evaluate_local`
- `internal/runtime/daemon/src/identity.rs:authorize_shim_callback`
- `crates/lilo-rm-core/src/types/lifecycle.rs:ShimLaunchRequest`
- `internal/runtime/daemon/src/handler.rs:RuntimeRpc::ShimLaunch`
- `crates/lilo-rm-core/src/launcher.rs:LaunchSpec`

No per-launch secret, inherited descriptor, process identity binding, or
single-use claim is present. Host agents run as the operator UID by default.
The current boundary therefore cannot distinguish an operator, an intended
shim, and another same UID process.

#### Secrets are copied and retained

When the caller supplies no explicit environment, Session copies the caller's
environment. The denylist removes parent markers while retaining ordinary
credentials. The unit test explicitly expects `LILO_GITHUB_PAT` and
`ANTHROPIC_API_KEY` to survive.

The full runtime `SpawnRequest`, including `Vec<LaunchEnv>`, is serialized into
`session_spawn_intents.spawn_request_json`. Resolved and aborted intents are
updated in place rather than deleted, and no retention job exists. Secret
values can therefore remain in Postgres after the launch ends.

For Docker isolation, every environment value is also rendered as
`--env KEY=VALUE` in the Docker client argument vector.

Evidence:

- `internal/session/daemon/src/handler/spawn.rs:spawn_launch`
- `crates/lilo-rm-core/src/spawn_context.rs:capture_caller_env`
- `crates/lilo-rm-core/src/spawn_context.rs:denylist_drops_parent_markers`
- `crates/lilo-rm-core/src/types/spawn.rs:SpawnRequest`
- `internal/session/store/src/postgres/spawn_intents.rs:insert_pending_spawn_intent_with`
- `internal/session/store/src/postgres/spawn_intents.rs:update_spawn_intent_status_with`
- `internal/db/migrations/0001_unified_schema.sql:session_spawn_intents`
- `internal/runtime/daemon/src/docker_argv.rs:append_env_args`

Transport must observe credentials in transit when a provider protocol requires
them. It must never become their owner, copy them into control records, emit
them in logs, place them in process arguments, or expose them through general
RPC.

#### Local state has no enforced permission policy

`LiloHome::from_path` checks only for an empty path. Run, data, log, and socket
directories use ordinary `create_dir_all`. The socket helper removes any file
at the configured socket path before bind. The socket, pidfile, event log, and
headless logs receive no explicit production modes or ownership checks.

Evidence:

- `crates/lilo-paths/src/lilo.rs:LiloHome::from_path`
- `crates/lilo-sys/src/sys/unix/ipc.rs:prepare_socket`
- `internal/session/app/src/compose.rs:run_core`
- `internal/runtime/daemon/src/shim_socket.rs:launch_headless_shim`
- `internal/runtime/daemon/src/event_log.rs:open_append_file`

The resulting permissions depend on parent directories and process umask.
Capture artifacts cannot rely on those ambient conditions.

#### Existing log reads and writes are unbounded

Headless stdout and stderr are copied until EOF with no rotation or byte quota.
Session logs load the entire transcript with `fs::read` before applying the
optional tail limit. Omitting the limit returns the whole file.

Evidence:

- `internal/runtime/daemon/src/shim_socket.rs:copy_log_stream`
- `internal/session/daemon/src/polish.rs:read_transcript`

Capture needs streaming reads, bounded pages, per-session quotas, global quotas,
and backpressure.

### Current littleorgans durability and recovery blockers

#### Runtime event journal has unsafe error ordering

The event append path inserts the deduplication key and increments the sequence
before serialization and file writes. A write failure leaves those in-memory
mutations in place, so retry can be treated as a duplicate.

`sync_if_due` runs only during append. A single event below the batch threshold
can remain unsynced after the time threshold passes because no timer performs a
later sync.

Compaction removes old entries from the in-memory vector with `split_off`
before it creates, writes, syncs, and renames the replacement. Any later error
leaves memory changed. The replacement file is synced, but its parent directory
is not. Startup truncates a partial tail, while any malformed complete line
fails the entire read. The whole retained journal is loaded into memory, and an
event request returns every event after a cursor without a page limit.

Retention keeps at least 10,000 events and at least seven days. It has no byte
ceiling, so recent high volume can grow without bound.

Evidence:

- `internal/runtime/daemon/src/event_log.rs:append_recorded_event`
- `internal/runtime/daemon/src/event_log.rs:sync_if_due`
- `internal/runtime/daemon/src/event_log.rs:compact_if_due`
- `internal/runtime/daemon/src/event_log.rs:recover_partial_tail`
- `internal/runtime/daemon/src/event_log.rs:read_entries`
- `internal/runtime/daemon/src/event_log.rs:events_since`
- `crates/lilo-rm-core/src/proto.rs:EVENT_LOG_RETENTION_MIN_EVENTS`
- `crates/lilo-rm-core/src/proto.rs:EVENT_LOG_RETENTION_MIN_AGE_SECS`

This journal should be replaced or rebuilt before Transport events use it.

#### Spawn has ambiguous and orphaning windows

After a backend spawn succeeds, a ten second `ShimReady` timeout returns an
error without calling `cancel_spawn` or terminating the launched process.

During startup recovery, any Runtime status error causes Session to abort the
spawn intent and delete the lifecycle immediately. The error path does not
first prove that the runtime is absent or terminate a possibly live process.

Session commits a successful session before appending the runtime event. An
event append failure returns an error after durable success. The public Session
spawn request has no caller supplied operation key, so a client retry can
create another SessionId and process.

Evidence:

- `internal/runtime/daemon/src/api.rs:spawn_domain`
- `internal/runtime/daemon/src/server/spawn.rs:cancel_spawn`
- `internal/session/daemon/src/handler/spawn.rs:reconcile_pending_spawn_intent`
- `internal/session/daemon/src/handler/spawn.rs:complete_spawn_intent`
- `internal/session/core/src/proto/spawn.rs:SpawnRequest`

Capture launch must have an externally stable idempotency key, explicit
in-doubt states, and recovery that preserves ownership until absence is proven.

### Current audit, retention, isolation, and operations gaps

- Identity audit records authorization decisions. It does not record durable
  operation intent, effect outcome, an in-doubt result, payload digest, or
  recovery outcome. Evidence:
  `crates/lilo-im-core/src/audit.rs:AuditRow`;
  `crates/lilo-im-store/src/postgres/audit.rs:insert_audit_row_with`.
- The audit table is ordinary mutable Postgres data. No append-only database
  role, hash chain, signed checkpoint, export command, or retention rule is
  present. Evidence:
  `internal/db/migrations/0001_unified_schema.sql:identity_audit`.
- Session delete terminates a process and retains its session row and logs.
  Namespace deletion physically removes session and mail rows, while no
  corresponding log purge contract is visible. Evidence:
  `internal/session/daemon/src/handler/sessions.rs:delete_one`;
  `internal/session/store/src/postgres/namespaces.rs:delete_sessions_by_namespace`.
- Docker preflight checks daemon availability, image user, architecture, and
  mount shape. The launch does not set CPU, memory, PID, or file descriptor
  limits; it does not add `no-new-privileges`, capability dropping, a read-only
  root, or a network allowlist. Evidence:
  `internal/runtime/daemon/src/docker_preflight.rs`;
  `internal/runtime/daemon/src/docker_argv.rs:docker_run_base_argv`.
- Runtime doctor reports lifecycle, watcher, launcher, tmux, Docker, log, and
  reconciliation health. It has no capture readiness, storage backlog, disk
  pressure, corruption, retention, or secret hygiene signal. Evidence:
  `internal/runtime/daemon/src/doctor.rs:collect`.
- CI has strong compile, test, database, and smoke coverage. No repository
  security policy, threat model, CODEOWNERS, dependency audit, license policy,
  source scanner, or committed SBOM configuration was found. Release
  attestations are enabled. Evidence: `.github/workflows/pr.yml`; `Cargo.toml`.

## Inferences

The following conclusions derive from the proven source facts. They were not
validated through live exploitation or crash injection.

1. A slow or oversized local RPC can consume unbounded task and heap resources
   before peer credentials are checked.
2. A same UID process that learns a pending SessionId can race the intended shim
   for `ShimLaunch`, receive secret environment values, or submit forged ready
   and exit callbacks. The source exposes the mechanism; exploitability depends
   on timing and socket reachability.
3. A transient Runtime status error during pending intent recovery can discard
   durable ownership of a live process and leave it orphaned.
4. A lone runtime event can survive in process memory yet be lost on abrupt host
   failure because the elapsed sync threshold has no independent timer.
5. An event log compaction error can make live memory disagree with the file
   that will be read after restart.
6. A response lost after Session commit but before event append response can
   cause a caller to retry a spawn that already succeeded.
7. Default file confidentiality varies with umask and ancestor permissions.
8. Prompt bodies, tool arguments, tool results, provider metadata, and errors
   routinely contain credentials, personal data, source code, and proprietary
   context. All raw capture data must therefore be classified as sensitive.
9. Removing the external `tm` boundary eliminates a large version, packaging,
   health, credential, and failure coordination surface. It does not reduce the
   required capture fidelity or recovery guarantees.

## Reusable lessons from Transport Matters research

These are patterns and tests to reimplement under littleorgans ownership.
No source, package, runtime, or protocol should be ported.

### Keep the data model lessons

- A provider neutral immutable IR limits mutation and preserves unknown
  provider fields. Evidence:
  `api/src/transport_matters/ir.py:TextBlock`;
  `UnknownBlock`; `InternalRequest`.
- A narrow provider adapter contract separates matching, inbound parsing, and
  outbound serialization. Evidence:
  `api/src/transport_matters/adapters/base.py:ProviderAdapter`.
- Raw evidence must be stored before post-processing observers run. Observer
  faults must not corrupt the wire path. Evidence:
  `api/src/transport_matters/storage/exchange_sink.py:emit_to_index`;
  `emit_unparsed_exchange`.
- Historical reads must dispatch from compatibility facts recorded with the
  capture and fail when facts are missing. They must not guess with the current
  adapter. Evidence:
  `api/src/transport_matters/session/backfill.py:replay_transcript_run`.
- Transcript ingestion should consume complete records and advance its durable
  cursor only after the corresponding write completes. Evidence:
  `api/src/transport_matters/index/tailer.py:TailCursor`;
  `_PendingCommit`.
- Unknown or malformed provider shapes should produce deduplicated drift
  evidence with deterministic digests and explicit capture safety. Evidence:
  `api/src/transport_matters/drift_capture.py:WireDriftObserver`;
  `api/src/transport_matters/harnesses/drift_emitter.py:DriftEmitter.evidence_fields`.

### Keep the local security primitives

- Sensitive transport headers are identified case insensitively and redacted
  before metadata storage. Evidence:
  `api/src/transport_matters/transport_redaction.py:redact_transport_artifacts`.
- Secret files can use exclusive temporary creation, mode `0600`, file sync,
  and atomic replacement. Evidence:
  `api/src/transport_matters/atomic_io.py:write_atomic_bytes`;
  `_write_temp_at`.
- Directory traversal can use directory descriptors with `O_NOFOLLOW` rather
  than validate then reopen a path. Evidence:
  `api/src/transport_matters/secure_workdir.py:secure_chdir`.
- A local control socket can enforce a `0700` parent, `0600` socket, bounded
  reader limit, and request deadline. Evidence:
  `api/src/transport_matters/shared_proxy/control.py:SharedProxyControlServer`.
- Cross-plane fixtures should prove their corpus is nonvacuous and exercise the
  shipped seam. Evidence:
  `api/src/transport_matters/api/v1/test_acting_context_conformance.py:
  test_shared_corpora_are_non_vacuous_and_complete`;
  `_python_verify_result`.
- Static boundary tests should anchor their roots and fail closed on missing or
  unresolved paths. Evidence:
  `api/src/transport_matters/test_private_import_boundary.py:violations`;
  `www/packages/shell/src/testSupport/importGraphBoundary.test.ts`.

### Reject these research shapes

| Research shape | Reason to reject | Evidence |
| --- | --- | --- |
| Broad local file GET | Any absolute regular file can be returned, and the route is deliberately unguarded. | `api/src/transport_matters/api/v1/local_file_routes.py:local_file_raw` |
| Owner from query input | Session reads trust a caller supplied owner string rather than an authenticated principal. | `api/src/transport_matters/api/v1/session_routes.py:list_sessions` |
| Unguarded breakpoint mutation | Arm, disarm, release, re-audit, and drop routes have no authorization dependency. | `api/src/transport_matters/api/v1/breakpoint_routes.py` |
| Constant health | `/health` always returns ok without dependency readiness. | `api/src/transport_matters/main.py:health` |
| Ambient artifact modes | The main disk backend creates roots and exchange files without enforced `0700` and `0600` modes. | `api/src/transport_matters/storage/disk.py:DiskStorageBackend`; `api/src/transport_matters/storage/disk_helpers.py:DiskStorageFileOpsMixin._write_bytes` |
| Rename without full durability | Exchange activation uses temporary and backup directories, but file writes do not sync and directory renames do not sync parents. | `api/src/transport_matters/storage/disk.py:persist_exchange`; `api/src/transport_matters/storage/disk_helpers.py:_activate_exchange_dir` |
| Best effort projection | Wire projection failures become result objects and observer completion suppresses exceptions. There is no durable replay queue at this seam. | `api/src/transport_matters/wire_store_observer.py:WireStoreObserver`; `api/src/transport_matters/session/writer.py:submit_wire_exchange` |
| Effect before audit | Prompt, close, and interrupt perform effects before the audit write. The failure text explicitly says delivery was attempted. | `api/src/transport_matters/controlplane/service.py:prompt`; `close`; `interrupt`; `api/src/transport_matters/controlplane/action_policy.py:persist_action` |
| Credential ownership in capture | The broker performs provider refresh and local writeback. A remote rotation followed by failed local persistence is an in-doubt credential boundary. | `api/src/transport_matters/credential_broker.py:CredentialBroker.mint` |
| Polyglot product packaging | Python, FastAPI, Node, native gateway, browser bundles, and desktop artifacts create a broad release and attack surface unrelated to the minimum native capture context. | `api/pyproject.toml`; `packages`; `www`; `desktop` |

The research credential code does contain useful primitives: access-only
minting, keychain use, `0700` directories, `0600` files, readback checks, and
sanitized errors. Those lessons belong in Identity. Transport should receive
only a minimum lifetime credential handle or observe provider headers in
memory.

## Target requirements

### Ownership and topology

| Context | Required ownership |
| --- | --- |
| Session | Authorize and orchestrate the user launch. Own the stable operation key and `SessionId`. |
| Transport | Prepare, observe, persist, inspect, retain, and recover capture. Never decide what may launch. |
| Runtime | Launch, supervise, signal, and reconcile processes. Never parse provider traffic. |
| Identity | Resolve principals, authorize capture actions, own credential sources and key material, and write audit records. |
| `lilod` composition | Sequence the contexts through typed in-process ports and expose one bounded operator socket. |

Recommended native layout:

- `internal/transport/core`: typed IDs, immutable provider neutral IR, capture
  and exchange state machines, RPC, errors, redaction policy.
- `internal/transport/store`: Postgres metadata, durable outbox, immutable blob
  references, retention state, and recovery queries.
- `internal/transport/driver`: provider adapter and capture worker ports.
- `internal/transport/daemon`: worker supervision, proxy policy, ingestion,
  reconciliation, and operator service.

The worker should be an internal mode of the same signed `lilo` binary, such as
an undocumented `__transport-worker` entry, launched directly by Runtime. It
must not be a separately installed executable. A per-session worker limits
parser faults and binds each listener to one SessionId without trusting a
caller header.

### Mandatory launch sequence

1. Session authenticates the operator and commits a secret-free launch intent,
   capture intent, audit attempt, and Forking lifecycle in one transaction.
2. Transport allocates the capture root and starts a per-session worker with a
   one-use capability over an inherited descriptor or private socketpair.
3. The worker binds only loopback endpoints, validates its storage and provider
   policy, and returns Ready. Transport commits Ready before Runtime may spawn.
4. Runtime launches the agent with only the capture endpoint, SessionId, and
   minimum credential reference required by the adapter.
5. Session commits Running and Active states with one durable outbox event.
6. If capture loses readiness, provider traffic fails closed. Runtime terminates
   or pauses the agent according to a recorded policy. No direct provider
   fallback is permitted.

Raw diagnostic runtime spawn must obey the same rule when the target is a model
agent. A narrowly typed non-provider process can remain outside Transport.

### Capture state and idempotency

- Add typed `CaptureId` and `ExchangeId` only when corresponding stored fields
  exist. Continue to use `SessionId` as the platform join key.
- Accept a caller supplied operation key for launch retries. Enforce one result
  per principal and operation key.
- Persist explicit capture states with semantics equivalent to Preparing,
  Ready, Active, Draining, Complete, Failed, and Lost.
- Persist explicit exchange states with semantics equivalent to Request
  Staging, Request Durable, Forwarding, Response Streaming, Complete,
  Interrupted, and Delivery Unknown.
- Never infer that a provider did not receive a request after the forwarding
  boundary. Recovery must expose Delivery Unknown and must not automatically
  resend.
- Record provider request IDs, model, adapter revision, wire protocol revision,
  content encoding, byte counts, hashes, timestamps, and terminal cause.
- Preserve unknown provider fields in bounded raw evidence and drift records.

### Storage durability

- Treat raw bodies as immutable sensitive blobs. Store secret-bearing headers
  only in a redacted metadata form.
- Create the capture root with verified ownership and mode `0700`. Create files
  with `O_CREAT | O_EXCL | O_NOFOLLOW` and mode `0600`.
- Resolve paths relative to an opened directory descriptor. Reject symlinks,
  hard link surprises, nonregular files, owner mismatch, and cross-device
  activation.
- Write a temporary blob, flush, sync the file, atomically rename, then sync the
  parent directory before recording its digest in Postgres.
- Insert blob reference, exchange transition, and outbox event in one Postgres
  transaction. Unreferenced blobs are safe and reclaimed after a recovery
  grace period.
- For streaming responses, append and sync each bounded chunk batch before
  forwarding it downstream. Apply backpressure. A configured durability window
  must be explicit, measured, and surfaced if strict sync per batch is relaxed.
- Preserve interrupted partial response evidence. Never present it as complete.
- Derived IR, search, drift, and UI projections consume the durable outbox.
  Projection failure leaves a visible backlog and can be replayed.
- Bound every RPC page, event page, blob stream, parser input, decompressed
  representation, queue, connection pool, worker, and retention scan.
- Define behavior for disk full, inode exhaustion, read-only media, database
  outage, slow sync, and checksum mismatch. New provider traffic fails closed.

### Secret and privacy controls

- Identity owns refresh tokens, access token minting, capture encryption keys,
  and trust anchor signing. Transport receives the smallest lifetime handle.
- Clear inherited environments for capture workers and shims. Use explicit
  allowlists. Do not put secret values in argv, durable intent JSON, audit,
  tracing fields, crash reports, health output, or metrics.
- Never serialize `LaunchSpec.env` to a general RPC response. Deliver launch
  material through a one-use authenticated channel tied to the spawned process.
- Classify raw capture as restricted. Derived sanitized views are a separate
  class and must never silently replace authoritative evidence.
- Add content and header canaries to tests. Scan database rows, files, logs,
  process arguments, doctor output, and error responses for leaks.
- Encrypt restricted blobs with a versioned envelope. Identity supplies the
  per-install key provider. A deployment without an available key provider is
  not ready for raw capture.
- Validate upstream TLS. Restrict each adapter to its provider host, SNI, port,
  method, and protocol. Reject arbitrary CONNECT and proxy use.
- Install no global proxy and no global trust anchor. Generate scoped trust
  material and remove it through the same durable lifecycle.

### Authorization and audit

- Add explicit Identity actions for capture start, metadata read, raw read,
  export, delete, retention change, hold, and repair.
- Extract peer credentials before body read. Operator calls require the local
  operator principal. Worker calls require a one-use capability plus peer
  process binding.
- Record authorization decision and secret-free operation intent before effect.
  Record success, failure, or in-doubt outcome afterward. Recovery closes
  unresolved audit intents.
- Audit rows contain IDs, actor, action, resource, policy revision, operation
  key, payload digest, timestamps, outcome, and recovery evidence. They contain
  no captured content or credentials.
- Protect audit with a dedicated append-only database role or equivalent
  constraint, a hash chain, and signed checkpoints. Provide bounded query and
  export commands.
- Capture deletion must not delete the audit fact that deletion occurred.

### Retention and deletion

Retention policy must be locked before implementation. No infinite implicit
default is acceptable. The policy needs independent values for:

- raw body time and byte ceilings;
- derived view time and byte ceilings;
- operational log ceilings;
- audit retention;
- per-session, global, and free-space reserve quotas;
- legal hold;
- deletion grace and cryptographic erase behavior.

If no valid policy is configured, `lilod` readiness must fail before agent
launch. Retention uses a durable tombstone:

1. authorize and commit the delete or expiry intent;
2. deny new reads and exports;
3. stop or drain active writers;
4. remove blob references and cryptographically erase restricted content;
5. reclaim unreferenced files with symlink safe traversal;
6. record byte counts, failures, and outcome in audit.

Repeated cleanup is idempotent. `lilo transport retention plan`, `gc`, and
`verify` should expose dry run, execution, and integrity views.

### Isolation and resource control

- Capture worker environment is allowlisted, cwd is a non-workspace directory,
  standard input is closed, inherited descriptors are closed except explicit
  channels, and core dumps are disabled.
- Apply CPU, memory, process, file descriptor, spool, and connection ceilings.
- Add a platform isolation port. Linux should use namespaces, seccomp, and
  privilege dropping where supported. macOS should use a scoped sandbox
  profile. Doctor reports enforced, degraded, or unavailable.
- The worker can reach only its provider endpoints, private supervisor channel,
  and assigned capture directory. It cannot read the workspace, operator
  configuration, arbitrary local files, the main operator socket, or another
  session's capture.
- Docker isolation remains a Runtime policy. It does not substitute for
  Transport worker isolation or authority separation.

### Operations and release

- `lilo doctor` reports capture live, ready, and degraded states; active workers;
  database and blob consistency; outbox backlog; oldest backlog age; disk and
  inode headroom; quota pressure; retention lag; corrupt artifacts; adapter
  revisions; and last successful recovery.
- `lilo transport list`, `show`, `status`, `export`, `delete`, `retention`, and
  `verify` are native operator commands over typed `LilodRpc::Transport`.
- Every read and export is paged or streamed with byte limits. Raw output
  requires an explicit action and audit record.
- Structured logs carry correlation IDs and state transitions, never content or
  credentials. Stable counters and gauges have bounded label cardinality.
- Capture ships in the Rust lockstep release. Release artifacts, SBOM, source,
  protocol capabilities, and attestations all identify the same version and
  commit.
- Add dependency and license policy, vulnerability scanning, secret scanning,
  a threat model, security response policy, CODEOWNERS for capture and identity,
  and pinned CI action revisions.
- Add a structural gate that fails if production manifests, launchers, release
  scripts, or generated surfaces invoke or depend on `tm` or Transport Matters.

## Hostile workload matrix

| Workload | Current exposure | Required target behavior | Required proof |
| --- | --- | --- | --- |
| Foreign UID sends no newline | Request is read before peer identity. | Authenticate first, then enforce a short read deadline and frame limit. | Socket test with foreign peer where supported, plus timeout and allocation assertions. |
| Same UID agent calls operator RPC | Same UID receives operator authority. | Agent has no operator socket capability. Worker has only a scoped one-use channel. | Spawn a hostile sibling process and prove every operator and shim action is denied. |
| Oversized JSON RPC | `read_until` is unbounded. | Reject before allocation exceeds the configured frame ceiling. | Send ceiling minus one, ceiling, and ceiling plus one while measuring RSS. |
| Connection storm and slowloris | Accept loop has no semaphore or deadline. | Bound active and queued connections per principal and globally. | Saturation test proves bounded tasks, descriptors, memory, and recovery. |
| Huge request body | Capture does not exist; current logs and RPC are unbounded. | Stream to bounded spool with request durable before upstream send. | Production sized and over-limit bodies; upstream receives nothing on quota failure. |
| Infinite or very slow response | Existing headless logs copy until EOF. | Apply idle, total duration, byte, and spool limits with backpressure. | Slow server and never-ending stream terminate with typed partial evidence. |
| WebSocket frame flood | No native capture policy exists. | Bound frame size, frames in flight, exchange bytes, and parser work. | Millions of tiny frames keep memory and queue depth within limits. |
| Compressed expansion bomb | No native capture policy exists. | Preserve bounded wire bytes; cap decoded bytes and expansion ratio separately. | Crafted encodings stop parsing without losing bounded raw evidence. |
| Malformed JSON, SSE, or WebSocket event | No native capture policy exists. | Preserve bounded unknown evidence, emit drift, and keep proxy availability. | Fuzz and corpus tests prove no panic, hang, or silent drop. |
| Disk full or inode exhaustion | Current writers have no capture policy. | Stop forwarding before uncaptured traffic; retain typed failure and recover after space returns. | Fault filesystem at every create, write, sync, rename, and unlink. |
| Postgres unavailable or deadlocked | New daemon startup fails, but no active capture policy exists. | Do not start new flows. Bound active flow behavior and expose backlog or fail closed. | Kill, pause, and deadlock database connections at every state transition. |
| Symlink swap under `LILO_HOME` | Paths are reopened by name and modes are ambient. | Use directory descriptors, no-follow opens, ownership checks, and atomic activation. | Concurrent symlink and rename attacker cannot escape the assigned root. |
| Secret canary in headers, body, env, and errors | Spawn env is persisted and can enter argv. | Headers are redacted, raw is encrypted, and secret values never enter control data or telemetry. | Canary scan covers DB, files, logs, argv, metrics, doctor, export, and crash output. |
| Arbitrary provider host or CONNECT | No native capture allowlist exists. | Fail closed on host, SNI, port, protocol, and certificate mismatch. | DNS, Host, SNI, redirect, and CONNECT adversarial cases. |
| Many sessions and exchanges | Runtime event retention has no byte ceiling. | Per-session and global quotas with bounded indexes, pages, and metrics cardinality. | Soak test reaches every quota without unbounded RSS, DB, or disk growth. |
| Corrupt complete record or hash mismatch | Runtime event startup fails on a malformed complete line. | Quarantine the damaged unit, preserve evidence, continue healthy sessions, report degraded. | Corrupt every record and blob position, restart, verify scoped degradation. |
| Clock rollback or jump | Retention and timestamps use wall time. | Ordering uses monotonic sequences; wall time is evidence, not ordering authority. | Simulated backward and forward jumps preserve order and retention safety. |
| Adapter upgrade and historical replay | No native facts exist. | Record adapter and protocol revisions and refuse guessed replay. | Old fixtures replay with old codecs; missing revisions yield typed unsupported. |
| Retention races active write or export | No capture retention exists. | Tombstone first, coordinate leases, and make repeated cleanup idempotent. | Concurrent write, read, export, hold, delete, and restart matrix. |

## Crash matrix

| Crash point | Required recovery | Forbidden outcome |
| --- | --- | --- |
| Before launch intent commit | No worker, process, capture, or audit success exists. | External effect without durable ownership. |
| After intent commit, before worker start | Reconcile to retry worker start or abort visibly using the same operation key. | Silent intent deletion. |
| Worker bound, before Ready commit | Terminate or adopt only through the original one-use capability. | Orphan listener or cross-session adoption. |
| Ready committed, before Runtime spawn | Resume the same operation or close the worker and mark aborted. | Second worker or uncaptured spawn. |
| Runtime spawned, before Running commit | Probe repeatedly, bind proven process identity, then complete or terminate. | Delete ownership on one transient status failure. |
| Partial request before durable state | Preserve typed partial evidence or remove safe temporary data. Send nothing upstream. | Provider receives bytes before durable request. |
| Request durable, before upstream connect | Mark interrupted or continue only within the live connection. | Automatic duplicate send after restart. |
| During upstream write, before sent marker | Mark Delivery Unknown with digest and provider facts. | Claim unsent or replay automatically. |
| Partial response append | Recover the exact synced prefix as Interrupted. | Present partial response as complete. |
| Response chunk synced, before downstream write | Retry downstream within the same live flow or terminate with duplicate-safe framing. | Lose a chunk already reported as delivered. |
| Complete blob activated, before DB finalize | Recover by staged manifest and digest, then finalize idempotently. | Orphan complete evidence forever. |
| DB finalize and outbox commit, before projection | Replay projection from outbox. | Best effort loss or manual database repair. |
| Audit intent committed, before effect | Recovery decides whether to resume or abort and writes outcome. | Audit says success without effect. |
| Effect attempted, before audit outcome | Preserve In Doubt until external evidence resolves it. | Rewrite uncertainty as success or failure. |
| Event journal append, before sync | Sync before acknowledging append. | Consumer advances over volatile data. |
| Compaction temp write or sync | Old journal remains authoritative. | In-memory entries removed before durable replacement. |
| Compaction rename, before parent sync | Recovery accepts exactly one complete generation by manifest and digest. | Missing both generations. |
| Retention tombstone commit, before unlink | Reads remain denied and GC resumes. | Deleted content becomes readable again. |
| Blob unlink, before deletion outcome | Recovery derives remaining work from tombstone and writes byte counts. | Lost audit trail. |
| Capture worker exits while agent runs | Provider connection fails closed; supervisor records Lost and applies policy. | Direct provider fallback. |
| Daemon graceful shutdown | Stop accepting, drain or mark each flow interrupted, sync, close workers, then close DB. | Acknowledged capture left volatile. |
| Credential or key rotation boundary | Identity owns rotation and records version. Transport retries handle acquisition only. | Transport refreshes or writes owner credentials. |

## Acceptance gates

Implementation is not complete until all of the following are automated and
required:

1. Every crash matrix row has deterministic fault injection at each database,
   file, sync, rename, process, and socket boundary.
2. Every hostile workload row has a bounded resource assertion and a typed
   operator-visible result.
3. Request and response durability ordering is proven at the provider and agent
   boundaries under the locked policy.
4. Restart tests prove no silent loss, duplicate, orphan, or guessed result.
   Uncertainty remains typed Delivery Unknown.
5. Secret canaries cover control tables, intent JSON, audit, logs, argv,
   metrics, doctor, errors, and sanitized views.
6. Path tests prove ownership, `0700` directories, `0600` files and sockets,
   no symlink traversal, and safe custom `LILO_HOME`.
7. Authorization tests use real peer credentials and hostile same UID sibling
   processes. Fake authorizers alone are insufficient.
8. Shared nonvacuous corpora cover Claude HTTP, Codex HTTP and WebSocket,
   unknown shapes, malformed shapes, and pinned historical revisions.
9. Retention tests cover quotas, free-space reserve, hold, concurrent export,
   tombstone recovery, cryptographic erase, and audit survival.
10. Operator tests cover bounded commands and live, ready, and degraded output
    in text and JSON.
11. CI requires dependency, vulnerability, secret, source, SBOM, provenance,
    Postgres, fault injection, and platform isolation jobs.
12. Build and release inspection prove zero relationship with `tm` or Transport
    Matters.
13. The repository gate remains `just check && just build && just test`.
    Structural changes also run `fmm generate && fmm validate`.

## Reshape sequence

1. Repair foundations. Update stale governing docs at `CLAUDE.md:54-73` and
   `AGENTS.md:54-73`; bound and authenticate RPC; replace shim callback
   authority; remove secrets from intents and argv; replace the event journal;
   enforce path policy; add spawn idempotency.
2. Build the native skeleton. Add Transport core, store, driver, daemon, typed
   RPC, Identity actions, schema, outbox, blob store, worker capability,
   readiness, recovery, doctor, and zero dependency gate. Complete the matrices
   with a deterministic fake provider first.
3. Add provider fidelity. Implement Claude HTTP and Codex HTTP and WebSocket
   capture through one durable state machine, immutable IR, compatibility facts,
   unknown preservation, drift evidence, and sanitized projections. Gate every
   model agent launch on capture readiness.
4. Add data lifecycle. Implement native inspection, bounded export, retention,
   deletion, hold, integrity, repair, Identity key integration, operational
   signals, and security documentation.
5. Qualify release. Run every gate on Linux and macOS, inspect the SBOM and
   attestation, prove zero dependency from the built archive, and verify launch,
   failure, recovery, retention, and export contracts directly.

## Delete and rebuild decisions

| Surface | Decision |
| --- | --- |
| External `tm` launch and package design in governing docs | Delete. Replace with native `lilod` composition. |
| SessionId only public shim callback | Delete. Replace with a one-use process bound channel. |
| Full `SpawnRequest` JSON in durable intent | Delete. Replace with a secret-free recovery record. |
| Unbounded newline JSON RPC | Delete. Replace with bounded authenticated framing. |
| Current runtime event journal as a Transport foundation | Delete or completely rebuild with fault injected durability. |
| Ambient `LILO_HOME` modes | Delete. Replace with one enforced path policy. |
| Docker `--env KEY=VALUE` secret transport | Delete. Replace with protected files, descriptors, or provider-native secret handles. |
| Transport Matters Python, API, Node, browser, desktop, and credential ownership | Do not port. Retain research lessons only. |
| littleorgans transaction, identity, typed contract, reconciliation, test fixture, CI, and release provenance seams | Keep and strengthen. |

## Baseline checks

- Revalidated the littleorgans and pinned Transport commit IDs after the audit.
- Pinned Transport paths and symbols were checked with `git ls-tree` and
  `git show`.
- littleorgans remained on `main` with only the pre-existing `LESSONS.md`
  change. The later Transport checkout remained clean and supplied no evidence.
- Required sections and matrices are present. `rg` found no em dash, forbidden
  private note citation, trailing whitespace, or unresolved marker.
- The report stays below 700 lines and labels its source-only limits.
