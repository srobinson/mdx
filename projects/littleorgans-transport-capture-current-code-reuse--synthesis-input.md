---
title: littleorgans current-code reuse map for mandatory native Transport capture
type: research
tags: [littleorgans, transport, capture, reuse-audit, synthesis-input]
summary: Symbol-first audit of littleorgans at 98d8928 classifying current code for native Transport capture integration
status: complete
source: codebase-analyst
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

Worker Status: none (single-analyst read-only pass, no subworkers spawned)

Audit target: littleorgans monorepo, immutable at commit `98d8928941b5b5db670ed73ed06af57f61dcfa0a` (verified `git rev-parse HEAD`; working tree clean apart from an uncommitted `LESSONS.md` edit, not audited as code).

Method: fmm structural navigation (388 files, 58,401 LOC indexed) plus targeted symbol reads and greps. Every classification below cites a symbol and file path. Facts and recommendations are labeled; anything under "Recommendation" is analyst judgment, not current code.

## 1. Executive summary

littleorgans today has **zero runtime, package, or process dependency on `tm` or transport-matters** (Section 11). The launch pipeline is fully native and already funnels every spawn path through one typed contract, `LaunchSpec`, produced by `RuntimeLauncher` and executed by the shim. That contract is the natural interposition seam for native capture. Transport capture itself is entirely **MISSING**: no proxy, no capture store, no capture paths, no capture authz action, no CLI namespace, no doctor probe. The stale prose that prescribed a `tm` wrapper lives only in docs (Section 12) and must be superseded.

## 2. Launch preparation and agent spawn paths

Current fact: there are exactly two user-facing spawn entries and one diagnostic entry, and all of them converge on `LaunchSpec`.

- `run` / `create_session` (`internal/session/app/src/cli/run.rs`, `run` [15,27], `spawn_session` [41,99]) send `SessionRpc::Spawn` over the lilod socket. Session-backed path; creates `session_record` + spawn intent.
- Diagnostic runtime spawn: `Command::Spawn` in `internal/runtime/app/src/cli.rs` (binary `rtm`, `internal/runtime/app/Cargo.toml [[bin]]`). Identity-gated, no session record.
- Session daemon composition: `DaemonState` spawn impl in `internal/session/daemon/src/handler/spawn.rs` (`spawn_launch` [369,407], `merge_env`/`upsert_env` [424,436]) builds the `SpawnLaunch`, folding in per-agent config env from `agent_env` (`internal/session/daemon/src/agent_config.rs` [138,147], which injects `CLAUDE_CONFIG_DIR`).
- Launcher: `RuntimeLauncher` trait (`crates/lilo-rm-core/src/launcher.rs` [62,90]) produces `LaunchSpec { argv, env, cwd, shell_resume }`; `BinaryLauncher` implements it for claude and codex (`internal/runtime/launchers/src/lib.rs`, `dispatch` [57,65], `registered_launchers` [67,69]).
- Env injection: `runtime_env` (`internal/runtime/launchers/src/lib.rs` [97,108]) upserts `LILO_AGENT_SESSION_ID` and `LILO_AGENT_RUNTIME` into every launch. This is the existing SessionId-to-agent-process propagation.
- Handshake: `SpawnCoordinator` (`internal/runtime/daemon/src/server/spawn.rs` [15,256]) parks the `LaunchSpec` (`begin_spawn`, `take_launch_spec`) until the shim collects it and reports `ShimReady` (`crates/lilo-rm-core/src/types/lifecycle.rs` [32,39]).
- Exec point: the shim (`internal/runtime/app/src/cli/shim.rs`, `run_for_session_blocking` [35,75], `runtime_command` [119,125], `apply_launch_env_cwd` [152,158]) builds the child `Command` from `LaunchSpec` and **clears pre-existing env** so the agent sees exactly the spec env. Backends: `RuntimeBackends::prepare_launch/spawn` (`internal/runtime/daemon/src/backend.rs` [20,54]) route host, tmux (`build_respawn_pane_args`, `internal/runtime/daemon/src/tmux.rs` [291,312], forwards env via `-e`), headless, and docker (`spawn_via_shim` wraps launch for the host shim).

