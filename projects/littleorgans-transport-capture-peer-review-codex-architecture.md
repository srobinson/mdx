---
status: complete
---

# Littleorgans Transport Capture Peer Review: Architecture

Status: COMPLETE

Worker Status: No nested workers. Review is being performed directly by the assigned Codex peer.

Verdict: CORRECTION REQUIRED

## Findings

### P0. The v1 contract leaves supported spawn paths outside mandatory capture

**Fact.** The pinned littleorgans command surface advertises session backed
Claude and Codex launches, headless and tmux targets, and Docker isolation.
`lilo_rm_core::RuntimeKind` also accepts arbitrary `Other(String)` values.
Diagnostic `lilo runtime spawn` accepts an operator supplied `SessionId` and
calls the same runtime spawn RPC without creating a Session record. Evidence:

- `crates/lilo/src/cli/generated_help.rs::RUN_EXAMPLES`
- `crates/lilo/src/cli/generated_help.rs::CREATE_EXAMPLES`
- `crates/lilo-rm-core/src/types/runtime.rs::RuntimeKind`
- `internal/runtime/app/src/cli/spawn.rs::SpawnArgs`
- `internal/runtime/app/src/cli/spawn.rs::run`

**Fact.** The synthesis minimum covers only `lilo run claude`. It places Codex
after v1, leaves Docker scope open in U8, and leaves raw runtime capture or an
uncaptured diagnostic escape open in U4. Its locked L1 simultaneously says
Transport capture is mandatory and littleorgans cannot ship without it.

**Fact.** `shell_resume` is not another captured agent launch. The shim invokes
it after the agent exits and applies `ShellResume.env`, which is independent of
`LaunchSpec.env`. Evidence:
`internal/runtime/app/src/cli/shim.rs::exec_shell_resume` and
`internal/runtime/app/src/cli/shim.rs::shell_resume_command`.

**Inference.** Convergence on `LaunchSpec` proves a useful code funnel. It does
not prove product coverage. The current surface can still admit an unsupported
adapter, isolation mode, or raw runtime path unless the new coordinator rejects
that cell before the shim starts.

**Required correction.** Add a normative spawn coverage matrix across:

- session `run` and `create`, raw runtime spawn;
- Claude, Codex, and arbitrary runtime kinds;
- host and Docker isolation;
- headless and tmux targets.

Every cell must say either CAPTURED or REJECTED BEFORE SHIM SPAWN. For the first
release, disable Codex, Docker, and arbitrary runtime cells whose adapters or
network route have not passed the named experiments. Update generated help,
MCP instructions, schemas, and tests in the same change. Capture raw model-agent
spawns or delete raw model-agent spawn. A typed non-provider workload category
may remain outside Transport only after the type exists. Exclude the post-agent
shell resume explicitly from the coverage claim.

### P0. The evidence root cannot be exact, redacted, and application-level at once

**Fact.** The synthesis makes four incompatible claims:

1. The first screen promises exactly what reached the provider.
2. The taxonomy calls the artifact byte-faithful raw capture and says wire
   fidelity is passthrough-perfect by construction.
3. The data model calls exact wire bytes the immutable root of trust.
4. The security model removes credential headers before bytes reach disk.

The synthesis later adopts the more precise names
`client_body_bytes` and `decoded_provider_body_bytes`, which acknowledges that
these classes differ.

**Fact.** The experimental source does not supply an exact-octet precedent.
At the pinned transport commit,
`api/src/transport_matters/exchange_recorder/artifacts.py::request_raw_bytes`
prefers decoded text and re-encodes it as UTF-8. Its own docstring says it
prefers a content-decoded body. Header redaction replaces values in
`api/src/transport_matters/transport_redaction.py::redact_transport_artifacts`.

**Inference.** An application reverse proxy observes an inbound HTTP
representation and creates an outbound one. Header framing, order, casing,
transfer encoding, decompression, and credential removal can change the byte
sequence. A redacted artifact can be valuable evidence, but it cannot also be
the exact immutable bytes presented to the provider. The current fidelity
acceptance oracle therefore has no uniquely defined subject.

**Required correction.** Replace every generic `raw` and `wire bytes` claim
with an artifact contract that names:

- inbound client headers and entity body;
- outbound provider headers and entity body;
- upstream response headers and body chunks;
- downstream response headers and body chunks;
- each decoding, decompression, framing, and redaction transform.

Choose one security posture for each authoritative class. Either store a
verbatim restricted class encrypted from first write and derive redacted views,
or store only redacted evidence and withdraw exact-octet and provider-truth
claims for removed fields. Point the fidelity tests at a named boundary.
Provider receipt should remain `Delivery Unknown` unless the provider
acknowledges it.

### P1. `LaunchSpec` is an injection seam, not the capture orchestration seam

**Fact.** At the pinned littleorgans commit,
`internal/runtime/daemon/src/api.rs::spawn_domain` performs launcher dispatch,
a synchronous backend `prepare_launch`, `begin_spawn`, and then shim spawn.
`internal/runtime/daemon/src/backend.rs::RuntimeBackend::prepare_launch` is a
pure synchronous `LaunchSpec` rewrite. Docker is the existing example.

