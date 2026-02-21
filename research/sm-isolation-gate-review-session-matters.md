---
title: sm isolation gate review for session-matters
type: research
tags: [session-matters, alp-2774, sm-isolation, moe-review, linear, runtime-matters]
summary: ALP-2774 pass 2 amendments were verified clean after fixing compile split, gate startup, and cleanup semantics.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Executive Summary

`ALP-2774` plans the sm-side plumbing for Docker isolation, image selection, and mount carrier forwarding from `sm run` and MCP into runtime-matters. The worker tree is directionally coherent with the live code and runtime-matters 0.7.0 wire, but pass 2 found three substantive blockers: `ALP-2776` cannot stay compile green if all rtm driver forwarding waits for `ALP-2777`, the plan-level gate names nonexistent daemon packages and binaries, and the gate lacks spawned-session teardown.

## Project Metadata

- Language: Rust 2024 edition.
- Workspace: 6 crates, 105 indexed files, 17,097 LOC from `fmm_list_files`.
- Crates: `sm-paths`, `sm-core`, `sm-store`, `sm-driver`, `sm-daemon`, `sm-cli`.
- Build system: Cargo workspace plus `justfile` recipes.
- Current runtime wire deps in session-matters: `lilo-rm-client = "0.6.1"` and `lilo-rm-core = "0.6.1"` in `Cargo.toml:21-22`.
- Target runtime wire in the plan: runtime-matters `lilo-rm-core` and `lilo-rm-client` 0.7.0. Verified in sibling checkout at `runtime-matters/crates/rtm-core/Cargo.toml:2-5` and `runtime-matters/crates/rtm-client/Cargo.toml:2-5`.
- Structural index: `.fmm.db` exists and `fmm validate` reported all 105 files indexed and current.

## Architecture

The spawn path is K8s shaped. The CLI constructs intent, `smd` owns the durable session record, and runtime-matters owns process execution.

Current source flow:

1. `RunArgs` contains imperative controls `target`, `force`, and `detach` at `crates/sm-cli/src/cli/cli_def.rs:78-90`.
2. `SessionCreateArgs` contains declarative session identity fields at `crates/sm-cli/src/cli/cli_def.rs:94-107`.
3. `spawn_session` builds `sm_core::SpawnRequest` at `crates/sm-cli/src/cli/run.rs:23-75`.
4. MCP `agent_run` also builds `SpawnRequest` at `crates/sm-daemon/src/mcp_tools.rs:117-163`.
5. `sm_core::SpawnRequest` currently contains runtime, role, workspace, dir, namespace, target, agent_config, env, shell_resume, labels, and force at `crates/sm-core/src/proto.rs:16-38`.
6. `spawn_launch` converts `SpawnRequest` into `SpawnLaunch` at `crates/sm-daemon/src/handler.rs:609-644`.
7. `RtmdDriver::spawn` converts `SpawnLaunch` into `lilo_rm_core::SpawnRequest` and sends it to rtmd at `crates/sm-driver/src/rtmd.rs:48-80`.

The public surface is generated from `tools/run.toml`. `crates/sm-cli/build.rs` generates MCP schema JSON, CLI help constants, docs, templates, and snapshots. The guard `generated_help_constants_have_source_consumers` at `crates/sm-cli/tests/generated_surface_guard_test.rs:104-115` means `tools/run.toml` changes and Rust consumers must land atomically.

## Key Patterns

- Public command and MCP documentation comes from `tools/*.toml`, not generated artifacts.
- `sm daemon start` is the operator surface for starting `smd`; it spawns hidden `__smd` from the current `sm` executable.
- `rtm daemon start` is the operator surface for starting runtime-matters. There is no `rtmd` package in the runtime-matters Cargo workspace.
- CLI `DaemonFixture` cannot observe `SpawnLaunch`; daemon tests using `MockDriver` and direct `mcp_tools::call_tool` are the right seam for field forwarding.
- Gate commands must use repo-built binaries when proving current worktree behavior.
- Runtime wire dependency bumps must check all downstream struct literals against the new upstream type before accepting a split worker plan.

## Detailed Findings

### F1. ALP-2776 cannot be atomic-green while all rtm driver forwarding waits for ALP-2777

