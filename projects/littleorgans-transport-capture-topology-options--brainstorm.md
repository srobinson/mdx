# littleorgans Transport Capture: Topology Options

Status: COMPLETE

Updated: 2026-07-31

Phase 1 report for the littleorgans Transport Capture Study. Scope: derive implementation topology options for a mandatory first-class littleorgans transport capture capability from requirements. transport-matters is used strictly as experimental evidence of mechanism feasibility.

## Zero-dependency rule

littleorgans will not invoke, package, version against, or depend on `tm` or transport-matters in any form: no tm invocation, no package dependency, no schema reuse, no release coupling, no compatibility contract. Mechanisms observed in transport-matters are treated as lab evidence only.

## Baselines

- littleorgans: `98d8928941b5b5db670ed73ed06af57f61dcfa0a` (working tree verified at this SHA)
- transport-matters: `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55` (inspected via detached read-only worktree; SHA diverges from repo HEAD, pinned per study baseline)

Constraint honored: no transport-matters `NOTES/` content read or cited (directory absent at the pinned SHA).

## Worker Status

Nested read-only exploration workers spawned by this report (no repo edits, evidence gathering only):

| Worker scope | State |
|---|---|
| littleorgans launch-chain evidence (`lilo run` path, spawn chain, env injection, interposition seams) at 98d8928941b5 | COMPLETE (evidence merged below) |
| transport-matters capture-mechanism evidence (interception, adapters, storage, lifecycle, auth) at a252df24a7e3 | COMPLETE (evidence merged below; one reported finding verified false and corrected) |

Verification performed directly by this report, not delegated: the worker's claim of 22 `SyntaxError` files at the transport-matters baseline was checked against the repo's own interpreter (`requires-python = ">=3.14"`, `uv run python` 3.14.5) and found false. PEP 758 permits unparenthesized multi exception `except` clauses; the flagged capture path files parse clean.

## Requirements (derived from littleorgans instructions, not from transport-matters)

- R1: Capture is a side effect of every run. Mandatory, first-class capability of the platform.
- R2: Two consumers: agents inspecting and sharing captured sessions, and the littleorgans human UI.
- R3: Captured sessions correlate to the control-plane `SessionId` (UUIDv4 issued by session at spawn time), never a provider-minted conversation id.
- R4: Fidelity diff between what the harness believed it sent and what actually reached the provider.
- R5: Pause-and-edit capability on the wire path.
- R6: Observation only. Capture does not authorize, does not decide what to spawn, does not reconcile. It stays outside the load-bearing control plane.
- R7: v1 is local-first: one operator, one host, one `lilod`.
- R8: All local state under `~/.lilo/` (`LILO_HOME`), database is Postgres via `LILO_DATABASE_URL`, exactly one env prefix (`LILO_`), agent-injected vars limited to the registered `LILO_AGENT_*` set.
- R9: Zero dependency on tm (see above).
- R10: No premature language or topology selection. If the choice lands on Rust, the crate-train lockstep release model applies; other languages ride independent trains.

## Evidence

### littleorgans launch chain (at 98d8928941b5)

Facts that constrain topology, each with path+symbol evidence:

