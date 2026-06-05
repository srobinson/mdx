# littleorgans Transport Capture: Definitive Synthesis

Status: COMPLETE

Updated: 2026-07-31

## What are we talking about?

littleorgans will make wire capture of agent-to-provider model traffic a mandatory, first class product capability. Every session-backed `lilo run` records exactly what the agent sent to its model provider and what came back, keyed by the platform `SessionId`, with zero setup, readable through `lilo transport` verbs. The capability is built natively inside the littleorgans monorepo as the fourth bounded context (Transport, beside Identity, Session, Runtime).

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

**[F]** littleorgans cannot answer "what did my agent actually do?" today. `lilo logs` returns nothing for tmux sessions (`internal/session/core/src/paths.rs::lifecycle_transcript_path` yields `None` for tmux); the only inspection tool is `lilo capture`, an ANSI pane scrape with no turn structure and no provider-side truth.

**[I]** Mandatory capture converts that question into a one-command answer for every run by construction, and upgrades launch truth from "a process spawned" (`ShimReady`) to "the agent reached the provider and got a response". The experimental evidence proves the mechanism is buildable without sudo, certificates, or system trust changes for the primary runtime.

**[R]** The product principle set (user-value study, converged across artifacts):

1. Capture is a property of the platform, not a feature. No enable flag, no setup.
2. Capture liveness at launch is a run invariant; derived persistence is an isolated observer.
3. One id is the spine: `SessionId`, injected as `LILO_AGENT_SESSION_ID`, keys everything.
4. Provider truth over harness self-report; wire and transcript are two streams, never collapsed.
5. Silence is the success state; capture speaks only through existing verbs.
6. Content capture ships with content governance (redaction, retention, deletion) in the same release.
7. Evidence is attributed and immutable once created.
8. Nothing ships dark: every artifact class has a read path in the same release.

## 2. User and enterprise value

Operator jobs, ranked by evidence strength (user-value study):

1. Reconstruct what happened after the fact. **[F]** Unanswerable in littleorgans today; fully demonstrated in the research system's per-exchange artifacts.
2. Confirm the launch actually worked. **[F]** The research `PromptReceipt` defines "submitted" as one correlated provider exchange with positive response evidence; capture provides that signal for free.
3. See what the agent is doing right now (live inspection).
4. Understand why a specific turn went wrong (raw request and response per turn).
5. Respond to an incident with the record already written.
6. Prove what happened (enterprise): decision audit already exists (`internal/session/daemon/src/handler/spawn.rs::begin_spawn_intent` commits the authorization audit in the spawn transaction); capture adds content evidence with digests and attribution.
7. Hand a session to another person or agent (unmet in both repos; second act).
8. Control what is retained (must be created alongside capture, not after).

**[I]** The enterprise story is "every agent action on this host is evidenced by construction: who authorized it, what was sent, what came back, whether a human touched it." An opt-in capture model cannot make that claim; mandatory is the proof. **[F]** A buyer will probe retention, deletion, and payload redaction first; the research system demonstrates the cost of deferring all three.

**[F]** Legal boundary: mandatory always-on capture of a developer's prompts is employee monitoring in the EU sense; consent is not the available basis in an employment relationship, and works-council co-determination applies in DE/NL/AT/SE (protocol research R37, primary sources cited there). **[R]** Resolve whether littleorgans enables monitoring or performs it before the word "mandatory" appears in user-facing enterprise copy. For v1 (one operator observing their own agents on their own host) this is a documentation posture, not a blocker.

## 3. Capability taxonomy and minimum coherent v1

Four tiers per dimension (capability-taxonomy study): V1 mandatory, ENT enterprise qualification, LATER deferred until read demand, DISTRACTION refused on evidence.

| Dimension | V1 | ENT | LATER | DISTRACTION |
|---|---|---|---|---|
| Wire | Loopback reverse proxy via base-URL env; byte-faithful raw capture persisted before derived work; streaming tee never buffer-only; zero mutation; anti-bypass env scrub | Scoped-CA MITM fallback for non-overridable harnesses; audited capture access | Codex WebSocket segmentation; credential-expiry observation | Multi-tenant shared proxy with per-run demux |
| Transcript | Launcher-owned session mint (`--session-id`); byte-faithful gap-detecting tee of the native transcript; best-effort, never stops the proxy, gaps recorded | Curated conversation projection | Codex seed-and-resume mint; subagent sidechains | Reconstructing harness belief by wire inference |
| Fidelity | Two-stream invariant only; v1 pipeline mutates nothing so wire fidelity is passthrough-perfect by construction | Typed drift evidence with digests gating harness versions | The wire-vs-transcript diff, as a read surface first | Diff algorithms before a single read exists |
| Artifacts | Raw request, raw response, minimal turn record, per-session index; provider-reported tokens only; UnknownBlock-style escape hatch | Content-addressed prompt and tool-set dedup; image blobs | Tool calls as rows; thinking blocks; Codex turn derivation | Proxy-bypassing count_tokens egress; full frozen IR taxonomy up front |
| Mutation | None. Observation only | Audited, identity-attributed override pipeline | Arm-once pause with timeout release | Shipping mutation before reads |
| Compatibility | One Claude adapter; fail-open comprehension (unknown shape passes through, recorded unparsed); `RuntimeCapability::WireCapture` gate | Signed versioned compatibility releases | Codex adapter; advisory-to-enforcing switch | Compat publication machinery for a pre-release product |
| Storage | Tier-1 files under `~/.lilo/data/`; raw bytes never in Postgres; session row points at the capture dir; atomic writes | Content-addressed dedup; retention with RLS-ready `owner` seam | Crash-staged dirs with full recovery predicates | A Postgres wire store before any reader |
| Reads | `lilo transport list|show|paths` off tier-1 disk; agents via CLI JSON and existing MCP reading `LILO_AGENT_SESSION_ID` | Twin-skin read service; token-bounded reads; audited raw access | Timeline projections; SSE streams | The human UI (separate train) |
| Operations | Proxy lifecycle in the shim supervision tree; kernel-allocated ports; capture state in doctor aggregate | Channel separation; loopback hardening | Fail-closed capture-health kill policy (explicit decision, not inherited) | Containerizing the proxy; rehydrating shared-proxy supervision |

