---
title: littleorgans transport capture boundary map
type: brainstorm
tags: [littleorgans, transport-matters, capture, bounded-context, boundary-map]
summary: Bounded-context seams and reusable mechanisms across littleorgans and experimental transport-matters, under the rule that littleorgans owns mandatory capture with zero tm dependency.
status: complete
source: codebase-analyst
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

## Baseline

- littleorgans HEAD: `98d8928941b5b5db670ed73ed06af57f61dcfa0a` (branch `main`, `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`). 25 workspace members (10 `crates/`, 13 `internal/`, plus `tests/integration`, `tools/xtask`), 3 binaries (`lilo`, `rtm`, `sm`), 388 Rust files, ~58.4k Rust LOC, 1 SQL migration (10 tables).
- transport-matters study SHA: `a252df24a7e3` (`fix(auth): close credential review residuals`), analyzed in a detached worktree; the live checkout `main` is 3 commits ahead at `ed099336`. Python API: ~74k non-test LOC across 374 files plus 344 colocated test files (~155k total), 32 Alembic migrations, 13 TS packages. Dependencies include `mitmproxy>=12.2,<13`, FastAPI, psycopg, alembic (`api/pyproject.toml:37-48`).
- Governing rule (Stuart, 2026-07-31, cm feedback `019fb644-2782-7531-8aee-b81000431d09` and `019fb646-8a11-7da1-8151-c9a3de5bb6ca`): transport capture is a first class littleorgans bounded context; littleorgans cannot ship without capture; littleorgans must not invoke, package, or version against `tm`. transport-matters is experimental research. Only validated capture, durability, fidelity, recovery, and testing lessons carry over, reimplemented under littleorgans ownership.
- `transport-matters/NOTES/` was not read or cited, per `transport-matters/LESSONS.md:23`.

## Worker Status

- Worker A (Explore, littleorgans seam map; scope: workspace topology, launch chain, env registry, existing capture code, data plane, socket protocol, identity seam): COMPLETE. Load-bearing claims re-verified at source (launcher `runtime_env`, `RUNTIME_PROTOCOL_VERSION`, `spawn_launch` env block, 10-line launcher files).
- Worker B (Explore, transport-matters capture mechanism inventory at `a252df24`; scope: proxy interposition, launch seam, transcript capture, wire store, pause/edit, correlation, redaction, scale): COMPLETE. Load-bearing claims re-verified at source (`credential_refresh.py` SyntaxError via `py_compile`, zero `LILO_` hits, `wire_session_id`, `prepare_captured_run`, module-scope import at `addon.py:27`).

## Headline findings

1. littleorgans has ZERO wire-capture or tm code today. No `tm`, `transport-matters`, `ANTHROPIC_BASE_URL`, `HTTP(S)_PROXY`, or `mitm` hits anywhere in Rust or Cargo sources. Every `Command::new` exec site enumerated; none is a wrapper. `CLAUDE.md:54-75` describes the tm launch chain in the present tense with no code behind it.
2. transport-matters has ZERO runtime coupling to littleorgans. No `LILO_*`, `lilod`, `RTM_SOCKET`, `rtm`, or `smd` identifiers in source; `TLDR.md:22-25` states the orthogonality explicitly. The claimed correlation contract ("tm reads `LILO_AGENT_SESSION_ID`") was never implemented on either side.
3. The corrected rule therefore requires no unwinding of code on either side. It requires only doc corrections in littleorgans and a greenfield capture context built at an already-identified 20-line seam.
4. The highest-value boundary is the runtime launcher `LaunchSpec` seam: `internal/runtime/launchers/` (230 LOC total; `claude.rs` and `codex.rs` are 10 lines each) is the single chokepoint where argv and env for every agent process are assembled, downstream of identity authorization and upstream of host, docker, and tmux carriers that faithfully transport `LaunchSpec` unchanged. Mandatory capture interposes here, because the session-side env seam (`spawn_launch`) is bypassed by raw `lilo runtime spawn`.

## Reuse map (mechanisms to reimplement under littleorgans ownership)

