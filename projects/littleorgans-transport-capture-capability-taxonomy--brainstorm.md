# littleorgans Transport Capture — Capability Taxonomy (Brainstorm)

Status: COMPLETE

## Evidence baseline

- littleorgans monorepo: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans` @ `98d8928941b5b5db670ed73ed06af57f61dcfa0a`
- transport-matters (experimental evidence only, zero runtime dependency proposed): phase-one pinned baseline `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55`. Initial audit ran against working-tree HEAD `ed099336ebfa9e72da32ed547b29b932f077ccbd`; all transport-derived findings have been revalidated against the immutable `a252df24` tree (see Baseline revalidation below).
- Exclusion honored: no content read or cited from any `NOTES/` directory. No checkouts, no repo edits; revalidation used read-only git plumbing (`git show <sha>:<path>`, `git diff <a> <b>`, `git ls-tree`, `git grep <ref>`).

## Baseline revalidation (a252df24)

Topology: the two baselines diverge from merge-base `101287bf`; `a252df24` ("fix(auth): close credential review residuals") carries 5 auth commits, `ed099336` carries 3 doc/UI commits. Neither is an ancestor of the other.

Method and results:

1. Symmetric tree diff `ed099336 ↔ a252df24` touches 26 files: `NOW.md`, `api/src/transport_matters/harnesses/test_inventory_vocabulary.py`, `shared/harness_inventory_vocabulary_v1.json`, and 23 `www/packages/{canvas,core}` UI files (firstrun, launcher, route, transport.ts, harnessInventory). Intersection with every file cited in Threads 2 and 3 and the taxonomy: empty, except the one shared JSON noted below. Every cited `api/src`, `api/migrations`, `packages/{runtime,contract,activity}`, `desktop`, `docs`, and top-level `*.md` file is byte-identical between the baselines, so all cited symbols and line numbers hold verbatim at `a252df24`.
2. Direct spot-checks in the `a252df24` tree confirmed 18 load-bearing anchors at their cited locations: `ANTHROPIC_BASE_URL` injection (`captured/claude.py:206`), `install_response_tee` (`response_stream.py:17`), `outbound_request_if_changed` (`request_diff.py:25`), `TranscriptSnapshotGapError` (`transcript_snapshot.py:37`), `armed_once` (`breakpoint.py:52`), `WireDriftObserver` (`drift_capture.py:174`), raw-bytes-never-in-Postgres pointer doctrine (`wire_store.py:8`), `ENV_PREFIX` (`env_keys.py`), `UnknownBlock` (`ir.py:40`), `_build_codex_ca_bundle` (`trust.py:82`), `wire_gc` (`db_cmd.py:69`), `CAPTURE_HEALTH_FAILURE_THRESHOLD` (`CaptureHealthMonitor.ts:7`), `capture-lost` settle (`RunManager.ts:86`), `projectConversationPage` caps (`conversation.ts:127`), "ships dark" (`TLDR.md:49`), two-stream doctrine (`PROJECT.md:59`), advisory posture (`docs/ARCHITECTURE.md:234`), `FrozenLaunchSpec` (`LAUNCH-CONTRACT.md:27`).
3. Zero `LILO_*` references at `a252df24` (git grep over `*.py`, `*.ts`, `*.md`, NOTES excluded): confirmed. Migration count at `a252df24`: 32, confirmed.

Later-only evidence, explicitly labeled:

- **LATER-ONLY (ed099336, absent at a252df24)**: `shared/harness_inventory_vocabulary_v1.json`. Thread 3 finding 1.5 counts four `shared/` vocabularies; at `a252df24` there are three (`char_accounting_v1.json`, `harness_descriptors_v1.json`, `override_targets_v1.json`). Non-load-bearing existence claim; no taxonomy tier depends on it.

No taxonomy tier, the minimum coherent product, or any exclusion changes under the pinned baseline.

## Worker Status

| Worker | Scope | State |
|---|---|---|
| Thread 1: littleorgans attachment points | Launch chain, existing transport code, storage substrate, session identity, CLI/protocol, runtime adapters, capture seams in littleorgans @ 98d8928 | COMPLETE |
| Thread 2: transport-matters wire layer | Proxy interposition, launch contract, harness compatibility, streaming, breakpoints, reliability, operations in transport-matters @ ed099336 (NOTES/ excluded) | COMPLETE |
| Thread 3: transport-matters capture data | Data model, transcript vs wire fidelity, artifacts, storage, read surfaces, identity correlation, product boundary claims in transport-matters @ ed099336 (NOTES/ excluded) | COMPLETE |
| Baseline revalidation | Revalidate all transport-derived load-bearing findings against pinned baseline a252df24 via read-only git plumbing; label later-only evidence | COMPLETE |

## Method

Three parallel evidence threads, synthesis to follow:

1. littleorgans attachment points: launch chain, storage substrate, session identity, existing transport surface, seams for in-repo capture.
2. transport-matters wire layer: proxy interposition, launch contract, harness compatibility, streaming, breakpoints, reliability.
3. transport-matters capture data: data model, transcript vs wire fidelity, artifacts, storage, read surfaces, product boundary claims.

Sections below are populated as threads complete; status flips to COMPLETE only when the full taxonomy, minimum coherent product, exclusions, and path+symbol evidence are present.

## Taxonomy

Four tiers per dimension. **V1** = mandatory for a coherent local-first capture capability in littleorgans, built in Rust with zero dependency on the transport-matters codebase. **ENT** = enterprise qualification, what makes the capability sellable to a team or org. **LATER** = real possibilities that should wait for a proven read demand. **DISTRACTION** = attractive work that evidence says to refuse.

### 1. Wire

- **V1** Reverse-proxy interposition for the claude runtime via `ANTHROPIC_BASE_URL` pointed at a lilod-owned loopback listener. Injection site: `HostRuntimeBackend::prepare_launch` (`internal/runtime/daemon/src/backend.rs:61`), the exact seam Docker already uses to rewrite launches (`docker_argv.rs:16`). tm proves the mechanism works without sudo, system proxy, or global certs (`captured/claude.py:181-207`; `README.md:3-11`).
- **V1** Byte-faithful raw capture of request and response, persisted before any derived work (tm invariant, `PROJECT.md:204-207`). SSE tee, never buffer: client streams live while the capture accumulates (`response_stream.py:17`).
- **V1** Zero mutation. The v1 proxy forwards original bytes untouched, always. tm's `request_diff.py:25` no-op fast path becomes the only path.
- **V1** Anti-bypass hygiene at spawn: extend the existing `CALLER_ENV_DENYLIST` (`spawn_context.rs:10`) with proxy and trust keys so the child cannot inherit a competing route.
- **ENT** Scoped-CA forward MITM for TLS-pinned or websocket harnesses (tm `cli/trust.py:82`); header redaction policy at the storage boundary (`transport_redaction.py:9-27`); audited capture access.
- **LATER** Codex websocket segmentation and HTTP fallback (`addon_handlers.py:279`); incremental live-status reframing with streaming decompression (`sse.py:49`); credential-expiry refresh (`credential_refresh.py:41`).
- **DISTRACTION** Multi-tenant shared proxy with per-run listener demux (`shared_proxy/`). v1 is one operator, one host; a per-session listener owned by the shim is simpler and self-cleaning.

### 2. Transcript

- **V1** Launcher-owned session minting. littleorgans already mints `SessionId` before any process exists (`handler/spawn.rs:29`); pass `--session-id <uuid>` to claude at the launcher so the native transcript, the wire metadata, and `session_sessions` all agree on one id. tm proves this contract (`PROJECT.md:103-118`; `DIRECT_MINT_PROVIDERS`, `owned_transcript_binding.py:32`).
- **V1** Byte-faithful, append-only, gap-detecting tee of the harness's native transcript file into the per-session capture dir. Deterministic path, no globbing, because the launcher minted the id (tm `transcript_snapshot.py:37-63`; `env_keys.py:53-59`). Best-effort: transcript failure never stops the proxy (tm `PROJECT.md:210`).
- **ENT** Curated conversation projection that filters injected harness framing for agent readers (tm `conversation_projection.py:9-105`); presentation denylist that never strips the wire (`transcript_denylist.py`).
- **LATER** Codex pre-seeded rollout + `resume` minting (uuid5 synthesis); subagent sidechain modeling.
- **DISTRACTION** Reconstructing "what the harness believed" from wire inference instead of teeing the harness's own bytes. tm's design shows ownership of the native file is strictly better evidence.

### 3. Fidelity

- **V1** The two-stream invariant only: capture wire and transcript separately, never collapse them, keep both raw (tm doctrine, `PROJECT.md:57-69`: "Their difference is the product"). v1 additionally holds the stronger invariant that the pipeline mutates nothing, so wire fidelity is passthrough-perfect by construction.
- **ENT** Typed drift evidence with detail codes, digests, and attribution that can gate a harness version (tm `harnesses/blocks.py:46-76,237`; `drift_capture.py:174`). This is the qualification story: proof the capture still understands the harness after a vendor update.
- **LATER** The wire-vs-transcript diff itself, as a read surface first. tm's own state is the warning: the wire store "ships dark... nothing reads them back" (`TLDR.md:47-52`).
- **DISTRACTION** Building diff algorithms or a diff substrate before a single read exists. tm names the need precisely: "a read surface over that store, not a new substrate."

### 4. Artifacts

- **V1** Per-exchange file set, minimal: raw request, raw response, a normalized turn record, and a per-session `index.jsonl` (subset of tm `disk_layout.py:13-24`). Provider-reported token usage only, never estimated (tm `storage/base.py:49-72` principle).
- **V1** An `UnknownBlock`-style escape hatch in whatever normalization exists, so unrecognized shapes are preserved verbatim rather than dropped (tm `ir.py`).
- **ENT** Content-addressed system-prompt and tool-schema sets with ordered-set hashes (`wire_contracts.py:27-34`), the queryable injected-context story; image blob store with dedup (`session/artifacts.py:12-44`); transport-layer artifacts with redaction.
- **LATER** Tool calls exploded into indexed rows; thinking blocks as first-class; Codex semantic turn derivation (`events.jsonl` + `turn.json`).
- **DISTRACTION** Two-source token accounting via a proxy-bypassing `count_tokens` egress using the agent's captured auth headers (tm `addon_runtime.py:352-357`). An observer minting its own un-observed traffic is the wrong trade for local v1. Also: the full frozen IR taxonomy up front; store raw plus minimal normalization and grow the IR from read demand.

### 5. Breakpoints

- **V1** None. Capture ships observation-only. This keeps transport outside the control plane in the load-bearing sense the monorepo CLAUDE.md already asserts.
- **ENT** Audited, identity-attributed mutation: the override pipeline with a persisted audit trail (`request_pipeline.py:65`; `overrides/audit.py`), gated through identity-matters so every rewrite has a principal.
- **LATER** Arm-once pause with serialized presentation, timeout auto-release, and in-flight byte rewrite (`breakpoint.py:52,58`; `pause_session.py:270,353`). tm proves the mechanism end to end when the demand arrives.
- **DISTRACTION** Shipping mutation before reads. Thread 3's medium-confidence inference stands as the cautionary shape: tm's control ambition ran ahead of its observation implementation while the flagship observation feature stayed unbuilt.

### 6. Compatibility

- **V1** One harness adapter (claude), first-match dispatch, and the fail-open comprehension rule: unknown shape or failed parse passes traffic through unmodified and records an unparsed exchange (tm `addon_handlers.py:184-193`). Gate the capability itself with `RuntimeCapability::WireCapture` in the existing protocol registry (`version.rs:51`).
- **V1** Update the launcher conformance tripwire deliberately (`conformance.rs:31-36` asserts `argv.len() == 1`) if the wrapper prepend lands at the launcher layer; prepending at `prepare_launch` avoids it.
- **ENT** Signed, versioned compatibility releases with wire-request and wire-response facet revisions, data-only publication, certification over real owned captures (tm `HARNESS-COMPATIBILITY.md:83-138`; `COMPATIBILITY-PUBLISHING.md:33-46`).
- **LATER** Codex adapter; advisory-to-enforcing posture switch (tm ships advisory-only today, `docs/ARCHITECTURE.md:224-244`).
- **DISTRACTION** Compat publication machinery for a pre-release single-operator product. tm needed it because it sells a signed desktop app; littleorgans v1 does not.

### 7. Storage

- **V1** Tier-1 files under `~/.lilo`, convention-consistent: `data/transport/<session_id>/` via a new `LiloPaths::capture_dir` alongside `runtime_log_dir` (`lilo.rs:79,107`), copying the existing `EventLog` JSONL-plus-cursor pattern (`event_log.rs:87-98`). Atomic writes.
- **V1** Raw bytes never enter Postgres; the session row points to disk. Populate the existing, currently tmux-empty `session_sessions.transcript_path` (`0001_unified_schema.sql:42`; `internal/session/core/src/paths.rs:8`) with the capture dir. No migration required.
- **ENT** Content-addressed dedup store in Postgres with stamp-stripping normalization (tm measured: without stripping, message dedup is ~0%, `wire_normalization.py:1-13`); reference-driven GC (`db wire-gc` shape); retention policy; the schema's existing `owner` column feeding the RLS tier.
- **LATER** Crash-safe staged dirs with recovery predicates (`.tmp/.bak/.del`, tm `disk_layout.py:129-165`); durable launch facts decoupled from liveness (`sessions.json` pattern); idempotent replay/backfill from tier-1.
- **DISTRACTION** A Postgres wire store before any reader. tm carries 32 migrations and a wire store that ships dark; littleorgans should not repeat the sequence.

### 8. Product reads

- **V1** `lilo transport list`, `lilo transport show <session>`, `lilo transport paths`, exactly the operator namespace the monorepo CLAUDE.md reserves. TOML-first authoring through `tools/schemas/cli.toml` to satisfy the generated-surface guards. Selector reuse: SessionId prefix resolution already exists (`id.rs:63`; session core `Selector`).
- **V1** Reads come straight off tier-1 disk (list from `index.jsonl`, show from turn records), no database read path required. Agents get the same data through the existing `lilo mcp` surface reading `LILO_AGENT_SESSION_ID`.
- **ENT** Twin-skin read service (REST + MCP, no logic in skins, tm `CONTROLPLANE.md:15-19`); token-bounded conversation reads with hard server caps and opaque cursors (`observe_models.py`; caps in `conversation.ts:3-7`); identity-attributed, audited reads.
- **LATER** Timeline projection with `SourceRef` provenance and SSE streams (tm `timeline_models.py:44-299`); resource resolver with range requests; roster and watch/unwatch damped push.
- **DISTRACTION** The human UI. The TS/Electron app is a separate release train by locked decision; building HTTP read APIs for it before CLI reads exist inverts the dependency.

### 9. Operations

- **V1** Proxy lifecycle owned by the shim: start the loopback listener in `runtime_command`'s process space or as a shim-supervised child (`shim.rs:119`), so parent-death cleanup is inherited from the existing shim contract (survives child, forwards SIGTERM, reports exit). Kernel-allocated ports per session (tm `loopback.py:16` pattern). Capture start/stop recorded in the runtime event log.
- **V1** `lilo doctor` aggregates capture health; no per-substrate doctor verb, per the locked surface rule.
- **ENT** Channel separation (stable/preview/dev homes, separate DBs and ports, tm `storage_roots.py:24-64`); loopback hardening (trusted-host checks, unix-socket control channels); operational audit.
- **LATER** Fail-closed capture-health monitoring that kills the run on capture loss (tm `CaptureHealthMonitor.ts:27`, `RunManager.ts:583`), a policy decision littleorgans should make explicitly, not inherit; bind-failure forensics with bounded retry (`bind_failure.py`); self-reap hardening (`self_reap.py`).
- **DISTRACTION** Containerizing the proxy (tm never does; compose is Postgres only) and building rehydrating shared-proxy supervision for a single-host product.

## Minimum coherent product

Every `lilo run claude` session is transparently routed through a session-scoped loopback reverse proxy injected at `HostRuntimeBackend::prepare_launch` via `ANTHROPIC_BASE_URL`, with raw request and response bytes teed (streaming preserved), reassembled into per-turn records, and persisted with the harness's own transcript file under `~/.lilo/data/transport/<session_id>/`, keyed by the launcher-minted `SessionId`, readable via `lilo transport list|show|paths` from disk, mutating nothing, failing open on comprehension and closed on liveness, with `RuntimeCapability::WireCapture` gating the contract. Everything else in the taxonomy is qualification, deferral, or refusal.

Rationale: this is the smallest slice where capture is a side effect of every run (the stated launch-chain goal), every captured byte is reachable by an operator command, and no dark store exists. It reuses five existing littleorgans seams (prepare_launch, shim, LaunchSpec handoff, EventLog pattern, transcript_path column) and takes only mechanisms tm has proven, while depending on none of tm's code.

## Exclusions

Scope honesty for this study:

- No `NOTES/` directory was read or cited in either repo, per directive.
- Static evidence only at the two pinned SHAs; nothing was executed, no runtime behavior verified, no git history mined beyond HEAD.
- No repo edits were made anywhere.
- Rust implementation selection (hyper/tower vs alternatives for the proxy) is a build decision, not evidence-derivable from these repos, and is out of scope.
- v2 multi-host topology, the TS/Electron human UI train, and schedule-matters reuse of the wrapper are out of scope per the monorepo's locked v1 boundaries.
- tm's Node gateway, desktop packaging (WHEEL), design system (DESIGN.md), and canvas/PTY capture were surveyed for boundary claims only, not decomposed.
- Enterprise tier items are qualification claims derived from tm's own framing (NORTHSTAR seat/team/org scoping, signed releases, identity attribution); no external market evidence was gathered.

## Evidence

### Thread 1: littleorgans @ 98d8928 (COMPLETE)

Launch chain (all facts, high confidence):
- `lilo run` is a thin RPC client; no exec. `crates/lilo/src/cli.rs:85` → `internal/session/app/src/cli/run.rs:15,64` (`SessionRpc::Spawn`).
- Caller env/cwd captured client-side: `crates/lilo-rm-core/src/spawn_context.rs:37` `capture_caller_env`, denylist at `:10` (`CLAUDECODE, TMUX, TMUX_PANE, LILO_SOCKET_PATH`) + prefix denylist `:15` (`CLAUDE_CODE_, CLAUDE_PLUGIN_, LILO_AGENT_`). `ANTHROPIC_API_KEY` explicitly kept (test `spawn_context.rs:151`).
- SessionId minted in session daemon: `internal/session/daemon/src/handler/spawn.rs:29` `SessionId::new()`; env stamped at `spawn.rs:369-392` (`LILO_AGENT_SESSION_ID/ROLE/WORKSPACE`), all inherited `LILO_AGENT_*` stripped first (`:381`).
- argv born in exactly one place: `internal/runtime/daemon/src/api.rs:81` `lilo_runtime_launchers::dispatch(...).launch_spec(...)`. `SpawnRequest` carries no argv.
- A wrapper is ALREADY interposed: the shim. `internal/runtime/daemon/src/backend.rs:96` `spawn_via_shim` → `shim_socket.rs:25` `launch_shim`; shim argv `[lilo, "__shim", "--session-id", <uuid>]` (`shim_socket.rs:130`); hidden verb `crates/lilo/src/cli.rs:325`.
- Real exec inside shim: `internal/runtime/app/src/cli/shim.rs:35` `run_for_session_blocking` → `:46` `runtime_command(&launch)?.spawn()`; `runtime_command` `:119`; `apply_launch_env_cwd` `:152` (`env_clear()` then LaunchSpec env).
- Two-phase env: only `LILO_SOCKET_PATH` rides tmux bootstrap (`shim_socket.rs:148` `shim_env`, guard tests `shim_socket.rs:264`, `tmux.rs:339`); everything else arrives over UDS via `ShimLaunch`.

Existing transport code: NONE (fact, high confidence):
- Zero wire/proxy/capture code; no `tm` binary, no `transport` crate in workspace `Cargo.toml`. "transport" hits are MCP stdio/JSON-line helpers only. "fidelity" appears in no `.rs` file.
- `lilo capture` = tmux pane snapshot only: `crates/lilo-rm-core/src/capture.rs` (`CaptureRequest`, `PaneSnapshot`, `strip_ansi_escapes:90`), `internal/runtime/daemon/src/tmux.rs:79` `capture_pane`, capability `TmuxPaneSnapshot` (`version.rs:19`).
- Only "turn" concept is a screen-scrape placeholder that names transport as its replacement: `internal/runtime/daemon/src/tmux_busy.rs:5-7` ("…future transport or shim turn signal can replace the scrape in one place").

Storage substrate (facts, high confidence):
- Postgres unified schema, one migration: `internal/db/migrations/0001_unified_schema.sql` (tables: identity_audit, session_sessions, session_namespaces, messages, message_deliveries, session_labels, session_event_cursor, session_spawn_intents, runtime_lifecycle, runtime_metadata; every long-lived table has `owner TEXT DEFAULT 'local'` for a future RLS tier).
- `session_sessions.transcript_path TEXT` (`0001_unified_schema.sql:42`) exists, populated only for headless (`internal/session/core/src/paths.rs:8`); None for tmux — natural pointer for capture artifacts (inference).
- Append-only JSONL event log + durable cursor pattern: `internal/runtime/daemon/src/event_log.rs` (`EventLogRecord{seq,ts_ms,kind,payload}`, kinds Running/Terminated/Lost only), path `crates/lilo-paths/src/runtime.rs:43` → `data/events/runtime.jsonl`.
- `~/.lilo` layout via `crates/lilo-paths/src/lilo.rs:16-109`: config/, run/, data/, logs/ (`logs/runtimes/<session_id>/{stdout,stderr}.log` via `server/config.rs:64-73`), cache/, tmp/. Convention-consistent capture homes: `data/transport/<session_id>/` or per-session turns JSONL (inference).

Session identity (facts, high confidence):
- `SessionId` newtype, UUIDv4, serde/sqlx transparent: `crates/lilo-common/src/id.rs:22-93`; `short()` with 7-char floor (`:63`).
- Doc drift: `docs/reference/env-vars.md:81` says "UUIDv7" — stale; code is v4.
- Env registry `crates/lilo-paths/src/env.rs`: agent namespace is exactly `LILO_AGENT_{SESSION_ID,RUNTIME,ROLE,WORKSPACE}` (`:33-41`); no transport var registered.
- `LILO_AGENT_SESSION_ID` writers: `handler/spawn.rs:384` and `internal/runtime/launchers/src/lib.rs:101`; readers: `internal/session/app/src/mcp/server.rs:19`, `cli/mail.rs:319`; conformance test `internal/runtime/launchers/tests/conformance.rs:42-51`.

CLI + protocol (facts, high confidence):
- No `lilo transport` stub anywhere: `crates/lilo/src/cli.rs:234-327`, mirror source `tools/schemas/cli.toml`. Operator namespaces exactly `runtime` and `session` (guard tests `cli.rs:409,427`).
- Protocol gate: `crates/lilo-rm-core/src/version.rs:8` `RUNTIME_PROTOCOL_VERSION = "0.8"`, additive `#[non_exhaustive] enum RuntimeCapability` (`:51`) + `RUNTIME_PROTOCOL_CAPABILITIES` (`:10`, 13 entries).
- Generated-surface guards force TOML-first authoring for any new verb (`tools/schemas/cli.toml`, `internal/session/app/tools/*.toml`, guard tests in `crates/lilo/tests/` and `internal/session/app/tests/`).

