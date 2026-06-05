# littleorgans Transport Capture: Definitive Synthesis

Status: COMPLETE

Updated: 2026-07-31

## What are we talking about?

littleorgans will make capture of managed agent-to-provider model inference traffic a mandatory, first class product capability. Every managed session-backed `lilo run` records the inbound client request, outbound provider request, upstream response, downstream response, and declared transforms, keyed by the platform `SessionId`, with zero setup, readable through daemon-mediated `lilo transport` verbs. The capability is built natively inside the littleorgans monorepo as the fourth bounded context (Transport, beside Identity, Session, Runtime).

`tm` and the transport-matters repository are experimental research only. littleorgans must never invoke, package, version against, port wholesale, depend on, or reach out to them. Their validated mechanisms, defects, and test patterns transfer as design evidence; their code, schema, topology, and dependencies do not.

Today littleorgans contains zero wire-capture code. This synthesis is the product study that consolidates thirteen phase-one artifacts and two phase-two inputs into one decision record: what to build, what to reuse, what to reject, what remains open, and in what order to retire the remaining risk.

Source pins (all repository evidence below is at these commits):

- littleorgans: `98d8928941b5b5db670ed73ed06af57f61dcfa0a`
- transport-matters (research evidence only): `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`

Evidence marking: **[F]** fact observed at a pinned source or a cited external primary source, **[I]** inference from facts, **[R]** recommendation. Repository citations use `path::symbol`. `transport-matters/NOTES/` was never read or cited by any input to this synthesis.

## Worker Status

- Owner: littleorgans:helioy-tools:research-synthesizer:5:2.1 (no nested agents spawned; synthesis performed in-pane)
- Inputs consumed: 13 phase-one artifacts (all `Status: COMPLETE`); 2 phase-two synthesis inputs consumed after each reached `Status: COMPLETE`

| Input | State |
|---|---|
| boundary-map, capability-taxonomy, data-authority, mechanics, product-boundary, product-contract, protocol-research, reject-map, research-program, security-durability, test-evidence, topology-options, user-value | CONSUMED |
| current-code-reuse synthesis input | CONSUMED (after orchestrator-directed correction of its event-log durability classification) |
| enterprise-gates synthesis input | CONSUMED (accepted by the orchestrator) |

## 1. Product thesis

**[F]** littleorgans cannot answer "what model inference exchange occurred?" today. `lilo logs` returns nothing for tmux sessions (`internal/session/core/src/paths.rs::lifecycle_transcript_path` yields `None` for tmux); the only inspection tool is `lilo capture`, an ANSI pane scrape with no turn structure and no provider-side exchange evidence.

**[I]** Mandatory capture converts that question into a one-command answer for the managed harness inference channel. Running means the process started while a live capture lease covered provider egress. A later first-exchange receipt records positive provider response evidence. The experimental evidence proves the primary redirect mechanism is buildable without sudo, certificates, or system trust changes, subject to the harness feature regression in section 7.

**[R]** The product principle set (user-value study, converged across artifacts):

1. Capture is a platform property. No enable flag, no setup.
2. A live capture lease covers provider egress from launch through every managed inference request; derived persistence remains isolated.
3. One id is the spine: `SessionId`, injected as `LILO_AGENT_SESSION_ID`, keys everything.
4. Provider exchange evidence over harness self-report; relay artifacts and transcript are two streams, never collapsed.
5. Silence is the success state; capture speaks only through existing verbs.
6. Content capture ships with content governance (redaction, retention, deletion) in the same release.
7. Evidence is attributed and append-only by application contract. Under the v1 same-UID threat model it is tamper-evident at best.
8. Nothing ships dark: every artifact class has a read path in the same release.

## 2. User and enterprise value

Operator jobs, ranked by evidence strength (user-value study):

1. Reconstruct what happened after the fact. **[F]** Unanswerable in littleorgans today; fully demonstrated in the research system's per-exchange artifacts.
2. Confirm the launch actually worked. **[F]** The research `PromptReceipt` defines "submitted" as one correlated provider exchange with positive response evidence; capture provides that signal for free.
3. See what the agent is doing right now (live inspection).
4. Understand why a specific turn went wrong (raw request and response per turn).
5. Respond to an incident with the record already written.
6. Prove what happened (enterprise): decision audit already exists (`internal/session/daemon/src/handler/spawn.rs::begin_spawn_intent` commits the authorization audit in the spawn transaction); capture adds attributed content evidence. Strong integrity requires the enterprise controls in sections 9 and 14.
7. Hand a session to another person or agent (unmet in both repos; second act).
8. Control what is retained, created alongside capture.

**[I]** The supportable v1 story is "managed model inference exchanges on this host are captured: who authorized the run, what transformed artifacts were persisted, and what response evidence returned." Mandatory enrollment supplies coverage within that boundary. It does not evidence shell activity, every agent action, human edits, direct egress, or hostile same-UID tampering. **[F]** A buyer will probe retention, deletion, and payload redaction first; the research system demonstrates the cost of deferring all three.

**[I]** Legal boundary: mandatory capture of a developer's prompts creates employment monitoring, privacy, and worker consultation risk in managed deployments. Jurisdiction-specific applicability and legal basis require primary-authority review by counsel. **[R]** Resolve whether littleorgans enables monitoring or performs it before the word "mandatory" appears in user-facing enterprise copy. For v1, one operator observing their own agents on their own host, this remains a documented scope boundary. Enterprise managed deployment cannot release before U9 closes.

## 3. Capability taxonomy and minimum coherent v1

Four tiers per dimension (capability-taxonomy study): V1 mandatory, ENT enterprise qualification, LATER deferred until read demand, DISTRACTION refused on evidence.

| Dimension | V1 | ENT | LATER | DISTRACTION |
|---|---|---|---|---|
| Wire | Loopback reverse proxy via base-URL env; named inbound client, outbound provider, upstream response, and downstream response artifacts with framing, decoding, and redaction transforms recorded; streaming tee; zero relay mutation; anti-bypass env scrub | Scoped-CA MITM fallback for non-overridable harnesses; audited capture access | Codex WebSocket segmentation; credential-expiry observation | Multi-tenant shared proxy with per-run demux |
| Transcript | Launcher-owned session mint (`--session-id`); byte-faithful gap-detecting tee of the native transcript; best-effort, never stops the proxy, gaps recorded | Curated conversation projection | Codex seed-and-resume mint; subagent sidechains | Reconstructing harness belief by wire inference |
| Fidelity | Two-stream invariant; relay fidelity verified by an independent client-and-upstream octet oracle; persisted body fidelity, structural round-trip, and intentional secret omission measured separately | Typed drift evidence with keyed digests gating harness versions | The relay-vs-transcript diff, as a read surface first | Diff algorithms before a single read exists |
| Artifacts | Canonical redacted request and response artifacts, transform manifest, minimal turn record, per-session index; provider-reported tokens only; UnknownBlock-style escape hatch | Content-addressed prompt and tool-set dedup; image blobs | Tool calls as rows; thinking blocks; Codex turn derivation | Proxy-bypassing count_tokens egress; full frozen IR taxonomy up front |
| Mutation | None. Observation only | Audited, identity-attributed override pipeline | Arm-once pause with timeout release | Shipping mutation before reads |
| Compatibility | One Claude adapter; fail-open comprehension (unknown shape passes through, recorded unparsed); `RuntimeCapability::WireCapture` gate | Signed versioned compatibility releases | Codex adapter; advisory-to-enforcing switch | Compat publication machinery for a pre-release product |
| Storage | Tier-1 files under `~/.lilo/data/`; content artifacts never enter Postgres; session row points at the capture dir; atomic writes | Content-addressed dedup; retention with RLS-ready `owner` seam | Crash-staged dirs with full recovery predicates | A Postgres content store before any reader |
| Reads | `lilo transport list\|show\|export` through the Transport `LilodRpc` variant; the daemon reads tier-1 disk and applies Identity authorization and audit | Twin-skin read service; token-bounded reads; stronger raw access controls | Timeline projections; SSE streams | Direct path disclosure and the human UI (separate train) |
| Operations | Proxy lifecycle in the shim supervision tree; kernel-allocated ports; capture state in doctor aggregate | Channel separation; loopback hardening | Fail-closed capture-health kill policy chosen explicitly | Containerizing the proxy; rehydrating shared-proxy supervision |

**Minimum coherent v1:** every managed `lilo run claude` model inference channel is routed through a session-scoped loopback reverse proxy injected at the runtime launch seam via `ANTHROPIC_BASE_URL`. The relay tees the four named HTTP directions while preserving streaming, records every transform, assembles per-turn records, and persists the canonical redacted artifacts with the harness transcript under `~/.lilo/data/transport/<session_id>/`. The launcher-minted `SessionId` keys the run. `lilo transport list|show|export` reads through daemon RPC. Relay traffic is not mutated, comprehension fails open, launch readiness fails closed, and `RuntimeCapability::WireCapture` gates the runtime. Agent-spawned processes with modified environments, direct egress, and post-agent shell resume are outside this v1 claim.