Classification:
- REUSE AS IS: `SpawnCoordinator` handshake, `ShimReady`, `runtime_env` correlation injection, backend routing.
- REFACTOR BEFORE USE: `RuntimeLauncher`/`LaunchSpec` production and the shim exec path are where a native capture proxy interposes (proxy env such as a provider base-URL override, or a sidecar started by the shim). The mechanism exists; a capture-aware preparation step does not.
- Note (refactor nit, current fact): `runtime_env` writes `"LILO_AGENT_SESSION_ID"` as string literals instead of the `lilo_paths::env` consts that define the same names (`crates/lilo-paths/src/env.rs` [35,37]).

Recommendation: treat `LaunchSpec` as the single capture-interposition contract. Every spawn path (tmux, headless, docker, shell-resume) already consumes it; capture wiring added anywhere else would be a second path.

## 3. lilod composition and wire API

Current fact: `lilo daemon` (`crates/lilo/src/cli/daemon.rs`, line 52) calls `lilo_session_app::compose::run_from_env`. The composition root is `run_core` (`internal/session/app/src/compose.rs` [115,204]), which builds `RuntimeService` + `SessionService` over one `LiloDb` and one unix socket. `handle_connection` ([206,254]) decodes `LilodRpc` (`internal/wire/src/lib.rs` [5,8], exactly two variants: `Session`, `Runtime`), extracts the peer principal via `peer_creds::extract`, and dispatches. Graceful shutdown is staged (`ShutdownStage` [20,28], includes `RuntimeShutdown`, `BeforeDbClose`).

Classification:
- REFACTOR BEFORE USE: `LilodRpc` needs a third variant and `run_core`/`handle_connection` need to compose and dispatch a transport service. Both are small, additive edits at one seam.
- REUSE AS IS: `peer_creds` principal extraction, staged shutdown, `ready_check_from_env` smoke primitive ([87,95]).
- MISSING: any transport service, and any capture-lifecycle hook in the shutdown stages.

## 4. SessionId propagation

Current fact: `SessionId` is a typed newtype from `define_id!` (`crates/lilo-common/src/id.rs`, 107 downstream dependents, the highest-blast-radius symbol after `lilo-rm-core`). It is minted at spawn time by session-matters, flows through `SpawnRequest` into `runtime_env`, and reaches the agent process as `LILO_AGENT_SESSION_ID`. `lilo_paths::env::LILO_AGENT_SESSION_ID` (`crates/lilo-paths/src/env.rs` [35]) is the registered name; its only current consumer is `internal/session/app/src/cli/mail.rs`.

Classification: REUSE AS IS. A native capture context receives the `SessionId` in-process from `SpawnRequest`; it does not need the env var the way external `tm` would have. The env var remains correct for the agent-side MCP/mail surface.

## 5. Identity and audit

Current fact: `Action` is a closed enum (`crates/lilo-im-core/src/types.rs`, `define_actions!` at line 137: `Spawn, Kill, List, Read, Logs, MailSend, MailRead, Nudge, Link, Doctor, Daemon, ShimCallback`). The canonical authz+audit pattern is `authorize_runtime_spawn` (`internal/runtime/daemon/src/identity.rs` [36,60]): `authorize_in_tx` writes the audit row inside one pool-scoped tx, committed regardless of decision. Session-door audit exists on the composed path (test `composed_spawn_writes_one_session_door_audit_row`, `internal/session/daemon/tests/handler/spawn_launch.rs` [67,109]). Identity has no CLI namespace; it runs as a library (`internal/session/daemon/src/identity_client.rs`).