**Fact.** The proposed capture preparation requires asynchronous work before
the agent starts: allocate and bind a listener, create and sync a capture
header, prove store writability, start supervision, and retain cleanup state.
The synthesis proposes adding a Transport port to Session's `DaemonState`.
Raw runtime spawn bypasses Session. It also says Transport starts the worker
while Runtime owns process launch, and leaves the worker process topology open
in U2.

**Inference.** `LaunchSpec` is the correct place to carry the resulting
endpoint into the child. It cannot, in its current shape, own preparation,
readiness, cancellation, finalization, or raw-spawn enforcement. Treating it as
the entire interposition seam creates either duplicate orchestration or a raw
runtime escape.

**Required correction.** Define one coordinator and one dependency direction
before implementation. A coherent option is:

1. Compose Transport before Runtime.
2. Inject a narrow `TransportCapturePort` into Runtime.
3. Have `spawn_domain` await `prepare_capture` before `begin_spawn`.
4. Receive an opaque, one-use capture lease containing child launch material.
5. Decorate `LaunchSpec` purely from that lease.
6. Cancel or finalize the lease on every runtime outcome.
7. Let Session record and reconcile the composite intent without starting a
   second worker.

If Session remains the sole coordinator, raw model-agent spawn must be removed.
Also decide whether the worker is an in-process task or a Runtime-owned child;
the ownership table must match that choice.

### P1. The authority model cannot replay deletion and governance state from files

**Fact.** The organizing invariant says tier-one files are the sole authority,
every Postgres row is replayable, a corrupt index can be dropped and rebuilt,
and the run directory is the backup unit. The same synthesis assigns capture
state, tombstones, retention state, legal holds, deletion outcomes, and access
audit to durable database rows. It also says the index tombstone is the
bootstrap arbiter after a staged deletion.

**Inference.** A tombstone, hold, or deletion audit cannot be reconstructed
from a run directory after its content is unlinked. Dropping the database can
either resurrect staged content or erase the only proof that content was
deleted. Audit records are independent authority by definition. The blanket
replayability claim therefore fails on the governance classes that make the
design enterprise credible.

**Required correction.** Define separate authorities:

- immutable capture content and launch facts;
- lifecycle and deletion control state;
- authorization and access audit;
- policy and legal hold state;
- derived query projections.

Give each class a backup and recovery source. If all capture control state must
remain file authoritative, persist a durable manifest and tombstone journal
outside deletable run directories and rebuild Postgres from it. If Postgres is
authoritative for control state, say so and require coordinated database plus
artifact backups. Remove the claim that every Postgres row is replayable.

### P1. Same-UID files and `paths` bypass the promised authorization and access audit

**Fact.** The synthesis says Identity gates raw reads and enterprise
qualification audits every raw read and export. It also ships
`lilo transport paths`, reads directly from tier-one disk, and protects capture
files with owner-only modes. Host agents run beneath the operator UID through
the existing shim; the current host backend performs no UID separation.

**Inference.** Mode `0600` protects against other Unix users. It grants the
operator's agent processes the same direct read authority as the operator.
Returning paths makes application-level Identity checks optional. An agent can
read another session's restricted evidence without producing a raw-read audit.
The stated enterprise guarantee cannot hold under this model.

**Required correction.** Choose and document an enforcement boundary. Viable
options include encrypted restricted blobs whose keys are available only
through an audited daemon path, a separate OS principal or sandbox boundary for
agents, or a narrower claim that agents have full operator file authority.
`paths` may expose sanitized or encrypted artifacts, but it must not expose
plaintext restricted content while the product claims mediated authorization.
Add a hostile same-UID direct-file test, not only an RPC authorization test.

### P1. `lilo delete session` currently means terminate, while the synthesis makes it erase

**Fact.** At the pin,
`internal/session/daemon/src/handler/sessions.rs::delete_one` authorizes Kill,
returns immediately for an already terminated session, or terminates a running
runtime and persists the exit. It does not delete the Session row. The response
returns a `Session`.

**Fact.** The synthesis requires `lilo delete session` to cascade capture rows
and artifacts, preserve a deletion audit fact, and pass an assertion that no
rows and no directory remain.

**Inference.** This is a breaking semantic replacement, not an additive
capture hook. Leaving the old implementation shape in place will retain
terminated sessions and their capture forever.

**Required correction.** Put the current delete path on the explicit
delete-and-rebuild list. Define whether `delete` first terminates and then
tombstones plus erases, and define its idempotent response after the Session row
is gone. If operators still need termination without erasure, give that action
a separate verb. Update Session selectors, namespace deletion, audit actions,
and response schemas together.

### P1. The hot-path durability contract still permits the loss it forbids

**Fact.** The synthesis requires durable request acknowledgement before
provider release and elsewhere requires temp write, file sync, rename, and
parent-directory sync. It then leaves the barrier as either strict fsync or a
measured durability window. A window permits provider delivery followed by
power-loss loss of the request record.