`ALP-2776` accepts a `cargo check --workspace` clean gate after bumping `lilo-rm-client` and `lilo-rm-core` from 0.6.1 to 0.7.0. It also lists driver and daemon forwarding as out of scope, deferred to `ALP-2777`. That split is not compile green against the live upstream 0.7.0 shape.

Evidence:

- Live `RtmdDriver::spawn` constructs the upstream `lilo_rm_core::SpawnRequest` at `crates/sm-driver/src/rtmd.rs:60-68`.
- runtime-matters 0.7.0 `SpawnRequest` has required `isolation`, `image`, and `mounts` fields at `runtime-matters/crates/rtm-core/src/types/spawn.rs:85-103`.
- That upstream struct derives `Clone`, `Debug`, `Deserialize`, `Eq`, `PartialEq`, and `Serialize`, but not `Default`, at `runtime-matters/crates/rtm-core/src/types/spawn.rs:85-86`.
- `ALP-2782` already says the bare dep bump breaks compile because `RtmdDriver::spawn` constructs the upstream `SpawnRequest`, but `ALP-2776` does not authorize the minimum rtm-side field additions needed to satisfy that reality.

Required amendment:

Prefer merging `ALP-2776` and `ALP-2777` into one worker so the dep bump, sm-core fields, `SpawnLaunch`, `spawn_launch`, and `RtmdDriver::spawn` forwarding land together. Acceptable fallback: keep the issues split, but extend `ALP-2776` to add minimum upstream defaults in `RtmdDriver::spawn`, such as `isolation: IsolationPolicy::default()`, `image: None`, and `mounts: Vec::new()`. `ALP-2777` can then replace those defaults with launch-carried values.

### F2. ALP-2782 names nonexistent daemon packages and binaries

`ALP-2782` says runtime-matters should start with `cargo run -p rtmd`, and session-matters should start with `cargo run -p smd` or `./target/release/smd` after `cargo build --release -p smd`. Those package and binary names do not exist in the live repos.

Evidence:

- Runtime-matters package inventory contains `rtm-cli`, `rtm-daemon`, `lilo-rm-core`, `lilo-rm-client`, and related crates. It has no `rtmd` package. `cargo run -p rtmd -- --help` fails with `package(s) rtmd not found`.
- Runtime-matters defines the operator binary as `rtm` in `runtime-matters/crates/rtm-cli/Cargo.toml:16-18`.
- Runtime-matters exposes daemon startup through `rtm daemon start` in `runtime-matters/crates/rtm-cli/src/cli/daemon.rs:7-21`.
- Session-matters has no `smd` package. `cargo run -p smd -- --help` fails with `package(s) smd not found`.
- Session-matters defines the operator binary as `sm` in `crates/sm-cli/Cargo.toml:15-17`.
- Session-matters daemon startup is `sm daemon start`; it spawns the hidden `__smd` command from the current executable at `crates/sm-cli/src/cli/daemon.rs:40-48`.
- README runtime setup documents `rtm daemon start` and `sm daemon start` at `README.md:9-23`.

Required ALP-2782 amendment:

```bash
# runtime-matters checkout
cargo build --release -p rtm-cli --bin rtm
./target/release/rtm daemon start

# session-matters checkout
cargo build --release -p sm-cli --bin sm
./target/release/sm daemon start
SM=./target/release/sm
```

If `rtm daemon start` is foreground, the gate should say to run it in a dedicated terminal or pane.

### F3. ALP-2782 lacks teardown for the spawned gate session

The gate starts a real Claude TUI, tmux target ownership, session record, and Docker container. It verifies the container environment, then leaves the smoke artifact running. The operator may keep rtmd and smd running, but the exact spawned smoke session should be terminated to make the gate repeatable and to remove the OAuth-bearing container.

Evidence:

- `print_session_line` prints the session id first at `crates/sm-cli/src/cli/output.rs:3-19`.
- `sm delete session` accepts a selector and grace period at `crates/sm-cli/src/cli/cli_def.rs:226-235`.
- CLI delete sends `DeleteRequest` at `crates/sm-cli/src/cli/delete.rs:19-50`.
- Daemon delete resolves targets and calls `delete_one` at `crates/sm-daemon/src/handler.rs:261-279` and `crates/sm-daemon/src/handler.rs:392-431`.
- `RtmdDriver::terminate` sends an rtm `KillRequest` at `crates/sm-driver/src/rtmd.rs:152-187`.
- Runtime-matters dispatches Docker isolated kills through `runtime-matters/crates/rtm-daemon/src/runtime_kill.rs:11-32`.
- Runtime-matters implements container termination with `docker kill` at `runtime-matters/crates/rtm-daemon/src/docker_runtime.rs:86-108`.

