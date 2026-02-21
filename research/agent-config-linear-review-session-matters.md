---
title: Agent Config Linear Review Findings for session-matters
type: research
tags: [session-matters, linear-review, agent-config, moe-review, mcp-schema, cli]
summary: Round 1 MoE review of ALP-2763 reached clean sign-off after live Linear verification of three applied fixes.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

`session-matters` is the Helioy session control plane. This review audited the live Linear tree for `ALP-2763`, "Make `sm run --agent-config` honest and debuggable", against the `linear-workflows` MoE issue review rules and live source in `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`.

Round 1 reached peer consensus on three substantive execution or review defects: the post execution review does not mirror worker acceptance bullet for bullet, ALP-2769 runs `cargo insta accept` before tests produce new snapshots, and ALP-2770 verifies a stale `sm` binary while only grepping for flag existence.

## Project Metadata

- Language: Rust, workspace edition 2024.
- Build system: Cargo workspace with Just recipes.
- Workspace crates: `sm-core`, `sm-daemon`, `sm-cli`, `sm-store`, `sm-driver`, `sm-paths`.
- Key dependencies: `clap`, `tokio`, `serde`, `serde_json`, `toml`, `rusqlite`, `uuid`, `insta`, `lilo-rm-core`, `lilo-rm-client`.
- fmm status: `.fmm.db` present and `fmm validate` reported all 104 indexed files up to date. The fmm MCP transport closed on first call, so the review used the local `fmm` CLI for structural navigation.

## Architecture

The reviewed plan touches the `sm run --agent-config` flow across three layers:

1. CLI request creation in `crates/sm-cli/src/cli/run.rs`, where `spawn_session` builds `SpawnRequest` and currently forwards `args.agent_config` verbatim at lines 36 to 47.
2. Daemon resolution and persistence in `crates/sm-daemon/src/agent_config.rs` and `crates/sm-daemon/src/handler.rs`. `resolve_agent_config_with_home` maps bare names to `$HOME/.agm/<name>/agent.toml`, reports missing files with the resolved lookup path, and returns `ResolvedAgentConfig.path` at lines 26 to 47. `DaemonState::spawn` currently persists `request.agent_config` at line 176, not the resolved path.
3. Generated public tool surfaces from `tools/run.toml` through `crates/sm-cli/build.rs`. `write_schema_outputs` emits generated MCP schema files at lines 184 to 199. `write_docs_outputs` emits CLI help, templates, and README content at lines 201 to 224. `generate_mcp_schema` iterates every registered tool, including aliases, at lines 227 to 254.

The MCP handler currently accepts deprecated `workspace` fallback in `agent_run` by reading `dir` or `workspace` at `crates/sm-daemon/src/mcp_tools.rs:123-125`.

## Key Patterns

- `tools/run.toml` is the source of truth for public `session_run` and `agent_run` MCP schema, CLI help, templates, and README generated surfaces.
- `agent_run` is generated from the `session_run` alias declaration in `tools/run.toml:139-141`, so one source edit plus regeneration should update both JSON schemas and both snapshots.
- Current agent config parsing preserves `[env]` precedence by inserting top level `claude_config_dir` first, then `[env]` entries afterward in `crates/sm-daemon/src/agent_config.rs:73-96`.

## Detailed Findings

### 1. ALP-2772 PER mirroring defect

`ALP-2772` currently uses generic review criteria: match worker acceptance, stay in scope, run verification commands, preserve cross step expectations, and avoid regressions. The MoE workflow requires the post execution review body to mirror each worker acceptance bullet for bullet, so the reviewer can falsify the review outcome from the PER body alone.

Impact: a reviewer must chase seven worker bodies to know what to check. This weakens the review gate and risks closing `ALP-2763` without replaying specific acceptance signals.

Required change: rewrite ALP-2772 `Review criteria` into per worker subsections for `ALP-2765` through `ALP-2771`, copying each worker Acceptance bullet verbatim. Retain the current cross cutting checks as an additional section if useful.

### 2. ALP-2769 snapshot verification order is wrong

`ALP-2769` verification currently runs:

```bash
cargo insta accept
cargo test -p sm-cli
cargo test -p sm-daemon
```

This order is unsafe. On a clean branch, `cargo insta accept` has no `.snap.new` files to accept. The subsequent `cargo test -p sm-cli` is the step that produces new snapshots for `session_run` and `agent_run`.