Runtime adapters (facts, high confidence):
- Exactly two runtimes, `claude` and `codex`, one `BinaryLauncher` shape: `internal/runtime/launchers/src/{claude,codex}.rs:9-10`; `RuntimeKind::{Claude,Codex,Other}` (`crates/lilo-rm-core/src/types/runtime.rs:10`), `Other` has no launcher.
- argv is bare `[which <binary>]`, single element: `internal/runtime/launchers/src/lib.rs:90,117`.
- Tripwire: `internal/runtime/launchers/tests/conformance.rs:31-36` asserts `argv.len() == 1` — any launcher-layer wrapper prepend breaks it.
- Proven argv-rewriting hook already exists: `RuntimeBackend::prepare_launch` (`internal/runtime/daemon/src/backend.rs:14`); `DockerRuntimeBackend::prepare_launch` (`:76`) prepends `docker run …` (`docker_argv.rs:16,26-43`); `HostRuntimeBackend::prepare_launch` (`:61`) is a pass-through — highest-leverage seam.
- Zero-code env interposition exists today: agent-config `[env]` table (`internal/session/daemon/src/agent_config.rs:138` `agent_env`, unrestricted keys, merged at `handler/spawn.rs:378`) — a per-agent `ANTHROPIC_BASE_URL` redirect is reachable without Rust changes (inference: proof-of-concept path).