Classification:
- REUSE AS IS: the `authorize_in_tx` audit-in-transaction pattern as the template for any capture-read verb.
- REFACTOR BEFORE USE: `Action` needs additive variants for capture inspection (reading another session's wire is privileged). `Action::ALL` is macro-derived, so the sweep is mechanical.
- MISSING: any capture/transport action or resource spec.

## 6. Postgres and store seams

Current fact: one `LiloDb` (`internal/db/src/lib.rs` [33,94], `open_postgres` [42,61]) reached via `LILO_DATABASE_URL` overlaid on `settings.toml` (`resolve_database_url`, `crates/lilo-paths/src/env.rs` [102,104]). Single unified migration `internal/db/migrations/0001_unified_schema.sql`. Store modules are per-context: `internal/session/store/src/postgres/{sessions, spawn_intents, mail, events, labels, namespaces}.rs` and `internal/runtime/store/src/postgres/lifecycle.rs`.

Classification:
- REUSE AS IS: `LiloDb`, migration runner, per-context store-module convention, `internal/db/src/test_support.rs` fixtures.
- MISSING: any capture schema (turns, runs, fidelity metadata). A capture store would land as an additive migration plus a new `internal/transport/store` (or equivalent) module following the existing shape.

## 7. Filesystem paths and env registry

Current fact: `LiloPaths` (`crates/lilo-paths/src/lilo.rs` [39,110]) derives the whole `~/.lilo/` tree: `config_root`, `run_root`, `data_root`, `logs_root`, `session_log`, `runtime_log_dir`, `events_log_path`, `cache_root`, `tmp_root`, `socket_path`. The owned env-name set is the const registry in `crates/lilo-paths/src/env.rs` (all `LILO_*` names, [7,83]) enforced by `scripts/check-env.sh --check` (justfile recipe `check-env`).

Classification:
- REUSE AS IS: `LiloHome`/`LiloPaths` derivation, env registry + lint.
- MISSING: a capture root accessor (e.g. a `capture` dir under the tree) and any capture-related env names. Both must go through the registry, not ad-hoc strings.

## 8. CLI command surface

Current fact: `Command` (`internal/session/app/src/cli/cli_def.rs` [33,58]) carries the kubectl-shaped verbs; `OperatorCommand` ([61,64]) holds substrate namespaces. `lilo capture` exists and is runtime's tmux pane-capture verb (`CaptureArgs` [248,253], `internal/session/app/src/cli/capture.rs`, `SessionRpc::Capture` at `internal/session/core/src/proto/rpc.rs` [40]). Generated surfaces are guarded (`crates/lilo/src/cli/generated_help.rs`, `generated_schema.rs`, `tests/generated_surface_guard.rs`; `tools/xtask` `run_codegen` is implemented, dist-check and mirror-publish are Phase 8 placeholders).

Classification:
- REUSE AS IS: `lilo capture` stays the pane-capture verb; do not overload it for transport.
- REFACTOR BEFORE USE: adding a `lilo transport ...` operator namespace is an additive `OperatorCommand` variant plus generated-surface regeneration via xtask codegen.
- MISSING: every transport verb (`list`, `show <session>`, paths/inspection).

## 9. Doctor and status

Current fact: `DoctorStatus` (`crates/lilo/src/cli/doctor.rs` [42,128]) aggregates `DaemonHealth`, `DatabaseHealth`, and `SubstrateHealth { identity, sessions, runtimes }` ([232,259]) with count queries per substrate, plus the runtime detail report (`internal/runtime/daemon/src/doctor.rs`, surfaced through `RuntimePort::doctor`).

Classification: REFACTOR BEFORE USE — `SubstrateHealth` is the designed extension point for a transport/capture health section (rows captured, proxy liveness). Doctor stays top-level per the locked surface; no per-substrate doctor command exists or should be added.

## 10. Lifecycle, recovery, events

Current fact: runtime reconciliation on restart lives in `internal/runtime/daemon/src/reconcile.rs`; shim reconnect with backoff in `shim.rs` (`reconnecting` [77,96], `SHIM_RECONNECT_MAX_ATTEMPTS`); session-side crash recovery aborts stuck spawn intents (`abort_spawn_intent_with`, `internal/session/store/src/postgres/spawn_intents.rs` [320,336]; test `abort_spawn_intent_clears_forking_and_marks_intent_aborted`). Durable runtime events append to JSONL via `internal/runtime/daemon/src/event_log.rs` (548 LOC) at `LiloPaths::events_log_path`, polled through `RuntimePort::poll_events`. Probe/resume knobs are registered env (`LILO_PROBE_SWEEP_INTERVAL_MS`, `LILO_RESUME_*`).

Event-log durability, inspected precisely (`internal/runtime/daemon/src/event_log.rs` at 98d8928):
- Appends are unbuffered `serde_json::to_writer` + newline with **no per-append fsync**. `sync_if_due` ([357,367]) calls `sync_data()` only when `events_since_sync >= EVENT_LOG_SYNC_BATCH` (32, line 19) or 100ms have elapsed since the last sync (`EVENT_LOG_SYNC_INTERVAL`, line 20), and it runs only inside an append. There is no background flush and no shutdown sync path in this module, so a quiescent log can hold up to 31 unsynced events **indefinitely** until the next append. `append_with_ts` ([253,259]) passes `sync_after_append: false` and never syncs.
- Recovery (`EventLog.open` [100,128] → `recover_partial_tail` [323,341]) truncates only a torn final line (`set_len` to last newline). `read_entries` ([343,355]) hard-fails on any corrupt interior line, so mid-file corruption makes the daemon unable to open the log at all.
- Compaction (`compact_if_due` [370,394]) does tmp-write + `sync_all` + rename, which is atomic for the file content, but never fsyncs the parent directory, so the rename itself is not power-loss durable. Retention deliberately drops events (`retain_from_index` requires both age and count thresholds).
- The whole log is mirrored in memory (`EventLogInner.events: Vec`, replayed at open) and deduplicated to one event per `(session_id, EventLogKind)` (`seen_event_keys`, `EventLogKey::from_event` [66,81]). Tests assert dedup and retention (`append_dedups_by_session_and_event_kind` [444,454], `compaction_requires_age_and_count` [478,491]); no test exercises fsync or power-loss semantics.

Classification:
- REJECT for capture payloads: the EventLog as implemented is a bounded, deduplicating, whole-log-in-memory lifecycle notifier with batched best-effort sync and lossy retention. Each of those properties is correct for runtime lifecycle events and wrong for wire capture (high volume, no dedup key, indefinite retention, per-record durability). This aligns with the security/durability report: it must be replaced or redesigned before any capture reuse.
- REFACTOR BEFORE USE (idioms only, not the implementation): the torn-tail truncation idiom in `recover_partial_tail` and the tmp + `sync_all` + rename idiom in `compact_if_due` are sound starting points, provided a capture store adds per-record or transactional durability (or lands in Postgres via `LiloDb`), interior-corruption tolerance, and parent-directory fsync.
- REUSE AS IS: intent-recovery shape (`abort_spawn_intent_with`) as the template for capture-run recovery; the cursor/poll read model (`events_since_or_wait`) as a read-side shape.
- MISSING: capture-specific lifecycle (what happens to an in-flight capture when the agent dies or lilod restarts), and any durable-write substrate meeting capture requirements.

Note on the port: `RuntimePort` (`internal/session/driver/src/port.rs` [18,55]) has `spawn, reap_exited, capture(scrollback), terminate, nudge, status, poll_events, doctor, terminate_all`. Its `capture` is tmux scrollback, not wire capture. Two real impls: `InProcessRuntime` (`internal/session/driver/src/in_process.rs`) and `RtmdDriver` (`rtmd.rs`). REUSE AS IS; wire capture should not be forced through this port — it is a different bounded context with its own seam.

## 11. Zero tm dependency: validated

Current fact, checked cold at the audit commit:
- No Cargo manifest in the workspace references `transport`, `tm`, or any transport-matters artifact (grep over every `Cargo.toml`: zero hits).
- No Rust source invokes a `tm` binary, `tm-shim`, or transport-matters module (workspace grep: zero hits). The only near-miss is the legacy test-fixture string `shim_path: PathBuf::from("/tmp/rtm-shim")` in `internal/runtime/daemon/src/server/config.rs` line 50 — that is littleorgans' own shim under its pre-monorepo name, not transport. The `rtm` bin (`internal/runtime/app`) is likewise littleorgans' internal runtime CLI.
- The launch chain is fully native: `lilo run` → `SessionRpc::Spawn` → `RuntimePort` → `SpawnCoordinator` → shim exec. No process in that chain is, or shells to, `tm`.

Conclusion: littleorgans has zero runtime, package, or process dependency on tm. The dependency exists only in prose (Section 12).

## 12. Stale docs prescribing a tm wrapper: DELETE OR SUPERSEDE

Current fact (locations only; contents not used as design input):
- `CLAUDE.md` (monorepo root): lines 62 ("`lilo run claude` execs `tm claude`"), 67, 115 (`lilo transport ...` premised on the tm wrapper), and the release-train mention of transport-matters (~line 246). Supersede the launch-chain-inversion prose; the `lilo transport` namespace concept survives but must be re-grounded on native capture.
- `NOTES/transport-integration.md`: entire note is premised on wrapping/shelling to `tm` (lines 37, 67, 79, 101). Supersede.
- `LESSONS.md` line 19 already records the correction (tm is experimental research; implement Transport natively). Keep.

## 13. Release, CI, testing

Current fact: single CI gate `moon ci` (`.github/workflows/pr.yml` line 87) running fmt-check, clippy, build, nextest; plus Postgres-backed ignored tests (`cargo nextest run --workspace --run-ignored ignored-only`, line 94) and a lilo binary smoke test. Operator surface is the root `justfile` (`check`, `build`, `test`, `test-db`, `check-env`, `check-loc`, `check-seam`, `check-provenance`). Compat contract: `RUNTIME_PROTOCOL_VERSION = "0.8"` with an explicit capabilities list (`crates/lilo-rm-core/src/version.rs` [8,40]). Crates release in lockstep via cargo-release; integration harness `LiloDaemon` in `tests/integration/tests/session_spawn_contract.rs` [376,472] boots a real lilod for contract tests.

Classification:
- REUSE AS IS: gate set, `LiloDaemon` harness (ready-made for capture end-to-end tests), capability-advertisement mechanism for any new capture capability flag.
- MISSING: any capture capability in `RUNTIME_PROTOCOL_CAPABILITIES`; any Python train (only Rust crates exist in-tree today, which simplifies the native-capture story).

## 14. The ten load-bearing symbols the synthesis must cite

1. `LilodRpc` — `internal/wire/src/lib.rs` [5,8]. Two-variant composed wire enum; the additive seam for a transport RPC family.
2. `run_core` (with `handle_connection`) — `internal/session/app/src/compose.rs` [115,254]. lilod composition root where a transport service gets constructed and dispatched.
3. `RuntimeLauncher` — `crates/lilo-rm-core/src/launcher.rs` [62,90]. Produces `LaunchSpec`, the single launch-preparation contract all spawn paths consume.
4. `runtime_env` — `internal/runtime/launchers/src/lib.rs` [97,108]. Existing env-injection point; proof that per-spawn correlation env already flows to every agent.
5. `run_for_session_blocking` (with `runtime_command`, `apply_launch_env_cwd`) — `internal/runtime/app/src/cli/shim.rs` [35,158]. The exec point that owns the agent's entire environment; the native interposition seam for a capture proxy.
6. `SpawnCoordinator.begin_spawn` — `internal/runtime/daemon/src/server/spawn.rs` [33,71]. The pending-launch/ShimReady handshake capture must not break.
7. `RuntimePort` — `internal/session/driver/src/port.rs` [18,55]. The hexagonal runtime seam; its `capture` is tmux scrollback and must stay distinct from wire capture.
8. `Action` — `crates/lilo-im-core/src/types.rs` (define_actions! at 137), with `authorize_runtime_spawn` (`internal/runtime/daemon/src/identity.rs` [36,60]) as the audit-in-tx template capture authz must follow.
9. `LiloPaths` — `crates/lilo-paths/src/lilo.rs` [39,110], with the `crates/lilo-paths/src/env.rs` const registry. Where a capture root and any new `LILO_*` names must be registered.
10. `SessionId` — `crates/lilo-common/src/id.rs` (define_id!, 107 dependents). The platform join key; captured sessions correlate by it, in-process, with no provider-minted id needed.

## 15. Open questions for the synthesis

- Interposition mechanism: provider base-URL env override in `LaunchSpec` versus a shim-spawned sidecar proxy. Both land on the same seam (symbols 3 and 5); the choice is a design decision, not a code constraint.
- Capture store placement: new `internal/transport/{core,store,...}` context following the session five-subdir shape, versus tables in the unified migration only. Current code constrains neither.
- Whether capture liveness belongs in `SubstrateHealth` counts alone or also in the runtime doctor detail report.
- TS product plane versus Rust control plane for the read/UI surface remains pending Stuart (noted in project memory; out of scope for this map).