Required ALP-2782 amendment:

```bash
SESSION_ID="$($SM run claude \
  --target "$TARGET" \
  --role pm \
  --label app=nginx \
  --isolation docker \
  --image runtime-matters-claude:local \
  --agent-config auth-passthrough | awk '{print $1}')"

# existing pass criteria here

"$SM" delete session "id:$SESSION_ID" --grace 5
```

A trap is preferable so cleanup runs after a failed env check. runtime-matters `--rm` is useful after Claude exits, but it does not make a live gate session self-cleaning.

### F4. ALP-2776 should pin direct re-exports for the rtm isolation and mount types

`ALP-2776` says to re-export the rtm isolation and mount types needed by sm callers, matching the existing runtime type abstraction. That can be read two ways: direct `pub use` of rtm types, or sm-core wrapper types analogous to `sm_core::RuntimeKind`. `ALP-2778` already commits to `Option<lilo_rm_core::IsolationPolicy>` in `RunArgs`, which implies direct use.

Required amendment:

Pin the wording to direct re-exports: `pub use lilo_rm_core::{IsolationPolicy, MountSpec}` through `sm-core`. Do not introduce wrapper types for this plan. The existing `RuntimeKind` wrapper is grandfathered behavior, not the desired pattern for this worker split.

### F5. ALP-2779 should correct the MCP dispatch wording

`ALP-2779` says the MCP `agent_run` handler is where `session_run` dispatches into. Live code uses a shared match arm in `call_tool`: `"agent_run" | "session_run" => agent_run(state, context, arguments).await` at `crates/sm-daemon/src/mcp_tools.rs:17-24`.

Required amendment:

Rewrite as: MCP `agent_run` handler in `crates/sm-daemon/src/mcp_tools.rs`, also dispatched for the `session_run` MCP name through the shared `call_tool` match arm.

### F6. ALP-2782 cleanup verification semantics, resolved

A delta verify found that `ALP-2782` cleanup criterion 3 briefly used `"$SM" list sessions | awk '{print $1}' | grep -qx "$SESSION_ID"`. Live CLI has no top-level `list` command, and session deletion does not remove session rows. The issue was amended and verified clean.

Evidence for the original issue:

- `Command` in `crates/sm-cli/src/cli/cli_def.rs:27-58` has `Get` but no `List`.
- `GetResource::Session` at `crates/sm-cli/src/cli/cli_def.rs:116-123` is the list and get surface, including the `sessions` alias.
- `crates/sm-cli/src/cli/get.rs:9-15` routes `sm get session` with no id into `list_sessions`.
- `./target/debug/sm list sessions --help` exits with `unrecognized subcommand 'list'`.
- `sm delete session` terminates runtime and persists a terminated row through `crates/sm-daemon/src/handler.rs:392-431` and `crates/sm-store/src/sqlite/sessions.rs:182-201`.
- `list_sessions_by_selector` at `crates/sm-store/src/sqlite/sessions.rs:86-128` selects persisted rows without filtering out terminated state.

Verified resolution:

- Live `ALP-2782` now uses `"$SM" wait "id:$SESSION_ID" --for terminated --timeout-secs 10` as the session cleanup proof.
- `WaitArgs` defines `--for` at `crates/sm-cli/src/cli/cli_def.rs:271-278`.
- `WaitCondition::Terminated` exists at `crates/sm-core/src/proto.rs:259-263`.
- `crates/sm-cli/src/cli/wait.rs:9-36` parses the condition with `WaitCondition::from_str` and sends a daemon `WaitRequest`.
- The Docker no-container check remains in the gate.

### Positive checks from the cold read

