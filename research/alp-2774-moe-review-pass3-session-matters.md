---
title: ALP-2774 MoE Review Pass 3 Findings for session-matters
type: research
tags: [session-matters, linear, moe-review, isolation, runtime-matters, docker]
summary: Pass 3 found four substantive defects in the ALP-2774 execution tree; the orchestrator edits were live verified and signed off.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Executive Summary

A cold MoE pass reviewed the ALP-2774 Linear tree against current `session-matters` source, generated CLI surfaces, and the sibling `runtime-matters` 0.7.0 wire shape. The pass found four substantive issues affecting autonomous execution or merge-gate behavior. After the orchestrator amended Linear, a live re-read verified the fixes and the artifact was signed off.

## Project Metadata

- Language: Rust 2024 workspace.
- Build system: Cargo workspace with generated CLI and MCP surfaces driven by `crates/sm-cli/build.rs` and `tools/*.toml`.
- Indexed state: `session-matters` and sibling `runtime-matters` both have `.fmm.db` indexes.
- Current `session-matters` runtime deps: `lilo-rm-client = "0.6.1"`, `lilo-rm-core = "0.6.1"` in root `Cargo.toml`; ALP-2776 authorizes bumping both to `0.7.0`.
- Live Linear artifact reviewed: master ALP-2774, gate ALP-2782, backlog ALP-2775, workers ALP-2776 through ALP-2780, PER ALP-2781.

## Architecture

The reviewed path is the `sm run` spawn pipeline:

1. CLI parses `RunArgs` and flattened `SessionCreateArgs` in `crates/sm-cli/src/cli/cli_def.rs`.
2. CLI `spawn_session` builds `sm_core::SpawnRequest` and sends `RpcRequest::Spawn` to `smd` (`crates/sm-cli/src/cli/run.rs:23-75`).
3. Daemon MCP `agent_run` and `session_run` share one handler that also builds `sm_core::SpawnRequest` (`crates/sm-daemon/src/mcp_tools.rs:23-25`, `117-163`).
4. Daemon `spawn_launch` converts `sm_core::SpawnRequest` into `sm_driver::SpawnLaunch` (`crates/sm-daemon/src/handler.rs:609-644`).
5. `RtmdDriver::spawn` converts `SpawnLaunch` into `lilo_rm_core::SpawnRequest` and delegates to runtime-matters (`crates/sm-driver/src/rtmd.rs:48-80`).
6. `runtime-matters` 0.7.0 `SpawnRequest` includes `isolation`, `image`, and `mounts` (`../runtime-matters/crates/rtm-core/src/types/spawn.rs:86-103`).

## Detailed Findings

### F1: ALP-2782 pass command used an invalid tmux target

The gate pass command used `TARGET="mywin:0.1"`, then passed `--target "$TARGET"`. Current runtime parsing requires `tmux:SESSION:WINDOW.PANE`.

Evidence:

- `crates/sm-driver/src/rtmd.rs:240-244` parses the string through `lilo_rm_core::SpawnTarget`.
- `../runtime-matters/crates/rtm-core/src/types/spawn.rs:128-140` accepts only `headless` or values with the `tmux:` prefix.
- `crates/sm-cli/src/cli/generated_help.rs:18` documents `tmux:SESSION:WINDOW.PANE`.

Risk: the operator copy-paste gate would fail before Docker isolation was exercised.

Fix verified: ALP-2782 now uses `TARGET="tmux:mywin:0.1"` and explains the required prefix in precondition 5.

### F2: ALP-2779 lacked the worker dependency that creates its observable field

ALP-2779 acceptance requires a daemon-level MCP handler test proving `isolation` and `image` reach the fake driver's recorded `SpawnLaunch`. `SpawnLaunch` does not currently have those fields; ALP-2777 is the worker that adds them.

Evidence:

- `crates/sm-daemon/src/mcp_tools.rs:117-163` constructs `sm_core::SpawnRequest` inside `agent_run`.
- `crates/sm-daemon/src/handler.rs:609-644` converts the request to `SpawnLaunch`.
- `crates/sm-driver/src/driver.rs:21-28` shows current `SpawnLaunch` lacks `isolation`, `image`, and `mounts`.
- The first live Linear read showed ALP-2779 blocked by ALP-2776 and ALP-2778, but not ALP-2777.