**Fact.** The text assumes an outbound request is small and pre-stream. No
protocol limit or pinned runtime evidence establishes that assumption. The
hostile workload matrix separately requires bounded handling of huge request
bodies. Response handling names a bounded spool but does not define behavior
when disk throughput falls behind the provider stream.

**Inference.** The design has not selected one of the physical consequences:
spool and sync the full request before upstream release, apply backpressure, or
allow a documented loss window. Those choices produce different latency,
timeout, and completeness guarantees. A bounded response queue also requires a
defined full condition and mid-run action.

**Required correction.** State the durability level in failure-domain terms:
process crash, kernel crash, or power loss. If the release claim includes power
loss, require file and directory durability before upstream release and remove
the window option. Define request size caps, disk spooling, timeouts, and
upstream release. Define response queue capacity, backpressure, disk-full
behavior, and the exact transition to `Interrupted` or `Lost`. Measure the
chosen contract after it is coherent.

### P2. The CLI, wire, and agent read contract is still a list of verbs

**Fact.** The minimum v1 lists `list`, `show`, and `paths`; the operator section
adds `export`; the taxonomy says agents use existing MCP; and the UI consumes a
committed CLI JSON schema. The proposed `LilodRpc::Transport` variant has no
request or response contract yet. Raw runtime captures may have no Session row,
while short-prefix selectors are said to share Session behavior.

**Inference.** Error shapes, pagination, byte limits, redacted versus
restricted views, raw-capture selectors, tombstone visibility, and schema
versioning remain undefined. Existing MCP behavior will not expose the new
variant automatically.

**Required correction.** Before Gate 5 closes, publish the typed v1 Transport
RPC and generated CLI JSON contract. Include bounded pagination and payload
limits, selector behavior for captures with and without Session rows,
authorization per view, stable error codes, schema versioning, and explicit MCP
tool ownership. Pick the v1 verb set once.

### P2. Readiness is a point-in-time check, while the text promises a process invariant

**Fact.** The synthesis requires the listener, adapter, store, and header to be
ready before Runtime spawn. The current shim starts the agent process and only
then sends `ShimReady` in
`internal/runtime/app/src/cli/shim.rs::run_for_session_blocking`.

**Inference.** A capture worker can exit after its readiness commit and before
the child starts. Base-URL enrollment can still prevent uncaptured provider
traffic, but the text's stronger promise that no agent process starts after a
capture failure does not follow from a readiness snapshot.

**Required correction.** Define the invariant around provider egress:
no provider request can bypass a live capture lease. Hold that lease through
child start, bind worker death to the launch attempt, and fault inject every
interval between prepare, readiness, shim start, child start, and first
request. Narrow process-existence claims unless the design adds a stronger
handshake.

## What survives review

1. **Fact.** The zero-dependency boundary is clean. At littleorgans commit
   `98d8928941b5b5db670ed73ed06af57f61dcfa0a`, the inspected Rust, Cargo,
   workflow, shell, and lock surfaces contain no `tm`, transport-matters,
   foreign transport environment prefix, proxy, or MITM implementation.
   The synthesis proposes no runtime or build relationship with the experiment.

2. **Fact.** Transport as a fourth bounded context is a sound product boundary.
   The exclusions around authorization, agent selection, process ownership,
   credential refresh, prompt mutation, and Session reconciliation are useful.

3. **Fact.** The pinned launch funnel is real. Session-backed and raw runtime
   requests reach `internal/runtime/daemon/src/api.rs::spawn_domain`; the shim
   executes a typed `LaunchSpec`. This is a strong foundation once capture
   coordination is added explicitly.

4. **Fact.** `SessionId` is already a UUIDv4 typed newtype and is propagated
   through runtime launch. It remains the right platform join key. The raw
   runtime ownership and deletion behavior still need the P0 coverage decision.

5. **Assessment.** The delete-and-rebuild instincts are correct for the
   unbounded local RPC, SessionId-only shim callback, secret-bearing durable
   intents, Docker secret argv, runtime event journal reuse, and ambient path
   permissions. The current Session delete contract belongs on that list too.

6. **Assessment.** The experiment and stop-gate sequence are disciplined.
   Interposition physics, crash injection, subscription authentication,
   background-agent coverage, Docker reachability, and failure experience are
   the right uncertainties to retire before implementation.

## Verification record

- littleorgans source pin verified and inspected immutably:
  `98d8928941b5b5db670ed73ed06af57f61dcfa0a`.
- transport research pin verified and inspected immutably:
  `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`.
  The live transport worktree is on another commit, so all cited experimental
  evidence came from `git show` at the requested pin.
- No transport-matters `NOTES` path was read or cited.
- Neither repository nor the definitive synthesis was edited.
- Zero `tm` dependency passed review.
- Unsupported runtime claims are called out above as findings rather than
  accepted as facts.

## Final decision

The product direction is strong and the native boundary is worth keeping.
Correction is required before this document can serve as the definitive
contract. Close the two P0 findings first, then repair the coordinator,
authority, access, delete, and hot-path contracts. Implementation planning
should remain gated until the corrected document has one complete spawn matrix
and one unambiguous evidence model.
