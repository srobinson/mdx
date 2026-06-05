# littleorgans transport capture: reject map (hostile negative-space study)

Status: COMPLETE

## Inspected SHAs

- littleorgans (monorepo): `98d8928941b5b5db670ed73ed06af57f61dcfa0a`
- transport-matters (phase-one pinned baseline): `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`

Constraint honored: transport-matters/NOTES/ was not read and is not cited anywhere in this study. No repo edits and no checkout were made; the pinned tree was read through `git show`/`git grep` against the immutable object.

### Baseline correction and revalidation

The first pass surveyed transport-matters at `ed099336ebfa9e72da32ed547b29b932f077ccbd`, not the pinned `a252df24`. Every transport-derived finding was revalidated against the pinned tree. Result: **no load-bearing finding changed**, because the two SHAs share an identical capture plane.

Divergence analysis (`git` against the immutable objects, no checkout):

- The two are **siblings, not ancestor and descendant**. Merge base `101287bf` (2026-07-31 04:25). `a252df24` (06:50) is a feature-branch tip carrying five auth commits; `ed09933` (10:35) is the main line carrying the same auth work in merged form (`8146f16d` "feat(auth): dispatch credentials by source (#352)") plus a canvas slice (`2ca10adb` #353) and a `NOW.md` update.
- The entire Python capture plane is **byte-identical** between the two: `git diff --name-only a252df24 ed09933 -- api/` returns exactly one file, `api/src/transport_matters/harnesses/test_inventory_vocabulary.py`. `packages/`, `desktop/`, `scripts/`, and `justfile` differ by one file (`shared/harness_inventory_vocabulary_v1.json`). Root docs differ only in `NOW.md`; `TLDR.md`, `README.md`, `QUICKSTART.md`, and `docs/` are identical.
- Every citation in appendix B is to `api/src/...`, `api/pyproject.toml`, `TLDR.md`, `README.md`, or `channel-specs.json`, all identical across the pair. Spot-verified directly at `a252df24`: the in-place outbound rewrite in `addon_handlers.py`, the drop path in `pause_session.py`, the hardcoded OAuth client id at `credential_broker.py:57-59`, `CLI_COMMAND = "transport-matters"`, the swallowed "transcript capture disabled this run" in `addon_runtime.py`, `uvicorn.Config` inside `web_runtime.py`, the "Unguarded GET on purpose" docstring in `local_file_routes.py`, `breakpoint_timeout_s: float = 300.0`, the 10-package dependency list including `mitmproxy>=12.2,<13`, 32 Alembic migrations, and zero `LILO_` occurrences tree-wide excluding NOTES/.

**Later-only evidence (present at `ed09933`, absent from the pinned baseline; not relied on by any prohibition):** the harness-inventory vocabulary contract (`shared/harness_inventory_vocabulary_v1.json`, `harnesses/test_inventory_vocabulary.py`) and the first-run harness evidence cards slice in `www/packages/canvas/src/firstrun/` plus `core/src/types/harnessInventory.ts` (#353). Frontend size figures in appendix B are stated at the pinned baseline and are therefore slightly lower than the first pass reported (www 63,636 LOC across 582 files at `a252df24`, versus 65,237 across 594 at `ed09933`; tracked files excluding NOTES/ 1,744 versus 1,758). No prohibition depends on these counts.

## Scope

What littleorgans must reject (architectures, features, dependencies, authority leaks, product claims, migration instincts) while building mandatory capture natively, with `tm` remaining experimental and unreachable as a dependency.

Sections: reject map (immediate prohibitions), deferred questions, falsifiable risks, failure sequences, evidence appendices.

## Worker Status

- Worker 1 (read-only Explore, scope: littleorgans at `98d8928`: launch chain, transport references, storage seams, boundary discipline, env registry, workspace shape): COMPLETE, evidence in appendix A.
- Worker 2 (read-only Explore, scope: transport-matters excluding NOTES/: architecture, launch chain, dependencies, authority surfaces, reliability semantics, product claims, coupling): COMPLETE, evidence in appendix B. Surveyed at `ed09933`; revalidated in-session against the pinned `a252df24` tree, no findings changed.
- Revalidation pass (no worker; direct `git show`/`git grep` against pinned objects, no checkout): COMPLETE. Divergence proven, later-only evidence labeled, two precision refinements applied (R2.2 and B5: wire rows have id-level consumers but no content reader).

## Reject map: immediate prohibitions

### R1. Architectures

**R1.1 Reject the god-process.** transport-matters runs the capture pipeline, the Postgres writer, the transcript tailer, the embedded uvicorn web server, the React UI, the agent launcher, and the credential broker inside one `mitmdump` process (`addon_runtime.py::load_runtime`, `web_runtime.py::start_web_runtime` with `uvicorn.Config(create_app(), ...)` inside the proxy). littleorgans capture must be a component composed by the existing `run_core` root (`internal/session/app/src/compose.rs:115`), never a second composition root, never a process that both sees bytes and serves an API.

**R1.2 Reject liveness coupling between agent and capture.** In transport-matters the child's `ANTHROPIC_BASE_URL`/`HTTPS_PROXY` point at the proxy with no fallback and a stripped proxy env, so proxy death kills agent traffic (fails closed), while capture startup failure is swallowed and the run continues uncaptured (fails open, `addon_runtime.py:527-533` "transcript capture disabled this run"). That is the worst quadrant on both axes for a mandatory-capture product. Prohibited: any design where a capture component crash terminates or blocks the agent, and any design where capture loss is only a log line. littleorgans already has the right primitive for loud loss: `session_sessions.lost_evidence` (`internal/db/migrations/0001_unified_schema.sql:30`).

**R1.3 Reject a second storage plane.** transport-matters keeps a tier-1 disk artifact tree plus a mandatory Postgres with 32 Alembic migrations plus a dark `wire_store`; littleorgans' own stale NOTES propose a separate SQLite `index.db` under `~/.lilo/capture/` (transport-integration.md Decision 6). `CLAUDE.md:141-143` already forbids database files under the tree. Capture rows go in the one Postgres via the one migration chain (`internal/db/migrations/`), capture blobs go under a `LiloPaths::capture_root()` sibling of the existing tree methods (`crates/lilo-paths/src/lilo.rs:39`). No SQLite, no channel homes, no `~/.transport-matters`-style parallel root.

**R1.4 Reject heuristic correlation.** transport-matters has zero occurrences of `LILO_` anywhere; it mints its own `run_id`, synthesizes session ids via `uuid5` (`index/sessions.py:19`), and joins exchanges to transcripts by probing 14 spelling/container permutations of `exchange_id` (`session/exchange_correlation.py::EXCHANGE_ID_CONTAINMENT_PROBES`). littleorgans mints `SessionId` before any process exists and injects it at two audited sites (`internal/session/daemon/src/handler/spawn.rs:369-392`, `internal/runtime/launchers/src/lib.rs:98`). Correlation must be contractual on `LILO_AGENT_SESSION_ID`, never glob-and-guess against provider-minted ids.

**R1.5 Reject subprocess operator namespaces.** Both existing operator namespaces are in-process re-exports (`crates/lilo/src/cli.rs` links `internal/session/app` and `internal/runtime/app`); a `lilo transport ...` namespace delegating to a Python subprocess breaks that mechanism invariant (`NOTES/lilo-operator-namespace-consistency.md`). Whatever capture verb ships, it is Rust, in-process, behind the existing socket.

### R2. Features

**R2.1 Reject traffic mutation in any form.** The transport-matters addon rewrites outbound bodies in place (`addon_handlers.py:222-225` `flow.request.set_text(...)`), carries nine override mutation ops that can delete tools, rewrite system prompts, edit message text, and set arbitrary provider fields (`overrides/__init__.py::apply_overrides`), pauses requests for operator edit (`pause_session.py::handle_breakpoint`), and forges a provider 400 on drop (`pause_session.py:337-342`). littleorgans capture is read-only by construction: no override store, no breakpoint, no pause-and-edit, no code path that can alter, delay, or fabricate a byte between agent and provider.

**R2.2 Reject write-only substrates.** The feature justifying the whole MITM architecture, the wire-vs-transcript fidelity diff, was never built. Verified at the pinned baseline: `session/wire_store.py` exposes only `write_wire_exchange`, `delete_wire_exchange`, and `sweep_wire_store` (a garbage collector), and there is **not one `FROM wire_` or `JOIN wire_` in non-test `api/src`**; zero `fidelity` product code. The only consumers are id-level, not content-level: the control plane subscribes to wire-exchange notifications and stores `wire_exchange_id` on delivery receipts to prove prompt delivery (`session/listen.py::subscribe_wire_exchanges`, `controlplane/delivery_proof.py:145-155`, `controlplane/delivery_wait.py:163`). Captured wire content is therefore written, referenced by id, and never read back (`TLDR.md:48-52` concurs: "nothing reads them back ... remains a product direction"). Prohibited: landing any capture table, artifact file, or store whose content has no reader in the same release train. The read surface is part of the capture slice, not a "product direction".

**R2.3 Reject product surfaces inside capture scope.** `www/` (65k LOC React), `desktop/` (Electron), `controlplane/` (7.2k LOC grants/prompt delivery), `space/` (3k LOC), and two MCP servers all live in the capture repo and are served from the proxy process. The TS/Electron product plane is a separate littleorgans release train; none of it enters `crates/` or `internal/`.

**R2.4 Reject certification machinery as capture scope.** `harnesses/` is 8,979 LOC of certification, compatibility manifests, and evidence minting that no capture reader needs, yet the addon reaches into it. littleorgans capture ships without a harness-certification subsystem.

**R2.5 Reject credential brokering.** transport-matters caches the user's provider auth headers in proxy memory (`counting.py::set_recent_auth`), spends them on its own `/v1/messages/count_tokens` calls, reads and writes the macOS Keychain via `/usr/bin/security` (`credential_broker.py:284,306`), performs its own OAuth refresh against Anthropic with a hardcoded client id (`credential_broker.py:57-59`), and rotates the user's refresh token. All of it is prohibited. Capture never harvests, caches, spends, refreshes, or persists credentials, and stored bytes are redacted at write time, not only in diagnostics (`transport_redaction.py` redacts diagnostics while `request.raw` stores headers as-is; that posture is also rejected).

**R2.6 Reject unauthenticated authority routes.** transport-matters ships an intentionally unguarded arbitrary local file read (`api/v1/local_file_routes.py`, "Unguarded GET on purpose", no root confinement), a websocket bridge that can type into a running agent's terminal (`run_proxy.py:457` → `RunManager.write`), and loopback-origin-only guards with no token. littleorgans has one door with peer credentials extracted once (`compose.rs:222` `peer_creds::extract`); capture adds no HTTP listener and no second door.

### R3. Dependencies

**R3.1 Reject `tm`/transport-matters as a dependency, verbatim.** `LESSONS.md:18-19` at HEAD: littleorgans must not invoke, package, version against, or depend on them. The workspace's verified negatives (zero `transport` in `Cargo.lock`, no `Command::new("tm")`, no `tm` literal, `python/` empty but for a README) are the acceptance state to preserve. Note `tm` does not even exist as a binary; the only CLI is `transport-matters` (`cli/identity.py:3`), so the "tm wrapper" named in stale docs was never real.

**R3.2 Reject mitmproxy-class interception dependencies.** `mitmproxy>=12.2`, pyOpenSSL overrides, CA bundle synthesis merging system trust roots with the shared `~/.mitmproxy` CA (`cli/trust.py:82`), per-process trust env injection (`CODEX_CA_CERTIFICATE`), and 34-key proxy plus 9-key trust denylists to stop the child escaping. None of this enters the Rust workspace. TLS interception and trust manipulation are not v1 capture mechanisms.

**R3.3 Reject the runtime zoo.** Python >=3.14, FastAPI/uvicorn, psycopg, Alembic (a second migration system), bundled node (~120MB wheel extra), node-pty prebuilds, Electron. The crate family stays pure Rust; any raw socket/process primitive goes through `crates/lilo-sys` (enforced by `scripts/check-seam.sh`, 17 banned patterns).

**R3.4 Reject foreign env prefixes.** Stale Decision 7 proposed permitting `TM_`/`TRANSPORT_`. littleorgans owns exactly `LILO_`; new capture names are `LILO_*` consts in the registry (`crates/lilo-paths/src/env.rs`) or they fail `scripts/check-env.sh --check`. transport-matters' 30+ `TRANSPORT_MATTERS_*` vars are a cautionary inventory, not a template.

### R4. Authority leaks

**R4.1 No writes outside `~/.lilo`.** transport-matters writes to the Keychain, `~/.claude-auth`, `tempfile.mkdtemp` CA dirs, and builds symlink overlays into the user's real `~/.claude`/`~/.codex` (`cli/home_overlay.py:311-432`). Capture writes under `LiloPaths` only.

**R4.2 No identity bypass.** Capture verbs get a new `Action::Capture` variant (`crates/lilo-im-core/src/types.rs:147`, currently 12 variants with none for the existing `lilo capture` either; fix that while adding it) and authorize at the existing single gates (`internal/runtime/daemon/src/handler.rs:132`, session verb pattern in `handler/authz.rs`). No self-minted principals, no route that skips `peer_creds`.

**R4.3 No blind spots.** `lilo runtime spawn` bypasses the session layer by design (`internal/runtime/app/src/cli.rs:72`, CLAUDE.md:130-133). Mandatory capture attaches at the runtime argv choke point (`internal/runtime/daemon/src/api.rs:81` via a `RuntimeBackend::prepare_launch` sibling, the seam Docker already uses at `docker_argv.rs:16`), not at the session layer where the diagnostic path would silently escape it.

**R4.4 No shim bootstrap widening without justification.** The shim env is contractually one variable, `LILO_SOCKET_PATH` (`shim_socket.rs:139-148`); capture env rides the existing post-spawn UDS handoff like everything else.

### R5. Product claims

**R5.1 Never claim the diff is the product before the reader exists.** transport-matters' banner claim ("their difference is the product", `TLDR.md:32-35`) is contradicted by its own tree: no fidelity code, dark store. littleorgans docs claim only what `lilo` can print today.

**R5.2 Never claim orthogonality while holding authority.** transport-matters claims it "does not coordinate with session-matters or runtime-matters at runtime" (`TLDR.md:23-25`) while shipping a control plane that spawns agents, kills runs, injects prompts, and types into terminals. littleorgans capture is observability; the moment a capture surface can act on a session, it is a session verb and moves behind the session boundary with its own authorization.

**R5.3 Never claim mandatory while failing open silently.** "Capture by construction" (`LESSONS.md:18`) means a capture gap is a recorded, queryable state on the session (`lost_evidence` pattern), surfaced in `lilo doctor` and `lilo get session`, not a log line in a file nobody tails.

### R6. Migration instincts

**R6.1 Reject porting the Python.** ~58k LOC of capture-plane Python does not translate; the lessons travel, the code does not. No FFI, no subprocess wrapping, no "temporary" vendoring.

**R6.2 Reject implementing from `NOTES/transport-integration.md`.** Its Decision 1 ("runtime execs tm", marked settled) and the `CLAUDE.md:61-63`/README bounded-context prose reconciled to it are stale against `LESSONS.md:19` at the same HEAD. Docs get flipped to the LESSONS posture; code never moves toward the dead premise. (Also see project memory: the note's capture-engine premise is dead; the open call is TS product plane vs Rust control plane, pending Stuart.)

**R6.3 Reject copying the artifact taxonomy wholesale.** The 12-file per-exchange directory (`ExchangeArtifactPaths`), channel homes, run-dir hashing, and provisional/finalize dance are shaped by mitmproxy's flow lifecycle and a two-plane repo. littleorgans derives its artifact shape from its own read surface, starting minimal.

**R6.4 Reject inheriting god modules.** transport-matters' load-bearing files (633-line `addon_runtime.py`, 8,965 LOC `cli/`, library importing CLI via `captured/run.py` → `cli.launch_runtime`) are exactly what littleorgans' 700/150 limits and `check-loc` gate exist to prevent. No capture file ships near the limit "because the pattern needs it".

## Deferred questions (not prohibitions; need design or Stuart)

- D1. Interception mechanism: wire-level capture (reverse proxy / env redirect, Rust-native) versus harness-transcript-only capture for v1. The transport evidence shows transcript tailing plus a contractual session id delivers most of the observable value without any TLS or proxy authority.
- D2. Failure posture knobs: does `lilo run --no-capture` exist; does traffic fall back to direct on capture failure or does the spawn refuse (stale Decisions 8/9 were left open; they remain genuinely open).
- D3. Read surface shape: which `lilo` verbs expose turns (`lilo get session` detail, a `turns` sub-resource, `lilo logs` extension) and their JSON contracts.
- D4. Redaction and retention policy for captured bodies (who decides, where the policy lives, defaults).
- D5. The TS product plane versus Rust control plane split for any capture UI (explicitly pending Stuart).
- D6. Whether `wire_session_id`-style provider-native ids are stored as secondary metadata alongside `SessionId` for cross-referencing provider consoles.

## Falsifiable risks

- F1. Liveness coupling regression: falsified by a test that SIGKILLs the capture component mid-turn and asserts the agent process and its provider traffic survive.
- F2. Silent capture loss: falsified by a test that makes Postgres unreachable at spawn and asserts the session row carries a queryable lost-capture marker and `lilo doctor` reports it.
- F3. Correlation drift: falsified by an integration test asserting every captured turn joins to a `session_sessions` row by `LILO_AGENT_SESSION_ID` with zero heuristic probing, including resumed sessions.
- F4. Mutation creep: falsified by the absence, enforceable by review grep, of any API returning a writable handle to an in-flight request; the moment one appears, R2.1 is breached.
- F5. Blind spot regression: falsified by a test that `lilo runtime spawn` (session-bypass path) still produces capture evidence, or by an explicit locked decision that diagnostic spawns are uncaptured.
- F6. Buffering loss: falsified by a crash-mid-stream test asserting partial response bytes are durable (transport-matters buffers whole responses in proxy memory, `response_stream.py:35`, losing everything on crash).

## Failure sequences (observed or derivable at pinned `a252df24`; must not be reproduced)

1. Proxy dies mid-turn → child's redirected env has no fallback route → agent hard-fails on every subsequent request. (Fail-closed traffic.)
2. Postgres down when the addon starts → exception swallowed, "capture disabled this run" logged → operator believes capture is mandatory, the run completes with no correlated history. (Fail-open capture, silent.)
3. Crash mid-stream → entire response body existed only in a proxy-memory `bytearray` → whole body lost, not truncated.
4. Operator arms a breakpoint, walks away → 300s timeout auto-releases the paused turn; concurrent turns serialize behind one pause lock at N x 300s worst case; proxy restart drops all paused flows (module-global state).
5. Substrate ships dark → wire store accrues writes and a GC sweep but never a reader → the architecture's justifying feature never materializes while its full cost (MITM, trust, Postgres) is paid.
6. Credential cache plus loopback HTTP route → any local process can trigger provider-billed calls with the user's harvested auth; the unguarded file route reads any user-readable file on the machine.
7. Backend hard-killed → mitmdump orphans leak to launchd; a self-reap watchdog had to be bolted on (`self_reap.py`).
8. Docs marked "settled" outlive their premise → `CLAUDE.md` and README reconciled to a design the newest lesson forbids → next implementer codes toward the stale doc. (This sequence is live in littleorgans at `98d8928`; R6.2 is its stop.)

## Evidence appendix A: littleorgans at `98d8928` (verified by repo survey)

### A1. Launch chain and the one legitimate interposition seam

`lilo run` → `Cli::run` (`crates/lilo/src/cli.rs:76`) → session CLI dispatch (`internal/session/app/src/cli.rs:45`) → `spawn_session` builds `SpawnRequest` over UDS (`internal/session/app/src/cli/run.rs:41`) → `DaemonState::spawn` mints `SessionId`, writes `session_spawn_intents` (`internal/session/daemon/src/handler/spawn.rs:24`) → `RuntimePort::spawn` (`internal/session/driver/src/port.rs:18`) → `spawn_domain` (`internal/runtime/daemon/src/api.rs:73`), where **line 81 is the single argv choke point** (`dispatch(&request.runtime)?.launch_spec(&request)?`) → `spawn_via_shim` (`internal/runtime/daemon/src/backend.rs:96`) → shim launches the agent (`internal/runtime/app/src/cli/shim.rs:35`).

- `RuntimeBackend::prepare_launch` (`internal/runtime/daemon/src/backend.rs:15`) is the existing, tested seam for argv interposition; Docker already rewrites `LaunchSpec.argv` through it (`internal/runtime/daemon/src/docker_argv.rs:16`). Native capture needs a `prepare_launch` sibling, not a new hop.
- Env injection is split: session-side upserts `LILO_AGENT_SESSION_ID/ROLE/WORKSPACE` after stripping inherited `LILO_AGENT_*` (`spawn.rs:369-392`); runtime-side upserts `SESSION_ID/RUNTIME` (`internal/runtime/launchers/src/lib.rs:98`). The shim bootstrap env is contractually minimal, exactly one variable, `LILO_SOCKET_PATH` (`internal/runtime/daemon/src/shim_socket.rs:139-148`).

### A2. Verified negatives: no transport code exists

- Zero `Transport` hits in `*.rs`; zero `transport` in `Cargo.lock`; no workspace member; no `Command::new("tm")` or `"tm"` literal; `python/` holds exactly one file, `python/README.md`.
- All transport presence is prose: `NOTES/transport-integration.md` (163 lines, 2026-06-05), `CLAUDE.md` bounded-context and command-surface sections, `README.md:27-33`.

### A3. The live contradiction at HEAD

- `NOTES/transport-integration.md` Decision 1 (marked "settled"): `lilo run claude → runtime execs tm claude`, "capture is a side effect of every `lilo run`". Decision 6 proposes SQLite `index.db` under `~/.lilo/capture/`. Decision 7 proposes permitting `TM_`/`TRANSPORT_` foreign env prefixes.
- `LESSONS.md:18-19` (added in HEAD commit `98d8928`, newest artifact in the tree): capture is a first-class littleorgans product context, and `tm`/transport-matters are experimental research; littleorgans "must not invoke, package, version against, or depend on them."
- `CLAUDE.md:141-143`: "The database is Postgres ... no database file lives under the tree", directly rejecting Decision 6's SQLite proposal.

### A4. Currently absent slots a native capture context would fill

- `LiloPaths` (`crates/lilo-paths/src/lilo.rs:39`) has no `capture_root()`; the `~/.lilo` tree has config/run/data/logs/cache/tmp, events at `data/events/runtime.jsonl`.
- `Action` enum (`crates/lilo-im-core/src/types.rs:147`) has 12 variants, no `Capture`.
- `internal/db/migrations/0001_unified_schema.sql` has no capture/turn table (existing: identity_audit, session_sessions, session_namespaces, messages, message_deliveries, session_labels, session_event_cursor, session_spawn_intents, runtime_lifecycle, runtime_metadata).
- `crates/lilo-paths/src/env.rs` registry has 34 owned names, no `LILO_CAPTURE_*`; `scripts/check-env.sh --check` mechanically rejects unregistered `LILO_*` literals.

### A5. Paths capture must not miss and boundaries it must not bypass

- `lilo runtime spawn` is a documented session-bypass diagnostic path (`internal/runtime/app/src/cli.rs:72`); capture attached at the session layer would silently miss it; attached at `api.rs:81` it would not.
- Authorization is a single gate per substrate (`internal/runtime/daemon/src/handler.rs:132` `authorize_runtime_rpc`; session verbs per `internal/session/daemon/src/handler/authz.rs`). Peer creds are extracted once at the socket door (`internal/session/app/src/compose.rs:222`).
- `scripts/check-seam.sh` bans raw platform primitives outside `crates/lilo-sys` (17 patterns); any capture proxy/socket code must go through `lilo-sys`.
- Existing observation is lifecycle + rendered terminal text only: `lilo capture` is tmux `capture-pane` (`internal/runtime/daemon/src/tmux.rs:79`), `lilo logs` slurps `transcript_path` (`internal/session/daemon/src/polish.rs:16`), events are lifecycle JSONL (`internal/runtime/daemon/src/event_log.rs:130`). Zero wire bytes observed today.

### A6. Known doc drift (baseline hygiene, not capture scope)

- `docs/reference/env-vars.md:81` still says `LILO_AGENT_SESSION_ID` is UUIDv7; `crates/lilo-common/src/id.rs:44` generates v4 and the test at `:132` asserts v4.

## Evidence appendix B: transport-matters at pinned `a252df24` (NOTES/ never opened)

Surveyed at `ed09933` and revalidated against the pinned tree; the capture plane is byte-identical between them, so every citation below resolves at `a252df24`. See the baseline correction section for the divergence proof and the two later-only items.

### B1. Shape and scale

1,744 tracked files excluding NOTES/; ~58k LOC non-test Python in `api/src/transport_matters`. Layout: `api/` (Python package, proxy addon, FastAPI, CLI, Postgres store, 32 Alembic migrations), `www/` (six React packages, 63,636 LOC across 582 files: inspector, canvas, shell, core, host, space-client), `packages/` (TS product plane `@tm/*`: fastify, node-pty, pg), `desktop/` (Electron), plus root markdown docs. Self-description (`TLDR.md:3-9`): proxies live agent traffic, parses bytes to IR, persists turn artifacts, "can pause the next outbound request so an operator can inspect or edit it", records correlated transcripts in Postgres.

### B2. Interposition and process model

- Claude: reverse proxy, child gets `ANTHROPIC_BASE_URL=http://localhost:{port}`. Codex: true TLS interception via explicit HTTPS proxy plus `CODEX_CA_CERTIFICATE` bundle (`cli/launch_runtime.py::build_mitmdump_argv:383`, `launch/environment.py::build_managed_child_env:216`).
- Everything runs inside the spawned `mitmdump` process: addon (`addon.py::TransportMattersAddon`), capture runtime bootstrap (`addon_runtime.py::load_runtime:580`), and the embedded FastAPI/uvicorn web server (`web_runtime.py::start_web_runtime`), which also serves the React bundles, the file-read routes, the run spawner, and two MCP servers.
- Child env hygiene: strips a 34-key proxy denylist and a 9-key trust denylist so the child cannot bypass the proxy (`launch/environment.py:30,76`).
- No `tm` binary exists; the CLI is `transport-matters` (`cli/identity.py:3`). Zero occurrences of `LILO_` anywhere in the tree: no seam for an external session id.

### B3. Authority surfaces

- Mutation: in-place outbound body rewrite (`addon_handlers.py:222-225`), nine override ops incl. system-prompt and message-text rewrite (`overrides/__init__.py:141` ff.), pause-and-edit breakpoints (`pause_session.py:296,363`), forged provider 400 on drop (`pause_session.py:337-342`), test addon forging HTTP 426 (`force_http_fallback_addon.py`).
- Credentials: caches user auth headers in proxy memory and spends them on `/v1/messages/count_tokens` (`counting.py:120,201,235`; `breakpoint.py:39-42` docstring says "on the user's behalf"); macOS Keychain read/write via `/usr/bin/security` (`credential_broker.py:284,306`); own OAuth refresh against Anthropic with hardcoded client id, rotating the user's refresh token (`credential_broker.py:57-59,347,412`); fleet auth home at `~/.claude-auth` (`claude_fleet_auth.py:16`).
- TLS: merges system trust roots with the shared `~/.mitmproxy` CA into per-process bundles (`cli/trust.py:82,110`); no global cert install (the README claim holds), but the machine-wide mitmproxy CA key is shared with any other mitmproxy user.
- Writes outside its state dir: Keychain, `~/.claude-auth`, temp CA dirs, symlink overlays into the user's real `~/.claude`/`~/.codex` (`cli/home_overlay.py:311-432`).
- Unauthenticated loopback surfaces: arbitrary absolute-path file read, no root confinement, "Unguarded GET on purpose" (`api/v1/local_file_routes.py:5,33,49`); websocket that writes keystrokes into a live agent PTY (`api/v1/run_proxy.py:457` → `packages/runtime/src/service/RunManager.ts:360`); run spawn/terminate routes; prompt-injection delivery (`controlplane/prompt_delivery.py:80`).

### B4. Reliability semantics

- Traffic fails closed: redirected env has no fallback; proxy must be up within 5s or the client is never spawned (`cli/runner.py:338`, `cli/launch_outcomes.py:25`).
- Capture fails open, silently: capture-start exceptions swallowed with "transcript capture disabled this run" (`addon_runtime.py:495,527-533,564-566`); override pipeline "Never raises", forwards unmodified (`request_pipeline.py:70,86`); drift capture "can never break or block capture" (`drift_capture.py:7-9`).
- Loss windows: Postgres-down whole-run loss; 0.25s transcript tail lag (`index/tailer.py`); provisional-exchange orphan on crash (`exchange_recorder/__init__.py:313,426`); whole response body buffered in memory until stream end (`response_stream.py:35,47`); breakpoint auto-release at 300s with process-local pause state (`config.py:113`, `breakpoint.py:52-54,79`).
- Done well and worth learning from: ordered drain shutdown (`addon_runtime.py:587-620`), parent-death self-reaping (`self_reap.py`, `PR_SET_PDEATHSIG` / getppid watchdog), atomic `.tmp`/`.bak`/`.del` disk staging with recovery (`atomic_io.py`, `storage/disk.py:38`), quarantine-not-drop for bad transcript records (`session/quarantine.py`).

### B5. The unbuilt payoff

The wire-vs-transcript fidelity diff ("their difference is the product", `TLDR.md:32-35`) has no implementation. Verified at the pinned baseline: `session/wire_store.py` exposes `write_wire_exchange`, `delete_wire_exchange`, `sweep_wire_store` and nothing else; no `FROM wire_`/`JOIN wire_` anywhere in non-test `api/src`; zero `fidelity` product code (the two `fidelity` string hits are `session/wire_normalization.py:8` prose and a test-harness caveat). Wire rows are referenced by id only, for prompt-delivery proof (`controlplane/delivery_proof.py`, `delivery_wait.py`, `session/listen.py::subscribe_wire_exchanges`), never read for content. The only shipped diff is the operator's own edits, original IR versus curated IR (`request_diff.py`; the single `diffLines` import in the frontend, `www/packages/inspector/src/components/editor/TextOverrideEditor.tsx:1`).

### B6. Coupling facts

- God junction: `addon_runtime.py` (633 lines) constructs and tears down pipeline, Postgres writer, tailer, wire store, live status, drift, and the web server.
- `cli/` is 8,965 LOC of launch policy with the library layer importing the CLI layer (`captured/run.py` imports `cli.launch_runtime`).
- `harnesses/` is 8,979 LOC of certification/compatibility that no capture reader needs, yet `addon.py` and `drift_capture.py` reach into it.
- `controlplane/` (7,243) plus `space/` (2,984) are a second product owning 11 of 32 migrations, inside the repo that claims runtime orthogonality (`TLDR.md:23-25`).
- Correlation joins transcripts to exchanges by probing 14 id spelling/container permutations (`session/exchange_correlation.py`).
- Cleanly separable, evidence the lessons can travel without the code: `storage/` (path policy + atomic writes), `adapters/` (pure bytes↔IR), `ir.py`, `overrides/` (pure IR→IR), `supervisor/`, `env_keys.py`.

### B7. Dependency inventory

Python >=3.14; `mitmproxy>=12.2,<13`, `fastapi`, `uvicorn`, `psycopg[binary,pool]`, `alembic`, `mcp`, `pyOpenSSL>=26` override; optional bundled node (~120MB); node-pty prebuilds; Electron. Postgres is mandatory (fixed logical DBs, `docker-compose.yml` pins postgres:17). Fixed channel ports 8787/8788/8789 (+preview/dev triples), all loopback.