Attachment points ranked (zero tm dependency):
1. `HostRuntimeBackend::prepare_launch` (`backend.rs:61`) — rewrite argv/env exactly as Docker backend does.
2. Shim `runtime_command` (`shim.rs:119`) — in-process capture proxy; shim already survives child, forwards SIGTERM, reports exit.
3. `LaunchSpec` additive `capture: Option<CaptureSpec>` field (`crates/lilo-rm-core/src/launcher.rs:31`) over the existing `ShimLaunch` UDS handoff (`handler.rs:180-183`).
4. `shim_env` widening point if pre-handoff visibility needed (`shim_socket.rs:148`, declared + guard-tested).
5. Register `LILO_AGENT_TRANSPORT_*` consts in `lilo_paths::env` — strip/reinject hygiene applies automatically.
6. Add `RuntimeCapability::WireCapture` for protocol negotiation (`version.rs:51`).
7. `LiloPaths::capture_dir(session_id)` alongside `runtime_log_dir`; copy `EventLog` JSONL+cursor pattern for turns.
8. Populate `session_sessions.transcript_path` with capture artifact path — no migration needed.
9. Replace `tmux_busy.rs` scrape with a real wire turn signal (code names this intent).
10. `--agent-config [env]` for zero-Rust proof of concept.

### Thread 2: transport-matters wire layer @ ed099336, revalidated at a252df24 (COMPLETE)