Ordered by leverage. "tm evidence" paths are relative to the `a252df24` worktree; "landing" paths are littleorgans.

1. **Managed session-id mint.** The launcher mints the id the harness will use, so wire, transcript, and store agree without inference: `claude --session-id <uuid>`; Codex pre-seeds the rollout and runs `codex resume <uuid>` (PROJECT.md § Session correlation; `owned_transcript_binding.py:35-100`; `index/sessions.py:19 wire_session_id`). Landing: littleorgans already mints `SessionId` before any process exists (join-key contract), so the mint collapses into launcher argv assembly at `internal/runtime/launchers/src/lib.rs` (`resolved_argv`). This dissolves tm's uuid5 synthesis entirely: the control-plane `SessionId` is the PK.
2. **Proxy interposition topology, per harness.** Claude: loopback reverse proxy in front of `https://api.anthropic.com` (`captured/claude.py:183`, `captured/models.py:53 CLAUDE_UPSTREAM_DEFAULT`) with the client pointed at it via settings in the runtime home (`apply_claude_proxy_env_settings`, `captured/claude.py:196-200`); no CA, no sudo. Codex: explicit HTTPS proxy via forced child env (`launch/environment.py:216 build_managed_child_env` strips inherited proxy vars then sets `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/WS_PROXY/WSS_PROXY`, pins `NO_PROXY`, sets `CODEX_CA_CERTIFICATE`). Landing: env injection at `internal/runtime/launchers/src/lib.rs:97-108 runtime_env` (runtime-owned, covers `lilo runtime spawn` too); docker isolation carries env as `-e K=V` (`internal/runtime/daemon/src/docker_argv.rs append_env_args`) and CA/socket material as `MountSpec` (gated by the `SpawnRequestMounts` capability).
3. **Loopback port discipline.** Simultaneous port-0 binds to prevent double issue, then poll for proxy readiness (`loopback.py:16 allocate_loopback_ports`, `:39 wait_for_port_ready`). Trivial Rust port.
4. **Tier-1 run directory, raw bytes first.** Per-run tree with per-exchange `request.raw` / `request.ir.json` / `response.raw` / `response.ir.json` / audit, a durable `index.jsonl`, owned `transcripts/{session_id}.jsonl`, and `sessions.json` launch facts; liveness manifest unlinked on exit; durable enumeration globs `index.jsonl`, never the manifest (PROJECT.md § Tier 1; `storage/disk_layout.py:9-24`; `storage/session_facts.py:38 OwnedSessionFacts` with `extra="forbid"`). Landing: under `LiloPaths::data_root()` (`crates/lilo-paths/src/lilo.rs`), modeled on the existing JSONL precedent `internal/runtime/daemon/src/event_log.rs` (tail recovery, compaction, cursors, long-poll already solved there).
5. **Transcript tailer discipline.** Poll, never inotify; byte-offset cursors with stat signatures; tee the consumed byte prefix to the owned snapshot BEFORE normalization; a snapshot write failure blocks cursor advance so events never get ahead of the owned copy (`index/tailer.py:115 TranscriptTailer`, `:197 _poll_cursor`, `storage/transcript_snapshot.py:41`; PROJECT.md § Backfill). Landing: new Rust component; `Session.transcript_path` (`internal/session/core/src/session.rs:67-89`) is an existing slot for the pointer.
6. **Two-stream product invariant.** Wire and transcript are captured separately and never collapsed; their difference is the product (TLDR.md:31-35). Carry as a design invariant, not code.
7. **Port pair per CLI.** `LaunchProfile` (argv/env projection, owned session facts) plus `TranscriptAdapter` (bind run facts to a session id, locate sources, normalize records); adding a CLI is one profile plus one adapter (PROJECT.md § Launch and adapter ports). Landing: `RuntimeLauncher` (`crates/lilo-rm-core/src/launcher.rs:62-90`) already is the profile half; the adapter half is new.
8. **Freeze-then-actuate discipline.** Intent, resolution context, frozen spec, actuation, and observation as distinct durable records; secrets never in digests or sanitized facts; drift between freeze and spawn fails the launch (LAUNCH-CONTRACT.md § Invariants, § Actuation). Landing: `session_spawn_intents.spawn_request_json` already persists the full `SpawnRequest` verbatim, so any capture field added to `SpawnRequest` is durable and survives crash reconciliation for free. Adopt the digest and sanitized-facts discipline; do not adopt the full six-stage contract (see rejection map).
9. **Header redaction table.** `transport_redaction.py` (97 lines, dependency-free): sensitive name set, prefix and suffix rules, scheme-preserving value redaction. Liftable as data.
10. **Env hygiene at spawn.** Harness credential denylist (`launch/environment.py:105 HARNESS_CREDENTIAL_ENV_KEYS`) and proxy/trust var stripping merge naturally with the existing `CALLER_ENV_DENYLIST` / `LILO_AGENT_` prefix scrub (`crates/lilo-rm-core/src/spawn_context.rs:10-28`, `internal/session/daemon/src/handler/spawn.rs:374-393`).
11. **Fidelity work only after durability.** Drift detection runs only after bytes are durably in Tier-1, never on the proxy hot path, and can never block capture (`drift_capture.py:1-10`); response streaming is byte-preserving tee then restore (`response_stream.py:17,47`).
12. **Wire store schema reference.** Content-addressed blob dedup, component sets, advisory-lock commit watermark so replay cursors cannot interleave (`0008_wire_store.py`; `session/wire_store.py:119 write_wire_exchange`, `:150 pg_advisory_xact_lock`). Reference material for a littleorgans `0002_*.sql`, joined by `SessionId` against the existing 10 tables.
13. **Engineering lessons (LESSONS.md).** Enforce invariants at one boundary, not N call sites (:5); inventory every producer before placing a launch security invariant, freeze validated fields (:19); dispatch on the axis that varies, not a proxy for it — the credential-handling incident (:21); diagnostics read config without materializing it (:4); real-binary platform tests over fake runners (:16).