**[R] Normative spawn coverage matrix.** Each grouped mode expands to both concrete cells. Before Gate 3 closes, every OPEN cell must become exactly `CAPTURED` or `REJECTED BEFORE SHIM SPAWN`. There is no uncaptured-success state. The choices assigned to Stuart remain open here.

| Surface | Harness | Host headless and tmux | Docker headless and tmux |
|---|---|---|---|
| session run/create | Claude | CAPTURED | OPEN U8: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN |
| raw runtime spawn | Claude | OPEN U4: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN | OPEN U4/U8: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN |
| session run/create | Codex | OPEN Gate 3: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN | OPEN Gate 3/U8: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN |
| raw runtime spawn | Codex | OPEN U4/Gate 3: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN | OPEN U4/U8/Gate 3: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN |
| session run/create | `RuntimeKind::Other` | OPEN Gate 3: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN | OPEN Gate 3/U8: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN |
| raw runtime spawn | `RuntimeKind::Other` | OPEN U4/Gate 3: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN | OPEN U4/U8/Gate 3: Stuart selects CAPTURED or REJECTED BEFORE SHIM SPAWN |

Conformance iterates `internal/runtime/launchers/src/lib.rs::registered_launchers` and requires a qualified capture adapter or pre-spawn refusal for every entry. Capability and doctor output report per runtime and backend. Post-agent shell resume is explicitly excluded because `internal/runtime/app/src/cli/shim.rs::shell_resume_command` does not consume `LaunchSpec.env`.

## 4. Bounded-context ownership and exclusions

| Context | Authority |
|---|---|
| Identity | Principals, authorization of capture actions (read, raw read, export, retention change, delete), audit, credential sources and key material |
| Session | User intent, composite spawn intent including capture preparation state, aggregate session state, reconciliation |
| Runtime | Agent process launch, shim, backends, isolation, process lifecycle and host evidence |
| Transport | Provider wire observation, capture lifecycle and persistence, transcript ingestion, capture read models, capture health |

Invariants (product-boundary study, nonnegotiable):

1. Every managed session-backed `lilo run` and `lilo create session` inference channel is either captured or rejected before shim spawn.
2. No managed provider request may bypass a live, one-use capture lease for its `SessionId`.
3. Session reports Running only after process start and capture readiness; positive provider response becomes a later first-exchange receipt.
4. Capture failure cannot fall through silently to a direct provider path.
5. `SessionId` correlates Session, Runtime, Identity audit, and Transport metadata; provider conversation ids are attributes, never keys.
6. Transport observes and records. It does not authorize, select the agent, decide to spawn, own the process, refresh credentials, mutate prompts, or reconcile the session. The moment a capture surface can act on a session, it is a session verb and moves behind the session boundary with its own authorization.
7. Runtime owns the process; it does not parse provider traffic or own capture artifacts.
8. Identity gates capture inspection, raw access, export, retention changes, deletion.
9. A release is unshippable unless a clean install proves a captured launch end to end.

Exclusions from capture scope: agent-spawned subprocesses that clear or replace the managed environment, direct agent network egress, post-agent shell resume, fast-mode checks, WebFetch preflight, telemetry, plugin downloads, override/breakpoint machinery, token counting egress, credential brokering, control-plane verbs, certification subsystems, the TS/Electron UI train, canvas/PTY products, channel homes, and run-identity name allocators. Construction-level coverage beyond the managed inference channel requires host or container network egress control and stays outside v1.

**[F]** The shim already phones home for its `LaunchSpec` before starting the agent (`internal/runtime/app/src/cli/shim.rs::run_for_session_blocking`), argv is materialized in one place (`internal/runtime/daemon/src/api.rs::spawn_domain`), and `RuntimeBackends::prepare_launch` (`internal/runtime/daemon/src/backend.rs`) is the proven rewrite precedent. `LaunchSpec` carries injection. Asynchronous orchestration belongs to the Session app. **[R]** One Session app coordinator depends inward on a Transport port and a Runtime port. It prepares Transport before `internal/runtime/daemon/src/server/spawn.rs::SpawnCoordinator::begin_spawn`, receives a one-use capture lease carrying child launch material, passes that material into `LaunchSpec`, and cancels or finalizes the lease for every Runtime outcome. Transport and Runtime do not depend on each other. The lease remains live through child start and first provider request. Diagnostic raw spawn uses the same coordinator only if Stuart selects CAPTURED at U4; otherwise it is rejected before shim spawn.

## 5. Current littleorgans reuse, rewrite, delete map

Reconciled across the product-boundary, boundary-map, and security-durability studies and the corrected current-code-reuse synthesis input (symbol-first audit, 388 files, 58,401 LOC). Headline: transport capture is entirely MISSING (no proxy, store, paths, authz action, CLI namespace, or doctor probe), and the zero-tm baseline is validated cold. Managed pre-agent spawn paths converge on `LaunchSpec`; post-agent shell resume does not. Treat `LaunchSpec` as the single injection carrier while the Session app coordinator owns preparation and lease lifecycle. A native capture context receives `SessionId` in-process from `SpawnRequest`; the env var stays for agent-side surfaces.

Keep and extend:

| Seam | Evidence | Reshape required |
|---|---|---|
| Typed id family, `SessionId` join key | `crates/lilo-common/src/id.rs::SessionId` | Add Transport ids only when a persisted field exists |
| Identity action registry | `crates/lilo-im-core/src/types.rs::Action` | Add Capture actions (also missing for existing `lilo capture`) |
| Transactional authorization | `internal/identity/service/src/client.rs::IdentityClient::authorize_in_tx` | Classify every Transport surface |
| Composite spawn intent, two-transaction shape | `internal/session/daemon/src/handler/spawn.rs::begin_spawn_intent` / `complete_spawn_intent` | Evolve into Session+Transport+Runtime composite intent recording capture preparation, lease issue, readiness, cancellation, finalization |
| Domain port pattern | `internal/session/driver/src/port.rs::RuntimePort` | Add a Transport port beside it; inject via `DaemonState` |
| Launcher registry and env upsert | `internal/runtime/launchers/src/lib.rs::runtime_env`, `resolved_argv` | Proxy env injection per launcher; conformance tripwire (`conformance.rs` asserts `argv.len() == 1`) updated deliberately if argv changes |
| Backend rewrite seam | `internal/runtime/daemon/src/backend.rs::prepare_launch` | Consume capture launch material after the coordinator prepares a lease; no second preparation path |
| Shim handoff and supervision | `internal/runtime/daemon/src/shim_socket.rs::shim_env` (one-var contract, guard-tested) | Capture config rides `LaunchSpec.env` over the UDS; the bootstrap env stays reserved |
| Event cursor pattern | `internal/session/store/src/postgres/events.rs::apply_runtime_events_and_cursor` | Same idiom for capture events; cursor advances only after commit |
| Path policy | `crates/lilo-paths/src/lilo.rs::LiloPaths` | New capture accessor family; `assert_default_tree` extends |
| Env registry and gate | `crates/lilo-paths/src/env.rs` + `scripts/check-env.sh --check` | New `LILO_*` capture names registered |
| Generated CLI surface | `tools/schemas/cli.toml` + `xtask codegen` + guard tests | `lilo transport` verbs authored there |
| Protocol capability gate | `crates/lilo-rm-core/src/version.rs::RuntimeCapability` | Additive `WireCapture` |
| Postgres test isolation | `internal/db/src/test_support.rs::TestDb` | Adopt template-clone speed and namespace-scoped sweep deltas |
| Readiness pattern | `internal/session/app/src/compose.rs::RunMode::ReadyCheck` | Capture proven among ready-check subsystems |
| Doctor aggregate | `crates/lilo/src/cli/doctor.rs::DoctorStatus` | `SubstrateHealth` is the designed extension point |
| Composed wire enum | `internal/wire/src/lib.rs::LilodRpc` (exactly Session, Runtime) | Additive third variant; `run_core`/`handle_connection` compose and dispatch a transport service; add a capture-lifecycle shutdown stage |
| Spawn handshake | `internal/runtime/daemon/src/server/spawn.rs::SpawnCoordinator::begin_spawn` | Reuse as is; capture must not break the pending-launch/ShimReady handshake |
| Intent recovery shape | `internal/session/store/src/postgres/spawn_intents.rs::abort_spawn_intent_with` | Template for capture-run recovery |
| Runtime port | `internal/session/driver/src/port.rs::RuntimePort` | Reuse as is; its `capture` is tmux scrollback; wire capture owns a separate bounded-context seam |
| Integration harness | `tests/integration` `LiloDaemon` | Ready-made for capture end-to-end contract tests |