Proxy mechanics (facts, high confidence unless noted):
- Interceptor is mitmproxy (`mitmdump` + Python addon `api/src/transport_matters/addon.py:60` `TransportMattersAddon`; argv builder `cli/launch_runtime.py:383`).
- Claude/Anthropic: reverse proxy via `ANTHROPIC_BASE_URL=http://127.0.0.1:{port}` (`captured/claude.py:181-207`); upstream default `https://api.anthropic.com` (`captured/models.py:54`). Route also persisted into the run-local Claude home `settings.json` env (`cli/claude_home.py:88`) so re-spawned subprocesses stay routed.
- Codex/OpenAI: explicit HTTPS forward proxy, true TLS MITM with process-scoped CA bundle (`cli/codex_cmd.py:167-184`; `launch/environment.py:235-250` sets HTTP(S)_PROXY/WS(S)_PROXY + `CODEX_CA_CERTIFICATE`). Trust is child-scoped, no sudo/keychain (`cli/trust.py:82,110`).
- Anti-bypass env scrub: 34 proxy keys + 9 trust keys popped before injection (`launch/environment.py:30-88,226`); nested tool shells deliberately de-proxied (`:118`). Env-level only; a hardcoded URL is not blocked (inference).
- Second topology: multi-tenant shared proxy, one `DumpMaster` with runtime-mutable per-run listeners, demux by listen port with sockname cross-check (`shared_proxy/subprocess.py:38,180`; `shared_proxy/addon.py:336`).

