---
title: littleorgans Transport capture product boundary study
type: architecture-study
status: complete
repository: /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans
sha: 98d8928941b5b5db670ed73ed06af57f61dcfa0a
date: 2026-07-31
---

# littleorgans Transport capture product boundary

Status: COMPLETE

## Determination

Transport capture is a mandatory, first class littleorgans bounded context.
littleorgans owns its implementation, product contract, installation, readiness,
diagnostics, data policy, lifecycle integration, application surface, and release
qualification.

`tm` and the transport-matters repository are experimental research. The
littleorgans product has zero runtime, build, package, schema, storage, version,
release, or compatibility dependency on either one.

The four product contexts are:

| Context | Authority |
|---|---|
| Identity | Principals, authorization, policy, and security audit |
| Session | User intent, aggregate session state, orchestration, and reconciliation |
| Runtime | Agent process execution, shim, isolation, host evidence, and process lifecycle |
| Transport | Provider wire observation, capture lifecycle, durable capture evidence, fidelity, and capture read models |

The existing README already names these four contexts
(`README.md:16-32`). Current executable composition implements Identity, Session,
and Runtime only. Transport has no workspace member, service, store, protocol
variant, CLI namespace, path policy, doctor section, or release gate. The present
Transport claim is therefore documentation without a product implementation.

## Nonnegotiable boundary

The normal product path has this logical ownership order:

```text
operator
  -> Session authorizes and records composite intent
  -> Transport prepares capture and returns a typed binding
  -> Runtime launches the selected agent with that binding
  -> Transport proves capture readiness
  -> Session reports the session running
```

This is a logical sequence. It does not select a language, process count, proxy
technology, network topology, or storage engine.

The following invariants define the product:

1. Every session backed `lilo run` and `lilo create session` is captured by
   construction.
2. The agent cannot send provider traffic before capture is armed for its
   `SessionId`.
3. Session never reports `RUNNING` from Runtime readiness alone.
4. Capture failure cannot fall through silently to a direct provider path.
5. The same typed `SessionId` correlates Session, Runtime, Identity audit, and
   Transport metadata.
6. Provider conversation identifiers remain Transport metadata. They never
   replace `SessionId`.
7. Transport observes and records. It does not authorize the operator, select
   the agent, decide to spawn, own the agent process, or reconcile the product
   session.
8. Runtime owns the agent process and shim. It does not own provider exchanges
   or capture artifacts.
9. Session owns the composite workflow and product outcome. It does not own raw
   Transport storage internals.
10. Identity gates capture inspection, raw payload access, export, retention
    changes, and deletion.
11. Product shutdown preserves the final provider bytes before capture
    finalization and database close.
12. A littleorgans release is unshippable unless a clean installation proves a
    captured agent launch end to end.

Raw `lilo runtime spawn` is a diagnostic substrate path under the current
contract (`CLAUDE.md:123-126`). Its capture policy remains an explicit decision.
If an uncaptured diagnostic path survives, it cannot create a Session record or
present itself as a product run.

## The highest value existing seam

The current Runtime shim already phones home for a `LaunchSpec` before it starts
the agent:

1. Session persists a pending spawn intent, then calls `RuntimePort::spawn`
   (`internal/session/daemon/src/handler/spawn.rs:64-89`).
2. Runtime resolves the agent specific command through
   `RuntimeLauncher::launch_spec`, prepares the selected backend, and begins the
   spawn (`internal/runtime/daemon/src/api.rs:74-99`).
3. The shim starts with only the daemon socket, requests its real `LaunchSpec`,
   and has not started the agent yet
   (`internal/runtime/app/src/cli/shim.rs:35-48`).
4. The shim starts the agent and reports `ShimReady`
   (`internal/runtime/app/src/cli/shim.rs:46-61`).

This pre execution handoff is the clean product seam for mandatory capture.
Transport can prepare and prove a typed capture binding before Runtime permits
the shim to start the agent. The agent command remains owned by
`RuntimeLauncher`; capture does not require an external wrapper CLI.

