---
title: sm isolation and image plumbing plan for session-matters
type: research
tags: [session-matters, sm-cli, smd, runtime-matters, docker, isolation, planning]
summary: session-matters needs only sm-side plumbing to expose Docker isolation and image selection, then forward both fields to rtmd.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

`sm run` currently rejects `--isolation` before any daemon or runtime work begins, while runtime-matters already has `isolation` and `image` on its spawn wire. The plan at `~/.mdx/projects/sm-isolation-plan--codex.md` adds the missing session-matters path: CLI and MCP input, `sm_core::SpawnRequest`, daemon `SpawnLaunch`, and `RtmdDriver` forwarding.

## Project Metadata

- Language: Rust workspace, edition 2024, Cargo resolver 3. `Cargo.toml:1-15`
- Crates: `sm-paths`, `sm-core`, `sm-store`, `sm-driver`, `sm-daemon`, `sm-cli`. `Cargo.toml:3-10`
- Key dependencies: `clap`, `tokio`, `serde`, `rusqlite`, `toml`, `uuid`, `lilo-rm-client`, `lilo-rm-core`. `Cargo.toml:26-40`
- Current runtime wire dependency is locked to `lilo-rm-client` and `lilo-rm-core` `0.6.1`. `Cargo.lock:708-723`
- fmm signal: `.fmm.db` is present and `fmm validate` reported all 104 indexed files current. Initial structural orientation used fmm file lists and outlines. The fmm MCP transport later closed, so follow-up line verification used targeted local reads.

## Architecture

session-matters keeps process ownership outside its boundary. `sm` builds an `sm_core::SpawnRequest`; `smd` normalizes and authorizes it; `SpawnLaunch` carries launch data to the driver; `RtmdDriver` sends a runtime-matters `SpawnRequest` over the rtmd socket. `AGENTS.md:3-12` `crates/sm-cli/src/cli/run.rs:36-55` `crates/sm-daemon/src/handler.rs:132-161` `crates/sm-driver/src/rtmd.rs:48-80`

The current internal request has runtime, role, workspace, dir, namespace, target, agent config, env, shell resume, labels, and force, but no isolation or image. `crates/sm-core/src/proto.rs:16-38`

The current driver launch object has runtime, cwd, target, env, shell resume, and force, but no isolation or image. `crates/sm-driver/src/driver.rs:21-28`

runtime-matters currently has the desired fields on its spawn type. `../runtime-matters/crates/rtm-core/src/types/spawn.rs:76-92`

## Key Patterns

- Public run tool docs are generated from `tools/run.toml`; generated Rust, MCP schema, skill, and README surfaces should not be edited directly. `tools/run.toml:1-3` `crates/sm-cli/build.rs:19-39` `crates/sm-cli/build.rs:201-224`
- `agent_run` is a generated alias of `session_run`, so schema changes must update both snapshots. `tools/run.toml:139-141` `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@session_run.snap:5-60` `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@agent_run.snap:5-60`
- `--agent-config` currently produces env only. The isolation plan should not add new `agent.toml` keys or absorb the typed `AgentConfigToml` work. `crates/sm-daemon/src/agent_config.rs:73-96` `~/.mdx/projects/agent-config-plan.md:72-85`

## Detailed Findings

### Missing session-matters fields

`sm run` and MCP `session_run` do not expose isolation or image today. `RunArgs` has target, force, and detach; `SessionCreateArgs` has runtime, role, dir, namespace, labels, and agent config. `crates/sm-cli/src/cli/cli_def.rs:78-107`

The CLI sends `args.agent_config`, env, target, labels, and force to the daemon, but has no place to send isolation or image. `crates/sm-cli/src/cli/run.rs:36-55`

The MCP handler reads runtime, role, dir, namespace, labels, agent config, target, and force, then builds the same missing field request. `crates/sm-daemon/src/mcp_tools.rs:116-154`

### Runtime-matters can already consume the values

runtime-matters parses `host`, `docker`, and `docker:PROFILE`, and stores Docker profile names on `IsolationProfile`. `../runtime-matters/crates/rtm-core/src/isolation.rs:36-64`

Docker profile validation is owned by runtime-matters preflight. session-matters should not duplicate it. `../runtime-matters/crates/rtm-daemon/src/spawn_preflight.rs:69-101`

Docker argv construction already consumes launch env and image in runtime-matters. `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:48-64`

### Planned steps

1. Update `lilo-rm-client` and `lilo-rm-core`, then add `isolation` and `image` to `sm_core::SpawnRequest`. `Cargo.toml:31-32` `Cargo.lock:708-723` `crates/sm-core/src/proto.rs:16-38`
2. Add public contract entries in `tools/run.toml` and regenerate help, schemas, README, skill, and snapshots. `tools/run.toml:67-141` `crates/sm-cli/build.rs:201-288`
3. Add `sm run` flags and MCP parsing. `crates/sm-cli/src/cli/cli_def.rs:78-107` `crates/sm-daemon/src/mcp_tools.rs:116-154`
4. Add fields to `SpawnLaunch` and copy them in `spawn_launch`. `crates/sm-driver/src/driver.rs:21-28` `crates/sm-daemon/src/handler.rs:606-641`
5. Forward the fields in `RtmdDriver::spawn` and assert them in the fake rtmd test. `crates/sm-driver/src/rtmd.rs:48-80` `crates/sm-driver/tests/rtmd_spawn.rs:23-72`
6. Prove the exact Docker command and run `fmm validate`, `just check`, `just build`, and `just test`. `README.md:7-29` `justfile:11-13` `justfile:43-44` `justfile:59-74`