Launch contract (facts):
- `transport-matters claude|codex` is a two-child supervisor: spawn mitmdump, wait for port, spawn harness on PTY (`cli/runner.py:338,384`). No `tm` alias exists in-repo.
- Zero `LILO_*` anywhere; env contract is `TRANSPORT_MATTERS_*` (`env_keys.py:15`). Distinct env sets for proxy child vs agent child (`launch/environment.py:130,216`); harness credential keys inherited by managed launches, stripped from probes (`:105`).
- Session id minted by launcher and injected, not discovered (`env_keys.py:53-59`; Codex `codex resume <native>` `cli/codex_cmd.py:121-124`).
- `LAUNCH-CONTRACT.md:23-30`: six-stage digest-pinned pipeline `LaunchRequest → LaunchIntent → ResolutionContext → FrozenLaunchSpec → LaunchActuation → LaunchReceipt`; `PromptReceipt` proves submission from correlated provider exchange evidence (`:348`), i.e. wire evidence is proof of delivery.
- Second entry point: loopback capture RPC for desktop (`packages/runtime/src/adapters/CaptureRpcClient.ts:68-83`; `capture_rpc.py:130,435`).

Compatibility (facts):
- Exactly two adapters: `[CodexAdapter(), AnthropicAdapter()]`, first-match-wins (`adapters/__init__.py:14-17`). Grok is documented, not coded.
- Compat is a signed versioned data artifact with wire-specific facet revisions (`HARNESS-COMPATIBILITY.md:83-138,198,211`); certification = seven observability facets over a real owned capture incl. zero wire and transcript drift (`COMPATIBILITY-PUBLISHING.md:33-46`); data-only publication, no rebuild for new models (`:17-19,52-62`).
- Enforcement currently ADVISORY; never blocks a launch (`docs/ARCHITECTURE.md:224-244`).
- Drift: one engine, two consumers (CI gate + runtime observer), post-persist, never blocks capture (`drift_capture.py:1-11`; unknown-shape hooks `adapters/anthropic.py:91,100`).