## Rejection map (tm surfaces littleorgans must NOT absorb)

1. **The `tm` binary, wheel, and any launch chain through it.** Withdrawn outright (cm `019fb646`). No exec, no packaging, no version gate.
2. **The Python/mitmproxy substrate.** littleorgans is Rust; `mitmproxy>=12.2` and the FastAPI-hosted addon runtime (`addon.py:60 TransportMattersAddon`, `web_runtime.py:35`) are implementation choices of the experiment, not the mechanism.
3. **tm's own control plane.** `controlplane/` (54 files), grants/actions/delivery migrations (`0012/0013/0016/0017/0019/0020`), `grant: none|observer|director`, roster/whoami verdicts. In littleorgans, Session owns the control plane and Identity owns authorization; transport observes only.
4. **The six-stage launch contract as a whole.** `LaunchRequest -> ... -> LaunchReceipt`, agent catalog, agent runtimes compiler, connection catalog, harness certification releases, enablement stores, 22-code failure table (LAUNCH-CONTRACT.md). littleorgans already has spawn intents plus `RUNTIME_PROTOCOL_VERSION` capability gating; adopt the freeze discipline (reuse item 8), reject the machinery.
5. **Channels.** stable/preview/dev homes, per-channel Postgres, ports, Electron identity (TLDR.md:15-17). littleorgans has one `~/.lilo` root and one release train.
6. **Desktop, canvas, www, Spaces/Worktree/Canvas ownership, RunManager PTY panes.** (`0032_space_worktree_ownership`, `/runs` + `WS /runs/{id}/terminal`.) Runtime-matters already owns process placement via tmux and the shim; the TS/Electron product plane is a separate train and an open product question, out of this study's scope.
7. **Run identity and the moons-v1 name allocator** (RUN-IDENTITY.md). `SessionId` plus session labels already cover identity; friendly-name machinery is product surface, not capture.
8. **`TRANSPORT_MATTERS_*` env namespace and `~/.transport-matters` home.** littleorgans owns exactly `LILO_`; every new name registers in `crates/lilo-paths/src/env.rs` and passes `scripts/check-env.sh --check`.
9. **uuid5 session-id synthesis** (`index/sessions.py:10 synth_session_id`). Only needed because tm lacks a platform-minted id; littleorgans has one.
10. **macOS keychain credential broker stack** (`credential_broker.py`, `claude_fleet_auth.py`, `credential_refresh.py`). Fleet-auth specific, macOS-gated, and the subject of tm's own lesson about proxy-axis dispatch (LESSONS.md:21). Also concretely broken at the study SHA (see contradictions, item 6).
11. **Breakpoint pause-and-edit** (`breakpoint.py`, `pause_session.py`). A product direction, not part of mandatory capture v1. Defer.
12. **A write-only wire store.** tm's rebuilt wire store "ships dark": `wire_store_observer` writes and nothing reads (TLDR.md:48-52). Do not replicate a store without a read surface; ship capture with its read verb or stage explicitly.

