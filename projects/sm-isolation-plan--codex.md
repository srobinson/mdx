# Plan: plumb `sm run --isolation` and `--image`

**Author:** Codex pane, `session-matters:helioy-tools:codebase-analyst:2:3.2`
**Repo:** `littleorgans/session-matters` at `b919b3d`
**Adjacent runtime read:** `littleorgans/runtime-matters` at `e138cb5`
**Status:** independent draft for MoE synthesis

## Pre-flight context

littleorgans is pre-release with zero downstream users. Breaking changes are welcome. The prior agent config plan records the same stance and says not to add backward compatibility shims, additive only schemas, or staged deprecations for compatibility reasons. `~/.mdx/projects/agent-config-plan.md:8-10` `LESSONS.md:6-7`

Apply that stance here. Do the clean plumbing for the current command shape. Do not preserve dead surfaces for callers that do not exist.

## Goal

Make the user command accepted by `sm run`, represented in the session-matters spawn request, preserved through `smd`, and delivered to `rtmd` as the runtime-matters `isolation` and `image` fields. The path is CLI or MCP input to `sm_core::SpawnRequest`, then `DaemonState::spawn`, then `SpawnLaunch`, then `RtmdDriver::spawn`, then `lilo_rm_core::SpawnRequest`. `--agent-config` remains the existing env producing mechanism; this plan does not add isolation or image defaults to `agent.toml`. Current `--agent-config` behavior is env only. `crates/sm-daemon/src/agent_config.rs:73-96` `crates/sm-daemon/src/handler.rs:606-641`

## Scope in

- `sm run --isolation host|docker[:PROFILE]`.
- `sm run --image IMAGE`.
- MCP `session_run` and `agent_run` inputs for the same fields.
- Internal `sm_core::SpawnRequest` fields.
- `SpawnLaunch` fields and daemon handoff.
- `RtmdDriver` passthrough to runtime-matters.
- Generated help, MCP schemas, snapshots, and focused tests.

## Scope out

- Runtime-matters changes. Current runtime-matters already has `isolation` and `image` on its spawn request. `../runtime-matters/crates/rtm-core/src/types/spawn.rs:76-92`
- Mount support. Current Docker argv has only the built in cwd bind and no caller supplied mount field. `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:66-83` `~/.mdx/projects/rtm-mount-analysis--codex.md:94-104`
- `agent.toml` defaults for `role`, `runtime`, `dir`, `target`, `isolation`, `image`, or `labels`. The prior plan explicitly defers schema expansion for those defaults. `~/.mdx/projects/agent-config-plan.md:26-31` `~/.mdx/projects/agent-config-plan.md:122-127`
- Session record persistence for `isolation` and `image`. Forwarding tests and live smoke prove the launch path. Historical audit fields can be filed separately if needed. Current `Session` has no fields for these values. `crates/sm-core/src/session.rs:66-88` `crates/sm-store/src/schema.rs:1-20`
- Credential bridge work, Keychain extraction, and Claude auth semantics. The env passthrough research is useful context, but not this plumbing task. `~/.mdx/projects/auth-token-debug--codex.md:151-186` `~/.mdx/projects/auth-token-debug--claude.md:376-390`
- Any work not required for the user command to run.

## Numbered steps

### Step 1. Align the runtime wire dependency and mirror the two rtmd fields in `sm_core::SpawnRequest`

**Files and line ranges**

- `Cargo.toml:31-32`
- `Cargo.lock:708-723`
- `crates/sm-core/src/proto.rs:16-38`
- `crates/sm-core/src/proto.rs:406-472`
- `../runtime-matters/crates/rtm-core/src/types/spawn.rs:76-92`

**What and why**

Update `lilo-rm-client` and `lilo-rm-core` to the runtime-matters release that exposes `SpawnRequest.isolation` and `SpawnRequest.image`. The current session-matters lockfile is on `0.6.1`, while the adjacent runtime-matters type already has the two fields. `Cargo.toml:31-32` `Cargo.lock:708-723` `../runtime-matters/crates/rtm-core/src/types/spawn.rs:76-92`

Add matching fields to `sm_core::SpawnRequest`: `isolation: lilo_rm_core::IsolationPolicy` with host default, and `image: Option<String>` with `None` default. Put them near `target`, because they are launch controls, not labels or env. Update the existing spawn request serde tests so the round trip includes Docker plus image, and the missing field decode paths still default to host and no image. The defaults are the natural spawn semantics, not a compatibility shim. `crates/sm-core/src/proto.rs:16-38` `crates/sm-core/src/proto.rs:406-472`