Streaming (facts):
- SSE tee, not buffer: `flow.response.stream = capture_chunk` returns chunks unchanged while accumulating (`response_stream.py:17-47`). Selected by content type; excluded for WS upgrades (`addon_handlers.py:159`).
- Full-turn SSE reassembly state machine into IR (`adapters/anthropic.py:291`: message_start/content_block_delta/thinking/input_json_delta/message_delta → `InternalResponse` + `UsageStats`).
- Incremental live SSE reframer with bounded tail + streaming gzip/brotli/zstd decompression (`sse.py:49,12`; `live_status_observer.py:53`).
- Tag sanitization at bytes→dict boundary (`sse.py:20-35`; `json_tags.sanitize_tag_fields`).
- Codex WS-first with HTTP/SSE fallback; turn segmentation on client frames + terminal detection (`addon_handlers.py:279`; `codex/transport.py:68`); synthetic 426 injector to force fallback for corpus collection (`force_http_fallback_addon.py:37`).

Breakpoints / mutation (facts):
- Arm-once two-state machine (`off`|`armed_once`, `breakpoint.py:52`); pauses serialized to one flow (`:58`); 300s auto-release (`config.py:113`; `pause_session.py:270`).
- Release rewrites actual outbound bytes: HTTP `flow.request.set_text` (`pause_session.py:353`), WS `message.content` (`:407`); drop = synthetic 400 or `message.drop()`. Unchanged IR forwards original bytes untouched (`request_diff.py:25`).
- Non-pausing override/curation pipeline, scoped per (run_id, track_id), audited, never raises (`request_pipeline.py:65,86`; targets `overrides/targets.py`). Model-filtered breakpoint skip (`addon_handlers.py:116`). REST surface arm/disarm/release/release-unmodified/re-audit/drop (`api/v1/breakpoint_routes.py`); fire-and-forget token-cost preview (`pause_session.py:134`).

Reliability (facts; key asymmetry):
- Liveness FAILS CLOSED: loopback base URL/proxy var, no upstream-direct fallback (mechanism fact; absence of bypass is inference). Unmapped shared-proxy flows refused: HTTP 502, WS 1011 + kill (`shared_proxy/addon.py:293,300`).
- Capture loss kills the run: 3s health poll, threshold 3, then SIGTERM→SIGKILL of agent, state FAILED (`packages/runtime/src/service/CaptureHealthMonitor.ts:27`; `RunManager.ts:548,583-588`).
- Comprehension FAILS OPEN: no adapter match or unparsable IR passes traffic through and records an unparsed exchange (`addon_handlers.py:184-193`); override exception forwards unmodified (`request_pipeline.py:86`).
- Proxy self-reaps on parent death (Linux `PR_SET_PDEATHSIG`, macOS getppid watchdog; drain then `os._exit` after 20s) (`self_reap.py`). If harness exits first proxy stays up; if proxy dies first client is torn down (`cli/runner.py:408-435`).
- Bind failure forensics: EADDRINUSE log scan distinguishes stolen port from broken config; 3 retries; fail-fast on user-pinned ports (`cli/bind_failure.py:38,67,99`).
- Shared-proxy monitor auto-restarts and rehydrates listeners + overrides (`shared_proxy/manager.py:195,236`). Credential-expiry classification + refresh at response boundary, claude only (`credential_refresh.py:41`).