## Product invariants

1. littleorgans cannot ship without capture. The `lilo run` path, install, readiness, diagnostics, lifecycle, and release qualification include Transport by construction (cm `019fb644`).
2. Zero tm dependency in any form (cm `019fb646`).
3. Four bounded contexts with distinct ownership: Identity, Runtime, Session, Transport. Transport observes; it never authorizes, decides what to spawn, or reconciles.
4. `SessionId` (UUIDv4, minted by Session at spawn time, before any process exists) is the sole correlation key across capture artifacts, store rows, audit (`identity_audit.session_ref`, indexed), and lifecycle. Never a provider-minted conversation id.
5. Mandatory means launcher-level. The enforcement point must sit on a seam every agent process crosses, including raw `lilo runtime spawn`: the `LaunchSpec` assembly in `internal/runtime/launchers/`, not the session-only `spawn_launch` env merge.
6. Capture rides the existing spawn authorization: `authorize_in_tx` precedes intent persistence and process launch in one transaction (`internal/session/daemon/src/handler/spawn.rs:106-124`); capture adds no second authorization authority.
7. One env namespace (`LILO_`, const registry gated), one state root (`~/.lilo`), one Postgres (`LILO_DATABASE_URL`), one migrations dir (`internal/db/migrations/`).
8. Two streams, never collapsed; raw bytes durable before any derived work (adopted from tm, TLDR.md:31-35, PROJECT.md § Storage contracts).
9. Secrets never enter digests, durable sanitized facts, or capture artifacts; redaction is a storage-boundary invariant, not per-call-site hygiene.
10. Protocol evolution is explicit: a capture capability lands as `RuntimeCapability::*` plus version bump in `crates/lilo-rm-core/src/version.rs` (currently `"0.8"`, 13 capabilities), with its pinning tests and serde snapshots.

## Contradictions

1. `littleorgans/CLAUDE.md:54-75` ("launch chain inverts: `lilo run claude` execs `tm claude`", "Transport is now interposed in the launch path", "The CLI binary is `tm` and the crate/package is `transport`") contradicts the corrected rule and, independently, the code: no such interposition exists at HEAD. Doc rewrite required.
2. Parent `littleorgans/CLAUDE.md` sibling table ("Migrating into the littleorgans monorepo... only transport's Python API migrates") carries the withdrawn code-migration premise. Under the corrected rule, lessons migrate; code does not.
3. `littleorgans/CLAUDE.md:66-72` claims "`tm` reads `LILO_AGENT_SESSION_ID`". False at `a252df24`: zero `LILO_` hits in the entire tm tree; tm's carriers are `TRANSPORT_MATTERS_RUN_ID` / `OWNED_NATIVE_SESSION_ID` etc. (`env_keys.py`). The correlation contract existed only in prose, on one side.
4. tm `TLDR.md:22-25` ("does not coordinate with session-matters or runtime-matters at runtime") always contradicted the littleorgans launch-chain framing; the code agrees with the TLDR. The contradiction resolves in tm's favor and the corrected rule formalizes it.
5. Fail-open vs fail-closed is unresolved and tm is internally split: Postgres is a hard precondition at the capture RPC boundary (`capture_rpc.py:159-161` raises) but soft inside the addon (`addon_runtime.py:527-533` continues with transcript capture disabled), and PROJECT.md declares "session capture startup is best effort". A mandatory-capture littleorgans must decide degraded-mode semantics deliberately (Tier-1 file capture as the never-fails floor, store ingestion as recoverable backfill is the tm-validated shape).
6. tm's "validated" status has a hole at the study SHA: `credential_refresh.py:83` reads `except TypeError, ValueError:` — Python 2 syntax, verified as a `SyntaxError` via `py_compile`, imported at module scope by `addon.py:27`, so the mitmproxy addon cannot load at `a252df24`; none of the 3 later commits touch the file. Evidence for treating tm as research to learn from, not a substrate to certify against.
7. Verb collision: `lilo capture` is pinned to runtime's tmux pane snapshot (`CLAUDE.md:70`; `crates/lilo-rm-core/src/capture.rs`, `internal/runtime/daemon/src/tmux.rs:79 capture_pane`). The wire-capture read surface needs a distinct name (the reserved `lilo transport ...` operator namespace fits: `list`, `paths`, `show <session>`).