Impact: a worker following the instructions literally can hit failing snapshots after the accept step and lose the atomic schema regeneration guarantee.

Required change:

```bash
cargo test -p sm-cli
cargo insta accept
cargo test -p sm-cli
cargo test -p sm-daemon
```

An equivalent one shot `cargo insta test --accept -p sm-cli` can work if the issue also asks for a confirming re run.

Evidence:

- `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@session_run.snap` exists.
- `crates/sm-cli/tests/snapshots/mcp_schema_snapshot_test__mcp_tool@agent_run.snap` exists.
- Current generated schemas contain `workspace` and only require `runtime` plus `role`, matching the intended snapshot delta.

### 3. ALP-2770 help verification uses stale binary and weak assertion

`ALP-2770` verification currently runs:

```bash
cargo test -p sm-cli
sm run --help | grep -A1 -- '--agent-config'
```

On this host, `sm` resolves to `/Users/alphab/.cargo/bin/sm`, an installed binary. That command may not run the just built worktree binary. It also greps only for flag existence, so it can pass with the old help text and fail to verify the accepted `~/.agm/<name>/agent.toml`, `claude_config_dir`, and `[env]` text.

Impact: the manual smoke can pass against stale code and does not assert the acceptance text. This changes verification behaviour, not just wording.

Required change:

```bash
cargo test -p sm-cli
cargo run -p sm-cli --bin sm -- run --help | grep -F '~/.agm/<name>/agent.toml'
cargo run -p sm-cli --bin sm -- run --help | grep -F 'claude_config_dir'
cargo run -p sm-cli --bin sm -- run --help | grep -F '[env]'
```

Alternative: remove the manual smoke and rely on the updated `crates/sm-cli/tests/cli_help_surface_test.rs` assertion. The current test checks the old text at lines 41 to 59.

### 4. Probes with no additional substantive findings

- Worker self sufficiency: the four gate design resolutions are restated in the bound workers. Persistence shape maps to `ALP-2765`, predicate location maps to `ALP-2766` and `ALP-2767`, schema strictness maps to `ALP-2768`, and MCP workspace alias maps to `ALP-2769`.
- `deny_unknown_fields` field inventory: no unsupported top level keys were found. The only live host config found was `~/.agm/auth-passthrough/agent.toml`, using `claude_config_dir` and `[env]`. Repo inline fixtures use the same supported keys.
- Verification command package names: `cargo metadata` confirms `sm-core`, `sm-daemon`, `sm-cli`, and `sm-store` package names exist.
- Schema regeneration atomicity: source topology is sound. `tools/run.toml` drives both `session_run` and the `agent_run` alias; `build.rs` emits all schema files from the registry.

## Dependencies

- `toml` and `serde` provide the typed config parsing path proposed by `ALP-2768`.
- `insta` owns the MCP schema snapshot workflow for `session_run` and `agent_run`.
- `clap` plus generated constants from `tools/run.toml` own CLI help rendering.
- `lilo-rm-core` and `lilo-rm-client` remain runtime boundary dependencies. The reviewed plan does not add a runtime-matters `agent_config` concept.

## Relevance to Helioy

This tree is a control plane correctness change. The reviewed fixes protect Helioy agent launch ergonomics by making agent config resolution observable, ensuring MCP schema truth, and preventing review gates from closing on generic acceptance claims.

The recurring lesson is generated surface discipline: source TOML, generated schema, CLI help, README, and snapshots must move together, and verification must run the current worktree binary or a repo native test.

## Consensus State

Pane A accepted Pane B's severity upgrade on ALP-2770. Both panes signed off conditional on the same three changes:

1. ALP-2772 Review criteria mirrors ALP-2765 through ALP-2771 Acceptance bullets in per-worker subsections.
2. ALP-2769 Verification runs sm-cli tests before `cargo insta accept`, then re-runs sm-cli tests and sm-daemon tests.
3. ALP-2770 Verification uses the current worktree binary and asserts `~/.agm/<name>/agent.toml`, `claude_config_dir`, and `[env]` in help output.

## Final Sign-off

After the orchestrator applied the three consensus edits, Pane B re-read live Linear for `ALP-2769`, `ALP-2770`, `ALP-2772`, and the worker acceptance references. The three edits landed as agreed. Pane B sent final bus sign-off to Pane A and CC'd the orchestrator:

`I sign off on ALP-2763 as currently filed`

## Open Questions

None for this review pass. The next action belongs to the orchestrator or execution selector.