## Dependencies

- `lilo-rm-core` and `lilo-rm-client` must resolve to a release whose spawn request includes `isolation` and `image`. The adjacent runtime source has those fields. `../runtime-matters/crates/rtm-core/src/types/spawn.rs:76-92`
- `clap` parses the new CLI inputs through `RunArgs`. `Cargo.toml:29-29` `crates/sm-cli/src/cli/cli_def.rs:78-90`
- `serde` backs internal JSON round trips and generated MCP schemas. `Cargo.toml:35-36` `crates/sm-core/src/proto.rs:16-38`

## Relevance to Helioy

This unblocks Docker backed Claude sessions through session-matters without changing runtime-matters. It keeps the Kubernetes shaped boundary intact: session-matters records intent and delegates process execution to runtime-matters. `AGENTS.md:10-12`

## Open Questions

- Whether `Session` should later persist `isolation` and `image` for audit. The current plan defers that because command success does not require new session columns. `crates/sm-core/src/session.rs:66-88` `crates/sm-store/src/schema.rs:1-20`
- Whether Docker credential access needs mounts, a token bridge, or container native auth. The current plan does not solve auth. `~/.mdx/projects/auth-token-debug--codex.md:151-186` `~/.mdx/projects/auth-token-debug--claude.md:384-390`
- Whether the existing agent config plan should remove the `workspace` MCP alias first. This plan does not depend on that cleanup. `~/.mdx/projects/agent-config-plan.md:87-97`
## Peer Consensus Review Findings

During `sm-isolation-signoff`, pane B found conditional sign-off issues in the unified plan at `~/.mdx/projects/sm-isolation-plan.md`:

1. Step 6 should not bundle worker integration acceptance with the real operator smoke gate. The smoke belongs at plan-level merge acceptance.
2. Step 6's proposed `DaemonFixture` plus fake runtime cannot record `SpawnLaunch.isolation` or `SpawnLaunch.image`. `DaemonFixture` starts real `rtmd` and `smd`; the fake runtime is just an executable process. The fake driver that records `SpawnLaunch` exists in daemon test helpers. `crates/sm-cli/tests/common/mod.rs:27-65` `crates/sm-cli/tests/common/mod.rs:207-228` `crates/sm-daemon/tests/common/mod.rs:30-68`
3. Steps 3 and 4 have an ordering cycle. CLI fields should use generated help constants, but the constants are generated from `tools/run.toml` in Step 4 while Step 4 depends on Step 3. These should be merged or filed atomically. `crates/sm-cli/src/cli/cli_def.rs:81-84` `crates/sm-cli/build.rs:256-288` `crates/sm-cli/tests/generated_surface_guard_test.rs:103-114`
4. The smoke gate should not claim filesystem `~/.claude` access through `agent.toml` while mount support is out of scope. Current rtm Docker mounts only cwd. `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:80-83`
## Peer Consensus Round 1 Outcome

Pane A and pane B converged on a combined conditional sign-off for `~/.mdx/projects/sm-isolation-plan.md`:

1. Split Step 6 worker acceptance from the real smoke gate. Step 6 keeps worker-reproducible tests; the real Docker TUI smoke moves to plan-level merge acceptance.
2. Rewrite Step 6 so it does not claim CLI `DaemonFixture` plus fake runtime can observe `SpawnLaunch`. Field-forwarding proof belongs in daemon fake-driver and rtmd fake-server tests.
3. Merge or atomically file the public-surface work that touches `tools/run.toml`, generated help constants, and clap consumers, because non-atomic ordering breaks generated-surface tests.
4. Make plan-level smoke acceptance prove env-key delivery only. Do not imply container filesystem access to host `~/.claude` while mount support is out of scope.

## Final Signoff Review

The revised `~/.mdx/projects/sm-isolation-plan.md` applied the major consensus changes: Step 5 is now a CLI surface regression only, the real Docker smoke is a plan-level merge gate, public-surface work is atomic, and the merge gate proves env-key delivery only. `~/.mdx/projects/sm-isolation-plan.md:142-156` `~/.mdx/projects/sm-isolation-plan.md:172-192` `~/.mdx/projects/sm-isolation-plan.md:83-127`

Final signoff was initially withheld for one remaining Step 4 issue. The plan still said an MCP-level test using `DaemonFixture` should observe a daemon-internal fake `SpawnDriver`. `DaemonFixture` starts real `rtmd` and `smd`, and its fake runtime is only a PATH shell script, so it cannot inspect `SpawnLaunch`. The fake `SpawnDriver` that records launches lives in daemon test helpers, and `mcp_tools::call_tool` is a direct daemon-level handler entrypoint suitable for this test. `crates/sm-cli/tests/common/mod.rs:27-65` `crates/sm-cli/tests/common/mod.rs:207-228` `crates/sm-daemon/tests/common/mod.rs:30-68` `crates/sm-daemon/src/mcp_tools.rs:16-41`

After the final revision, Step 4 explicitly disclaims `DaemonFixture`, points at the daemon fake `SpawnDriver`, and instructs direct `mcp_tools::call_tool` invocation. `fmm validate` passed with all 104 indexed files current. Pane B sent the clean signoff: `I sign off on sm-isolation-plan as currently filed`. `~/.mdx/projects/sm-isolation-plan.md:128-140`