- `ALP-2774`, `ALP-2782`, `ALP-2776` through `ALP-2781` are aligned on absorbing `ALP-2798`, moving to lilo-rm 0.7.0, adding the sm-core `mounts` carrier, forwarding it through `SpawnLaunch`, and keeping public mounts out of scope.
- runtime-matters 0.7.0 `SpawnRequest` has `isolation`, `image`, and `mounts` fields at `runtime-matters/crates/rtm-core/src/types/spawn.rs:85-103`.
- runtime-matters `IsolationPolicy::from_str` accepts `host`, `docker`, and `docker:PROFILE`, and rejects unknown policies at `runtime-matters/crates/rtm-core/src/isolation.rs:36-68`.
- Current session-matters source confirms the planned touch points: `RunArgs`, `SessionCreateArgs`, `spawn_session`, `agent_run`, `SpawnRequest`, `SpawnLaunch`, `spawn_launch`, and `RtmdDriver::spawn`.
- The Docker env verification snippet in `ALP-2782` uses portable Docker CLI formatting, POSIX `test -n`, and grep. No Darwin versus Linux issue was found in that snippet itself.

## Verification Run

Commands run from `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`:

```bash
fmm validate
cargo tree -p sm-driver -i lilo-rm-core
cargo check --workspace
./target/debug/sm run claude --isolation docker --image runtime-matters-claude:local --role x --dir /tmp
cargo run -p smd -- --help
```

Results:

- `fmm validate`: all 105 files indexed and current.
- `cargo tree -p sm-driver -i lilo-rm-core`: current source still uses `lilo-rm-core v0.6.1`, as expected before ALP-2776.
- `cargo check --workspace`: clean.
- Current `sm run --isolation` exits with clap code 2 and `unexpected argument '--isolation' found`, confirming the baseline ALP-2774 intends to change.
- `cargo run -p smd -- --help`: fails because package `smd` is absent.

Commands run from the sibling runtime-matters checkout:

```bash
cargo run -p rtmd -- --help
```

Result:

- Fails because package `rtmd` is absent.

## Dependencies

Critical dependencies for this plan:

- `lilo-rm-core` 0.7.0: owns `IsolationPolicy`, `MountSpec`, and runtime `SpawnRequest` fields.
- `lilo-rm-client` 0.7.0: client side rtmd RPC surface.
- `clap`: derives CLI parsing for `RunArgs`; `IsolationPolicy::from_str` drives accepted `--isolation` values.
- `serde`: keeps new fields backward decodable through defaults.
- `tokio`: async daemon and driver runtime.
- Docker CLI: operator merge gate verification and runtime-matters Docker launch and kill paths.

## Relevance to Helioy

This review reinforces three Helioy process rules. First, runtime wire dep bumps must account for every downstream struct literal in the same compile-green unit. Second, issue gates must use the actual operator surface, not conceptual daemon names. Third, real smoke gates that start long lived agent processes must include exact teardown for the spawned artifact while preserving operator owned infrastructure.

## Bus Follow-up

On the `2774-review-pass2` bus thread, `helioy:general:9.1.1` agreed that all five conditional requirements are load-bearing. Pane A then withdrew the softer teardown framing and concurred with the stronger session-lifecycle requirement. The strongest requirement remains the ALP-2776 compile-green split: either merge ALP-2776 and ALP-2777, or extend ALP-2776 with minimum upstream rtm `SpawnRequest` fields. The spawned-session teardown requirement was also reaffirmed: Docker `--rm` is not session cleanup, so the gate needs an id-capturing cleanup trap that runs `sm delete session "id:$SESSION_ID" --grace 5`. Both panes are now aligned on conditional signoff and will re-review after Linear amendments land.

## Open Questions

- Should `ALP-2782` embed the gate as a single shell script with `set -euo pipefail` and a cleanup trap, or keep it as prose plus commands?
- Should the gate require isolated `SM_HOME` and `RTM_SOCKET_PATH` values to avoid touching operator default daemons?
- After ALP-2774 lands, should a follow-up persist `isolation`, `image`, and `mounts` on `Session` for operator observability?


## Final Pass 2 Verify

After re-reading live `ALP-2782` and the cited wait surface, the delta amendment is valid. The gate now asserts TERMINATED state with `sm wait "id:$SESSION_ID" --for terminated --timeout-secs 10`, which matches `WaitArgs` and `WaitCondition::Terminated`. Bus response sent: `I sign off on ALP-2782 as currently filed.`