**Minimum coherent v1** (verbatim conclusion of the taxonomy, reconciled with the other studies): every `lilo run claude` session is transparently routed through a session-scoped loopback reverse proxy injected at the runtime launch seam via `ANTHROPIC_BASE_URL`, with raw request and response bytes teed (streaming preserved), assembled into per-turn records, persisted with the harness's own transcript file under `~/.lilo/data/transport/<session_id>/`, keyed by the launcher-minted `SessionId`, readable via `lilo transport list|show|paths`, mutating nothing, failing open on comprehension and closed on launch readiness, gated by `RuntimeCapability::WireCapture`. Everything else is qualification, deferral, or refusal.

## 4. Bounded-context ownership and exclusions

| Context | Authority |
|---|---|
| Identity | Principals, authorization of capture actions (read, raw read, export, retention change, delete), audit, credential sources and key material |
| Session | User intent, composite spawn intent including capture preparation state, aggregate session state, reconciliation |
| Runtime | Agent process launch, shim, backends, isolation, process lifecycle and host evidence |
| Transport | Provider wire observation, capture lifecycle and persistence, transcript ingestion, capture read models, capture health |

Invariants (product-boundary study, nonnegotiable):

1. Every session-backed `lilo run` and `lilo create session` is captured by construction.
2. The agent cannot send provider traffic before capture is armed for its `SessionId`.
3. Session never reports RUNNING from Runtime readiness alone.
4. Capture failure cannot fall through silently to a direct provider path.
5. `SessionId` correlates Session, Runtime, Identity audit, and Transport metadata; provider conversation ids are attributes, never keys.
6. Transport observes and records. It does not authorize, select the agent, decide to spawn, own the process, refresh credentials, mutate prompts, or reconcile the session. The moment a capture surface can act on a session, it is a session verb and moves behind the session boundary with its own authorization.
7. Runtime owns the process; it does not parse provider traffic or own capture artifacts.
8. Identity gates capture inspection, raw access, export, retention changes, deletion.
9. A release is unshippable unless a clean install proves a captured launch end to end.

Exclusions from capture scope: override/breakpoint machinery, token counting egress, credential brokering, control-plane verbs, certification subsystems, the TS/Electron UI train, canvas/PTY products, channel homes, run-identity name allocators.

**[F]** The highest-value existing seam: the shim already phones home for its `LaunchSpec` before starting the agent (`internal/runtime/app/src/cli/shim.rs::run_for_session_blocking`), argv is materialized in exactly one place (`internal/runtime/daemon/src/api.rs::spawn_domain` line 81), and `RuntimeBackends::prepare_launch` (`internal/runtime/daemon/src/backend.rs`) is the proven rewrite precedent (Docker wraps argv there). Capture interposes at this pre-execution handoff; no external wrapper CLI is required. Attaching at the runtime layer rather than the session layer also covers the diagnostic `lilo runtime spawn` path (reject map R4.3), pending the explicit posture decision in the ledger (U4).

## 5. Current littleorgans reuse, rewrite, delete map

Reconciled across the product-boundary, boundary-map, and security-durability studies and the corrected current-code-reuse synthesis input (symbol-first audit, 388 files, 58,401 LOC). Headline: transport capture is entirely MISSING (no proxy, store, paths, authz action, CLI namespace, or doctor probe), the zero-tm baseline is validated cold, and every spawn path (session-backed, diagnostic `rtm` spawn, tmux, headless, docker, shell-resume) converges on one typed contract, `LaunchSpec`. Treat `LaunchSpec` as the single capture-interposition contract; capture wiring anywhere else would be a second path. A native capture context receives `SessionId` in-process from `SpawnRequest`; the env var stays for agent-side surfaces.

Keep and extend:

| Seam | Evidence | Reshape required |
|---|---|---|
| Typed id family, `SessionId` join key | `crates/lilo-common/src/id.rs::SessionId` | Add Transport ids only when a persisted field exists |
| Identity action registry | `crates/lilo-im-core/src/types.rs::Action` | Add Capture actions (also missing for existing `lilo capture`) |
| Transactional authorization | `internal/identity/service/src/client.rs::IdentityClient::authorize_in_tx` | Classify every Transport surface |
| Composite spawn intent, two-transaction shape | `internal/session/daemon/src/handler/spawn.rs::begin_spawn_intent` / `complete_spawn_intent` | Evolve into Session+Transport+Runtime composite intent recording capture preparation, readiness, finalization |
| Domain port pattern | `internal/session/driver/src/port.rs::RuntimePort` | Add a Transport port beside it; inject via `DaemonState` |
| Launcher registry and env upsert | `internal/runtime/launchers/src/lib.rs::runtime_env`, `resolved_argv` | Proxy env injection per launcher; conformance tripwire (`conformance.rs` asserts `argv.len() == 1`) updated deliberately if argv changes |
| Backend rewrite seam | `internal/runtime/daemon/src/backend.rs::prepare_launch` | Capture decorator symmetric to `DockerRuntimeBackend` |
| Shim handoff and supervision | `internal/runtime/daemon/src/shim_socket.rs::shim_env` (one-var contract, guard-tested) | Capture config rides `LaunchSpec.env` over the UDS, not the bootstrap env |
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
| Runtime port | `internal/session/driver/src/port.rs::RuntimePort` | Reuse as is; its `capture` is tmux scrollback and wire capture is a different bounded context with its own seam, not forced through this port |
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
- `docs/reference/env-vars.md` UUIDv7 claim for `LILO_AGENT_SESSION_ID` (code is v4).
- Doctor response `runtime_matters` naming residue (`internal/session/core/src/proto/doctor.rs`).