Operations (facts):
- Ports kernel-allocated per run, accepted TOCTOU window (`loopback.py:16`); pinned defaults 8787/8788 (`config.py:70`).
- docker-compose provides ONLY Postgres; proxy never containerized (`docker-compose.yml`).
- CLI ops: claude|codex|desktop|tail|doctor|paths|list|version; channel list|stop|ensure-db; PID record verified by identity not existence before reap (`shared_proxy/process.py:144,162,242`).
- Config: channel-home `settings.toml` overridden by `TRANSPORT_MATTERS_*` env (`config.py:48,146`). Loopback hardening: trusted-host check vs DNS rebinding (`config.py:131-144`); shared-proxy control channel is a unix socket (`shared_proxy/manager.py:267`).
- Token counter bypasses the proxy deliberately (`trust_env=False`, direct `api.anthropic.com` egress using the agent's captured auth headers) (`addon_runtime.py:352-357`; `counting.py:66`).
- Gateway (Node) supervised by Python with ordering-sensitive shutdown (gateway stops before the listening socket closes) (`gateway_supervisor.py:1-24,73`).

Compressed wire capability inventory: 35 items, spanning reverse-proxy interposition, scoped-CA forward MITM, route persistence into harness home, anti-bypass scrub, nested-shell de-proxying, multi-tenant demux, live listener control, SSE tee, turn reassembly, incremental reframing + decompression, WS segmentation + fallback, audited override pipeline, arm-once breakpoint, in-flight rewrite, no-op byte preservation, token preview, model-filtered skip, provisional exchange rotation, tier-1 raw durability, two-stream doctrine, post-capture drift, tag sanitization, header redaction, credential refresh, wire-derived activity classification, wire-evidence delivery proof, fail-closed liveness, fail-closed routing, fail-open comprehension, self-reaping, bind forensics, rehydrating supervision, launcher-minted identity, signed advisory compat releases.

### Thread 3: transport-matters capture data @ ed099336, revalidated at a252df24 (COMPLETE; one later-only item labeled in Baseline revalidation)

Data model (facts, high confidence unless noted):
- Two distinct captured units, never collapsed: transcript event (`api/src/transport_matters/session/models.py:184` `EventRow`) vs wire exchange (`session/wire_store.py:60` `WireExchangeWrite`, `wire_contracts.py:21`). Doctrine: "Their difference is the product" (`PROJECT.md:57-69`, `TLDR.md:31-35`).
- `SessionRow` is the correlation anchor: session_id, provider, harness, run_id, workspace slug+hash, space/worktree/canvas ids, native_session_id, minted flag, source_descriptor, purpose, visibility, lineage (`parent_session_id`, `forked_at_seq`) (`models.py:93-127`; DDL `api/migrations/versions/0001_session_store_foundation.py:21-56`).
- Turn = `EventRow` keyed `(session_id, seq)`: kind {turn,meta}, native_turn_id, subagent lineage, role, is_sidechain, model, `raw` (verbatim provider JSON), `ir` (normalized), `source_path`/`source_line` provenance, search_text, artifacts (`models.py:184-207`).
- Provider-neutral frozen IR with full block taxonomy: text, tool_use, tool_result, thinking, image, unknown; request carries system[], tools[], messages[], sampling, metadata, provider_extras (`api/src/transport_matters/ir.py:17-173`).

Transcript vs wire, fidelity (facts):
- Transcript captured by tailing the harness's own native session file, byte-faithful tee into run dir (`storage/transcript_snapshot.py:41,52`; tailer `index/tailer.py`; binding `owned_transcript_binding.py:35,57,77`). Gap = hard failure (`TranscriptSnapshotGapError:37`); cursor cannot advance past un-snapshotted bytes.
- Wire captured by a mitmproxy addon; raw bytes persisted to tier-1 BEFORE derived work (`addon.py`, `exchange_recorder/artifacts.py:213`, `storage/exchange_sink.py`; `PROJECT.md:204-207`).
- NO symbol named "fidelity diff". Concept split into: `request_diff.py:15,25` (pipeline-mutation diff, original vs curated IR), `drift_capture.py:174` `WireDriftObserver` + `harnesses/blocks.py:46` `DriftKind` (harness-contract drift evidence), and the wire-vs-transcript diff itself which is UNIMPLEMENTED: wire store "ships dark… nothing reads them back" (`TLDR.md:47-52`, migration `0008_wire_store`).
- Drift detail codes: unknown_request_field, unknown_response_event, transcript_locator_mismatch, transcript_record_shape_mismatch, session_bootstrap_rejected, session_resume_rejected, actuation_rejected, startup_prompt_rejected (`harnesses/blocks.py:52-76`); attribution can create_block or pause_release (`:65,237,253`).

Artifacts (facts):
- Per-exchange tier-1 file set: entry.json, request.raw, request.ir.json, request.curated.raw, request.curated.ir.json, request.audit.json, response.raw, response.ir.json, transport.json, events.jsonl, turn.json (`storage/disk_layout.py:13-24,32,93`).
- System prompts + tool defs are content-addressed first-class blobs: kinds system_part/tool_def/message, ordered sets with `system_set_hash`/`tools_set_hash` (`session/wire_contracts.py:27-34`; migration `0008_wire_store.py:40-101`).
- Tool calls exploded into indexed rows with partial index on block_type='tool_use' (`0008_wire_store.py:124-141`).
- Token accounting is two-source and never estimated: provider usage + authoritative `count_tokens` pre/post pipeline (`counting.py:86,235`; `storage/base.py:49-72`; failure → None → em dash).
- Images: blake2b-256 content-addressed, deduped binary rows (`session/artifacts.py:12-44`; DDL `0001:91-108`).
- Transport-layer artifacts (ws upgrade, frames, close codes, headers) with sensitive-header redaction at storage boundary (`storage/base.py:188-271`; `transport_redaction.py:9-27`).
- Override audit (`request.audit.json`, `PipelineStats.overrides_applied` with chars before/after); quarantine dead-letter rows with byte ranges + error class (`models.py:217` `DeadLetterWrite`; migration 0003).

Storage (facts):
- Two tiers: tier-1 per-run disk dir (authoritative, raw bytes), tier-2 Postgres session store (correlated, NO raw bytes; `exchange_id` is the only pointer back to disk — `wire_store.py:9`; `PROJECT.md:70-102`).
- Tier-1 layout: `<channel home>/workspaces/{slug}/{hash}/{run}/` with per-exchange dirs `{ts}-{exchange_id[:8]}`, `index.jsonl`, `sessions.json` (durable launch facts), `compatibility.json`, `transcripts/{session_id}.jsonl` (`disk_layout.py:53-114`; `storage_roots.py:16-64`). Crash-safe staged dirs `.tmp/.bak/.del` (`disk_layout.py:129-165`, `atomic_io.py`).
- Channel-scoped homes (stable/preview/dev) with separate DBs/ports; `$TRANSPORT_MATTERS_HOME` override.
- Postgres via Alembic, 32 migrations at this SHA; no SQLite in capture path.
- Content-addressed dedup: sha256 over canonical JSON of normalized components; stamp-stripping (cache-control, wire-index) required for dedup to work at all (`wire_normalization.py:1-57`).
- NO automatic retention/TTL/size caps on tier-1; only manual `db wire-gc` reference-driven sweep (`cli/db_cmd.py:68-88`, `wire_store.py:111,208`). (Absence inferred from exhaustive grep.)
- Run manifest is a liveness beacon, unlinked on exit; durable enumeration globs `*/*/*/index.jsonl` (`PROJECT.md:82-84`; `captured/models.py:165-169`).

Read surfaces (facts):
- FastAPI (`main.py:493-545`): `/api` legacy, `/v1` public, `/mcp` agent skin.
- `/v1/sessions…`: list/get with owner/workspace/space/worktree/purpose/visibility filters + cursors, events by seq range, timeline projection, resource content with ranges, SSE streams (`api/v1/session_routes.py:108-296`).
- `/v1/runs/{run_id}/exchanges…`: tier-1 disk-backed list/detail/turn-content/pipeline_tokens (`api/v1/exchanges.py:46-268`).
- Timeline = presentation-neutral projection: discriminated items (message|state|subagent|context|diagnostic), resources map, subagents map, layout hints, per-item `SourceRef` with source_path:source_line provenance (`session/timeline_models.py:44-299`).
- Wire evidence reachable from timeline only as redirect to tier-1 exchange detail; no HTTP browse over `wire_*` Postgres tables. Only production wire reads = delivery proof (`controlplane_statements.py:86`; `controlplane/delivery_proof.py`).
- Agent surface: MCP FastMCP bearer-authed at `/mcp`, tools agents/workspace_summary/whoami/harnesses/roster/conversation/prompt/wait_for_reply/launch/close/interrupt/watch/unwatch, 1:1 REST twins (`api/v1/controlplane_mcp.py:364-470`, `controlplane_routes.py`).
- `conversation` reader is token-bounded by design: default 10 msgs max 50, 2000 chars/msg max 8000, 12000 chars/page, opaque cursors (`controlplane/observe_models.py:16,28`; `packages/activity/src/projections/conversation.ts:3-7,127`; `CONTROLPLANE.md:22-25`).
- Curated conversation filters injected harness framing (isMeta/isSidechain/compact summaries, Codex AGENTS.md/environment_context prefixes) (`session/conversation_projection.py:9-105`); presentation-only denylist read fresh per request, never strips the wire (`transcript_denylist.py:1-14`).

Identity/correlation (facts):
- `session_id` universal key. Claude: TM mints uuid, runs `claude --session-id <uuid>` (minted=True). Codex: mints native rollout uuid, pre-seeds, `codex resume <uuid>`; stored id uuid5 over native (minted=False) (`PROJECT.md:103-118`; `owned_transcript_binding.py:32,90-97`).
- Run identity separate and frozen at launch: run_id, leased friendly name, agent_id/revision (`RUN-IDENTITY.md:5-21,216-238`; `run/identity.py:21,52`); four projections incl. env `TRANSPORT_MATTERS_RUN_IDENTITY` and injected markdown (Claude `--append-system-prompt`, Codex AGENTS.md).
- ZERO `LILO_*` references in repo; env contract entirely `TRANSPORT_MATTERS_*` (`env_keys.py:15`). Correlation vars: `TRANSPORT_MATTERS_OWNED_NATIVE_SESSION_ID`, `TRANSPORT_MATTERS_OWNED_SOURCE_DESCRIPTOR` (`env_keys.py:53-59`).
- Extra keys: run_id on every event/exchange; track_id/parent_track_id/track_role + `SpawnAnchor` for subagent trees (`storage/base.py:107-135`); delivery_id binds control-plane prompt to wire exchange (migration 0017); workspace identity by canonical path (`workspace.py`).

Product boundary claims (facts, doc claims):
- NORTHSTAR: TM owns capture (wire+transcript), control plane, agent homes, artifact store + entitlements, eval/label substrate, metrics; does NOT own agent cognition, vendor CLIs, model quality. "TM measures; models compete" (`NORTHSTAR.md:167-174`). "Orchestration is the product, with a launcher attached" (`:10-22`). "Content never flows down the tree; authority does" (`:40-44`).
- TLDR: orthogonal to Little Organs stack — "sees the bytes regardless of who spawned the agent" (`TLDR.md:23-25`).
- README: "context control plane" — proxies, captures, shows, and can pause+edit next outbound request. "No system proxy toggle. No global certificate install. No sudo" (`README.md:3-11`).
- CONTROLPLANE: twin skins one service (REST + MCP), no logic in skins (`CONTROLPLANE.md:15-19`); identity never self-declared, tokens minted at spawn, digests only persisted (`:20-29,59-70`); Node gateway is a dumb executor, no policy in TypeScript (`:36-49`).
- PROJECT: tier-1 authoritative, raw-first persistence; transcript-capture failure never stops the proxy; public APIs never expose raw bytes (`PROJECT.md:204-215`).
- Inference (med confidence): TM has already crossed into control plane in code (breakpoints, overrides, prompt delivery, launch/close/interrupt shipped) while its flagship observation capability (wire-vs-transcript diff) remains unbuilt for lack of a read surface.

Compressed capability inventory: 12 CAPTURE (reverse-proxy wire capture no-sudo; Codex explicit-proxy websocket w/ process-scoped CA; byte-faithful transcript tee; launcher-owned session minting; in-flight breakpoint hold/edit/release; override pipeline w/ audit; post-persist drift detection incl. unparsed; dead-letter quarantine; degradation contract; live status stream; run lifecycle; PTY capture) · 16 DATA (two-stream model; frozen IR w/ UnknownBlock; content-addressed dedup wire store; system/tool ordered-set hashes; tool-call rows; image blob store; two-source tokens; transport-layer artifacts; Codex turn derivation; typed drift evidence; subagent track tree; session lineage/purpose/visibility; two-tier raw-bytes-on-disk invariant; canonical-path workspace identity; durable launch facts; idempotent replay) · 16 READ (session list/get; event range + SSE; timeline projection + SSE; resource resolver; tier-1 exchange API; MCP twin; token-bounded conversation; framing filter; whoami; roster; watch/unwatch damped push; delivery proof; denylist; wire-gc/db CLI; GAP: no browse read over wire_* tables).