The source already has two useful abstractions around this seam:

1. `RuntimePort` keeps Session orchestration independent of Runtime placement
   (`internal/session/driver/src/port.rs:18-55`).
2. `DaemonState` receives Runtime and Identity as ports
   (`internal/session/daemon/src/handler/state.rs:17-59`).

A Transport domain port belongs beside those boundaries. Its implementation
placement stays open.

## Product lifecycle semantics

### Start

The composite intent must durably identify:

1. `SessionId`
2. Requested runtime and execution target
3. Required capture policy
4. Capture preparation state
5. Runtime preparation state
6. Attempt and recovery evidence
7. Terminal failure reason

The minimum ordering contract is:

```text
authorized intent
  -> capture prepared
  -> runtime started
  -> capture armed
  -> product session running
```

Capture preparation failure leaves no agent process. Runtime failure releases
the prepared capture. A process that starts without capture readiness must be
terminated or held behind a gate before it can reach the provider.

The current spawn intent pattern is worth retaining. Transaction A writes the
authorization audit, pending intent, and forking lifecycle
(`internal/session/daemon/src/handler/spawn.rs:96-136`). Transaction B writes the
session and running lifecycle, then resolves the intent
(`internal/session/daemon/src/handler/spawn.rs:138-209`). The record must evolve
from a Runtime only intent into a composite Session, Transport, and Runtime
intent.

### Running

Runtime and Transport have separate observed state:

| Observation | Owner |
|---|---|
| Shim and agent process alive | Runtime |
| Provider capture ingress armed | Transport |
| Provider exchange durably recorded | Transport |
| Product session healthy | Session, derived from both contexts |

A capture fault during a live session must become explicit product state and
audit evidence. The exact policy, terminate, pause, bounded retry, or operator
intervention, remains open. Continuing as a healthy captured session is
forbidden.

Backpressure also needs a product contract. Transport cannot consume unbounded
memory or silently discard payloads. The system must choose bounded buffering
and an explicit outcome when durable storage cannot keep pace.

### Exit

Runtime terminal evidence does not prove capture completeness. Exit ordering
must support:

```text
agent process terminal
  -> final provider bytes drained
  -> capture manifest finalized
  -> completeness recorded
  -> Session terminal state reconciled
```

If finalization fails, Session must retain the Runtime outcome and expose the
capture as incomplete. Recovery must be idempotent after daemon restart.

### Shutdown

Current composition closes the listener, aborts connection tasks, stops Session
tasks, shuts down Runtime, removes the socket, and closes Postgres
(`internal/session/app/src/compose.rs:181-203`). Transport introduces a required
ordering constraint:

1. Stop accepting new product launches.
2. Quiesce or terminate live agents according to shutdown policy.
3. Drain and finalize their captures.
4. Stop Transport background work.
5. Close durable stores.

The precise service placement stays open.

## Reuse map

