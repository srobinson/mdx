---
title: runtime-matters codebase review (v0.1.8, post PR #17 session-matters runtime contract)
type: research
tags: [runtime-matters, rtm, rtmd, codebase-review, k8s, sandboxclaim, agent-sandbox, session-matters, helioy, rust-2024]
summary: rtmd is a coherent 9.3k-LOC Rust 2024 per-host daemon at v0.1.8. PR #17 lands the session-matters wire contract (stable v0.2 protocol, typed nudge and validate target, structured error codes, headless log paths). Zero kubernetes code. Single-shot diagnose handler present in skeletal form (80 LOC at rtm-daemon/src/doctor.rs:14). Per-harness directory shape is implemented as per-session, not per-launcher, and the draft language for it is stale.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-18
updated: 2026-05-18
---

## 1. Snapshot

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/runtime-matters`. Workspace version `0.1.8` (`Cargo.toml:14`), git `6b15ef9` on `main`, last commit `chore(main): release 0.1.8 (#18)` shipped 25 minutes before review start. Previous commit `0f57833 feat: add session-matters runtime contract (#17)`. Working tree carries unstaged work on `dist-workspace.toml`, `crates/rtm-cli/Cargo.toml`, a new `.github/workflows/v-release.yml`, and a deleted `release.yml`. Release-tooling churn in flight.

Rust 2024 edition, `rust-version = "1.90"`, resolver 3. Stack: `tokio` 1.48, `sqlx` 0.8 sqlite, `chrono`, `uuid v7`, `clap` 4, `anyhow`, `thiserror`, `tracing`, `serde_json`, `insta` 1.43. macOS only in v1 by intent: `kqueue` is hand-rolled via `libc`; `crates/rtm-platform/src/pidfd.rs` is a 9-line stub.

Source LOC under `crates/` excluding `target/`: 9,275 across 47 `.rs` files. Public crates on crates.io: `lilo-rm-core` (`crates/rtm-core`) and `lilo-rm-client` (`crates/rtm-client`). Private: `rtm-cli`, `rtm-daemon`, `rtm-launchers`, `rtm-platform`, `rtm-store`. Single binary `rtm` produced by `rtm-cli`.

Seven-crate inventory (workspace member count):

| Crate | LOC src | One-line |
|---|---|---|
| `rtm-core` (`lilo-rm-core`) | ~1,800 | Stable wire contract: `RuntimeRpc`, `RuntimeResponse`, `Lifecycle`, `RuntimeEvent`, `ErrorCode`, `VersionInfo`, `RuntimeCapability`, JSON-line framing, caller env denylist, MCP JSON-RPC envelope. No IO. |
| `rtm-client` (`lilo-rm-client`) | 155 | New in PR #17: `RuntimeClient` over UnixStream, `ClientError` mapping `RuntimeResponse::Error { code }` into a typed enum. Two integration tests. |
| `rtm-store` | 696 | sqlx + sqlite Lifecycle persistence (`sqlite/lifecycle.rs:18`). Migrations, `recent_lost_since`, `record_probe_sweep`, `list(StatusFilter)` with composed filters. |
| `rtm-platform` | 478 | macOS primitives: `process` (pid alive + sysctl start_time), `kqueue` (NOTE_EXIT watcher), `signal` POSIX, `tmux` gateway, `pidfd` stub. |
| `rtm-launchers` | 127 | Compile-time registry of `ClaudeLauncher` and `CodexLauncher`. `dispatch` and `registered_launchers`. `which` runs once, cached in `OnceLock`. |
| `rtm-daemon` | 1,571 | rtmd: `server::run_daemon` (`server.rs:66`), UnixListener accept loop, `handler::handle_rpc` dispatch, `shim_socket::launch_shim` per-spawn, `reconcile::run_periodic` with kqueue belt-and-braces, `doctor::collect`, `mcp_bridge::handle_line`. |
| `rtm-cli` | 1,310 (+994 tests, +293 examples/benches) | The `rtm` binary. Subcommands `daemon`, `spawn`, `kill`, `nudge`, `status`, `mcp`, `version`, `doctor`, `events`, `initdb`, `__shim`. Build-time codegen reads `tools.toml`. |

700-LOC threshold check (CLAUDE.md invariant): nothing source over. Two files tied at the cliff: `crates/rtm-store/src/sqlite/lifecycle.rs` at 668 LOC (525 impl + 143 test) and `crates/rtm-core/src/types.rs` at 656 LOC (527 impl + 128 test). `crates/rtm-daemon/src/server.rs` at 591 and `crates/rtm-cli/src/cli/mod.rs` at 427 are comfortable. Test fixture `crates/rtm-cli/tests/common/mod.rs` at 598 is the only test file approaching the cliff. No function exceeds the 150-line guideline.

## 2. Grade

**A−**. v1 shipped on intent. Wire contract is stable, structured, fully serde-snapshotted, exercised by 994 LOC of integration tests across `integration_pass1..7`, `critical_scenarios`, `spawn_target`, `surface_snapshots`. Six declared capabilities advertised at boot. Code is idiomatic Rust 2024 with tight error taxonomy. Deductions: zero k8s consumer code despite the locked Option B decision (the seam is design-only); the "per-harness directory shape" from the draft is implemented as per-session, not per-launcher; the single-shot diagnose handler exists but is skeletal (80 LOC) compared to the 881-LOC BerriAI reference; `tools.toml` lives both as a real file at `crates/rtm-core/tools.toml` and as a symlink at the workspace root, undocumented.

## 3. What actually shipped vs the draft

| Draft feature | Status | Cite |
|---|---|---|
| `rtmd` daemon | shipped | `crates/rtm-daemon/src/server.rs:66` |
| One `rtm` binary with `daemon`, `__shim`, admin subcommands | shipped | `crates/rtm-cli/src/cli/mod.rs:30-52` |
| `RuntimeLauncher` trait | shipped | `crates/rtm-core/src/launcher.rs:1-77` |
| Claude + Codex launchers | shipped, 22 LOC each | `crates/rtm-launchers/src/{claude,codex}.rs` |
| `kqueue` NOTE_EXIT watcher | shipped | `crates/rtm-platform/src/kqueue.rs:1-113`, used at `server.rs:412` |
| `pidfd` Linux stub | shipped literal | `crates/rtm-platform/src/pidfd.rs:1-9` |
| Probe sweep + reconcile (PidNotAlive + PidReuseDetected) | shipped | `crates/rtm-daemon/src/reconcile.rs:67-184` |
| Tmux gateway (`discover`, `nudge`, `alive`, `respawn_pane`) | shipped | `crates/rtm-platform/src/tmux.rs:7-66` |
| Unix-socket RPC + JSON-line framing | shipped | `crates/rtm-core/src/proto.rs:73-200` |
| sqlite Lifecycle log, WAL | shipped | `crates/rtm-store/src/sqlite/lifecycle.rs:30-39` |
| `tools.toml` codegen | shipped | `crates/rtm-cli/build.rs:1-220`, source at `crates/rtm-core/tools.toml:1-157` |
| MCP admin (kill-by-pid, status, version, watchers) | shipped | `crates/rtm-daemon/src/mcp_bridge.rs:80-117` |
| `rtm doctor` substrate health (human + JSON) | shipped | `crates/rtm-daemon/src/doctor.rs:14`, `crates/rtm-cli/src/cli/doctor.rs:19` |
| Hot-path RPC under 5ms | met. README: 0.065 ms p50 status, 9.991 ms p50 spawn | `README.md:97-101` |
| 50 sessions under 90 MB | met. README: 83.67 MiB app footprint | `README.md:99-103` |
| Reconnect-on-rtmd-restart for shims | shipped, exponential backoff, 10 attempts | `crates/rtm-cli/src/cli/shim.rs:14-86` |
| `nudge` admin verb with typed outcome | shipped | `crates/rtm-daemon/src/server.rs:339-363` |
| Strict membership boundary | shipped, no self-spawn | `handler.rs:39-135`, `server.rs:151` |
| K8s `SandboxClaim` consumer | NOT shipped, zero matches for `kube|sandbox|claim|k8s|kubernetes` | grep empty |
| Per-harness directory shape | NOT shipped as drafted; reality is per-session dirs under `RTM_HOME/logs/<session_id>/{stdout.log,stderr.log}` | `crates/rtm-daemon/src/server.rs:46-48`, `shim_socket.rs:46-50` |
| Single-shot diagnose super-bundle | shipped in skeleton form, 80 LOC, no detection codes, no recommended_action, no severity | `crates/rtm-daemon/src/doctor.rs:14-80` |

Shipped, not in the draft:

1. **Public-crate split.** `lilo-rm-core` + `lilo-rm-client` are the crates.io surface (`release-plz.toml:9-22` whitelists those two only). Daemon, CLI, store, platform, launchers stay private. Sharper cut than the draft's monolithic publish boundary.
2. **`RuntimeCapability` enum.** `crates/rtm-core/src/version.rs:8-15` broadcasts six capability strings on every `Version` and `Doctor` response: `structured_protocol_errors`, `headless_stdio_log_paths`, `status_session_set_filter`, `status_updated_since_filter`, `typed_nudge_outcomes`, `validate_target_preflight`.
3. **`ValidateTarget` preflight RPC.** `crates/rtm-core/src/types.rs:204-270` adds `ValidateTargetRequest`, `ValidateTargetResponse`, `ValidateTargetOutcome` (`Valid | InvalidTarget | TmuxPaneDead | UnsupportedTarget`). Consumed publicly via `server.rs:191-212` and internally before any state mutation.
4. **Headless log paths on `RuntimeResponse::Spawned`.** `crates/rtm-core/src/proto.rs:103-110` returns `log_dir`, `stdout_path`, `stderr_path` so the caller never guesses.
5. **`apply_launch_env_cwd` `env_clear()` contract.** `crates/rtm-cli/src/cli/shim.rs:102-108`. The runtime sees exactly `LaunchSpec.env`, never the shim bootstrap env or the daemon env. The daemon's `shim_env` (`shim_socket.rs:119-133`) is documented as "exactly one variable, `RTM_SOCKET_PATH`; adding entries is a deliberate widening".
6. **Resume-from-sleep detection in periodic reconcile.** `crates/rtm-daemon/src/reconcile.rs:96-120` measures wall-clock delta against `RESUME_GAP_THRESHOLD` (3 s default) and triggers an immediate reconcile on jump. Test at `reconcile.rs:378-384`.
7. **Three-tool release pipeline.** release-please bumps workspace version + Changelog; release-plz publishes `lilo-rm-core` and `lilo-rm-client` only; cargo-dist builds macOS binaries.

## 4. Primitives that landed

From **BerriAI/litellm-agent-platform** (cm `019e34ba`):

- **Single-shot diagnose (#3).** Landed as `crates/rtm-daemon/src/doctor.rs:14-30`. Wire shape stable per docstring at `admin.rs:109-112`. Snapshot `crates/rtm-cli/tests/snapshots/surface_snapshots__doctor_json_response_is_stable.snap:1-59` is the contract. Departures from the 881-LOC reference: no severity, no `recommended_action`, no named codes, sequential async instead of `tokio::join!`.
- **Image snapshot at agent-creation (#2).** Lives in agent-matters per the draft's own boundary. Confirmed: `crates/rtm-launchers/src/lib.rs:80-105` calls `which` lazily and caches in `OnceLock`. No agent-pinned binary path; correct for v1 because `agm` does not exist yet.
- **HMAC-derived per-pod auth token (#7).** Not landed. Lives in identity-matters or transport-matters.
- **Three-tier env precedence with explicit deletion (#10).** Landed stricter: single-tier authoritative `LaunchSpec.env` after `env_clear()` (`crates/rtm-cli/src/cli/shim.rs:102-108`). The BerriAI trap cannot occur here.
- **Multi-stage CA bundle composer (#8).** Not landed. Only matters when a vault MITM exists.

From **kubernetes-sigs/agent-sandbox** (cm `019e3784`):

- **Centralized `computeReadyCondition` (#7).** Partial. `crates/rtm-core/src/types.rs:390-440` (`Lifecycle::mark_running`, `mark_exited`, `mark_lost`) centralizes the state machine; transitions are owned by `Lifecycle` and the daemon never sets `state` directly. The `RuntimeEvent::{Running, Terminated, Lost}` enum (`types.rs:508-526`) is the only event surface; events emitted once per session via `terminated_events: HashSet<Uuid>` (`server.rs:122`, `server.rs:514`).
- **Default-deny NetworkPolicy (#9), `+kubebuilder:subresource:scale` (#3), four-resource CRD decomposition (#1).** Not landed; rtm is the consumer, not the issuer.

Validated by the rubrics:

- **Stable wire-contract crate with documented versioning.** `crates/rtm-core/src/version.rs:1-110`. `RUNTIME_PROTOCOL_VERSION = "0.2"` + capability enum let smd do feature detection before sending an unsupported RPC.
- **Structured error codes.** `crates/rtm-core/src/error.rs:6-35` (`ErrorCode`) plus per-context mapping at `crates/rtm-daemon/src/error.rs:64-100`. Seven codes: `runtime_unavailable`, `session_not_found`, `tmux_pane_dead`, `headless_nudge_unsupported`, `launch_failed`, `invalid_target`, `protocol_mismatch`. Tested at `error.rs:135-220`.

## 5. Primitives missing

**Deferred (will land later, per draft):**

- `SandboxClaim` k8s consumer (Option B). v1 chose not to even gate; there is no `k8s` Cargo feature. Acceptable for a tracer slice.
- Linux pidfd parity. `pidfd.rs` is a literal stub.
- Multi-stage CA bundle composer (BerriAI #8). Only matters with k8s + vault sidecar.
- Vault sidecar MITM (BerriAI #1). identity-matters.
- WS PTY attach (BerriAI #4). session-matters and transport-matters.

**Oversight (could have landed cheaply, did not):**

- **`recommended_action` + severity in diagnose.** `doctor.rs:14-30` returns raw counts and lists. The rubric draft says explicitly: "this is a v1 deliverable. Decompose by detection (one fn per code) and parallel-await via `tokio::join!`." Neither parallel fan-out nor the named-detection taxonomy is present.
- **`tokio::join!` in `doctor::collect`.** Sequential async; trivial cost today but the rubric calls for parallel fan-out as a model.
- **Events `since` cursor.** Reserved for v0.3 per docstring at `crates/rtm-core/src/lib.rs:11-19`. Deliberate, documented, fine.

**Superseded (rubric primitive does not apply to rtm):**

- `SELECT FOR UPDATE SKIP LOCKED` (BerriAI #6) and in-process `SimpleSandboxQueue` (agent-sandbox #6) belong to orchestration-matters once it ships warm-pool controllers.
- Four-resource CRD decomposition (agent-sandbox #1). rtm is the consumer, not the issuer.
- EnvVarsInjectionPolicy template-vs-claim split (agent-sandbox #14) lives in agent-matters and the k8s seam.

## 6. K8s consumer state

No k8s consumer code yet; the draft's Option B lock is design-only. Grep for `kube|sandbox|claim|k8s|kubernetes` across `crates/**/*.rs` returns zero matches.

The seam where it would land is `crates/rtm-launchers/src/lib.rs:16-24` (`dispatch(kind: &RuntimeKind)`). Current dispatch knows only `Claude` and `Codex`. A k8s-mode launcher would either be a third variant or, more likely per the draft, an alternate `dispatch_k8s` selected at daemon boot by config flag. No such gate exists today.

The companion seam is `crates/rtm-daemon/src/server.rs:151-189` (`begin_spawn` + `validate_spawn_target`). A k8s spawn would write a `SandboxClaim`, poll `Sandbox.status.conditions` for `Ready=True`, then transition Lifecycle into `Running` from observed pod state rather than from a `ShimReady` RPC. The `mark_running` transition (`types.rs:403-413`) currently requires a `ShimReady` with `runtime_pid` and `start_time`; a k8s-mode Lifecycle would need either a synthetic `ShimReady` populated from `Sandbox.status` or a new transition method.

Plain reading: the k8s consumer story is entirely future work. The current code does not block it but does not enable it either.

## 7. Per-harness directory shape

Reality is per-session, not per-launcher.

- `DaemonConfig.log_root` is computed once at daemon boot via `default_log_root` → `default_rtm_home`, returning `RTM_HOME` if set or `$HOME/.rtm` otherwise (`crates/rtm-daemon/src/server.rs:51-64`).
- `DaemonConfig.session_log_dir(session_id) = log_root.join(session_id.to_string())` (`server.rs:46-48`). One directory per session, keyed by UUID.
- `launch_headless_shim` writes `stdout.log` and `stderr.log` directly under that session dir (`crates/rtm-daemon/src/shim_socket.rs:46-50`).
- Paths flow back via `RuntimeResponse::Spawned { log_dir, stdout_path, stderr_path }` (`proto.rs:103-110`) and are printed by the CLI at `crates/rtm-cli/src/cli/mod.rs:154-164`.

What the draft (`runtime-matters-kubelet-draft.md:502-509`) promised: a BerriAI-shaped `rtm-launchers/{claude,codex,...}/` per-launcher directory plus a `_shared/` extraction. What landed: `crates/rtm-launchers/src/lib.rs:1-105` carries shared utilities (`resolved_argv`, `runtime_env`, `upsert_env`, `cached_binary`, `resolve_binary`) directly in the crate root. No `_shared/`. `claude.rs` and `codex.rs` are 22 lines each, both delegate everything to crate-root helpers.

The rtm equivalent of "per-harness directory" is "per-launcher Rust module", and there are two of those, both single-file. The on-disk shape the draft talked about is **the per-session log directory**, implemented as `RTM_HOME/logs/<session_id>/{stdout.log,stderr.log}` and matching what a kubelet-shaped substrate actually needs.

The draft language is stale. Replacement in section 12.

## 8. Single-shot diagnose handler

Exists, skeletal. `crates/rtm-daemon/src/doctor.rs:14-30` (`collect`). LOC: 80 file total. Compared to BerriAI's 881-LOC `diagnose/route.ts`, this is a tracer-slice. What is present:

- Stable response shape (`DoctorResponse`, `crates/rtm-core/src/admin.rs:109-125`) marked "Stable v0.2 daemon diagnostics JSON. Clients may rely on field names and JSON value kinds."
- Ten fields: version, socket path, uptime, sqlite migration state, lifecycle counts by state, watcher counts, per-launcher reachability with command path and error, tmux availability with version, last probe sweep timestamp, 24h `recent_lost` list with evidence and occurred_at.
- Both human-readable and JSON outputs. Human at `crates/rtm-cli/src/cli/doctor.rs:19-66`, JSON via the same `DoctorResponse` over the RPC.
- Two insta snapshots locking the shape.

Missing relative to BerriAI and the draft:

- No named detection codes (BerriAI ships `dead_node_assigned`, `pod_image_pull_backoff`, etc.).
- No severity classification (`ok | info | warning | error`).
- No `recommended_action` string per detection.
- No `--json` flag on `rtm doctor`; human output is the only CLI surface today. The JSON shape is reachable only via the raw RPC (`surface_snapshots.rs:34-51` exercises it directly).
- Sequential async rather than `tokio::join!` fan-out.

If a richer diagnose handler lands, the obvious shape is to keep `DoctorResponse` as the raw-state bundle and add a sibling `RuntimeRpc::Diagnose { session_id: Option<Uuid> }` returning `DiagnoseResponse { detections: Vec<Detection>, raw: DoctorResponse }`. The decomposition rule ("one fn per code, parallel-await via `tokio::join!`") applies to the new method without breaking the existing `Doctor` contract.

## 9. Session-matters runtime contract (PR #17)

`0f57833` landed 84 files changed, +2,557 / -425.

**New crate**: `lilo-rm-client` at `crates/rtm-client/` (155 LOC + 12-LOC README). Public Unix-socket client over the JSON-line contract. Two integration tests assert daemon-unavailable and typed-error-response paths. `RuntimeClient` is the type session-matters holds.

**New types in `lilo-rm-core`**:

- `ErrorCode` enum (`crates/rtm-core/src/error.rs:6-26`): seven stable snake_case codes carried on every `RuntimeResponse::Error { code, message }`.
- `ValidateTargetRequest`, `ValidateTargetResponse`, `ValidateTargetOutcome` (`crates/rtm-core/src/types.rs:204-270`). Preflight without spawning.
- `NudgeResponse`, `NudgeOutcome`, `NudgeFailureReason` (`crates/rtm-core/src/types.rs:337-356`). Typed delivery outcomes (`delivered | unsupported | failed`).
- `RuntimeCapability` enum + `RUNTIME_PROTOCOL_CAPABILITIES` constant (`crates/rtm-core/src/version.rs:8-90`). Six capability strings on every Version and Doctor response.
- `RuntimeResponse::Spawned` gains `stdout_path` and `stderr_path` (`crates/rtm-core/src/proto.rs:103-110`).
- `RuntimeResponse::ValidateTarget` and `RuntimeResponse::Nudge` variants added.
- `StatusFilter` gains `session_ids: Vec<Uuid>` and `updated_since: Option<DateTime<Utc>>` plus `requested_session_ids()` helper merging singular and plural fields (`crates/rtm-core/src/admin.rs:23-53`). `StatusRequest` mirrors the additions with bidirectional `From` (`proto.rs:8-44`).
- `RuntimeRpc::Events` documented as v0.2 stable with cursor support deferred to v0.3 (`lib.rs:7-19`, `types.rs:500-527`).

**New daemon-side module**: `crates/rtm-daemon/src/error.rs:1-231`. `RuntimeFailure` enum carries semantic failures (`ProtocolMismatch | SessionAlreadyExists | SessionNotFound | TmuxPaneDead`). `rpc_error_response` and `protocol_error_response` map any error chain to a stable `ErrorCode` based on the originating RPC context (`Spawn` defaults unmapped errors to `LaunchFailed`, everything else to `RuntimeUnavailable`). Four exhaustive test cases at lines 135-220.

**tools.toml relocation**: was workspace-root, now at `crates/rtm-core/tools.toml` with a symlink at the workspace root. Codegen pipeline in `crates/rtm-cli/build.rs` already reads from the new path. Per `release-plz.toml:9-22` only `lilo-rm-core` and `lilo-rm-client` are published, so the move keeps the contract registry inside the published crate. New `mcp_tool_list_contract` test at `crates/rtm-core/tests/tool_contract_snapshots.rs:1-11` pins the generated list.

**Shape of the rtmd–smd relationship after PR #17**:

- smd imports `lilo-rm-core` for types and `lilo-rm-client` for transport. It does not import `rtm-daemon`, `rtm-store`, or `rtm-platform`.
- smd calls `RuntimeClient::request(RuntimeRpc::Spawn { request })` and receives `RuntimeResponse::Spawned { lifecycle, event, log_dir, stdout_path, stderr_path }`. smd owns session id, target, runtime kind; rtmd owns pid, start_time, lifecycle state.
- smd preflights a target with `RuntimeRpc::ValidateTarget` before showing a spawn confirmation prompt. Outcome enum distinguishes invalid string, unsupported mode (e.g. `ssh:`), and a tmux pane that does not exist.
- smd polls `RuntimeRpc::Events` and dedupes by session id plus full event content (contract documented at `lib.rs:11-19` and `types.rs:500-507`).
- smd uses `RuntimeRpc::Status { request }` with `session_ids` + `updated_since` for authoritative lifecycle reconciliation.
- On error, smd reads `RuntimeResponse::Error { code, message }` and branches on the code enum. `runtime_unavailable` is retryable; the others are not.

The contract is internally coherent. Capability advertisement at boot lets smd detect a downgraded rtmd and refuse unsupported requests. Versioning is at the protocol level (`0.2`) plus the capability enum, not in URL paths.

## 10. Fit against helioy-controller-conventions.md

rtm has no controller code today. Conventions 1, 2, 4 are k8s-specific (CRDs, controllerRef, SSA) and N/A. Convention 5 (label-selector watch scoping) is satisfied in spirit by the per-session kqueue watcher only registered on confirmed running pids (`server.rs:412-431`). Convention 3 (`Option<bool>` three-state) is satisfied in spirit by the typed `NudgeOutcome` enum replacing a `bool` (`types.rs:337-356`). Convention 6 (non-destructive defaults) is materially satisfied: `Lifecycle::mark_lost` (`types.rs:431-439`) refuses to overwrite a terminal `Exited` or `Lost` state with new evidence; `mark_exited` only updates from `Forking | Running`; `finish_terminal` (`server.rs:507-525`) deduplicates termination via `terminated_events: HashSet<Uuid>` so a session is never declared terminated twice; lifecycle deletion happens only via `cancel_spawn` for never-ran sessions or explicit `delete` from store. When the k8s consumer lands, the conventions become load-bearing.

## 11. Surprises

1. **`finish_terminal` deduplication via `terminated_events: Mutex<HashSet<Uuid>>` (`server.rs:122`, `server.rs:514`).** Belt-and-braces termination (shim exit + kqueue + probe sweep + reconnected ready possibly racing) collapses to a single set check. A session emits at most one `Terminated` or `Lost` event in the rtmd lifetime.
2. **`record_reconnected_ready` is a separate code path (`server.rs:527-556`).** When a shim reconnects after rtmd restart, ready arrives without a pending `oneshot::Sender`. The method re-derives lifecycle state from the store, transitions `Forking` to `Running` if appropriate, registers the kqueue watcher. Terminal sessions error out.
3. **`upsert_env` in `runtime_env` (`crates/rtm-launchers/src/lib.rs:51-78`).** Caller-supplied env is authoritative, but rtm forcibly upserts `HELIOY_SESSION_ID`, `HELIOY_RUNTIME`, `RTM_SESSION_ID`, `RTM_RUNTIME_KIND`. The double-naming is redundant; presumably one is the long-term Helioy contract and the other a backstop.
4. **`StatusFilter::requested_session_ids` merges singular and plural (`admin.rs:44-52`).** Passing both `session_id: Some(X)` and `session_ids: [Y, Z]` queries `X UNION {Y, Z}`. A caller migrating from singular to plural can pass both during the transition.
5. **Codegen produces three artifacts from one `tools.toml`.** `crates/rtm-cli/build.rs` emits `crates/rtm-cli/src/generated/{cli_help.rs, mcp_tools.rs, contracts.rs}` plus README block markers (`<!-- rtm-admin-tools:start -->` in README.md:117-126). Single source of truth for CLI help, MCP schemas, typed Rust aliases, README admin tools table. `generated_snapshots.rs` catches drift at PR time.
6. **`tools.toml` lives in two places.** Real file at `crates/rtm-core/tools.toml`; symlink at workspace root. Symlink for build tooling that expects root; real file ships inside the published `lilo-rm-core` crate. Easy to miss; not documented.
7. **`build.rs` lives in `rtm-cli` but reads via the `lilo-rm-core` workspace dep.** Codegen is driven by the consumer, not the contract crate. Contract changes need `cargo build -p rtm-cli` to refresh.
8. **`apply_launch_env_cwd` integration test runs `/usr/bin/env`** (`crates/rtm-cli/src/cli/shim.rs:148-191`). Asserts env clear actually clears and `PATH=` is not inherited. Worth flagging for any future Alpine-based Linux CI.
9. **`RuntimeKind::Other(String)` exists.** `crates/rtm-core/src/types.rs:14`. Parses any non-empty unrecognized runtime name; dispatcher returns `LauncherError::NoLauncher`. A hook for v2+ plugin loading without breaking the wire enum.

## 12. Recommended draft updates

Concrete updates to `runtime-matters-kubelet-draft.md`.

**Per-harness directory shape section (lines 502-509).** Drop the BerriAI per-launcher directory mapping. Replace with a section titled "Per-session log directory shape" stating: rtmd writes one directory per session at `RTM_HOME/logs/<session_id>/` containing `stdout.log` and `stderr.log` for headless spawns. `RuntimeResponse::Spawned` returns `log_dir`, `stdout_path`, `stderr_path` so callers never guess. Tmux spawns produce no log files because the tmux pane owns the buffer. The launcher-side shared code lives in the `rtm-launchers` crate root because both launchers are 22 lines each; the `_shared/` mod is unnecessary until a third launcher arrives or one exceeds 200 LOC.

**Open question 8 (rtmd's MCP scope), line 465.** Close. v1 ships four MCP tools: `rtm_kill_by_pid`, `rtm_status`, `rtm_version`, `rtm_watchers`. Source-of-truth is `crates/rtm-core/tools.toml`. RuntimeLauncher introspection is not exposed; `rtm doctor` returns launcher reachability inside `DoctorResponse.launchers`, which is JSON-stable and snapshot-tested. Future MCP additions go through tools.toml.

**External validation section, line 491.** Drop the "`cfg(feature = "k8s")` gate reserved for v2" promise. v1 chose not to ship a stub feature flag. The k8s seam is a new launcher variant (`RuntimeKind::Sandbox` or sibling enum) plus a new `LifecycleState` transition that recovers `Running` from `Sandbox.status.conditions` rather than a `ShimReady` RPC. Name the precise seam: `crates/rtm-launchers/src/lib.rs::dispatch` and `crates/rtm-core/src/types.rs::Lifecycle::mark_running`.

**Single-shot diagnose super-bundle section, lines 513-522.** Split into "landed in v0.2" and "owed". Landed: version + capabilities, socket path, uptime, sqlite migration state, lifecycle counts by state, watcher counts, per-launcher reachability with `which`-resolved path or error, tmux availability with version, last probe sweep timestamp, 24h `recent_lost` list. Owed: per-session detection codes with severity and recommended_action, `tokio::join!` parallel fan-out, `--json` CLI flag (today the JSON shape is reachable only via the raw RPC), rtmd process self-stats (RSS, fd count, socket queue depth), pod/CR status (waits on k8s mode).

**Spawn flow section, lines 152-194.** Draft says session-matters' Spawn carries `{ session_id, runtime, env, cwd, agent_config }`. Drop `agent_config`. The actual `SpawnRequest` (`types.rs:272-280`) is `{ session_id, runtime, env: Vec<LaunchEnv>, cwd: PathBuf, target: SpawnTarget }`. Persona / agent config arrives via env vars (because `agm` does not exist yet). Target enum is `Tmux(TmuxSpawnTarget) | Headless(HeadlessSpawnTarget)`. The daemon validates the target preflight before any state mutation via `server.rs:176-189`; the public `ValidateTarget` RPC exposes the same logic without spawning.

**Boundary contracts → runtime-matters → session-matters (event channel), lines 376-387.** Draft says: "Pushed over a long-lived unix socket connection from rtmd to smd. smd's reconcile task consumes; sqlite is updated." Replace. smd pulls, not pushes. The events contract (`lib.rs:11-19`, `types.rs:500-507`): rtmd retains events in current-daemon-process memory in append order, smd polls `RuntimeRpc::Events` and dedupes by session id plus full event content. No long-lived push connection. Cursor support reserved for v0.3. Restarting rtmd starts a fresh in-memory vector; authoritative lifecycle reconciliation goes through `RuntimeRpc::Status` with `session_ids` and `updated_since` filters.

**Add new section: "PR #17 contract changes (v0.2)".** Insert before "Success criteria". Name the seven `ErrorCode` values, the six `RuntimeCapability` strings, the new `ValidateTarget` and typed `NudgeOutcome` RPCs, the `StatusFilter` `session_ids` + `updated_since` additions, the headless `stdout_path` / `stderr_path` additions to `RuntimeResponse::Spawned`, the new `lilo-rm-client` published crate. Cite `crates/rtm-core/src/version.rs:8-15` for capabilities and `crates/rtm-core/src/error.rs:8-26` for error codes.

**transport-matters open question 4 (`transport-matters-ws-upgrade-brief.md:126`).** Close as no. rtmd has no HTTP listener and no WS code. The admin surface is Unix-socket JSON-line. `rtm doctor` is a JSON-over-UDS RPC. The MCP bridge at `crates/rtm-daemon/src/mcp_bridge.rs:13-128` runs over the same Unix socket via the `McpBridge` envelope. If `sm attach` ever flows through rtmd, the surface area stays Unix socket plus possibly a per-session UDS for the PTY duplex; no HTTP, no WS, no upgrade handling, and therefore no contention with the recommended axum `WebSocketUpgrade` choice for smd.

## 13. Provenance

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/runtime-matters`
- Version: `0.1.8` (`Cargo.toml:14`)
- Commit SHA: `6b15ef94d08b40c59b0687cc328124f37a06d6c2` (HEAD), with `0f57833` (PR #17, "feat: add session-matters runtime contract") immediately prior
- Date: 2026-05-18
- Working tree: unstaged work on `dist-workspace.toml`, `crates/rtm-cli/Cargo.toml`, new `.github/workflows/v-release.yml`, deleted `release.yml`. Release-tooling churn.
- cm anchors: `019e34ba` (BerriAI/litellm-agent-platform), `019e3784` (kubernetes-sigs/agent-sandbox), `019e327f` (seven-product family)
- Companion drafts read in full: `~/.mdx/projects/runtime-matters-kubelet-draft.md`, `~/.mdx/projects/helioy-controller-conventions.md`, `~/.mdx/projects/transport-matters-ws-upgrade-brief.md`
- Companion reviews read in full: `~/.mdx/research/berriai-litellm-agent-platform.md`, `~/.mdx/research/kubernetes-sigs-agent-sandbox.md`
- fmm: indexed (`./.fmm.db` present, 4 MB WAL on disk indicating recent churn). The MCP-side `fmm_list_files` errored because the index was registered at the parent `/Users/alphab/Dev/LLM/DEV/helioy/` path; review used direct file reads against the known structure.