1. **Single daemon process.** `lilod` hosts both session and runtime substrates in-process. Composition root: `internal/session/app/src/compose.rs::run_core` (:115). One UDS `~/.lilo/run/lilod.sock` multiplexed by `LilodRpc { Session, Runtime }` (`internal/wire/src/lib.rs:5`). No separate `rtmd` process; `RtmdDriver` (`internal/session/driver/src/rtmd.rs:25`) exists but is not wired into the composition root.
2. **Process tree.** `lilod` → `lilo __shim --session-id <uuid>` (fork+wait supervisor, `internal/runtime/app/src/cli/shim.rs:35,160`) → `claude|codex` (`runtime_command`, `shim.rs:119`). tmux target uses `tmux respawn-pane` (`internal/runtime/daemon/src/tmux.rs:32,291`); headless uses piped stdio (`shim_socket.rs:83-96`). lilo allocates no PTY itself.
3. **No transport wrapper exists in code.** Grep across `crates/` and `internal/` finds zero `tm` invocation; `CLAUDE.md:61-63` "`lilo run claude` execs `tm claude`" is aspirational, `NOTES/transport-integration.md` is `Status: design, planning`. Today's argv is literally `[which("claude")]` (`internal/runtime/launchers/src/claude.rs:9`, `lib.rs:90-135`).
4. **Env injection choke points.** Session level: `spawn_launch` (`internal/session/daemon/src/handler/spawn.rs:369-407`) strips inherited `LILO_AGENT_*` then upserts `LILO_AGENT_SESSION_ID/ROLE/WORKSPACE`. Runtime level: `runtime_env` (`internal/runtime/launchers/src/lib.rs:97-108`) upserts `LILO_AGENT_SESSION_ID/RUNTIME`. Registry: `crates/lilo-paths/src/env.rs:33-41`.
5. **No endpoint-override knob exists.** No `ANTHROPIC_BASE_URL`, `HTTPS_PROXY`, or provider endpoint symbol anywhere in the workspace. The only zero-code path is the agent-config `[env]` table (`internal/session/daemon/src/agent_config.rs:138`, `~/.lilo/config/session/agents/<name>/agent.toml`).
6. **Launcher abstraction is thin and uniform.** `RuntimeLauncher` trait (`crates/lilo-rm-core/src/launcher.rs:62-90`), one concrete `BinaryLauncher` (`internal/runtime/launchers/src/lib.rs:23-55`); claude and codex differ only by binary name. Backend rewriting seam already exists: `RuntimeBackends::prepare_launch` (`internal/runtime/daemon/src/backend.rs:33`) where the Docker backend wraps argv (`docker_argv.rs:16`). A capture decorator would be structurally symmetric to `DockerRuntimeBackend`.
7. **Bootstrap env is deliberately minimal.** `shim_env` returns exactly `[LILO_SOCKET_PATH]` with a guard test (`internal/runtime/daemon/src/shim_socket.rs:148-156,264`); real runtime env crosses the UDS in `LaunchSpec.env` and is applied after `env_clear()` (`shim.rs:152-158`). Capture config must ride `LaunchSpec.env`, not the bootstrap env.
8. **Storage and events.** Postgres via `LILO_DATABASE_URL` (`internal/db/migrations/0001_unified_schema.sql`; `session_sessions:30`, `runtime_lifecycle:130`). Event JSONL at `~/.lilo/data/events/runtime.jsonl` (`EventLog::append`, `internal/runtime/daemon/src/event_log.rs:130`) with seq, dedup, crash recovery, compaction. Path registry `LiloPaths` (`crates/lilo-paths/src/lilo.rs:39-110`) has slots for per-session logs (`runtime_log_dir:79`) that a capture artifact tree can mirror.
9. **Lifecycle events.** `RuntimeEvent { Running, Terminated, Lost }` (`crates/lilo-rm-core/src/types/lifecycle.rs:188-204`) emitted by spawn/termination coordinators and reconcile, fanned to Postgres session state via `apply_runtime_event` (`internal/session/store/src/postgres/events.rs:37`). Capture lifecycle can key off the same events.
10. **Credential passthrough exists.** `capture_caller_env` denylists `CLAUDECODE`, `TMUX*`, `LILO_SOCKET_PATH`, `CLAUDE_CODE_*`, `LILO_AGENT_*` but explicitly keeps `ANTHROPIC_API_KEY` (`crates/lilo-rm-core/src/spawn_context.rs:10-15,151`).

### transport-matters mechanism evidence (at a252df24a7e3)

Lab evidence only. Cited for mechanism feasibility, never as a dependency, schema, or contract.