## Evidence appendix (path + symbol)

littleorgans (`98d8928`):
- Launch chain: `crates/lilo/src/cli.rs:85-87,326` (Run dispatch; hidden `__shim`); `internal/session/app/src/cli/run.rs:41-99 spawn_session`; `internal/session/app/src/compose.rs:115-253 run_core/handle_connection` (composed `lilod`, single socket `~/.lilo/run/lilod.sock`); `internal/wire/src/lib.rs:5-8 LilodRpc`; `internal/session/daemon/src/handler/spawn.rs:24-91 DaemonState::spawn`, `:106-124 begin_spawn_intent` (authorize+audit+intent in one tx), `:369-407 spawn_launch` (session-side env injection, verified); `internal/session/driver/src/port.rs:18-55 RuntimePort`; `internal/runtime/daemon/src/api.rs:74-113 spawn_domain`; `internal/runtime/launchers/src/lib.rs:57-69 dispatch`, `:90-95 resolved_argv`, `:97-108 runtime_env` (verified: upserts `LILO_AGENT_SESSION_ID`, `LILO_AGENT_RUNTIME`), `claude.rs`/`codex.rs` (10 lines each, verified); `internal/runtime/daemon/src/shim_socket.rs:25-108 launch_shim/launch_headless_shim`, `:148-156 shim_env` (shim child gets only `LILO_SOCKET_PATH`); `internal/runtime/app/src/cli/shim.rs:35-75 run_for_session_blocking`, `:119-125 runtime_command` (env cleared, only `launch.env` applied).
- Protocol: `crates/lilo-rm-core/src/version.rs:7 RUNTIME_PROTOCOL_VERSION="0.8"` (verified), `:10-24` 13 capabilities, pinning tests `:153-167`; `crates/lilo-rm-core/src/proto.rs:86-136 RuntimeRpc`.
- Data plane: `crates/lilo-paths/src/lilo.rs` (`~/.lilo` tree, `events_log_path`); `crates/lilo-paths/src/env.rs` (complete `LILO_` const registry, gated by `scripts/check-env.sh`); `internal/db/src/lib.rs:33-94 LiloDb`; `internal/db/migrations/0001_unified_schema.sql` (10 tables; `session_spawn_intents:115-128` stores `spawn_request_json`; `identity_audit:9-28` with indexed `session_ref`); `internal/session/core/src/session.rs:67-89 Session` (`transcript_path`, `runtime_session` slots); `internal/runtime/daemon/src/event_log.rs EventLog` (JSONL append/cursor/long-poll precedent).
- Existing capture verb (tmux, not wire): `crates/lilo-rm-core/src/capture.rs`; `internal/session/app/src/cli/capture.rs`; `internal/runtime/daemon/src/tmux.rs:79-133 TmuxGateway::capture_pane`.
- Identity seam: `internal/identity/service/src/client.rs:52-74 authorize_in_tx`; `internal/session/daemon/src/identity_client.rs:14-41 IdentityPort`; stub authorizer `crates/lilo-im-stub`.
- Negative results: zero hits for `tm`/`transport-matters`/`ANTHROPIC_BASE_URL`/`HTTPS_PROXY`/`mitm` in Rust/Cargo sources; all non-test `Command::new` sites enumerated (git, agent binary, docker, tmux, shim, doctor, `which`).