**Acceptance test**

- `cargo tree -p sm-driver -i lilo-rm-core` shows the chosen runtime-matters version with `isolation` and `image` support.
- `cargo test -p sm-core spawn_request_round_trips_as_tagged_json` passes.
- `cargo test -p sm-core spawn_request_decodes_legacy_payload_without_new_fields` passes and asserts `IsolationPolicy::Host` plus `image == None`.
- `cargo test -p sm-core spawn_request_decodes_new_payload_without_legacy_workspace` passes and asserts the same defaults.

### Step 2. Update the public tool contract source and regenerate every derived surface

**Files and line ranges**

- `tools/run.toml:1-3`
- `tools/run.toml:22-25`
- `tools/run.toml:67-141`
- `crates/sm-cli/build.rs:19-39`
- `crates/sm-cli/build.rs:201-224`
- `crates/sm-cli/build.rs:227-288`
- `crates/sm-cli/src/cli/generated_help.rs:1-20`
- `crates/sm-cli/src/mcp/generated_schema/session_run.json:1-56`
- `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@session_run.snap:5-60`
- `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@agent_run.snap:5-60`

**What and why**

`tools/run.toml` is the source for public session-matters tools, including MCP schema, CLI help constants, skill output, and README sections. Add `isolation` and `image` params to `tools.session_run`, update the run tool description to mention Docker isolation and image selection, then regenerate instead of editing generated Rust or JSON directly. `tools/run.toml:1-3` `crates/sm-cli/build.rs:19-39` `crates/sm-cli/build.rs:201-224` `crates/sm-cli/build.rs:227-288`

`agent_run` is generated as an alias from `tools/run.toml`, so both `session_run` and `agent_run` snapshots must change together. `tools/run.toml:139-141` `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@session_run.snap:5-60` `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@agent_run.snap:5-60`

Use a string shape for `isolation`, with help text that says `host`, `docker`, or `docker:PROFILE`. Do not enumerate only `host` and `docker`, because current runtime-matters accepts Docker profile names such as `own-init`, `allow-root`, and `arm64-manifest-escape`. `../runtime-matters/crates/rtm-core/src/isolation.rs:36-64` `../runtime-matters/crates/rtm-daemon/src/spawn_preflight.rs:69-101`

**Acceptance test**

- Generated help defines `SESSION_RUN_ISOLATION_HELP` and `SESSION_RUN_IMAGE_HELP`. `crates/sm-cli/src/cli/generated_help.rs:1-20`
- Generated `session_run.json` and `agent_run.json` expose `isolation` and `image` inputs. `crates/sm-cli/src/mcp/generated_schema/session_run.json:1-56`
- `cargo test -p sm-cli mcp_each_tool_snapshot` passes after `cargo insta accept` for the affected snapshots.
- `cargo test -p sm-cli generated_help_constants_have_source_consumers` passes, proving new generated constants have real consumers. `crates/sm-cli/tests/generated_surface_guard_test.rs:103-114`

### Step 3. Add `sm run` flags and MCP argument parsing

**Files and line ranges**

- `crates/sm-cli/src/cli/cli_def.rs:78-107`
- `crates/sm-cli/src/cli/run.rs:12-55`
- `crates/sm-daemon/src/mcp_tools.rs:116-154`
- `crates/sm-cli/tests/cli_help_surface_test.rs:41-59`
- `crates/sm-cli/tests/cli_get_test.rs:58-88`

**What and why**

Add `RunArgs.isolation` and `RunArgs.image`. Keep them on `sm run`, not `SessionCreateArgs`, so `sm create session` remains the declarative headless surface without imperative target controls. The existing split already keeps `--target`, `--force`, and `--detach` on `RunArgs`; follow that pattern. `crates/sm-cli/src/cli/cli_def.rs:78-90` `crates/sm-cli/tests/cli_get_test.rs:58-88`

Pass those values into `spawn_session`, and have `create_session` call the same helper with host isolation and no image. Then populate the new `SpawnRequest` fields beside `target` and `force`. `crates/sm-cli/src/cli/run.rs:12-55`