Explicitly rejected for capture reuse: the runtime `EventLog` (`internal/runtime/daemon/src/event_log.rs`) as a capture-payload substrate. **[F]** As implemented it is a bounded, deduplicating, whole-log-in-memory lifecycle notifier: no per-append fsync (batched `sync_data` only inside appends, so a quiescent log holds unsynced events indefinitely), hard failure on any interior corrupt line, compaction rename without parent-directory fsync, dedup to one event per `(session_id, kind)`, and deliberately lossy retention. Each property is correct for lifecycle events and wrong for wire capture. Only two idioms are candidates, and only under a new durability contract adding per-record durability, interior-corruption tolerance, and parent-directory fsync: the torn-tail truncation in `recover_partial_tail` and the tmp plus `sync_all` plus rename in `compact_if_due`.

Repair before capture uses them (security-durability study; pre-release, no compatibility preserved):

1. Local RPC reads an unbounded line before peer credentials are extracted (`internal/session/app/src/compose.rs::handle_connection`; `crates/lilo-rm-core/src/proto.rs::read_async_json_line`). Authenticate first; bound frames; add accept limits and deadlines.
2. Same UID is full authority; `ShimLaunch` returns full `LaunchSpec.env` to any same-UID caller that knows a pending `SessionId` (`internal/runtime/daemon/src/identity.rs::authorize_shim_callback`). Replace with a one-use process-bound launch capability.
3. Secrets are copied into durable state: full `SpawnRequest` including env serialized into `session_spawn_intents.spawn_request_json`; Docker renders env as `--env KEY=VALUE` argv (`internal/runtime/daemon/src/docker_argv.rs::append_env_args`). Make intents secret-free; move secrets by reference or descriptor.
4. Runtime event journal has unsafe error ordering, no timed sync, no byte ceiling (`internal/runtime/daemon/src/event_log.rs::append_recorded_event`, `compact_if_due`). Replace or rebuild before Transport events reuse the pattern.
5. `LILO_HOME` has no enforced permission policy (`crates/lilo-paths/src/lilo.rs::LiloHome::from_path`; `crates/lilo-sys/src/sys/unix/ipc.rs::prepare_socket`). Capture roots require `0700`/`0600` with ownership checks.
6. Spawn lacks a caller-supplied idempotency key; recovery can abort ownership of a live process on a transient status error (`internal/session/daemon/src/handler/spawn.rs::reconcile_pending_spawn_intent`).

Delete or rewrite (docs and dead premises):

- `CLAUDE.md` lines making `tm` the launch wrapper and transport-matters a release train; `NOTES/transport-integration.md` (Decision 1 "runtime execs tm", Decision 6 SQLite `index.db`, Decision 7 foreign env prefixes) is superseded and should become a littleorgans Transport decision record.
- `CLAUDE.md` command-surface text listing Transport verbs as `list`, `paths`, `show <session>`; remove `paths` and align the list with daemon-mediated `list`, `show`, and `export`.
- `docs/reference/env-vars.md` UUIDv7 claim for `LILO_AGENT_SESSION_ID` (code is v4).
- `internal/session/daemon/src/handler/sessions.rs::delete_one` currently terminates Runtime and returns without deleting the Session row. Replace that semantic with terminate-then-erase for `lilo delete session`; any terminate-only verb is U16.
- Doctor response `runtime_matters` naming residue (`internal/session/core/src/proto/doctor.rs`). Repair requires a versioned wire-contract change.

**[F]** Verified negatives that define the acceptance baseline: zero `tm`/transport-matters/`ANTHROPIC_BASE_URL`/proxy/mitm references in Rust, Cargo, workflow, or shell sources; no Transport workspace member, RPC variant, CLI namespace, path, or doctor slot.

## 6. Experimental lessons to leverage and to reject

Leverage (reimplement under littleorgans ownership; tm evidence cited as lab proof):

1. Interpose before launch; proxy listening before the agent execs (`cli/runner.py::run_client_children_until_outcome`).
2. Claude needs no MITM: loopback reverse proxy plus `ANTHROPIC_BASE_URL` (`captured/claude.py::_build_claude_captured_invocation`); route persisted into the managed harness home so re-spawned subprocesses stay routed (`cli/claude_home.py`).
3. Launcher-owned session mint closes identity (`claude --session-id <uuid>`; `owned_transcript_binding.py`): wire, transcript, and store agree on one key with zero heuristics.
4. Tier-1 observed artifacts and transform metadata first, durably, before any derived observer (`storage/exchange_sink.py`); observers isolated; atomic temp+sync+rename (`atomic_io.py::write_atomic_bytes`).
5. Streaming tee that forwards chunks unchanged while accumulating (`response_stream.py::install_response_tee`); observer exceptions isolated.
6. Byte-faithful transcript tee with hard gap failure; cursor advances only after snapshot plus commit ack (`storage/transcript_snapshot.py`, `index/tailer.py::TranscriptTailer`).
7. Preserve unknown shapes (`ir.py::UnknownBlock`); fail-open comprehension with a recorded unparsed exchange (`addon_handlers.py`).
8. Drift detection post-persist, from owned evidence, never blocking capture (`drift_capture.py::WireDriftObserver`).
9. Anti-bypass env hygiene: strip ~34 proxy and 9 trust keys before setting owned values, pin `NO_PROXY` (`launch/environment.py::build_managed_child_env`).
10. Orphan protection: parent-death reaping with bounded force exit (`self_reap.py`).
11. Fail-closed demultiplexing when listener-to-session mapping is unknown (`shared_proxy/addon.py`).
12. Local security primitives: `0700`/`0600` control sockets with bounded reads (`shared_proxy/control.py`); header redaction table (`transport_redaction.py`); directory-descriptor traversal (`secure_workdir.py`).
13. Producer-to-consumer shutdown drain ordering (`addon_runtime.py::close_capture_runtime`).

Reject (observed failure shapes; must not be reproduced):

1. Silent fail-open capture: persistence failure logs and returns None while provider traffic proceeds (`exchange_recorder/__init__.py::persist_http_provisional_exchange`); Postgres-down swallowed as "transcript capture disabled this run" (`addon_runtime.py::load_capture_runtime`).
2. Whole response bodies held only in an unbounded in-memory buffer; crash loses everything (`response_stream.py`).
3. The god process: proxy, writer, tailer, web server, UI, launcher, and credential broker in one process (`web_runtime.py` inside the addon).
4. Write-only substrates: the wire store ships dark, no content reader anywhere (`session/wire_store.py`; TLDR concurs). The read surface is part of the capture slice.
5. Credential ownership in the capture plane: caching and spending user auth headers, Keychain writes, OAuth refresh with a hardcoded client id (`counting.py`, `credential_broker.py`).
6. Unauthenticated authority routes: arbitrary local file GET (`api/v1/local_file_routes.py`), keystroke-writing websocket, unguarded breakpoint mutation.
7. Heuristic correlation: uuid5 synthesis and 14-permutation exchange-id containment probes (`index/sessions.py::synth_session_id`, `session/exchange_correlation.py`).
8. Read-time mutation of raw evidence (`storage/disk.py::read_exchange` rewrites `transport.json` during a read); destructive legacy cache migration that can wipe the storage root; whole-file index rewrites presented as durability.
9. Claims exceeding implementation: "raw" HTTP artifacts are decoded text and contain no wire octets (`exchange_recorder/artifacts.py::request_raw_bytes`); the flagship fidelity diff never existed.

Pinned-baseline auth syntax question, adjudicated and closed: two studies reported `credential_refresh.py` and `credential_source.py` as `SyntaxError` at the pin; the topology study re-verified with the repository's declared interpreter (`requires-python >= 3.14`, PEP 758 permits unparenthesized multi-exception clauses) and found both files parse clean, and an orchestrator-directed direct check with the project interpreter (`api/.venv/bin/python`, 3.14.5) successfully `ast.parse`d both exact blobs at `a252df24`. **[F]** The parse-failure claims are retracted as ambient-interpreter error. No conclusion in this synthesis rests on "tm was broken at the pin"; the zero-dependency rule and the credential-broker rejection stand on product and authority-boundary grounds alone.

## 7. Interception decision tree and cheapest decisive experiments

Decision tree per harness (protocol research, primary vendor sources):

1. Does the harness document a base-URL override? Yes for Claude Code (`ANTHROPIC_BASE_URL`, preserves claude.ai subscription login without a gateway credential), yes for Codex CLI (`OPENAI_BASE_URL` / `openai_base_url` with `wire_api` in `[model_providers]`), yes for Gemini CLI (localhost exempt from the HTTPS requirement). **[F]**
2. If yes: loopback reverse proxy in redirect mode. No CA, no MDM, no admin rights, immune to HTTP/3 blindness. Default and only mode in v1.
3. If no: CONNECT proxy plus TLS interception as an explicitly opted-into fallback (enterprise). Carries the CA-boundary exposure (B6): a root-equivalent key on every machine. Never SOCKS (unsupported by Claude Code).
4. Never kernel or packet capture (fails pause-and-edit later, TLS-opaque, requires root). Never transcript-tailing alone because it cannot independently evidence relay fidelity.