| Current seam | Evidence | Reuse | Required reshape |
|---|---|---|---|
| Typed identifier family | `crates/lilo-common/src/id.rs:22-96` | Keep the macro and `SessionId` join key | Add a Transport owned identifier only when an actual persisted field requires one |
| Identity action registry | `crates/lilo-im-core/src/types.rs:124-177` | Keep exhaustive actions and typed resources | Add Transport resource kinds and read, raw read, export, verify, retention, and delete actions |
| Session authorization plan | `internal/session/daemon/src/handler/authz.rs:13-49` | Keep compile time exhaustive RPC classification | Classify every Transport surface and fix vocabulary that cannot express the real action |
| Session composite intent | `internal/session/daemon/src/handler/spawn.rs:64-209` | Keep transactions around external side effects and restart reconciliation | Record capture preparation, readiness, cleanup, and finalization |
| Session domain port pattern | `internal/session/driver/src/port.rs:18-55` | Keep domain altitude and placement independence | Add a Transport boundary with domain faults and typed outcomes |
| Session state injection | `internal/session/daemon/src/handler/state.rs:17-59` | Keep port injection into orchestration state | Promote composition so Session receives Identity, Runtime, and Transport boundaries rather than constructing dependencies internally |
| Runtime launcher registry | `crates/lilo-rm-core/src/launcher.rs:62-89`; `internal/runtime/launchers/src/lib.rs:43-69` | Keep agent specific argv resolution | Keep capture integration after command resolution and before execution |
| Shim launch handoff | `internal/runtime/app/src/cli/shim.rs:35-61` | Keep as the pre execution gate | Require an authenticated capture binding and capture readiness before child traffic |
| Runtime backend seam | `internal/runtime/daemon/src/backend.rs:14-53` | Keep host versus isolation preparation | Apply the capture binding consistently for every backend |
| Runtime lifecycle | `crates/lilo-rm-core/src/types/lifecycle.rs:53-119` | Keep process evidence owned by Runtime | Do not overload it with Transport state |
| Runtime event consumption | `internal/session/daemon/src/events.rs:33-109` | Keep cursor, replay, and reconcile behavior as a pattern | Give Transport its own events or durable observations; Session composes outcomes |
| Shared database handle | `internal/db/src/lib.rs:18-59` | Keep one composed ownership and transaction boundary for metadata if selected | Do not put large raw payloads into Postgres by default; storage remains an open decision |
| Path policy | `crates/lilo-paths/src/lilo.rs:38-110` | Keep `LILO_HOME` as the only product root | Add authored Transport paths only after the artifact layout is decided |
| Daemon protocol envelope | `internal/wire/src/lib.rs:3-8` | Keep a typed top level substrate envelope | Add Transport or expose a Session composed read surface; decide from consumer needs |
| Aggregate doctor | `crates/lilo/src/cli/doctor.rs:41-74` | Keep one top level health command | Add Transport readiness, storage, capture progress, corruption, quota, and compatibility findings |
| CLI composition | `crates/lilo/src/cli.rs:77-135`, `234-327` | Keep one `lilo` binary and operator namespaces | Add Transport capabilities from an authored contract; no shelling to `tm` |
| Generated CLI and MCP surfaces | `internal/session/core/src/tool_contracts.rs:1-137` and generated surface tests | Keep authored source and generated consumers | Define capture reads once and generate CLI, MCP, and application contracts |
| Application placeholders | `apps/README.md`, `packages/README.md`, `products/README.md` | Preserve the future consumer boundary | UI reads through an authorized typed API, never arbitrary artifact paths |
| Workspace and release metadata | `Cargo.toml:1-28`, `132-150` | Keep one private source tree and release evidence | Include the littleorgans owned Transport implementation and mandatory capture acceptance in the product release |

## Data contract

Transport owns two classes of data.

### Authoritative evidence

1. Exact provider request and response bytes, subject to an explicit secret and
   data classification policy.
2. Capture timestamps and ordering.
3. Provider and harness compatibility facts observed for that capture.
4. Completeness and truncation evidence.
5. Durable linkage to `SessionId`.
6. Integrity evidence for finalized artifacts.

### Derived data

1. Provider neutral exchange models.
2. Curated views.
3. Harness transcript projections.
4. Fidelity comparisons.
5. Search and application indexes.

Derived data must carry a decoder or projection version and remain rebuildable
from authoritative evidence when policy permits.

The minimum metadata record needs:

| Field | Purpose |
|---|---|
| `SessionId` | Product join |
| Transport owned capture identity | Stable capture address if multiple captures or attempts can exist |
| Attempt identity | Recovery and retry discrimination |
| Provider and harness facts | Historical decode and drift analysis |
| Started, armed, first byte, last byte, finalized timestamps | Readiness and completeness |
| State and terminal reason | Product status |
| Byte and exchange counts | Quota and integrity |
| Integrity digest or equivalent | Corruption detection |
| Retention class and expiry | Lifecycle policy |
| Projection versions | Rebuild and compatibility |

Raw payload access must use opaque identifiers through an authorized API. The
future application must never receive unrestricted local paths.