Risk: Nancy could select ALP-2779 after ALP-2778 while ALP-2777 remained todo. In that order, ALP-2779 was unimplementable without taking ALP-2777 scope.

Fix verified: ALP-2779 is now `blockedBy` ALP-2777, ALP-2777 blocks ALP-2779, and ALP-2782 now states `ALP-2777 and ALP-2778 before ALP-2779` with a design call explaining the `SpawnLaunch` contract dependency.

### F3: The create-session help test did not enforce the new negative boundary

The gate said `create_session_help_exposes_only_declarative_arguments` enforces that `--isolation` and `--image` stay off `sm create session`. Current source only checked absence of `--target`, `--detach`, and `--force`.

Evidence:

- `crates/sm-cli/tests/cli_get_test.rs:58-75` asserts `sm create session --help` excludes `--target`, `--detach`, and `--force`, but has no assertions for `--isolation` or `--image`.

Risk: `cargo test -p sm-cli` could pass even if the new runtime-control flags leaked into the declarative create surface.

Fix verified: ALP-2778 now lists `crates/sm-cli/tests/cli_get_test.rs` as an entry point and requires extending `create_session_help_exposes_only_declarative_arguments` to assert `--isolation` and `--image` are absent. ALP-2781 mirrors the same PER criterion. ALP-2782 clarifies the existing test's current scope and the required extension.

### F4: Docker container lookup was image scoped, not session scoped

ALP-2782 pass criteria located the container with `docker ps --filter ancestor=runtime-matters-claude:local`. Runtime-matters already labels and names containers by session id, which is a safer lookup key.

Evidence:

- `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:66-98` builds the Docker argv.
- `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:79-82` sets container name and the `io.helioy.runtime-matters.session=$session_id` label.
- `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:12-14` derives the container name as `rtm-$session_id`.

Risk: on a host with another running `runtime-matters-claude:local` container, the env check could inspect the wrong container and the cleanup check could fail on unrelated state.

Fix verified: ALP-2782 pass criterion 2 now uses `CONTAINER="rtm-$SESSION_ID"` and `docker inspect "$CONTAINER"`. Pass criterion 3 now checks cleanup with `docker ps --filter "label=io.helioy.runtime-matters.session=$SESSION_ID" --quiet`.

## Verification After Orchestrator Edits

Received `VERIFY v1` on bus topic `2774-review-pass3` and re-read live ALP-2776, ALP-2777, ALP-2778, ALP-2779, ALP-2781, and ALP-2782 from Linear with relations.

Verified state:

- ALP-2782 has selector-clean `Outcome:`, `Authorized execution parent:`, `Execute:`, and `Required order:` lines.
- ALP-2779 now has `blockedBy` ALP-2776, ALP-2777, and ALP-2778.
- ALP-2777 now blocks ALP-2779.
- ALP-2778 now requires the create-session negative assertions for `--isolation` and `--image`.
- ALP-2781 mirrors the ALP-2778 test-boundary criterion.
- ALP-2782 now uses the `tmux:` target prefix and session-bound Docker locators.

Bus verification response sent:

```text
V|I sign off on ALP-2774 master tree as currently filed
```

## Dependencies

- `lilo-rm-core` 0.7.0: provides `IsolationPolicy`, `MountSpec`, and the expanded runtime `SpawnRequest`.
- `lilo-rm-client` 0.7.0: runtime client used by `RtmdDriver`.
- Docker: used by the operator-only merge gate.
- tmux: used by the `tmux:` runtime target.
- Linear: authoritative planning substrate for ALP-2774 and child ordering.

## Relevance to Helioy

This review protects the session-matters to runtime-matters boundary. The recurring lesson is to bind issue ordering to the exact carrier where a value becomes observable, not just to the first issue that adds a field to an upstream wire type.

## Open Questions

None for pass 3 after live verification. Future passes should cold-read the amended artifact if the issue tree changes again.