**[F]** Verified negatives that define the acceptance baseline: zero `tm`/transport-matters/`ANTHROPIC_BASE_URL`/proxy/mitm references in Rust, Cargo, workflow, or shell sources; no Transport workspace member, RPC variant, CLI namespace, path, or doctor slot.

## 6. Experimental lessons to leverage and to reject

Leverage (reimplement under littleorgans ownership; tm evidence cited as lab proof):

1. Interpose before launch; proxy listening before the agent execs (`cli/runner.py::run_client_children_until_outcome`).
2. Claude needs no MITM: loopback reverse proxy plus `ANTHROPIC_BASE_URL` (`captured/claude.py::_build_claude_captured_invocation`); route persisted into the managed harness home so re-spawned subprocesses stay routed (`cli/claude_home.py`).
3. Launcher-owned session mint closes identity (`claude --session-id <uuid>`; `owned_transcript_binding.py`): wire, transcript, and store agree on one key with zero heuristics.
4. Tier-1 raw bytes first, durably, before any derived observer (`storage/exchange_sink.py`); observers isolated; atomic temp+fsync+rename (`atomic_io.py::write_atomic_bytes`).
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
9. Claims exceeding implementation: "raw" HTTP artifacts are decoded text, not wire octets (`exchange_recorder/artifacts.py::request_raw_bytes`); the flagship fidelity diff never existed.

Pinned-baseline auth syntax question, adjudicated and closed: two studies reported `credential_refresh.py` and `credential_source.py` as `SyntaxError` at the pin; the topology study re-verified with the repository's declared interpreter (`requires-python >= 3.14`, PEP 758 permits unparenthesized multi-exception clauses) and found both files parse clean, and an orchestrator-directed direct check with the project interpreter (`api/.venv/bin/python`, 3.14.5) successfully `ast.parse`d both exact blobs at `a252df24`. **[F]** The parse-failure claims are retracted as ambient-interpreter error. No conclusion in this synthesis rests on "tm was broken at the pin"; the zero-dependency rule and the credential-broker rejection stand on product and authority-boundary grounds alone.

## 7. Interception decision tree and cheapest decisive experiments

Decision tree per harness (protocol research, primary vendor sources):

1. Does the harness document a base-URL override? Yes for Claude Code (`ANTHROPIC_BASE_URL`, preserves claude.ai subscription login without a gateway credential), yes for Codex CLI (`OPENAI_BASE_URL` / `openai_base_url` with `wire_api` in `[model_providers]`), yes for Gemini CLI (localhost exempt from the HTTPS requirement). **[F]**
2. If yes: loopback reverse proxy in redirect mode. No CA, no MDM, no admin rights, immune to HTTP/3 blindness. Default and only mode in v1.
3. If no: CONNECT proxy plus TLS interception as an explicitly opted-into fallback (enterprise). Carries the CA-boundary exposure (B6): a root-equivalent key on every machine. Never SOCKS (unsupported by Claude Code).
4. Never kernel or packet capture (fails pause-and-edit later, TLS-opaque, requires root). Never transcript-tailing alone (cannot support fidelity by construction).

Relay correctness constraints (each has a documented hard failure mode): never buffer a streamed response; forward `anthropic-beta` and `anthropic-version` byte-for-byte as an open list (stripping fails subscription auth with 401); never modify request bodies; forward error bodies unmodified (retry logic matches upstream wording); pass the `system` array structurally unchanged; serve `/v1/models` without redirects inside 3s or omit it. **[F]** Capture is a protocol participant, not a passive tap; every mutation is a correctness hazard before it is a privacy one.

Coverage honesty: base-URL capture sees inference traffic only. Fast-mode checks, WebFetch domain preflight, telemetry, plugin downloads, and Anthropic-hosted surfaces bypass it by design. **[R]** Product copy says "mandatory capture of model inference" and publishes the exclusion list.

Correlation spine: Claude Code sends `x-claude-code-session-id`, `x-claude-code-agent-id`, `x-claude-code-parent-agent-id` on the wire. **[F]** Subagent topology is available from headers with no body parsing; join to `SessionId` at the capture boundary.

Cheapest decisive experiments, ordered by how much option space each collapses:

| # | Experiment | Decides | Cost |
|---|---|---|---|
| X1 | Null-transform loopback relay under a claude.ai-logged-in session; confirm 200, then 401 with `anthropic-beta` stripped (protocol research U2) | Whether intercept mode is needed at all for the primary runtime | half day |
| X2 | Codex CLI against a base-URL override with `wire_api` configured, including its WebSocket path | Whether the entire MITM/CA branch is unnecessary for Codex too. **[I]** Emergent finding: the research system's explicit-proxy-plus-CA design for Codex may be an artifact of its era; current vendor config documents an override no phase-one littleorgans artifact connected to this | half day |
| X3 | Rust reverse-proxy SSE fidelity spike against a real multi-turn session (research program E1) | Language and process model (D2) | 1 to 3 days |
| X4 | Env-only interposition through `prepare_launch` on a real `lilo run claude` (E2) | Seam (D3), context home (D1), topology (D4) | 1 day |
| X5 | `--session-id` mint closure: transcript stem, wire metadata, and `session_sessions.id` all equal (E3) | Identity binding (D6) | half day |
| X6 | kill -9 crash injection at every write stage of the tier-1 layout (E4) | Store shape (D5) | 1 to 2 days |
| X7 | Background-agent supervisor coverage: does the documented supervisor (fixed-path spawn, first-shell env inheritance) escape env-only enrollment under littleorgans-managed launches; does route persistence into the managed harness home close it (protocol research R21/R25/U8) | Whether env injection alone satisfies "mandatory"; whether settings-file enrollment is required | 1 day |
| X8 | Docker backend reachability: host loopback listener from the container netns; CA path across the boundary | Container scope (irreversible decision 9) | 1 day |
| X9 | Failure-mode operator experience: proxy-down-at-spawn and proxy-death-mid-run under both candidate contracts, exact CLI output recorded (E7) | Decision brief for the mid-run loss policy (Stuart) | 1 day |

Stop rule: any spike exceeding roughly three focused days without proof or falsification is itself a finding; stop and re-scope.

## 8. Data authority and durability model

Organizing invariant (data-authority study, triangulated in three independent places in the research evidence): **tier-1 filesystem artifacts are the sole authority; every Postgres row is an idempotently replayable projection.** littleorgans already runs the *idiom* natively on the runtime axis (durable stream plus `internal/session/store/src/postgres/events.rs::apply_runtime_events_and_cursor` in one transaction), so capture extends an existing pattern; the runtime `EventLog` *implementation* is nonetheless rejected as a capture substrate (section 5), so capture builds its own durable tier to this contract.