The existing `Session.transcript_path` is Runtime stdout evidence
(`internal/session/core/src/session.rs:66-88`). It must not be overloaded with a
Transport transcript or raw capture path.

## Operator and application surface

The product needs capabilities, while exact command spellings remain a design
decision.

### Session surface

`lilo get session` and machine output must expose a compact capture summary:

1. Capture required
2. Current capture state
3. Completeness or failure reason
4. Exchange count
5. Opaque capture reference

`lilo wait` needs capture aware conditions if operators must gate later work on
readiness or finalization.

`lilo delete session` must execute an explicit retention policy. Deleting the
control record and deleting capture evidence are separate decisions that
require audit.

### Transport operator namespace

The `lilo transport ...` namespace should expose capabilities for:

1. Context health and readiness
2. Listing captures by Session selector
3. Inspecting capture metadata and completeness
4. Reading exchanges and fidelity evidence
5. Verifying artifact integrity
6. Exporting under an explicit raw or redacted policy
7. Applying retention and deletion policy

It must not expose a spawn command. It must not reveal implementation paths as
the primary read contract.

### Existing `lilo capture`

The current command captures tmux pane output through Runtime
(`crates/lilo/src/cli.rs:106-108`;
`internal/runtime/daemon/src/api.rs:154-159`). It is terminal capture. Wire
capture needs distinct language and must never inherit this command's semantics
by accident.

### Doctor

`lilo doctor` remains the aggregate surface. Transport health must include:

1. Capture implementation available
2. Required provider adapters available
3. Durable artifact store writable
4. Recovery scan complete
5. No corrupt or abandoned active captures
6. Quota and retention status
7. Current implementation and schema compatibility
8. A bounded active capture probe

The current doctor has only Identity, Session, and Runtime counts
(`crates/lilo/src/cli/doctor.rs:231-259`). The daemon response also names
`runtime_matters`, which is migration residue
(`internal/session/core/src/proto/doctor.rs:6-22`).

### Human application

No application implementation exists in this snapshot. The reserved directories
contain only one line placeholders. The future application contract must offer:

1. Session scoped capture summaries
2. Paginated or cursored exchange reads
3. Live updates with replay and resynchronization
4. Fidelity and completeness status
5. Authorized raw and redacted views
6. Stable opaque identifiers

HTTP, daemon RPC, embedded service, and process placement remain open.

## Documentation and decision authority reset

The user correction supersedes every littleorgans statement that makes `tm` or
transport-matters part of the product implementation.

### Must be withdrawn

| Source | Contradiction |
|---|---|
| `CLAUDE.md:27-30` | Defines a later Python transport-matters release train |
| `CLAUDE.md:54-73` | Migrates the experimental Python API, names `tm`, and makes Runtime execute it |
| `CLAUDE.md:82-85` | Calls `tm` the default launch wrapper |
| `CLAUDE.md:114-118` | Defines Transport commands around a Runtime invoked `tm` wrapper |
| `CLAUDE.md:243-250` | Makes the transport-matters package a release train |
| `NOTES/transport-integration.md:23-48` | Defines the work as a Python migration and `tm` spawn path inversion |
| `NOTES/transport-integration.md:50-112` | Locks `tm` naming, packaging, command routing, and join behavior |
| `NOTES/transport-integration.md:114-169` | Inherits experimental storage, environment, reliability, phase, and topology choices |
| `~/.mdx/projects/littleorgans-monorepo-migration--synthesis.md:487-488` | Keeps Transport outside the locked product scope |
| `~/.mdx/projects/helioy-product-direction.md:16-38` | Treats transport-matters as a product and release surface rather than a research source |

`NOTES/transport-integration.md` should become superseded research history or be
replaced by a littleorgans Transport product decision record. Its settled labels
no longer have authority.

### Current implementation gap

The product source confirms zero current dependency on `tm` or
transport-matters. A search across Rust, Cargo, workflow, TOML, YAML, and shell
source returned no references. That is the correct dependency baseline.

It also confirms that first class Transport is absent:

