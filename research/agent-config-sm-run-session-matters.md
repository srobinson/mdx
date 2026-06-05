---
title: sm run agent config implementation in session-matters
type: research
tags: [session-matters, sm-run, agent-config, rtmd, runtime-matters]
summary: '`sm run --agent-config` resolves named or explicit TOML files in smd and currently affects runtime launch only through environment variables.'
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

`sm run --agent-config` is wired end to end for named configs and absolute explicit paths, but its runtime effect is currently limited to environment injection. The detailed deliverable for the MoE brief is `~/.mdx/projects/agent-config-analysis--codex.md`, with smoke evidence in `~/.mdx/projects/agent-config-analysis--smoke.log` and focused test evidence in `~/.mdx/projects/agent-config-analysis--tests.log`.

## Project Metadata

- Rust workspace, edition 2024, Cargo resolver 3. `Cargo.toml:1-15`
- Workspace crates are `sm-paths`, `sm-core`, `sm-store`, `sm-driver`, `sm-daemon`, and `sm-cli`. `Cargo.toml:1-10`
- Relevant dependencies include clap, tokio, serde, rusqlite, toml, uuid, `lilo-rm-client`, and `lilo-rm-core`. `Cargo.toml:26-40`
- `smd` connects to `rtmd` through `RTM_SOCKET_PATH`, `$XDG_RUNTIME_DIR/rtm/sock`, or `~/.rtm/sock`, and probes protocol before serving. `crates/sm-paths/src/lib.rs:98-103`, `crates/sm-daemon/src/server.rs:18-30`, `crates/sm-daemon/src/server.rs:126-149`

## Architecture

- The CLI surface parses `--agent-config <AGENT_CONFIG>` as `Option<String>` inside `SessionCreateArgs`. `crates/sm-cli/src/cli/cli_def.rs:94-107`
- `sm run` sends the raw value into `sm_core::SpawnRequest.agent_config`; the CLI does not resolve or validate the config path. `crates/sm-cli/src/cli/run.rs:36-47`, `crates/sm-core/src/proto.rs:17-38`
- `smd` resolves the config during spawn, before target validation and driver spawn. `crates/sm-daemon/src/handler.rs:137-161`
- Named configs resolve to daemon `$HOME/.agm/<name>/agent.toml`; path like values are used as paths with only `~` expansion. `crates/sm-daemon/src/agent_config.rs:20-24`, `crates/sm-daemon/src/agent_config.rs:49-71`
- The parsed TOML contributes env only: top level `claude_config_dir` becomes `CLAUDE_CONFIG_DIR`, and `[env]` contributes string key value pairs. `crates/sm-daemon/src/agent_config.rs:73-96`
- The daemon merges config env into `SpawnLaunch.env`, strips stale `HELIOY_SESSION_*`, and upserts session identity env. `crates/sm-daemon/src/handler.rs:606-641`, `crates/sm-daemon/src/handler.rs:658-670`
- The `rtmd` hop carries env through `lilo_rm_core::SpawnRequest`; no `agent_config` field crosses into runtime-matters. `crates/sm-driver/src/rtmd.rs:48-80`, `../runtime-matters/crates/rtm-core/src/types/spawn.rs:77-92`

## Key Patterns

- Generated surfaces come from `tools/*.toml`, then `crates/sm-cli/build.rs` emits MCP schema, README, skill docs, and CLI help constants. `tools/run.toml:1-3`, `crates/sm-cli/build.rs:19-40`
- Session rows persist the original `agent_config` request string, not the resolved path. `crates/sm-daemon/src/handler.rs:163-177`, `crates/sm-store/src/sqlite/sessions.rs:31-55`
- Runtime launchers in runtime-matters apply env uniformly for Claude and Codex through `runtime_env`. `../runtime-matters/crates/rtm-launchers/src/claude.rs:14-20`, `../runtime-matters/crates/rtm-launchers/src/codex.rs:14-20`, `../runtime-matters/crates/rtm-launchers/src/lib.rs:55-74`

## Detailed Findings

- Named mode works today. The smoke run used `--agent-config demo`, received `CLAUDE_CONFIG_DIR` and custom env in the runtime, and persisted `agent_config: "demo"`. `~/.mdx/projects/agent-config-analysis--smoke.log:1-20`
- Explicit absolute path mode works today. The smoke run used `--agent-config /var/.../explicit-agent.toml`, received the explicit env values, and persisted the path string. `~/.mdx/projects/agent-config-analysis--smoke.log:21-40`
- Focused tests passed for named resolution, explicit path resolution, missing config errors, daemon env merge, and rtmd env forwarding. `~/.mdx/projects/agent-config-analysis--tests.log:1-8`, `~/.mdx/projects/agent-config-analysis--tests.log:21-24`, `~/.mdx/projects/agent-config-analysis--tests.log:41-56`
- Main current gaps: relative explicit paths resolve in daemon context, named lookup depends on daemon `HOME`, resolved path is not persisted, MCP schema omits the handler required `dir`, and `RunArgs.detach` is parsed but unused. `crates/sm-daemon/src/agent_config.rs:56-71`, `crates/sm-daemon/src/agent_config.rs:16-24`, `crates/sm-daemon/src/handler.rs:163-177`, `crates/sm-cli/src/mcp/generated_schema/session_run.json:50-54`, `crates/sm-daemon/src/mcp_tools.rs:121-126`, `crates/sm-cli/src/cli/cli_def.rs:85-89`, `crates/sm-cli/src/cli/run.rs:12-14`

## Dependencies

- `lilo-rm-client` and `lilo-rm-core` provide the rtmd client and runtime wire types. `Cargo.toml:31-32`, `crates/sm-driver/src/rtmd.rs:48-80`
- `toml` parses `agent.toml`. `Cargo.toml:39`, `crates/sm-daemon/src/agent_config.rs:35-40`
- `rusqlite` persists the session record, including `agent_config TEXT`. `Cargo.toml:34`, `crates/sm-store/src/schema.rs:1-20`

## Relevance to Helioy

This path is usable now for Helioy agent specialization through environment variables, including `CLAUDE_CONFIG_DIR` and arbitrary env keys. It is not yet a typed agent profile system for models, instructions, skills, or runtime args. `crates/sm-daemon/src/agent_config.rs:73-96`, `../runtime-matters/crates/rtm-launchers/src/claude.rs:14-20`, `../runtime-matters/crates/rtm-launchers/src/codex.rs:14-20`

## Open Questions

- Should named config roots stay at daemon `$HOME/.agm`, or move under `SM_HOME` or a dedicated env override. `crates/sm-daemon/src/agent_config.rs:16-24`, `crates/sm-daemon/src/agent_config.rs:49-54`
- Should Codex get a first class config field, or should all runtime specific behavior remain under `[env]`. `crates/sm-daemon/src/agent_config.rs:73-96`, `../runtime-matters/crates/rtm-launchers/src/codex.rs:14-20`
- Should `Session` persist both requested and resolved config identity for auditability. `crates/sm-daemon/src/agent_config.rs:10-14`, `crates/sm-daemon/src/handler.rs:163-177`