1. **Two interception modes, dispatched per harness.** Claude: `mitmdump --mode reverse:https://api.anthropic.com` on loopback plus `ANTHROPIC_BASE_URL` injected into the child (`captured/claude.py:183,206`; `cli/launch_runtime.py::build_mitmdump_argv`). Plain HTTP to loopback, no TLS, no CA. Codex: `mode="regular"` forward proxy with TLS MITM (`cli/codex_cmd.py:169`), child gets `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY` plus a run scoped CA bundle via `CODEX_CA_CERTIFICATE` (`cli/trust.py::resolve_codex_ca_certificate`). Proves the two mechanisms are not interchangeable: the mode is forced by whether the harness honors a base URL override.
2. **Bypass proofing is explicit work.** `launch/environment.py::build_managed_child_env` deletes roughly 30 proxy env keys and 9 TLS trust keys (`NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, npm/yarn/bundler variants) before setting its own, and `managed_child_shell_env_excludes()` strips them again for nested shells the agent spawns.
3. **Per run sidecar is the shipped lifecycle.** One `mitmdump` per agent process, started before the agent and torn down with it (`cli/runner.py::run_client_children_until_outcome`, `start_prepared_proxy`). Ports allocated by double `bind(("127.0.0.1", 0))` with no reservation, an acknowledged TOCTOU absorbed by bounded retry (`captured/run.py::prepare_captured_run`, `_BIND_RETRY_ATTEMPTS`).
4. **A shared daemon alternative exists in tree but is not the default route.** `shared_proxy/subprocess.py::SharedProxySubprocess._apply_modes` adds and removes `reverse:<upstream>@127.0.0.1:<port>` listeners live on one `DumpMaster`; demux maps flow to run by listen port with fail closed behavior on unmapped flows (`shared_proxy/addon.py::_resolve_new_flow`, `DemuxFailure`). `capture_rpc.py::prepare_capture` still rejects non embedded runtimes, so the shared path is built and not adopted.
5. **PTY ownership is separable from capture.** Two different PTY owners share one capture seam: the Python CLI (`supervisor/pty_process.py::spawn_with_pty`, manual cbreak in `supervisor/pty.py::install_parent_cbreak`) and the TypeScript product plane via node-pty (`packages/runtime/src/adapters/NodePtyAdapter.ts`), the latter obtaining `{argv, env}` over an RPC (`POST /v1/capture/prepare` → `capture_rpc.py::CaptureLeaseRegistry.prepare_capture`). Evidence that the capture plane can expose a prepare/release contract and let another process own the child.
6. **Orphan protection is required.** `self_reap.py::install_parent_death_reaping` uses `prctl(PR_SET_PDEATHSIG)` on Linux and a `getppid()` watchdog on macOS, with a hard exit after 20 seconds. A sidecar proxy outliving its run is a real failure mode that had to be engineered against.
7. **Two tier artifacts, both retained.** Tier 1 per run directory holds raw bytes and parsed IR side by side: `request.raw`, `request.ir.json`, `request.curated.raw`, `request.audit.json`, `response.raw`, `response.ir.json`, `transport.json`, `events.jsonl` (`storage/disk_layout.py::DiskStorageLayout`), with atomic tmp/bak/del writes. Tier 2 is Postgres with content addressed blobs (`wire_blob`, `wire_exchange`, migration `0008_wire_store`; writer `session/wire_store.py::write_wire_exchange`). The wire tables ship dark: written, not read back.
8. **Streaming capture primitive.** `response_stream.py::install_response_tee` sets `flow.response.stream` to buffer every chunk while forwarding, and `restore_streamed_response` writes the buffer back so downstream parsers see whole bytes. SSE framed incrementally with a bounded 1 MiB tail (`sse.py::IncrementalSseFrames.feed`).
9. **Identity binding is pre minted, not discovered.** The launcher pre mints the native session id the harness will write and hands it to the addon as `TRANSPORT_MATTERS_OWNED_NATIVE_SESSION_ID`, plus an exact source descriptor so the tailer byte tails a known path instead of globbing (`env_keys.py`; `owned_transcript_binding.py::build_proxy_run_binding`). Correlation pivot `index/sessions.py::wire_session_id(run_id, provider, native_session_id)`: direct for anthropic, `uuid5` synthesis for codex so wire and transcript sides independently compute the same key.
10. **Pause and edit is wired on both transports and requires an async hot path.** The mitmproxy `request` hook is async, so awaiting inside it holds the outbound request before it reaches the provider (`addon_handlers.py:223` → `pause_session.py::handle_breakpoint`). Mutation applied via `flow.request.set_text` (HTTP, `pause_session.py:354`) or frame content replacement (Codex WS, `:407`). Persistent non paused overrides run through `request_pipeline.py::run_pipeline` → `overrides.apply_overrides`.
11. **Fidelity diff: harness sent versus provider received is implemented; wire versus transcript is not.** `request_diff.py::request_unchanged(original_ir, curated_ir)` and `outbound_request_if_changed` are exact frozen IR comparisons, and when they differ both byte streams are persisted. Parser drift is captured separately and off the hot path (`drift_capture.py::WireDriftObserver` → `harness_drift_evidence`, migration `0023`). The wire versus transcript diff remains scaffolding only.
12. **Interception needs no provider credentials, but launch does.** The agent's own auth headers ride through untouched; the addon only snapshots them (`counting.py::relevant_auth_headers`). The real credential work is which credential the spawned child sees (`cli/credential_source.py::resolve_harness_credential_source`, native file versus macOS keychain broker) plus mid session refresh observed on the wire path (`credential_refresh.py::refresh_expired_claude_credential` invoked from `handle_response`).

Correction to an intermediate finding: 22 files were initially flagged as `SyntaxError` for unparenthesized multi exception `except` clauses. This is a false positive from an older ambient interpreter. `api/pyproject.toml` sets `requires-python = ">=3.14"`, PEP 758 permits that form, and both flagged capture path files parse clean under the repo interpreter (`uv run python`, 3.14.5). No syntax defect exists at this SHA.

### littleorgans constraints that transport-matters does not answer

- **Docker backend breaks loopback interception.** `DockerRuntimeBackend` wraps argv into `docker run` (`internal/runtime/daemon/src/backend.rs:71`, `docker_argv.rs:16`). A capture listener bound to host `127.0.0.1` is not reachable at `127.0.0.1` from inside the container. transport-matters has no container backend, so it provides zero evidence here. Any topology must state its container story explicitly.
- **Env prefix ownership.** transport-matters carries roughly ten `TRANSPORT_MATTERS_*` keys. littleorgans owns exactly one prefix and validates it (`crates/lilo-paths/src/env.rs`, `scripts/check-env.sh --check`). Every capture variable must be a registered `LILO_` name, and the agent injected subset is currently a closed four name set.
- **Bootstrap env is guarded.** `shim_env` returns exactly `[LILO_SOCKET_PATH]` with a guard test. Capture configuration must travel in `LaunchSpec.env` over the UDS, not in the bootstrap env.

## Option matrix

Six independent axes. A topology is one choice per axis. Language is deliberately deferred to the end because only two axes actually constrain it.

### Axis A: interception mechanism

| Option | Shape | Requires | Fails |
|---|---|---|---|
| A1 Reverse proxy plus base URL env | Listener on loopback fronting one upstream; child pointed at it by env | Harness honors a base URL override | Any harness without such an override |
| A2 Forward proxy plus TLS MITM | Standard `HTTP_PROXY`/`HTTPS_PROXY` interception with a generated CA | Per process trust injection; CA lifecycle | Harnesses that pin certificates |
| A3 Per harness dispatch of A1 and A2 | Adapter decides mechanism per runtime kind | Both mechanisms plus a per harness capability table | Nothing structurally; costs two code paths |
| A4 In harness hook or SDK shim | Load capture inside the agent process | Source or plugin access to vendor binaries | Not available for closed harnesses |
| A5 Kernel or network layer capture | eBPF, pf, packet capture | Root, plus TLS key material to be useful | R5 pause and edit; TLS opacity |
| A6 Transcript tailing only | Read the harness's own transcript file, no wire | Nothing on the wire path | R4 fidelity diff and R5 by construction |

Evidence: A1 and A2 are both demonstrated working, dispatched per harness (A3 in practice). A4 through A6 have no supporting evidence and each fails a stated requirement. A6 is worth naming only because it is the cheap option that looks adequate until R4 is examined: diffing the transcript against itself proves nothing.

### Axis B: process boundary

| Option | Shape | Cost | Note |
|---|---|---|---|
| B1 In `lilod` | Capture listener hosted inside the existing daemon | Blast radius: a capture fault takes the control plane with it | Tension with R6 observation only |
| B2 Sidecar child of `lilod` | One capture process per run, parented by the daemon | Supervision, orphan reaping, port allocation | Matches existing `SpawnCoordinator` shape |
| B3 Sidecar child of the shim | Capture process parented by `lilo __shim` | Shim becomes a two child supervisor | Natural lifetime coupling to the agent |
| B4 Standalone shared daemon | Long lived capture process independent of `lilod` | Second daemon, second socket, second lifecycle | Contradicts "one `lilod`" framing of R7 |
| B5 Argv wrapper in the launch path | `argv` rewritten so a wrapper execs the agent | Wrapper owns proxy bring up and PTY passthrough | The documented but unimplemented inversion |

Existing seams, ranked by cleanliness: `RuntimeBackends::prepare_launch` (`backend.rs:33`, already a launch rewriting seam where Docker wraps argv, structurally symmetric for a capture decorator), `runtime_env` (`launchers/src/lib.rs:97`, existing idempotent env upsert point), `BinaryLauncher::argv` (`lib.rs:48`, single argv choke point), session level `spawn_launch` (`handler/spawn.rs:369`, has role/workspace/namespace context), shim `runtime_command` (`shim.rs:119`, truest observation point, least context). Zero code today: the agent config `[env]` table already injects arbitrary env (`agent_config.rs:138`), so A1 can be exercised per agent without touching Rust.

### Axis C: capture lifecycle

| Option | Shape | Trade |
|---|---|---|
| C1 Per run | One capture instance per agent process | Isolation and simple teardown; port churn, N processes, orphan risk |
| C2 Shared with dynamic listeners | One instance, listeners added and removed per run, demux by listen port | One process; a shared fault domain and a demux correctness burden |
| C3 Per run now, shared later | C1 as the shipped path, C2 behind the same prepare/release contract | Only viable if the contract is defined before C1 ships |

Evidence: C1 shipped, C2 built and unadopted in the lab system, with fail closed demux already engineered. C3 is what that repo effectively arrived at without having planned for it.

### Axis D: artifact and store authority

| Option | Shape | Trade |
|---|---|---|
| D1 Files only | Per run directory of raw bytes and parsed IR | Simple, greppable, no schema migration; weak query, weak cross session |
| D2 Postgres only | Everything into `LILO_DATABASE_URL` | One store, queryable, matches R8; large blobs in the OLTP database |
| D3 Two tier, files authoritative | Raw bytes on disk, projections in Postgres | Rebuildable index; two truths to keep consistent |
| D4 Two tier, Postgres authoritative | Content addressed blobs in Postgres, disk as cache | Single authority; heaviest write path |

littleorgans already has both halves: a Postgres schema with an event cursor pattern, and a `~/.lilo/` tree with per session log directories (`LiloPaths::runtime_log_dir`) that a per run artifact tree mirrors naturally. Lab evidence is D3 in shape with the Postgres tier shipping dark, which is the failure mode to avoid: a second tier that nothing reads is cost without value.

### Axis E: provider adapter boundary

| Option | Shape | Trade |
|---|---|---|
| E1 Opaque bytes only | Persist raw request and response, never parse | Trivial, provider agnostic, survives format drift; fails R4 and R5 |
| E2 Parse to a provider neutral IR | Per provider parse and reserialize through one internal model | Enables diff, override, pause; large surface, drifts with providers |
| E3 Bytes plus lazy parse | Raw bytes authoritative, parsing a read side concern | Capture cannot break on an unknown format; pause and edit still needs a live parse |

R4 and R5 both require understanding the request in flight, so E1 alone is insufficient. E3 is the shape that keeps the hot path safe: capture what you cannot reconstruct, parse where failure is recoverable. Lab evidence supports the cost warning on E2: two providers produced one adapter module and roughly forty modules of Codex specific derivation because Codex turns arrive incrementally across WebSocket frames.

### Axis F: language and release train

| Option | Shape | Trade |
|---|---|---|
| F1 Rust, in the existing workspace | Capture crates alongside session and runtime | One train, one lockstep version, one gate; must build proxy and TLS MITM machinery |
| F2 Separate non Rust process on its own train | Capture plane in a language with mature proxy tooling | Reuses an existing MITM stack; a second release train and a cross language contract |
| F3 Rust control with a non Rust capture engine | Rust owns launch and lifecycle, another process owns bytes | Clean boundary; two trains and an IPC contract to version |

Only axes A and E materially constrain this. A2 requires a TLS MITM implementation, which is where the mature tooling gap is largest. A1 alone needs an HTTP reverse proxy, which is well served in Rust. The monorepo already sanctions independent trains for non Rust surfaces, so F2 and F3 are not novel, but each adds a versioned boundary that F1 does not have.

### Coherent topologies

Combinations that hold together, presented without a recommendation:

- **T1 Minimal observation:** A1, B5 or the config `[env]` seam, C1, D1, E3, F1. Smallest surface that captures anything. Cannot serve Codex, cannot pause.
- **T2 Backend decorator:** A3, B2 via `prepare_launch`, C3, D3, E3, F1 or F3. Uses the existing Docker symmetric seam; defers the shared daemon behind a contract defined up front.
- **T3 Wrapper inversion:** A3, B5, C1, D3, E2, F2 or F3. Closest to the lab system and to the aspirational `CLAUDE.md` line; moves PTY and supervision into the wrapper and duplicates lifecycle logic the shim already owns.
- **T4 Prepare and release service:** A3, B4 or B2, C2, D4, E3, F3. Capture plane exposes prepare and release; `lilod` keeps owning the child. Strongest separation, heaviest contract.

## Irreversible decisions

Decisions that are expensive or impossible to reverse after the first run is captured. Each should be made explicitly rather than inherited from a prototype.

1. **Mandatory versus opt in interposition.** R1 says capture is a side effect of every run. Making it mandatory changes the process tree for every session, so retrofitting it later is a launch contract break. Making it optional first and mandatory later means a corpus with holes.
2. **Whether raw bytes are retained.** Parsed projections can be rebuilt from raw bytes. Raw bytes cannot be rebuilt from projections. A decision not to store `request.raw` and `response.raw` is unrecoverable for all history captured under it.
3. **Store authority.** Which tier is the source of truth determines the migration story forever. D3 and D4 are not symmetric: moving authority from disk to database later is a data migration, moving it the other way is a rewrite of every read path.
4. **Identity binding strategy.** Pre minting the harness native session id at launch versus discovering it after the fact. Pre minting requires the launcher to know each harness's id derivation, which is a per harness contract that is hard to add later and constrains the launch sequence. R3 already fixes the join key as the control plane `SessionId`, so this decision is only about how the provider side stream binds to it.
5. **Whether the hot path may block.** R5 requires holding a request before it reaches the provider. An interception layer built on a synchronous or fire and forget path cannot gain this later without a rewrite. This is the single decision most likely to be underestimated.
6. **Env surface.** Capture variables become part of the `LILO_` registry and the agent injected set, which is currently a closed four name set with a guard script. Names added here are a public contract with the agent process.
7. **TLS trust model.** Per process CA bundles versus any form of machine or keychain trust. The latter is a security posture change affecting the whole host and is not reversible in users' trust stores.
8. **Release train placement.** Rust in the lockstep crate train versus an independent train. Splitting a train later means versioning a boundary that did not previously exist.
9. **Container support scope.** Declaring Docker runs out of scope for capture is a defensible v1 decision but becomes a correctness hole the moment R1 is read literally as every run.

## Experiments needed

Ordered by how much they collapse the option space. Each is cheap relative to the decision it informs.

1. **Base URL override support per harness.** Confirm which runtime kinds honor an endpoint override to a plain HTTP loopback listener, and which require proxy plus TLS MITM. This single result decides A1 versus A2 versus A3 and therefore most of axis F. Lab evidence indicates Claude honors it and Codex does not, but that must be re verified against current binaries rather than inherited.
2. **Container reachability.** With the Docker backend, determine whether a host loopback listener is reachable from the agent container and at what address, and whether the CA bundle path survives the container boundary. No lab evidence exists. Outcome decides whether decision 9 is a scope cut or an engineering task.
3. **Blocking hold feasibility.** Prove a request can be held in flight, mutated, and released without the harness timing out, and measure the harness's client side timeout budget. Decides irreversible decision 5 before any code commits to a shape.
4. **Streaming overhead.** Measure added p95 latency and memory for a tee on a long SSE response at realistic token volumes. Capture that degrades interactive latency will not survive contact with daily use.
5. **Port allocation under concurrency.** Exercise simultaneous spawns to characterize the bind TOCTOU window that the lab system absorbs with retry. Decides whether C1 needs a reservation mechanism or whether bounded retry suffices.
6. **Native session id determinism.** For each harness, verify the native id and its transcript path are derivable at launch time and stable across versions. Decides irreversible decision 4. A negative result forces discovery based binding.
7. **Credential passthrough and refresh.** Verify that interposition does not break OAuth style refresh mid session, including the case where the harness re authenticates through the proxy. The lab system needed explicit refresh handling on the response path, which suggests the naive assumption fails.
8. **Bypass surface.** Enumerate the env keys a harness consults for proxy and trust configuration, and confirm they can be deterministically cleared and reset. Lab evidence is roughly 30 proxy keys and 9 trust keys, which is larger than a first estimate would suggest.
9. **Orphan and teardown behavior.** Confirm the capture process cannot outlive its run under kill, crash, and daemon restart. Decides how much supervision machinery axis B actually costs.
10. **Fidelity diff sufficiency.** Determine whether the harness transcript carries enough structure to diff against the wire capture at all. R4 is the requirement with the least supporting evidence anywhere: the lab system persists both sides and joins them, and still has not computed this diff.