**[F]** Redirect mode has a confirmed harness feature cost. As of Claude Code 2.1.196, Remote Control is disabled when `ANTHROPIC_BASE_URL` points away from `api.anthropic.com`; MCP tool search is default-disabled for a non-first-party base URL. Redirect remains the v1 lean only conditionally. X1 must test and disclose the affected feature surface, and Stuart decides U15 before mandatory enrollment ships.

Relay correctness constraints (each has a documented hard failure mode): never buffer a streamed response; forward `anthropic-beta` and `anthropic-version` byte-for-byte as an open list (stripping fails subscription auth with 401); never modify request bodies; forward error bodies unmodified (retry logic matches upstream wording); pass the `system` array structurally unchanged; serve `/v1/models` without redirects inside 3s or omit it. **[F]** Capture participates in the protocol; every mutation is a correctness hazard before it is a privacy one.

Coverage honesty: base-URL capture sees inference traffic only. Fast-mode checks, WebFetch domain preflight, telemetry, plugin downloads, and Anthropic-hosted surfaces bypass it by design. **[R]** Product copy says "mandatory capture of model inference" and publishes the exclusion list.

Correlation spine: Claude Code sends `x-claude-code-session-id`, `x-claude-code-agent-id`, `x-claude-code-parent-agent-id` on the wire. **[F]** Subagent topology is available from headers with no body parsing; join to `SessionId` at the capture boundary.

Cheapest decisive experiments, ordered by how much option space each collapses:

| # | Experiment | Decides | Cost |
|---|---|---|---|
| X1 | Null-transform loopback relay under a claude.ai-logged-in session; confirm 200, then 401 with `anthropic-beta` stripped; exercise inference, streaming, tools, subagents, MCP tool search, resume, background work, Remote Control, and locally generated 422/413 faults with retry count zero | Redirect correctness, local-fault non-retryability, and the full operator-visible harness regression matrix | half day |
| X2 | Codex CLI against a base-URL override with `wire_api` configured, including its WebSocket path | Whether the entire MITM/CA branch is unnecessary for Codex too. **[I]** Emergent finding: the research system's explicit-proxy-plus-CA design for Codex may be an artifact of its era; current vendor config documents an override no phase-one littleorgans artifact connected to this | half day |
| X3 | Rust reverse-proxy SSE fidelity spike against a real multi-turn session (research program E1) | Language and process model (D2) | 1 to 3 days |
| X4 | Env-only interposition through `prepare_launch` on a real `lilo run claude` (E2) | Seam (D3), context home (D1), topology (D4) | 1 day |
| X5 | `--session-id` mint closure: transcript stem, wire metadata, and `session_sessions.id` all equal (E3) | Identity binding (D6) | half day |
| X6 | Inject process, kernel, and power failure at every write stage; prove strict durability for request artifacts, transform manifests, and synchronized response prefixes; prove any lost response suffix is at most 1 MiB and recovers as Interrupted; verify the APFS pre-created directory layout | Store shape, per-artifact durability, and resource contract | 1 to 2 days |
| X7 | Background-agent supervisor coverage: does the documented supervisor (fixed-path spawn, first-shell env inheritance) escape env-only enrollment under littleorgans-managed launches; does route persistence into the managed harness home close it (protocol research R21/R25/U8) | Whether env injection alone satisfies "mandatory"; whether settings-file enrollment is required | 1 day |
| X8 | Docker backend reachability: host loopback listener from the container netns; CA path across the boundary | Container scope (irreversible decision 9) | 1 day |
| X9 | Failure-mode operator experience: proxy-down-at-spawn and proxy-death-mid-run under both candidate contracts, exact CLI output recorded (E7) | Decision brief for the mid-run loss policy (Stuart) | 1 day |

Stop rule: any spike exceeding roughly three focused days without proof or falsification is itself a finding; stop and re-scope.

## 8. Data authority and durability model

Authority is split by data class. Content artifacts, transcript snapshots, compatibility facts, and launcher facts are filesystem authority. Authorization audit, access audit, capture lifecycle rows, tombstones, holds, and deletion outcomes form a transactional Postgres control ledger and are authoritative. Derived search indexes, cursors, and read-model rows are rebuildable. A rebuild cannot infer, resurrect, or erase control facts from content files.

Crash contract:

1. Durability is scoped per artifact class. The request artifact, transform manifest, and each durably synchronized response prefix survive process crash, kernel crash, and power loss. At most 1 MiB of the in-flight response suffix may remain unsynchronized and be lost on kernel or power failure; recovery records Interrupted and never Complete.
2. On macOS APFS, file durability uses `fcntl(F_FULLFSYNC)`. APFS has no directory-entry equivalent. Before a request may forward, Transport pre-creates and synchronizes the exchange directory and fixed artifact slots, so the strict barrier updates already reachable files and does not depend on a post-barrier rename. Gate 2 must prove this layout. On Linux, the barrier uses `fsync` on the file and parent directory. The request artifact and transform manifest cross this barrier before provider delivery; response bytes enter the strict claim only when their prefix crosses it. Derived-index commit precedes cursor or watermark advance. Control-ledger transitions commit transactionally and are never rebuilt from content.
3. Post-persist sinks fire exactly once, at the terminal persist; sink failures are isolated and leave a visible, replayable backlog.
4. Deletion is two-phase with the control ledger as bootstrap arbiter; tier-1 delete and derived-index GC close through a reconciler, never described as atomic.
5. Transcript tee is append-only and restart-idempotent; a gap ahead of the snapshot raises rather than silently advancing; malformed complete records become durable opaque records with byte provenance, never a silent skip (inverting the research system's locked skip behavior).
6. Corrupt derived indexes drop and rebuild from run dirs. Poison records quarantine with bounded attempts and dead-letter rows; one poison never loses the stream. Control-ledger corruption is a recovery incident and cannot use content replay as a substitute.

Artifact contract:

| Class | Persisted evidence |
|---|---|
| Inbound client | Observed client headers and body, with HTTP decoding, framing, and credential-redaction transforms recorded |
| Outbound provider | Headers and body emitted by the relay, with host, framing, encoding, and normalization transforms recorded |
| Upstream response | Provider response headers and ordered response chunks, with transfer decoding recorded |
| Downstream response | Headers and ordered chunks emitted to the harness, with framing and encoding transforms recorded |

`wire octets` is reserved for a capture point that observes transport octets. Application-level HTTP artifacts never inherit that name. Relay fidelity compares independent client and upstream byte oracles; persisted body fidelity, structural round-trip, and intentional secret omission are separate results. E4's artifact-first ordering remains.

The unkeyed digest domain is the versioned canonical redacted artifact plus its transform manifest. If credential identity must be provable in the enterprise tier, Identity supplies a key outside the agent principal's reach and Transport computes a keyed HMAC transiently over the credential-bearing source field. Bare hashes of credential-bearing bytes are prohibited because they provide an offline verification oracle.

Recovery precedence is explicit:

| Disagreement | Authority and recovery |
|---|---|
| Content directory exists, lifecycle row missing | Quarantine content; rebuild derived indexes only; never infer authorization or lifecycle |
| Lifecycle row exists, content directory missing | Preserve ledger, mark `content_missing`, surface degraded; never fabricate content |
| Staged delete exists | Tombstone governs; resume erase and record outcome |
| Hold conflicts with retention or delete | Authoritative hold blocks erasure until an audited release |
| Audit intent lacks an outcome | Preserve `InDoubt`; content presence cannot rewrite it as success or failure |

Per-exchange state machine (product-contract plus security study, reconciled): request staging, request durable, forwarding, response streaming, complete, interrupted, delivery unknown. Never infer non-delivery after the forwarding boundary; recovery exposes Delivery Unknown and never auto-resends. Per-session capture states: pending, active, complete, lost (evidence attached), failed. Durable rows, reconciled on restart by the same sweep pattern as spawn intents.

## 9. Identity, security, privacy, credential model

**[F] V1 threat model.** One non-adversarial operator observes their own agents on one host, and operator, daemon, and agent processes share one local UID. `crates/lilo-im-core/src/audit.rs::AuditDecision::evaluate_local` allows every action for that matching UID. `0700` directories and `0600` files exclude other UIDs but cannot stop the agent from altering or directly reading same-UID evidence. V1 evidence is attributed and corruption-detectable under normal operation; it is tamper-evident at best and carries no tamper-proof enterprise claim.

- Identity owns principals, capture authorization actions (start, metadata read, restricted content read, export, delete, retention change, hold, repair), audit, credential sources, and future encryption keys.
- All product reads are daemon-mediated through the Transport variant of `internal/wire/src/lib.rs::LilodRpc`. The daemon reads tier-1 disk only after Identity authorization and records an access audit. `lilo transport paths` is removed from v1 because it would establish an unaudited direct-read product boundary. Same-UID filesystem access remains an explicit v1 limitation.
- Peer credentials are extracted before any request body is read; operator RPC frames are bounded; worker channels and capture leases are one-use and process-bound rather than SessionId-only.
- The per-session loopback endpoint is a data-plane listener. Transport adds no management listener. The endpoint accepts only the expected adapter host and path, requires session or process binding, caps connections, request bytes, decoded expansion, and concurrent streams, applies header, body, idle, and total deadlines, validates upstream TLS, and rejects arbitrary CONNECT. Hostile same-UID sibling tests attempt connection theft, capability replay, host confusion, path confusion, slowloris, and limit exhaustion.
- Transport is a transient processor of provider credentials. It may relay a credential only for the bound upstream request. It may never own, reuse, refresh, persist, log, index, export, or return the credential. The canonicalization boundary strips credential headers before persistence, then records the intentional omission in the transform manifest. The body posture remains U13: write-time body redaction or verbatim encrypted body artifacts with redacted projections.
- Child environment is an explicit allowlist; secrets never enter argv, durable intent JSON, audit rows, logs, metrics, doctor output, or API payloads; no capture RPC serializes full environments.
- Capture roots are `0700`, files `0600`, opened with `O_CREAT|O_EXCL|O_NOFOLLOW` relative to directory descriptors. Symlink swap under `LILO_HOME` is defeated structurally.
- Secret canaries scan DB rows, files, logs, argv, doctor output, exports, and error paths. The never-capture test fails closed.

**[R] Enterprise integrity precondition.** Strong integrity requires a distinct agent principal, a process-bound capability carried on every read path, and an anchor outside that principal's reach. The minimum anchor is a hash chain with checkpoints signed by a key the agent cannot read. Restricted blobs use an Identity-supplied encryption key, and every content read and export is access-audited. Enterprise copy stays blocked until hostile same-UID direct-file tests demonstrate the remaining v1 limitation and the distinct-principal tier passes its own adversarial tests.

## 10. Launch readiness and per-request failure semantics

Mandatory launch sequence:

1. The Session app coordinator authenticates the operator and commits a secret-free composite intent containing the authorization audit, `SessionId`, capture policy, preparation state, runtime state, and idempotency key.
2. Through its Transport port, the coordinator prepares the capture root, commits a versioned header with the platform durability primitive, starts the worker, and receives a one-use capture lease carrying child launch material.
3. Readiness proves real work: listener bound and session-bound, adapter qualified, store writable, header readback durable, and lease live. TCP accept alone is insufficient.
4. Only then does the coordinator call `internal/runtime/daemon/src/server/spawn.rs::SpawnCoordinator::begin_spawn`. Runtime consumes the lease material through `LaunchSpec`; the lease remains held through shim start, child start, and the first provider request.
5. Every Runtime outcome cancels or finalizes the lease. Fault injection covers each interval between prepare, readiness, shim start, child start, first request, and first response chunk.
6. Session commits Running after process start plus capture readiness. A separate `first_exchange_observed` receipt records the first positive provider response. No launch state implies that a provider responded.
7. Preparation failure aborts before `begin_spawn` with `capture_bind_conflict`, `capture_start_timeout`, or `capture_store_unavailable`. Runtime failure releases the lease. Provider auth errors, 429s, and 5xx responses remain captured provider outcomes.

**[R] Availability contract.** `capture_start_timeout` is 3 seconds and completes before Runtime enters its existing 10 second ShimReady wait at `internal/runtime/daemon/src/api.rs::spawn_domain`; the two ceilings are sequential and observable separately. Capture adds at most 500 ms p95 to successful launch. E6 fails if pre-provider request overhead exceeds 100 ms p95 at 1 or 5 concurrent streams, 250 ms p95 at 20 streams, or if streamed response relay adds more than 10 ms p95 chunk latency at any tested concurrency. Gate 2 measures these on the target macOS and Linux platforms. V1 has no break-glass setting: capture unavailability stops managed launches on the host, and doctor reports the reason.

Per-request resource and durability contract:

- The encoded client request-body ceiling is 64 MiB; an adapter may publish a lower provider limit. The response writer allows at most 1 MiB of unsynchronized bytes and an 8 MiB queued disk spool per exchange. Kernel or power failure may lose only that unsynchronized response suffix; recovery marks Interrupted. At spool high water, the relay applies upstream backpressure for at most 5 seconds. No progress produces typed Interrupted evidence and follows U1. The per-session lifetime ceiling in U11 remains a separate retention decision.
- Before provider delivery, the canonical redacted request artifact and transform manifest cross the strict platform barrier from section 8. Each synchronized response prefix carries the same strict guarantee. Postgres and derived observers remain off the hot path.
- A persistence or quota fault before upstream delivery returns HTTP 422 with `{"source":"lilo","type":"lilo_capture_error","code":"<stable_code>","message":"capture unavailable"}`. Request bodies over 64 MiB return HTTP 413 with the same envelope and `capture_request_too_large`. These client-error statuses are deliberately non-retryable under the harness retry contract. The capture record sets `origin=lilo`; CAPTURE is `failed` with `failure_origin=lilo` and the stable code. The daemon records the session and operator guidance; CLI and doctor render that record.
- After provider delivery begins, storage failure preserves the durably synchronized prefix as Interrupted, records a capture fault, and follows U1. Partial evidence is never presented as complete and the proxy never fabricates a provider response.
- Comprehension fails open: unknown traffic relays unmodified and persists as an unparsed exchange within the same byte and spool bounds.
- X6 validates the 64 MiB ceiling and spool policy against multi-turn requests, cached prefixes, images, and production-shaped response streams. It proves the APFS pre-created-directory contract with `F_FULLFSYNC`, the Linux file-plus-directory `fsync` sequence, strict request, manifest, and synchronized-prefix durability, and the 1 MiB Interrupted response-loss bound. Failure reopens the scoped claim with Stuart.

## 11. Lifecycle, recovery, retention, deletion

- Capture state rides durable rows keyed by `SessionId` and reconciles on daemon restart exactly as spawn intents do; the 30s probe sweep extends to capture liveness, transitioning `active` to `lost` with evidence when the worker is gone.
- Exit ordering: agent terminal, final provider bytes drained, capture finalized and sealed, completeness recorded, Session terminal state reconciled. Finalization failure keeps the Runtime outcome and exposes the capture as incomplete; recovery is idempotent.
- Shutdown ordering: stop accepting launches, quiesce agents per policy, drain and finalize captures, stop Transport background work, close stores. Producers drain before consumers.
- Crash matrix: every boundary (intent commit, worker start, ready commit, spawn, running commit, request staging, request durable, upstream write, response chunk, blob activation, DB finalize, audit intent, tombstone, unlink, graceful shutdown) has a required recovery and a forbidden outcome (security study's full matrix is normative). Restart proves no silent loss, duplicate, orphan, or guessed result; uncertainty stays typed Delivery Unknown.
- Retention is configured in `settings.toml`, age and global-size bounded, enforced by a daemon sweeper, audited, and surfaced in doctor. U11's numerical defaults must close at Gate 3 and ship with capture.

Exhaustion order is normative:

1. Doctor warns when free space crosses `warning_bytes`, which must be greater than the configured `reserve_bytes`.
2. At `reserve_bytes`, new launches are rejected with `capture_space_reserve` while existing captures retain their reserved capacity.
3. Each session has a shipped `session_byte_ceiling`. Crossing it writes a typed `capture_truncated` outcome with byte counts and applies U1; no content is silently dropped or described as complete.
4. Retention never erases an active capture. Holds override expiry. The reserve, warning threshold, and session ceiling are mandatory release fields even though Stuart still owns their values at U11.

`lilo delete session` becomes terminate-then-erase. It writes a tombstone, terminates an active Runtime, finalizes or marks the capture incomplete, erases every daemon-owned content replica and derived index, removes the Session row, then records the deletion outcome. A repeated delete by full `SessionId` resolves the tombstone and returns typed `already_deleted`. Termination without erasure is never an alternate meaning of delete; whether a separate verb ships is U16.

Data lineage and deletion closure:

| Content class or replica | Delete, expiry, hold, and erase contract |
|---|---|
| Canonical request, response, manifest, transcript snapshots | Daemon owned; tombstone and hold governed; deleted on explicit erase or expiry; closure scans every owned root and index |
| Quarantine and dead-letter evidence | Daemon owned; follows the source tombstone and hold; cannot outlive source deletion |
| Daemon-created exports under `LILO_HOME` | Daemon owned; tracked as replicas and erased with the source unless held |
| Exports copied outside `LILO_HOME` | Operator owned and outside daemon authority; export response and manifest disclose this boundary |
| Staged delete directories | Daemon owned; tombstone resumes erase after crash; never restored as live content |
| Future content-addressed blobs | Daemon owned; reference decrements are transactional; erase occurs only at zero live or held references |
| External backups and snapshots | Outside daemon authority; enterprise policy must define backup expiry and operator proof of erasure |

The surviving deletion audit contains `SessionId`, principal, authorized action and decision, policy version, request and outcome timestamps, deleted content classes, byte counts, hold disposition, completion state, and stable error code. It contains no captured prompt, response, credential, or export payload.

## 12. Operator and UI/CLI experience

- `lilo get session` gains a CAPTURE column (`active`, `complete`, `lost`, `failed`; no `none` for session-backed runs) via `internal/session/app/src/cli/output.rs::print_session_table_with_rows`; JSON follows free from serde on `Session`.
- `lilo transport list | show <session> | export <session>` is the third operator namespace, read and ops only, no spawn verb. It is authored in `tools/schemas/cli.toml` and dispatched through the Transport `LilodRpc` variant. The daemon authorizes the view, reads tier-1 disk, and records access audit. Direct path disclosure is absent from v1.
- Agents self-inspect through the same RPC via `lilo transport show $LILO_AGENT_SESSION_ID --output json` and the existing `lilo mcp` surface; sharing between agents is by `SessionId`, which mail already carries.
- `lilo doctor` gains a transport block: store reachable and migrated, loopback bind capability, active/lost counts with warnings, disk and quota headroom, retention lag, adapter revisions. No per-substrate doctor.
- `lilo capture` remains the tmux pane snapshot verb; wire capture never reuses that name. `lilo daemon start --ready-check` proves capture among its subsystems by doing real work through the real teardown.
- Export is a self-contained bundle with versions, transform manifest, intentional-secret-omission record, and authority disclosure for copies outside `LILO_HOME`. The support payload is the bundle plus `lilo doctor --output json`.
- The human UI (separate TS/Electron train) consumes the committed CLI JSON schema as its contract; whether a headless HTTP read surface ships in v1 stays open (U6). The UI never reads capture files directly.
- Nothing prints on success. The operator-visible surface is session verbs that now return real answers, one doctor block, and failure states that name themselves.

**[R] V1 read contract.** Before Gate 5 closes, generated CLI JSON and typed RPC schemas publish:

- `schema_version`, stable error codes, and bounded cursor pagination with default 50 and maximum 200 records;
- metadata responses capped at 2 MiB, content slices capped at 1 MiB per call, and streamed export outside the JSON frame;
- full and short `SessionId` selectors resolved against the Transport index even when the Session row is absent, with stable `not_found` and `ambiguous_selector` outcomes;
- separate Identity actions for metadata, restricted content, and export, applied before selector candidates or content are disclosed;
- Transport-owned MCP tool schemas exposed by the existing `lilo mcp` composition, with the same limits, authorization, and errors.

## 13. Test and acceptance matrix

Acceptance evidence classes (test-evidence study, 30 ranked invariants; all recreated natively, zero code ported):

1. Relay fidelity: an independent client-and-upstream byte oracle compares the inbound client, outbound provider, upstream response, and downstream response directions while streaming; the relay claim passes only for fields and chunks declared untransformed.
2. Persisted body fidelity: canonical artifact bodies equal the independent oracle after the versioned transform manifest is applied.
3. Structural round-trip: parsed then serialized supported structures match their declared canonical form; SSE incremental parse equals whole-buffer parse under proptest.
4. Intentional secret omission: credential fields are absent from persisted and exported artifacts, the omission is represented in the manifest, and optional credential identity uses keyed HMAC only.
5. Isolation: a raising derived observer never degrades the proxied stream; unparseable payloads keep bounded artifacts plus a parse-failure marker; sink explosions never escape the hook.
6. Durability: crash injection at every write stage leaves zero residue; two-phase delete arbitration; derived indexes rebuild from sidecars; whole-tree byte-snapshot equality as the idempotence oracle; transcript tee restart-idempotent with hard gap failure.
7. Pipeline: quarantine with dead-letter provenance; drift observational only; replay determinism byte-identical to whole-input replay; repair never fabricates.
8. Identity: correlation contractual on `SessionId` with zero heuristic probing; trusted launcher stamp beats derived re-bind; fail closed on ambiguous binding; subagent corpus joins.
9. Process: parent-death reaping triad with a probative control; pid-reuse-safe supervision; SIGTERM-to-SIGKILL escalation; shutdown ordering proven at a real socket; fail-closed demux.
10. Security: credential headers provably absent; canary scans across DB, files, logs, argv, doctor, and export; hostile same-UID siblings attempt RPC and direct-file access. The v1 test documents that same-UID file integrity is outside its guarantee. Enterprise fails until a distinct principal and external checkpoint prevent or detect that attack without trusting the agent.

Gaps the research evidence never covered, authored fresh: tailer rotation and truncation resync (inode tracking), timestamp monotonicity, repair after byte-level corruption, concurrent atomic-write races, and the four-part fidelity suite above.

Two research tests invert into acceptance tests: persistence failure must prevent provider release and reach Runtime (was: return None on failure); malformed complete transcript records must produce durable opaque evidence (was: silent skip).

Compatibility gates:

1. A run directory written by each retained earlier adapter revision must read through the current reader with declared transforms and stable JSON.
2. CI constructs the migration chain from an empty database through every revision and rejects branches, duplicate versions, gaps, or down-level readers.

Release-gate assertions: ready-check includes capture; proxy accepting before agent pid exists and proxy kill before exec aborts with a stable code; child env contract exact; the launcher conformance test covers every `registered_launchers()` entry; a pre-delivery 422/413 capture fault yields one harness failure, zero upstream requests, zero retry amplification, and no persisted artifact that attributes the local fault to the provider; CAPTURE and the capture record mark `origin=lilo`; mid-run kill reaches `lost`; every artifact class is readable by `show` or `export`; credential export contains zero credential bytes; delete closes every daemon-owned lineage root and index while preserving the enumerated audit fields; retention and reserve policy works; generated-surface guards preserve `lilo capture` as tmux; redirect feature regressions are tested and disclosed; grep gate finds zero `tm`/transport-matters/`TRANSPORT_MATTERS_*` relationships; the compatibility and migration-chain gates pass; full `just check && just build && just test` is green.

House method: surgical failure injection by argument predicate; residue assertions after every injected failure; dual-path parametrization (fresh and provisional-finalize); byte-level determinism; control tests proving the repro is probative; hostile same-UID sibling tests with real peer credentials. Fake authorizers are prohibited.

## 14. Enterprise release gates

Reconciled with the enterprise-gates synthesis input (accepted). The enterprise claim, once its prerequisites pass, is: managed model inference exchanges on this host have attributed authorization, declared-transform content evidence, provider response evidence, and audited access. The claim excludes shell activity, direct egress, human edits, and every action outside the managed inference channel. V1's shared-UID posture cannot carry this copy. Enterprise qualification requires a distinct agent principal, process-bound read capabilities, and signed integrity checkpoints outside the agent principal's reach.

Gate set:

1. Every crash-matrix row has deterministic fault injection at each database, file, sync, rename, process, and socket boundary.
2. Every hostile-workload row (slowloris, oversized frames and request bodies, connection storms, spool exhaustion, stream floods, compression bombs, disk full, Postgres outage, symlink swap, clock jumps, retention races) has a bounded resource assertion and a typed operator-visible result.
3. Durability ordering proven at provider and agent boundaries under the locked barrier policy; restart proves no silent loss, duplicate, orphan, or guessed result.
4. Secret canaries across control tables, intent JSON, audit, logs, argv, metrics, doctor, errors, sanitized views.
5. Path policy proven: ownership, `0700`/`0600`, no symlink traversal, safe custom `LILO_HOME`.
6. Authorization tests use real peer credentials and hostile same-UID siblings. V1 tests expose its direct-file limitation; enterprise tests prove distinct-principal read denial and externally anchored tamper detection.
7. Nonvacuous shared corpora: Claude HTTP, Codex HTTP and WebSocket, unknown, malformed, pinned historical revisions.
8. Retention and deletion: quotas, warning threshold, free-space reserve, per-session ceiling, hold, concurrent export, every lineage class, tombstone recovery, external-copy disclosure, erase semantics, audit survival.
9. Encryption at rest with Identity key provider; hash-chain audit with signed checkpoints; U9 closed by counsel using jurisdiction-specific primary authority before managed-deployment release.
10. Supply chain: dependency, vulnerability, secret, and source scanning; SBOM; signed and notarized artifacts; pinned CI actions; CODEOWNERS for capture and identity; release attestations already configured extend to capture.
11. Structural gate: build and release inspection prove zero relationship with `tm` or transport-matters from the built archive.
12. The repository gate remains `just check && just build && just test`; structural changes also run `fmm generate && fmm validate`.
13. Every retained artifact revision passes reader compatibility, and CI proves one linear migration chain.
14. The typed Transport RPC, generated CLI JSON, pagination, payload limits, stable errors, selectors, per-view authorization, and MCP ownership contract is published and compatibility-tested.

## 15. Implementation sequence with stop gates

The sequence binds the research program's decision register (D1 to D11, E1 to E7) to the enterprise-gates adjudication. Gates 0 to 5 are decision gates; implementation phases follow only after Gate 5. No gate locks an unresolved design.

**Gate 0, governance and contract honesty (before this document governs implementation).** Close D8 native config homes, D9 Claude first, and D10 artifact-first ordering; adopt observation-only v1; withdraw stale launch-chain prose; add the zero-dependency grep gate; record the retracted syntax claims. Exit: the managed-inference coverage boundary, same-UID limitation, daemon-mediated read path, four-direction evidence vocabulary and digest domain are explicit; the spawn matrix has no implicit-success cell; the root `CLAUDE.md` Transport verb list removes `paths` and matches `list`, `show`, and `export`; docs match `LESSONS.md:18-19`; both source pins remain recorded; and the `runtime_matters` doctor repair is planned as a generated wire-contract change with compatibility review.

**Gate 1, interposition physics.** X1 subscription-auth null relay and complete harness feature matrix, X2 Codex base-URL probe, X3 Rust SSE fidelity spike, X4 env-only interposition through the real spawn path, X7 background-supervisor coverage. Exit: interception mode resolved per harness; D2 language and D3 injection carrier closed; inference, streaming, tools, subagents, MCP tool search, resume, background work, and Remote Control outcomes recorded; an operator disclosure list published; U15 briefed; and the coverage exclusion list written into the product contract.

**Gate 2, identity, coordination, durability, and availability.** X5 managed-mint four-way key agreement; X6 per-artifact process, kernel, and power failure injection using the APFS pre-created-directory `F_FULLFSYNC` contract and Linux file-plus-parent `fsync`; real 64 MiB request-boundary coverage; 1 MiB unsynchronized and 8 MiB queued-spool tests; overhead at 1, 5, and 20 streams. Exit: request artifacts, transform manifests, and synchronized response prefixes pass the strict barrier; every lost response suffix is at most 1 MiB and recovers as Interrupted; the split authority contract passes recovery precedence tests; one Session coordinator and dependency direction are locked; one-use lease fault injection covers every preparation-to-first-request interval; p95 added launch is at most 500 ms; the 3 second capture timeout remains distinct from the 10 second ShimReady timeout; per-turn ceilings from section 10 pass; D5, D6, and U2 close.

**Gate 3, Stuart decisions (briefed by X9 and gates 1 to 2 evidence).** U1 mid-run loss; every OPEN cell in the spawn matrix including Codex, Docker, Other, and raw spawn; U13 body posture; U14 future hold capability; U11 concrete age, global-size, warning, reserve, and session-ceiling values; U9 legal posture; U15 Remote Control tradeoff; U16 terminate-only verb. Exit: every matrix cell reads CAPTURED or REJECTED BEFORE SHIM SPAWN; every release field has a value; each owner decision has an operator-experience brief; none is inherited from a prototype.

**Gate 4, foundation repairs (littleorgans-side, before capture code lands).** Bounded authenticated RPC framing; one-use process-bound launch capability; secret-free spawn intents; event journal replacement or rebuild; enforced `LILO_HOME` path policy; spawn idempotency key. Exit: each repair merged with the hostile-workload row it retires; capture design references these seams only after repair lands.

**Gate 5, contract synthesis and program exit.** Fold gate outputs into the Transport product decision record: boundary invariants, both state-machine granularities, artifact classes and transforms, authority and recovery precedence, deletion lineage, and acceptance suites. Publish the typed Transport RPC and generated CLI JSON contract before closure, including bounded pagination, payload limits, stable errors, versioning, orphan-capture selectors, authorization per view, and MCP ownership. Exit: earlier adapter fixtures read with the current reader; CI proves one linear migration chain; the decision register is closed for Claude; only then is an implementation plan warranted.

Implementation phases after Gate 5: native skeleton (Transport context, typed RPC variant, Identity actions, migration, filesystem policy, `WireCapture` capability, coordinator and lease, readiness, recovery, doctor block) proven against a deterministic fake provider first; then the Claude vertical slice (real proxy, tier-1 persistence, transcript tee, `lilo transport list|show|export`, CAPTURE column, terminate-then-erase, lineage closure, retention and reserve enforcement) whose clean-install acceptance is the release gate. Build and install with no `tm` on PATH and no transport-matters checkout; prove one `SessionId` across authorization, intent, lifecycle, capture, and read model; kill the daemon at every boundary and reconcile idempotently; force storage failure with no direct fallback. A release in which this slice fails does not tag. Enterprise qualification follows only after distinct-principal integrity, encryption, legal, audit, supply-chain, and platform gates pass.

Stop rules: every experiment has a falsification criterion and a three-day timebox; a falsified experiment stops its branch and reopens the named decision, never silently continues; program-level stop and escalation to Stuart if SSE fidelity fails in Rust and its fallback, or if env-only interposition falsifies and the wrapper alternative is rejected on boundary grounds. Do not expand v2: no multi-host, no UI train work, no fidelity-diff product, no isolated runtime homes, no pause-and-edit, no shared proxy.

## 16. Decision ledger

### LOCKED (governing frame and locked repo decisions)

| # | Decision |
|---|---|
| L1 | Transport capture is a mandatory, first class littleorgans bounded context; littleorgans cannot ship without it |
| L2 | Zero `tm`/transport-matters dependency in any form: no invocation, packaging, versioning, porting, or outreach |
| L3 | `SessionId` (UUIDv4, Session-minted pre-process) is the sole join key; provider ids are attributes |
| L4 | One env prefix (`LILO_`, registry-gated), one state root (`~/.lilo`), one Postgres, one migration chain; no SQLite, no second root |
| L5 | Transport observes only: never authorizes, spawns, reconciles, refreshes credentials, or mutates traffic |
| L6 | Operator surface is `lilo transport ...` (reads and ops, no spawn); `lilo capture` stays tmux; doctor stays aggregate |
| L7 | v1 is local-first (one operator, one host, one `lilod`); v2 scope excluded |
| L8 | The human UI is a separate release train consuming a committed read contract |
| L9 | V1 has no capture break-glass path; capture unavailability rejects managed launches |

### EVIDENCE-SUPPORTED (converged positions, subject to named gates)

| # | Position | Basis |
|---|---|---|
| E1 | Redirect mode is the v1 lean, conditional on X1's feature matrix and U15; MITM/CA is an enterprise fallback branch | Vendor overrides support inference, while Claude Code 2.1.196 disables Remote Control and defaults MCP tool search off under a non-first-party base URL |
| E2 | Claude first; Codex gated second phase | Every Codex-specific mechanism is strictly harder; X2 may collapse the gap |
| E3 | Native config homes in v1; no credential broker problem class | The broker existed only because the experiment redirected homes |
| E4 | Canonical artifacts and transform manifests precede IR; parsing grows from read demand | Derived projections rebuild from artifacts; the four-part fidelity oracle qualifies exactness |
| E5 | Content and launch facts use filesystem authority; audit, lifecycle, tombstone, hold, and deletion outcomes use an authoritative transactional control ledger; only indexes and read models replay | Recovery cannot infer governance from content |
| E6 | Per-session isolation in the existing supervision tree; in-process task versus Runtime-owned child remains U2; shared proxy rejected for v1 | Blast radius and ownership table |
| E7 | `LaunchSpec` is the injection carrier; one Session app coordinator prepares a Transport lease before Runtime `begin_spawn` and owns cancellation/finalization | Async preparation and one dependency direction cannot live in a pure synchronous rewrite |
| E8 | Launcher-owned session mint (`--session-id <SessionId>`), pending X5 | Dissolves uuid5 synthesis and heuristic probing entirely |
| E9 | Launch-time fail closed: no capture readiness, no agent process, typed abort codes | All studies agree; only the mid-run branch is open |
| E10 | Comprehension fails open with recorded unparsed exchanges; unknown shapes preserved | Capture must survive provider drift |
| E11 | Credential headers are omitted at canonicalization, transforms are recorded, and persisted evidence never mutates on read; body posture is U13 | Headers have no evidentiary value; read-time mutation destroys evidence |
| E12 | Two-stream invariant: wire and transcript captured separately from v1, never collapsed; transcript tee best-effort with recorded gaps | The fidelity option stays open only if both streams exist |
| E13 | No dark stores: every artifact class ships with a read path in the same release | The experiment's central product failure |
| E14 | Retention, deletion cascade, and doctor visibility ship in the same release as capture | The experiment's largest validated gap |
| E15 | Correlation spine additionally records the `x-claude-code-*` header family | Free topology, no body parsing |
| E16 | Foundation repairs (bounded RPC, launch capability, secret-free intents, journal rebuild, path policy, idempotency) precede capture code | Capture traffic is larger and more adversarial than control traffic |
| E17 | Resource exhaustion uses explicit ceilings, backpressure, typed faults or truncation, and no silent continuation; v1 numbers are in section 10 and retention values close at U11 | Mandatory capture and bounded-host operation require a named outcome |
| E18 | Product reads are daemon-mediated and audited; direct path disclosure is excluded from v1 | CLI-direct file reads would bypass Identity and access audit |

### UNRESOLVED (open decisions with owners)

| # | Question | Resolver |
|---|---|---|
| U1 | Mid-run capture loss: terminate the run (lab behavior) or keep alive with a loud `lost` state | Stuart, briefed by X9 |
| U2 | Implementation language and process topology, formally | X3, X4 (Rust in-workspace is the evidence-supported lean; not decided until the spike passes) |
| U3 | Whether the strict request, manifest, and synchronized-response-prefix barriers pass section 10 latency budgets on target macOS and Linux | X6; the unsynchronized response suffix remains bounded to 1 MiB with Interrupted recovery |
| U4 | Raw `lilo runtime spawn` posture: CAPTURED or REJECTED BEFORE SHIM SPAWN | Stuart, Gate 3 |
| U5 | v1 artifact depth: raw only versus raw plus parsed IR at write | Read-demand review after X6 |
| U6 | Headless HTTP read API in v1 versus CLI JSON only | Stuart, with the UI train |
| U7 | Fidelity inputs: transcript snapshots from v1 (E12 says yes in principle; cost unquantified) and whether v1 must store everything the future diff needs | Cost measurement in Phase 4 |
| U8 | Docker/container cells: CAPTURED or REJECTED BEFORE SHIM SPAWN | Stuart, briefed by X8 at Gate 3 |
| U9 | Legal posture of mandatory enterprise capture, with jurisdiction-specific primary-authority review | Stuart with counsel, before managed-deployment release or enterprise copy |
| U10 | Background-agent supervisor coverage and settings-file enrollment | X7 |
| U11 | Retention age and global-size defaults, warning threshold, free-space reserve, and per-session byte ceiling | Stuart at Gate 3; all values ship with capture |
| U12 | Whether provider-native session ids are stored as secondary metadata for provider-console cross-reference | Design detail, post-Gate 5 |
| U13 | Body storage posture: write-time body redaction versus verbatim encrypted body artifacts with redacted projections. Unredacted persisted bytes require encryption from day one | Stuart, Gate 3 |
| U14 | Whether the v1 hot path must be architected async-hold-capable so pause-and-edit remains buildable later, or "store the inputs, compute later" honesty suffices | Stuart, Gate 3, priced by a hold-blocking spike |
| U15 | Whether Remote Control unavailability under mandatory redirect capture is an accepted product tradeoff or requires mitigation | Stuart, after X1 at Gate 3 |
| U16 | Whether termination without erasure receives a separate user verb; `lilo delete session` always terminates then erases | Stuart, Gate 3 |

### EXPLICITLY REJECTED

| # | Rejection |
|---|---|
| R1 | Any `lilo`-to-`tm` launch chain, packaging, or version coupling; porting the Python plane in any form (FFI, subprocess, vendoring) |
| R2 | mitmproxy-class dependencies, Python/FastAPI/Alembic runtime zoo, second migration system, foreign env prefixes |
| R3 | The exec-wrapper inversion as the enrollment premise (stale NOTES Decision 1); SQLite `index.db`; channel homes |
| R4 | uuid5 session synthesis and heuristic exchange correlation |
| R5 | Traffic mutation in any form in v1: overrides, breakpoints, pause-and-edit, forged responses |
| R6 | Credential brokering: harvesting, caching, spending, refreshing, or persisting user credentials; Keychain writes; writes outside `~/.lilo` |
| R7 | Shared proxy as initial topology; god-process composition; a second composition root or management listener |
| R8 | Unauthenticated authority routes (local file GET, PTY keystroke bridges, unguarded mutation routes); capture RPCs serializing environments |
| R9 | Write-only substrates: any capture table or artifact class without a same-release reader |
| R10 | Silent fail-open capture writes; capture loss as only a log line |
| R11 | Read-time mutation of raw evidence; destructive legacy-cache migration; whole-file index rewrites presented as durability |
| R12 | Capture-core ownership of token counting, certification machinery, control-plane verbs, canvas/UI state |
| R13 | Claims exceeding implementation: decoded bodies presented as wire octets; a fidelity diff that does not exist; orthogonality claims while holding authority |
| R14 | Capture opt-out flag; capture of agent-run shell commands; public share links in v1; analytics dashboards before governance |
| R15 | Construction-level v1 coverage claims beyond managed inference without host or container egress control |
| R16 | `lilo transport paths` or any CLI-direct capture-file read that bypasses daemon authorization and access audit |

## 17. Self-audit

Original synthesis audit, rechecked during the bounded correction:

- [x] All 13 phase-one artifacts consumed at `Status: COMPLETE`; both synthesis inputs consumed only after each reached `Status: COMPLETE` (current-code-reuse after its orchestrator-directed correction); sections 5, 8, and 14 reconciled against them; no stale IN PROGRESS input consumed
- [x] Every required section present (first-screen framing, thesis, value, taxonomy and minimum v1, ownership and exclusions, reuse map, lessons, interception tree and experiments, data authority, security model, launch and failure semantics, lifecycle and retention, operator experience, test matrix, enterprise gates, sequence with stop gates, four-class decision ledger); both source pins stated in the header
- [x] Zero tm dependency: every mention of `tm`/transport-matters is as research evidence, rejection, or withdrawal target; no invocation, packaging, versioning, porting, or outreach proposed
- [x] No unsupported runtime claim: source facts, inferences, and recommendations are marked; no test execution or live-traffic claim is attributed to the pinned commits beyond what the phase-one artifacts themselves verified; the pinned auth syntax defect is recorded as retracted and carries no load
- [x] `transport-matters/NOTES/` never cited (the only `NOTES/` references are littleorgans' own superseded note); load-bearing repository evidence uses `path::symbol` citations; external claims cite primary sources via the protocol research artifact
- [x] Contradictions reconciled through explicit decisions or owner-tagged UNRESOLVED entries
- [x] Final line count is 552; em-dash scan, status scan, and bounded archive diff pass

Consensus correction map:

- [x] CS-1 integrity honesty: sections 1, 2, 9, 13, 14
- [x] CS-2 daemon-mediated read path: sections 3, 9, 12, 16
- [x] CS-3 mandatory managed-inference scope: sections 1, 3, 4, 7, 14, 16
- [x] CS-4 spawn coverage matrix and conformance: sections 3, 15, 16
- [x] CS-5 artifact vocabulary and digest domain: sections 1, 3, 8, 13, 16
- [x] CS-6 split content and control authority: sections 8, 16
- [x] CS-7 durability physics and resource bounds: sections 7, 8, 10, 15, 16
- [x] CS-8 availability budgets and no break-glass posture: sections 10, 15, 16
- [x] CS-9 retention exhaustion valve: sections 11, 15, 16
- [x] CS-10 deletion semantics and lineage closure: sections 5, 11, 13, 15, 16
- [x] CS-11 coordinator, lease, and readiness invariant: sections 4, 5, 10, 15, 16
- [x] CS-12 listener and credential threat model: section 9
- [x] CS-13 redirect feature regression: sections 7, 13, 15, 16
- [x] CS-14 legal-risk downgrade: sections 2, 14, 15, 16
- [x] CS-15 non-retryable capture-fault response: section 10
- [x] CS-16 compatibility, migration, RPC, CLI, and doctor gates: sections 5, 12, 13, 14, 15

Sign-off closure map:

- [x] B-1 local 422/413 origin, CAPTURE attribution, persisted-artifact assertion, and X1 retry proof: sections 7, 10, 13
- [x] B-2 option (b) per-artifact power-loss scope and 1 MiB Interrupted response-loss bound: sections 8, 10, 15, 16
- [x] F-2 APFS directory-entry limitation and pre-created-directory proof: sections 8, 10, 15
- [x] F-3 stale `CLAUDE.md` Transport verb list rewrite target and Gate 0 exit: sections 5, 15
- [x] Delta against archived v2 is bounded, under 700 lines, em-dash free, and preserves both source pins and zero `tm` dependency