1. `Cargo.toml:1-28` has no Transport workspace member.
2. `internal/wire/src/lib.rs:3-8` has only Session and Runtime RPC variants.
3. `internal/session/app/src/compose.rs:115-133` builds Runtime and Session only.
4. `crates/lilo/src/cli.rs:234-327` has no Transport command.
5. `crates/lilo/src/cli/doctor.rs:231-259` has no Transport health.
6. `crates/lilo-paths/src/lilo.rs:48-109` has no Transport path.
7. `lilo --help` lists Runtime and Session as the only substrate operator
   namespaces.

## Open product decisions

These questions must be decided from littleorgans requirements. Experimental
implementation choices have no default authority.

1. Which interception mechanisms satisfy Claude, Codex, and future providers?
2. Which implementation language and process topology best satisfy those
   mechanisms?
3. What exact evidence is mandatory before capture reports armed?
4. What happens when capture fails after the agent has started?
5. What bounded buffering and backpressure policy applies?
6. Where do raw artifacts live, and what belongs in Postgres?
7. What encryption, secret classification, retention, quota, and secure deletion
   policies apply?
8. Does a session permit multiple capture attempts? If yes, which identifiers
   and selection rules apply?
9. Which Transport events are durable, and how does Session replay or reconcile
   them?
10. Which capture capabilities belong in CLI, MCP, and the human application?
11. What capture behavior applies to raw diagnostic Runtime spawn?
12. How is the littleorgans owned Transport implementation packaged in one
    product installation and qualified in one release?
13. Which real provider tests are safe and necessary in addition to deterministic
    provider stubs?
14. Are pause and edit product requirements, or research features outside the
    first capture release?

## Release acceptance

A release cannot pass without this clean installation proof:

1. Build and install littleorgans with no `tm` binary on `PATH` and no
   transport-matters checkout available.
2. Start `lilod`.
3. Run a deterministic supported agent against a provider stub.
4. Prove one `SessionId` across authorization, Session intent, Runtime lifecycle,
   Transport metadata, and application read model.
5. Prove the agent cannot reach the provider before capture readiness.
6. Prove exact request and response evidence survives process and daemon
   finalization.
7. Prove Session reports running only after Runtime and Transport readiness.
8. Kill the daemon at every boundary: intent write, capture prepare, shim launch,
   child start, first byte, response write, process exit, and capture finalization.
9. Restart and prove idempotent reconciliation with no healthy uncaptured
   session, duplicate exchange, or abandoned active capture.
10. Force a capture storage failure and prove there is no direct fallback.
11. Verify `lilo doctor`, CLI, MCP, and application summaries expose the same
    capture state.
12. Verify retention, deletion, audit, and integrity checks.

## Recommended design sequence

1. Replace the obsolete Transport integration note with a product decision
   record containing the boundary and open decisions above.
2. Define the Transport domain language and lifecycle without selecting
   deployment topology.
3. Define the composite Session spawn and recovery matrix.
4. Define the typed capture binding at the existing pre execution shim handoff.
5. Define authoritative evidence, metadata, retention, and access policy.
6. Define operator, MCP, doctor, and application read contracts.
7. Select implementation topology from those contracts.
8. Implement one fake provider vertical slice.
9. Add the crash and failure matrix.
10. Make that vertical slice a mandatory release gate.

## Verification performed

1. Repository SHA:
   `98d8928941b5b5db670ed73ed06af57f61dcfa0a`
2. Branch: `main`
3. `fmm status`: 388 source files, 388 indexed.
4. `fmm validate`: all 388 files current.
5. User visible smoke:
   `cargo run -q -p lilo -- --help`
6. Result: help lists `runtime` and `session` under substrate operator commands;
   no Transport namespace exists.
7. Source dependency search found no `tm`, transport-matters,
   `TRANSPORT_MATTERS`, or `python/transport` references in Rust, Cargo,
   workflow, TOML, YAML, or shell files.
8. The repository had a preexisting uncommitted `LESSONS.md` change. This study
   did not modify the repository.