Eleven data classes with distinct authority answers: exact wire bytes (root of trust, immutable, filesystem); normalized IR (derived, re-derivable); transcript snapshots (irreplaceable once the native file is GC'd); fidelity findings (derived) with durable evidence excerpts; compatibility facts (frozen per run); launch facts (written once by the launcher before any wire frame); indexes (Postgres, rebuildable); product projections (computed, no storage authority); retention and deletion state (two-phase, reconciled at startup); replay inputs (the run dir is the backup unit); operational streams (ephemeral).

Crash contract:

1. File writes are temp, fsync, rename; exchange activation is an atomic directory swap; parent directory sync where durability is claimed (a gap in the research evidence littleorgans closes).
2. Durable tier-1 write precedes index submit; index commit precedes cursor or watermark advance.
3. Post-persist sinks fire exactly once, at the terminal persist; sink failures are isolated and leave a visible, replayable backlog.
4. Deletion is two-phase with the index row as bootstrap arbiter; tier-1 delete and index GC close through a reconciler, never described as atomic.
5. Transcript tee is append-only and restart-idempotent; a gap ahead of the snapshot raises rather than silently advancing; malformed complete records become durable opaque records with byte provenance, never a silent skip (inverting the research system's locked skip behavior).
6. Corrupt index has a defined answer: drop and rebuild from run dirs. Poison records quarantine with bounded attempts and dead-letter rows; one poison never loses the stream.

Evidence naming precision (mechanics study): the contract names what each artifact is (`client_body_bytes`, `decoded_provider_body_bytes`, `websocket_frame_bytes`, `harness_transcript_bytes`, and so on) and records the transformation applied. "Wire bytes" is reserved for exact octets. The research system's `request.raw` is decoded text; littleorgans must not inherit the overclaim.

Per-exchange state machine (product-contract plus security study, reconciled): request staging, request durable, forwarding, response streaming, complete, interrupted, delivery unknown. Never infer non-delivery after the forwarding boundary; recovery exposes Delivery Unknown and never auto-resends. Per-session capture states: pending, active, complete, lost (evidence attached), failed. Durable rows, reconciled on restart by the same sweep pattern as spawn intents.

## 9. Identity, security, privacy, credential model

- Identity owns principals, capture authorization actions (start, metadata read, raw read, export, delete, retention change, hold, repair), audit, credential sources, and any future encryption keys. Transport receives at most a minimum-lifetime handle and never harvests, caches, spends, refreshes, or persists credentials.
- Peer credentials are extracted before any request body is read; frames are bounded; operator calls require the operator principal; worker channels are one-use and process-bound (replacing SessionId-only shim authority).
- Captured requests carry live credentials in `Authorization`/`x-api-key` on every request. **[F]** Redaction cannot happen on the wire without breaking pass-through, so the storage boundary is the security surface. Credential headers, which have no evidentiary value, are redacted or tokenized before bytes hit disk (write-time); raw evidence never mutates during read; redacted views are separate projections. The posture for *bodies* is a genuine two-way split the corpus does not settle: write-time redaction of body content (export safe by construction) versus immutable verbatim raw encrypted at rest with redacted projections. Only one invariant can govern the raw body artifact; this goes to Stuart (ledger U13, enterprise-gates axis 8).
- Child environment is explicit allowlist, not ambient inheritance; secrets never enter argv, durable intent JSON, audit rows, logs, metrics, doctor output, or API payloads; no capture HTTP RPC that serializes full environments.
- Capture roots are `0700`, files `0600`, opened with `O_CREAT|O_EXCL|O_NOFOLLOW` relative to directory descriptors; symlink swap under `LILO_HOME` is defeated structurally.
- No new listener doors: capture adds no HTTP server; reads go through the existing socket and typed RPC. Upstream TLS is validated; each adapter is restricted to its provider host; arbitrary CONNECT is rejected.
- Secret canaries are a standing test class across DB rows, files, logs, argv, doctor output, exports, and error paths. The research system has no test proving a secret is never written to disk; littleorgans authors the real never-capture test with fail-closed semantics.
- Enterprise tier adds encryption of restricted blobs with an Identity-supplied key provider, append-only audit protections (hash chain, signed checkpoints), and access audit for every raw read and export.

## 10. Launch readiness and per-request failure semantics

Mandatory launch sequence (reconciled across product-boundary, product-contract, security studies):

1. Session authenticates the operator and commits, in one transaction, a secret-free composite intent: authorization audit, `SessionId`, capture policy, capture preparation state, runtime preparation state, idempotency key.
2. Transport prepares the capture root, commits a versioned capture header, and starts the per-session capture worker.
3. Readiness is proven by real work, not TCP accept alone: listener bound and owned, adapter available, store writable, header readback durable. Readiness commits before Runtime may spawn.
4. Runtime launches the shim; the agent receives only the loopback endpoint, `SessionId`, and the minimum env the adapter requires, over the existing `LaunchSpec` handoff.
5. Session commits Running only after Runtime and Transport readiness (never Runtime alone).
6. Capture preparation failure aborts the spawn with a typed stable code (`capture_bind_conflict`, `capture_start_timeout`, `capture_store_unavailable`); the intent row records the abort. No agent process exists. Nothing ran unobserved.
7. Runtime failure releases the prepared capture. Provider rejection (auth errors, 429, 5xx) is recorded as an exchange, never treated as a capture failure, and never authorizes or blocks a launch.

Per-request semantics, the central reconciled tension of this study:

- The mechanics and security studies require a durable request acknowledgement before provider release; the user-value and taxonomy studies prohibit blocking the hot path on durable writes and prohibit buffering streams. These reconcile through the authority model rather than by voting: the pre-release barrier is a bounded, local, tier-1 filesystem commit of the outbound request (small, pre-stream, fsync-class latency), while Postgres and every derived observer stay strictly off the hot path as replayable projections. Responses stream through a tee with a bounded spool, never an unbounded memory buffer and never full buffering before relay.
- Before provider delivery: request persistence failure fails the request and surfaces a typed capture fault. After delivery has begun: a storage failure preserves the synced prefix as Interrupted, records a capture fault, and follows the mid-run loss policy. Partial evidence is never presented as complete.
- Comprehension always fails open: unknown or unparsable traffic passes through unmodified and is recorded as an unparsed exchange with raw bytes retained.
- The exact strength of the pre-release barrier (strict fsync per request versus a measured, surfaced durability window) is an explicit knob resolved by X6 plus latency measurement, not an inherited default. Silent degradation has no place in the default contract; a break-glass fail-open mode, if it ever exists, requires an explicit operator setting and Identity audit.

## 11. Lifecycle, recovery, retention, deletion

- Capture state rides durable rows keyed by `SessionId` and reconciles on daemon restart exactly as spawn intents do; the 30s probe sweep extends to capture liveness, transitioning `active` to `lost` with evidence when the worker is gone.
- Exit ordering: agent terminal, final provider bytes drained, capture finalized and sealed, completeness recorded, Session terminal state reconciled. Finalization failure keeps the Runtime outcome and exposes the capture as incomplete; recovery is idempotent.
- Shutdown ordering: stop accepting launches, quiesce agents per policy, drain and finalize captures, stop Transport background work, close stores. Producers drain before consumers.
- Crash matrix: every boundary (intent commit, worker start, ready commit, spawn, running commit, request staging, request durable, upstream write, response chunk, blob activation, DB finalize, audit intent, tombstone, unlink, graceful shutdown) has a required recovery and a forbidden outcome (security study's full matrix is normative). Restart proves no silent loss, duplicate, orphan, or guessed result; uncertainty stays typed Delivery Unknown.
- Retention is a tier-1 policy configured in `settings.toml`, age and size bounded, generous but finite defaults, enforced by a daemon sweeper, auditable, surfaced in doctor before it is an incident. No valid policy configured is a readiness failure for the enterprise tier; for v1 a finite default ships in the same release as capture. The research system's largest validated gap (unbounded growth, no sweeper, unexposed deletes) closes at ship.
- `lilo delete session` deletes capture rows and artifacts with the session: staged two-phase delete, tombstone, blob reclaim, byte counts in audit; deletion of content never deletes the audit fact that deletion occurred. Retention can never delete an active capture.

## 12. Operator and UI/CLI experience

- `lilo get session` gains a CAPTURE column (`active`, `complete`, `lost`, `failed`; no `none` for session-backed runs) via `internal/session/app/src/cli/output.rs::print_session_table_with_rows`; JSON follows free from serde on `Session`.
- `lilo transport list | show <session> | paths | export <session>`: third operator namespace, read and ops only, no spawn verb, authored in `tools/schemas/cli.toml`, selector and short-prefix rules shared with `lilo get session`. Reads come off tier-1 disk; no database read path required for v1.
- Agents self-inspect via `lilo transport show $LILO_AGENT_SESSION_ID --output json` and the existing `lilo mcp` surface; sharing between agents is by `SessionId`, which mail already carries.
- `lilo doctor` gains a transport block: store reachable and migrated, loopback bind capability, active/lost counts with warnings, disk and quota headroom, retention lag, adapter revisions. No per-substrate doctor.
- `lilo capture` remains the tmux pane snapshot verb; wire capture never reuses that name. `lilo daemon start --ready-check` proves capture among its subsystems by doing real work through the real teardown.
- Export is a self-contained bundle with versions and manifest; safe by construction because credential headers were never persisted in the clear. The support payload is the bundle plus `lilo doctor --output json`.
- The human UI (separate TS/Electron train) consumes the committed CLI JSON schema as its contract; whether a headless HTTP read surface ships in v1 stays open (U6). The UI never reads capture files directly.
- Nothing prints on success. The operator-visible surface is session verbs that now return real answers, one doctor block, and failure states that name themselves.

## 13. Test and acceptance matrix

Acceptance evidence classes (test-evidence study, 30 ranked invariants; all recreated natively, zero code ported):

1. Fidelity: real captured multi-turn fixture corpora are drift-silent, dedup at least 96 percent against true wire bytes, exact round-trip; streamed capture equals buffered capture at every byte boundary; SSE incremental parse equals whole-buffer parse under proptest.
2. Isolation: a raising capture observer never degrades the proxied stream; unparseable payloads keep raw bytes plus a parse-failure marker; sink explosions never escape the hook.
3. Durability: crash injection at every write stage leaves zero residue; two-phase delete arbitration; index rebuildable from sidecars; whole-tree byte-snapshot equality as the idempotence oracle; transcript tee restart-idempotent with hard gap failure.
4. Pipeline: quarantine with dead-letter provenance; drift observational only; replay determinism byte-identical to whole-input replay; repair never fabricates.
5. Identity: correlation contractual on `SessionId` with zero heuristic probing; trusted launcher stamp beats derived re-bind; fail closed on ambiguous binding; subagent corpus joins.
6. Process: parent-death reaping triad with a probative control; pid-reuse-safe supervision; SIGTERM-to-SIGKILL escalation; shutdown ordering proven at a real socket; fail-closed demux.
7. Security: narrow header allowlist with `authorization` provably absent; the fail-closed never-capture secret test (absent in the research evidence, authored fresh); canary scans across DB, files, logs, argv, doctor, export.

Gaps the research evidence never covered, authored fresh: tailer rotation and truncation resync (inode tracking), timestamp monotonicity, repair after byte-level corruption, concurrent atomic-write races, golden wire-bytes parse-then-serialize round-trip.

Two research tests invert into acceptance tests: persistence failure must prevent provider release and reach Runtime (was: return None on failure); malformed complete transcript records must produce durable opaque evidence (was: silent skip).

Release-gate assertions (product-contract, 12 items): ready-check includes capture; proxy accepting before agent pid exists and proxy kill pre-exec aborts with a stable code; child env contract exact (loopback base URL, no inherited proxy/trust vars, `NO_PROXY` pinned, all names registered); CAPTURE column live and correct across the lifecycle; mid-run kill transitions to `lost` within one sweep; every artifact class readable by `show` or `export`; export of a credentialed run contains zero credential bytes; delete leaves no rows and no directory; retention sweeper works under a test policy; generated-surface guards pass with `lilo transport` present and `lilo capture` still tmux; grep gate zero `tm`/transport-matters/`TRANSPORT_MATTERS_*` references; full `just check && just build && just test` green or the release does not tag.

House method: surgical failure injection by argument predicate; residue assertions after every injected failure; dual-path parametrization (fresh and provisional-finalize); byte-level determinism; control tests proving the repro is probative; hostile same-UID sibling tests with real peer credentials, not fake authorizers.

## 14. Enterprise release gates

Reconciled with the enterprise-gates synthesis input (accepted). The enterprise claim: every agent action on this host is evidenced by construction: who authorized it, what was sent, what came back, whether a human touched it. No opt-in capture model can make that claim. Buyers will probe four gating gaps first: retention and deletion, payload redaction, secret never-capture proof, and authorized audited reads; all four are v1-or-enterprise-tier requirements, none deferrable past the enterprise release. Coverage honesty is part of the claim: "mandatory capture of model inference" with the non-covered host list published.

Gate set:

1. Every crash-matrix row has deterministic fault injection at each database, file, sync, rename, process, and socket boundary.
2. Every hostile-workload row (slowloris, oversized frames, connection storms, stream floods, compression bombs, disk full, Postgres outage, symlink swap, clock jumps, retention races) has a bounded resource assertion and a typed operator-visible result.
3. Durability ordering proven at provider and agent boundaries under the locked barrier policy; restart proves no silent loss, duplicate, orphan, or guessed result.
4. Secret canaries across control tables, intent JSON, audit, logs, argv, metrics, doctor, errors, sanitized views.
5. Path policy proven: ownership, `0700`/`0600`, no symlink traversal, safe custom `LILO_HOME`.
6. Authorization tests with real peer credentials and hostile same-UID siblings.
7. Nonvacuous shared corpora: Claude HTTP, Codex HTTP and WebSocket, unknown, malformed, pinned historical revisions.
8. Retention: quotas, free-space reserve, hold, concurrent export, tombstone recovery, erase semantics, audit survival.
9. Encryption at rest with Identity key provider; append-only audit (hash chain, checkpoints); works-council/legal posture documented (U9).
10. Supply chain: dependency, vulnerability, secret, and source scanning; SBOM; signed and notarized artifacts; pinned CI actions; CODEOWNERS for capture and identity; release attestations already configured extend to capture.
11. Structural gate: build and release inspection prove zero relationship with `tm` or transport-matters from the built archive.
12. The repository gate remains `just check && just build && just test`; structural changes also run `fmm generate && fmm validate`.

## 15. Implementation sequence with stop gates

The sequence binds the research program's decision register (D1 to D11, E1 to E7) to the enterprise-gates adjudication. Gates 0 to 5 are decision gates; implementation phases follow only after Gate 5. No gate locks an unresolved design.

**Gate 0, governance and doc reset (closeable now, no code).** Close D8 native config homes, D9 Claude first, D10 raw bytes first; adopt observation-only v1; withdraw the stale `CLAUDE.md` launch-chain prose and supersede `NOTES/transport-integration.md` with the Transport product decision record; add the zero-dependency grep gate to CI; record the retracted syntax-defect claims so they do not resurface. Exit: docs match `LESSONS.md:18-19`; grep gate green; ledger updated.

**Gate 1, interposition physics.** X1 subscription-auth null relay, X2 Codex base-URL probe, X3 Rust SSE fidelity spike, X4 env-only interposition through the real spawn path, X7 background-supervisor coverage. Exit: interception mode resolved per harness with recorded evidence; D2 language and D3 seam closed; the coverage-boundary host list written into the product contract; if X2 succeeds the Codex MITM program is struck from scope entirely.

**Gate 2, identity and durability.** X5 managed-mint four-way key agreement; X6 crash injection across the chosen tier-1 layout plus the barrier latency measurement (fsync-before-forward cost on real request sizes) and the bounded-spool streaming test; overhead envelope at 1, 5, 20 concurrent streams (E6). Exit: D5 store shape closed with the one-sentence seam contract (capture-state rows in Postgres, artifact authority on disk); D6 identity closed; the durability barrier resolved with numbers, not positions; D4 topology closed.

**Gate 3, Stuart decisions (briefed by X9 and gates 1 to 2 evidence).** U1 mid-run loss policy; Codex-in-v1; U13 body redaction versus encrypt-raw posture; U4 escape-hatch existence; U14 hot-path hold-capability reservation (priced by a hold-blocking spike measuring harness client timeout budgets); U11 retention default strictness (startup-blocking policy versus shipped finite default); U9 legal posture. Exit: each has a ledger entry with the operator-experience brief attached; none inherited from a prototype.

**Gate 4, foundation repairs (littleorgans-side, before capture code lands).** Bounded authenticated RPC framing; one-use process-bound launch capability; secret-free spawn intents; event journal replacement or rebuild; enforced `LILO_HOME` path policy; spawn idempotency key. Exit: each repair merged with the hostile-workload row it retires; capture design references these seams only after repair lands.

**Gate 5, contract synthesis and program exit.** Fold gate outputs into the Transport product decision record: boundary invariants, both state-machine granularities (session-facing `active/complete/lost/failed` and the internal exchange states), the precise evidence vocabulary, the acceptance suite (two matrices, twelve release-gate assertions, six fresh test gaps). Exit: the decision register is fully closed for the Claude scope; only then is an implementation plan warranted.

Implementation phases after Gate 5: native skeleton (Transport context, typed RPC variant, Identity actions, migration, paths, `WireCapture` capability, readiness, recovery, doctor block) proven against a deterministic fake provider first; then the Claude vertical slice (real proxy, tier-1 persistence, transcript tee, `lilo transport list|show|paths`, CAPTURE column, delete cascade, retention sweeper, export) whose clean-install acceptance is the release gate: build and install with no `tm` on PATH and no transport-matters checkout, one `SessionId` across authorization, intent, lifecycle, capture, and read model, daemon killed at every boundary and reconciled idempotently, a forced storage failure with no direct fallback. A release in which this slice fails does not tag. Enterprise qualification (encryption, audit hardening, SBOM and scanning, platform matrix) follows; Codex opens only after the Claude scope holds and X2 has decided its branch.

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

### EVIDENCE-SUPPORTED (converged, adoptable without further ceremony)

| # | Position | Basis |
|---|---|---|
| E1 | Redirect mode (loopback reverse proxy via base-URL env) is the default and only v1 interposition; MITM/CA is an enterprise fallback branch | Vendor-documented overrides for all three harnesses; CA-boundary asymmetry |
| E2 | Claude first; Codex gated second phase | Every Codex-specific mechanism is strictly harder; X2 may collapse the gap |
| E3 | Native config homes in v1; no credential broker problem class | The broker existed only because the experiment redirected homes |
| E4 | Raw bytes first; IR and parsing grow from read demand | Projections rebuild from bytes; bytes do not rebuild from projections |
| E5 | Tier-1 filesystem authoritative; Postgres rows are replayable projections; raw bytes never enter Postgres | Triangulated in the evidence; matches the existing littleorgans event idiom |
| E6 | Per-session capture worker in the existing supervision tree; shared proxy rejected for v1 | Shipped versus built-and-unadopted lab evidence; blast radius |
| E7 | Interposition by env at the runtime launch seam (`prepare_launch` / `runtime_env`), not an exec wrapper | Docker precedent; single funnel covers diagnostic spawns; wrapper premise was never real code |
| E8 | Launcher-owned session mint (`--session-id <SessionId>`), pending X5 | Dissolves uuid5 synthesis and heuristic probing entirely |
| E9 | Launch-time fail closed: no capture readiness, no agent process, typed abort codes | All studies agree; only the mid-run branch is open |
| E10 | Comprehension fails open with recorded unparsed exchanges; unknown shapes preserved | Capture must survive provider drift |
| E11 | Credential headers redacted at write time; raw evidence never mutates on read; redacted views are projections (body posture is U13) | Headers have no evidentiary value; read-time mutation destroys evidence |
| E12 | Two-stream invariant: wire and transcript captured separately from v1, never collapsed; transcript tee best-effort with recorded gaps | The fidelity option stays open only if both streams exist |
| E13 | No dark stores: every artifact class ships with a read path in the same release | The experiment's central product failure |
| E14 | Retention, deletion cascade, and doctor visibility ship in the same release as capture | The experiment's largest validated gap |
| E15 | Correlation spine additionally records the `x-claude-code-*` header family | Free topology, no body parsing |
| E16 | Foundation repairs (bounded RPC, launch capability, secret-free intents, journal rebuild, path policy, idempotency) precede capture code | Capture traffic is larger and more adversarial than control traffic |

### UNRESOLVED (open decisions with owners)

| # | Question | Resolver |
|---|---|---|
| U1 | Mid-run capture loss: terminate the run (lab behavior) or keep alive with a loud `lost` state | Stuart, briefed by X9 |
| U2 | Implementation language and process topology, formally | X3, X4 (Rust in-workspace is the evidence-supported lean; not decided until the spike passes) |
| U3 | Pre-release durability barrier strength: strict fsync per request versus a measured, surfaced window | X6 plus latency measurement |
| U4 | Raw `lilo runtime spawn` capture posture: captured at the runtime seam, or an explicit locked uncaptured-diagnostic decision | Stuart; the seam choice already makes capture the default |
| U5 | v1 artifact depth: raw only versus raw plus parsed IR at write | Read-demand review after X6 |
| U6 | Headless HTTP read API in v1 versus CLI JSON only | Stuart, with the UI train |
| U7 | Fidelity inputs: transcript snapshots from v1 (E12 says yes in principle; cost unquantified) and whether v1 must store everything the future diff needs | Cost measurement in Phase 4 |
| U8 | Docker/container capture scope: engineering task or explicit v1 scope cut | X8 |
| U9 | Legal posture of "mandatory" for enterprise deployments (enables versus performs monitoring) | Stuart with counsel, before enterprise copy |
| U10 | Background-agent supervisor coverage and settings-file enrollment | X7 |
| U11 | Retention default values (age, size, free-space reserve) | Stuart, at Phase 4 |
| U12 | Whether provider-native session ids are stored as secondary metadata for provider-console cross-reference | Design detail, post-Gate 5 |
| U13 | Body storage posture: write-time redaction of body content versus immutable verbatim raw encrypted at rest with redacted projections. Only one invariant can govern the raw body artifact; bytes written unredacted exist forever unless encrypted from day one | Stuart, Gate 3 |
| U14 | Whether the v1 hot path must be architected async-hold-capable so pause-and-edit remains buildable later, or "store the inputs, compute later" honesty suffices | Stuart, Gate 3, priced by a hold-blocking spike |

### EXPLICITLY REJECTED

| # | Rejection |
|---|---|
| R1 | Any `lilo`-to-`tm` launch chain, packaging, or version coupling; porting the Python plane in any form (FFI, subprocess, vendoring) |
| R2 | mitmproxy-class dependencies, Python/FastAPI/Alembic runtime zoo, second migration system, foreign env prefixes |
| R3 | The exec-wrapper inversion as the enrollment premise (stale NOTES Decision 1); SQLite `index.db`; channel homes |
| R4 | uuid5 session synthesis and heuristic exchange correlation |
| R5 | Traffic mutation in any form in v1: overrides, breakpoints, pause-and-edit, forged responses |
| R6 | Credential brokering: harvesting, caching, spending, refreshing, or persisting user credentials; Keychain writes; writes outside `~/.lilo` |
| R7 | Shared proxy as initial topology; god-process composition; a second composition root or listener door |
| R8 | Unauthenticated authority routes (local file GET, PTY keystroke bridges, unguarded mutation routes); capture RPCs serializing environments |
| R9 | Write-only substrates: any capture table or artifact class without a same-release reader |
| R10 | Silent fail-open capture writes; capture loss as only a log line |
| R11 | Read-time mutation of raw evidence; destructive legacy-cache migration; whole-file index rewrites presented as durability |
| R12 | Capture-core ownership of token counting, certification machinery, control-plane verbs, canvas/UI state |
| R13 | Claims exceeding implementation: decoded bodies presented as wire octets; a fidelity diff that does not exist; orthogonality claims while holding authority |
| R14 | Capture opt-out flag; capture of agent-run shell commands; public share links in v1; analytics dashboards before governance |

## 17. Self-audit

Completed 2026-07-31 before Status flipped to COMPLETE:

- [x] All 13 phase-one artifacts consumed at `Status: COMPLETE`; both synthesis inputs consumed only after each reached `Status: COMPLETE` (current-code-reuse after its orchestrator-directed correction); sections 5, 8, and 14 reconciled against them; no stale IN PROGRESS input consumed
- [x] Every required section present (first-screen framing, thesis, value, taxonomy and minimum v1, ownership and exclusions, reuse map, lessons, interception tree and experiments, data authority, security model, launch and failure semantics, lifecycle and retention, operator experience, test matrix, enterprise gates, sequence with stop gates, four-class decision ledger); both source pins stated in the header
- [x] Zero tm dependency: every mention of `tm`/transport-matters is as research evidence, rejection, or withdrawal target; no invocation, packaging, versioning, porting, or outreach proposed
- [x] No unsupported runtime claim: source facts, inferences, and recommendations are marked; no test execution or live-traffic claim is attributed to the pinned commits beyond what the phase-one artifacts themselves verified; the pinned auth syntax defect is recorded as retracted and carries no load
- [x] `transport-matters/NOTES/` never cited (the only `NOTES/` references are littleorgans' own superseded note); load-bearing repository evidence uses `path::symbol` citations; external claims cite primary sources via the protocol research artifact
- [x] Contradictions reconciled rather than voted (durability barrier, redaction posture, raw-spawn posture, syntax-defect dispute, Codex interception premise); undecided matters are named UNRESOLVED with resolvers, not presented as decided
- [x] 434 lines, no em dashes, under the 700-line limit