For MCP, read optional `isolation` with `IsolationPolicy::from_str`, default to host, read optional `image` as a string, and put both values into the same `SpawnRequest`. Keep existing `agent_config`, labels, target, and force behavior unchanged. `crates/sm-daemon/src/mcp_tools.rs:116-154`

**Acceptance test**

- `cargo test -p sm-cli run_help_describes_every_flag` passes and includes the new flag descriptions. `crates/sm-cli/tests/cli_help_surface_test.rs:41-59`
- `cargo test -p sm-cli run_help_exposes_force_as_imperative_argument` is updated to assert `--isolation` and `--image` are present on `sm run`. `crates/sm-cli/tests/cli_get_test.rs:77-88`
- `cargo test -p sm-cli create_session_help_exposes_only_declarative_arguments` is updated to assert `--isolation` and `--image` do not appear on `sm create session`. `crates/sm-cli/tests/cli_get_test.rs:58-75`
- A parser level or CLI level test proves `sm run claude --role pm --dir <tmp> --isolation docker --image runtime-matters-claude:local` no longer fails with `unexpected argument '--isolation'`.

### Step 4. Carry isolation and image through the daemon launch model

**Files and line ranges**

- `crates/sm-driver/src/driver.rs:21-28`
- `crates/sm-daemon/src/handler.rs:132-143`
- `crates/sm-daemon/src/handler.rs:606-641`
- `crates/sm-daemon/tests/handler.rs:94-149`
- `crates/sm-daemon/tests/handler.rs:152-197`
- `crates/sm-daemon/tests/common/mod.rs:259-270`

**What and why**

Add `isolation` and `image` to `SpawnLaunch`, then copy them from `SpawnRequest` inside `spawn_launch`. `SpawnLaunch` is the handoff object between daemon policy and the driver. If the values do not live there, the driver cannot send them to rtmd. `crates/sm-driver/src/driver.rs:21-28` `crates/sm-daemon/src/handler.rs:606-641`

Keep agent config as env merge only. The ordering remains request env, then agent config env, then forced `HELIOY_SESSION_*` values. `crates/sm-daemon/src/handler.rs:611-630` `crates/sm-daemon/src/handler.rs:658-670`

Update daemon tests and helpers without duplicating large request literals. If more than two tests in one file need the same field additions, factor a local fixture helper rather than copying two new fields everywhere. Existing tests already cover agent config env and caller env handoff; add or extend one daemon test to assert Docker isolation and image reach the fake spawn driver. `crates/sm-daemon/tests/handler.rs:94-149` `crates/sm-daemon/tests/handler.rs:152-197` `crates/sm-daemon/tests/common/mod.rs:259-270`

**Acceptance test**

- A daemon test named along the lines of `isolation_and_image_reach_spawn_driver` passes.
- That test sends a `SpawnRequest` with Docker isolation and `runtime-matters-claude:local`, then asserts the captured `SpawnLaunch` has the same isolation and image.
- Existing `agent_config_env_reaches_spawn_driver` still passes. `crates/sm-daemon/tests/handler.rs:94-149`
- Existing caller env, shell resume, and force assertions still pass. `crates/sm-daemon/tests/handler.rs:152-197`

### Step 5. Forward isolation and image in the rtmd driver

**Files and line ranges**

- `crates/sm-driver/src/rtmd.rs:48-80`
- `crates/sm-driver/tests/rtmd_spawn.rs:23-72`
- `../runtime-matters/crates/rtm-core/src/types/spawn.rs:76-92`
- `../runtime-matters/crates/rtm-daemon/src/spawn_preflight.rs:69-101`
- `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:48-64`

**What and why**

Set `isolation: launch.isolation.clone()` and `image: launch.image.clone()` when `RtmdDriver::spawn` builds the runtime-matters `SpawnRequest`. This is the final missing hop. Current code forwards runtime, env, cwd, target, force, and shell resume, but cannot forward isolation or image because `SpawnLaunch` does not carry them and the struct literal does not set them. `crates/sm-driver/src/rtmd.rs:48-80` `crates/sm-driver/src/driver.rs:21-28`

Do not duplicate runtime-matters validation in session-matters. Runtime-matters owns Docker profile acceptance and Docker argv construction. `../runtime-matters/crates/rtm-daemon/src/spawn_preflight.rs:69-101` `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:48-64`

**Acceptance test**