transport-matters (`a252df24`, worktree):
- Interposition: `addon.py:60 TransportMattersAddon`; `cli/launch_runtime.py:383 build_mitmdump_argv`; `captured/claude.py:183` (reverse mode), `:196-200 apply_claude_proxy_env_settings`; `cli/codex_cmd.py:169` (regular mode); `launch/environment.py:216 build_managed_child_env`; `loopback.py:16,39`; `self_reap.py:73 install_parent_death_reaping`.
- Launch/capture seam: `captured/run.py:185 prepare_captured_run` (verified), `:390 _secure_workspace_client`; `capture_rpc.py:130 CaptureLeaseRegistry`, `:159-161` (hard Postgres preflight); `workspace.py:61 workspace_id` (blake2b canonical-path hash); `storage/disk_layout.py:9-24` (run-dir file names); `storage/session_facts.py:38 OwnedSessionFacts`; `lock.py:82 WorkspaceLock`; `secure_workdir.py:10 secure_chdir`.
- Transcript: `owned_transcript_binding.py:35-103`; `index/tailer.py:115 TranscriptTailer`, `:197 _poll_cursor` (tee-before-normalize); `storage/transcript_snapshot.py:41`; `session/writer.py:106 SessionWriter`; `index/adapters/claude.py:82`, `index/adapters/codex.py:114`; `index/sessions.py:19 wire_session_id` (verified).
- Wire store: `ir.py` (frozen IR models incl. `UnknownBlock`); `request_pipeline.py:65 run_pipeline`; `request_diff.py:15 request_unchanged`; `response_stream.py:17 install_response_tee`; `wire_store_observer.py:68`; `session/wire_store.py:119 write_wire_exchange` (advisory-lock watermark `:150`); migrations `0001`, `0008`, `0014`, `0018`, `0028`, `0032`; `drift_capture.py:1-10,174`.
- Redaction/secrets: `transport_redaction.py:29,81`; `launch/environment.py:105 HARNESS_CREDENTIAL_ENV_KEYS`; `credential_refresh.py:83` SyntaxError (verified via `py_compile`; module-scope import verified at `addon.py:27`).
- Negative results: zero `LILO_*`/`lilod`/`RTM_SOCKET` hits; `littleorgans` appears only in repo URLs, a theme preset, a UTM string, and naming-convention comments (`desktop/src/env.ts:4`, `env_keys.py:8`).

## Open questions

1. Degraded-mode contract for mandatory capture: proxy up but store down, proxy fails to bind, backfill semantics. tm's validated shape is Tier-1-first with store ingestion as recoverable backfill; littleorgans must pick where fail-closed applies.
2. Rust proxy substrate for the two interposition modes. Claude's reverse-proxy mode needs no TLS interception at all; Codex's explicit-proxy mode requires CONNECT handling plus a per-run CA (tm ships `CODEX_CA_CERTIFICATE`). Crate choice (hyper-based custom vs an interception library) is unstudied here.
3. Wire-capture read-surface naming under the collision with tmux `lilo capture` (the reserved `lilo transport ...` namespace is the natural home).
4. Docker isolation plumbing: proxy reachability from the container netns, CA and socket material as `MountSpec`, path-shaped env preflight (`crates/lilo-rm-core/src/path_shaped_envs.rs`).
5. Whether capture artifacts land DB-first (`0002_*.sql`, joinable by `SessionId`) or file-first under `~/.lilo/data/` with store ingestion following the tm two-tier pattern. The existing `event_log.rs` and the tm evidence both argue file-first for the raw tier.