- Extend `rtmd_spawn_forwards_env_shell_resume_and_force` or add a sibling test so the fake rtmd server asserts `request.isolation` is Docker and `request.image` is `Some("runtime-matters-claude:local")`. `crates/sm-driver/tests/rtmd_spawn.rs:23-72`
- `cargo test -p sm-driver rtmd_spawn_forwards` passes.
- The test also keeps the existing env, shell resume, and force assertions. `crates/sm-driver/tests/rtmd_spawn.rs:46-49`

### Step 6. Prove the exact user path, then run the repo gate

**Files and line ranges**

- `README.md:7-29`
- `justfile:11-13`
- `justfile:43-44`
- `justfile:59-74`
- `tools/run.toml:22-25`
- `tools/run.toml:67-141`

**What and why**

After the unit and generated surface tests pass, run the real command path. Start `rtmd` and `smd` as documented, ensure the Docker image and `auth-passthrough` agent config exist, then run the exact command from this plan level acceptance section. `README.md:7-29`

Use the repo gates before declaring done. The justfile defines build, test, formatting, clippy, and LOC checks. `justfile:11-13` `justfile:43-44` `justfile:59-74`

**Acceptance test**

- `fmm validate` reports the index is current.
- `just check && just build && just test` passes.
- The exact command reaches a Claude TUI in tmux pane `3:1.1`:

```bash
sm run claude --target tmux:3:1.1 --role pm --label app=nginx \
  --isolation docker --image runtime-matters-claude:local \
  --agent-config auth-passthrough
```

- `sm get session id:<uuid> --show-labels` shows a running Claude session with label `app=nginx`. The session record does not need to persist `isolation` or `image` for this plan. The runtime driver test proves those fields crossed to rtmd.

## Cross-plan dependency on `agent-config-plan`

This plan stands independently. Step 4 of `agent-config-plan` adds a typed `AgentConfigToml` schema for the existing env only keys, and its acceptance test preserves `[env].CLAUDE_CONFIG_DIR` precedence. `~/.mdx/projects/agent-config-plan.md:72-85`

`--isolation` and `--image` should not wait on that step, because this plan does not add new `agent.toml` keys. The command supplies isolation and image explicitly as CLI flags. `--agent-config auth-passthrough` only needs the existing env path, which current code already implements. `crates/sm-daemon/src/agent_config.rs:73-96` `crates/sm-daemon/src/handler.rs:606-641`

If Step 4 lands first, this plan uses the typed parser as found. If Step 4 has not landed, this plan must not absorb it. Keep the two changes separate so the Docker launch path is easy to review.

## Acceptance signal at the plan level

The user's exact command works:

```bash
sm run claude --target tmux:3:1.1 --role pm --label app=nginx \
  --isolation docker --image runtime-matters-claude:local \
  --agent-config auth-passthrough
```

Expected result: `sm run` no longer rejects `--isolation`; `smd` forwards Docker isolation and `runtime-matters-claude:local` to `rtmd`; runtime-matters starts the Docker backed Claude process; tmux pane `3:1.1` reaches the Claude TUI; the session label `app=nginx` is present. Existing agent config env is applied before runtime launch. `crates/sm-cli/src/cli/run.rs:36-55` `crates/sm-daemon/src/handler.rs:606-641` `crates/sm-driver/src/rtmd.rs:48-80`

If the command fails because the Docker image is missing, `auth-passthrough` is absent, or credentials are invalid, that is not a successful acceptance run. Fix or provision that environment, then rerun. Do not replace this with a host isolation smoke.

## Non-goals and known follow-ups

- Mount support for Docker spawns. The current rtm Docker path only binds cwd to the same path in the container. `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:66-83`
- Credential bridge work for interactive Claude auth. Env passthrough works for explicit env, but interactive TUI auth may need mounted config or a separate login path. `~/.mdx/projects/auth-token-debug--codex.md:151-186` `~/.mdx/projects/auth-token-debug--claude.md:384-390`
- Agent config schema expansion for runtime defaults. `~/.mdx/projects/agent-config-plan.md:122-127`
- Persisting `isolation` and `image` on `Session`. Current records do not include those fields. `crates/sm-core/src/session.rs:66-88` `crates/sm-store/src/schema.rs:1-20`
- Removing the deprecated MCP `workspace` alias. That belongs to the existing agent config plan. `~/.mdx/projects/agent-config-plan.md:87-97`
