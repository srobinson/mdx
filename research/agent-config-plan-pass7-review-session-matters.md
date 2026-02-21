---
title: ALP-2763 agent config plan pass 7 review
type: research
tags: [session-matters, linear, moe-review, agent-config, mcp]
summary: Pass 7 found three conditional amendments, verified the orchestrator edits, and signed off on ALP-2763 as currently filed.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

A live pass 7 review of Linear master `ALP-2763` found three substantive issues before execution: `ALP-2767` title understates MCP scope, `ALP-2766` acceptance misses the separator only relative path branch, and the source plan at `~/.mdx/projects/agent-config-plan.md` has drifted from live Linear. Test parallel safety and PER mirror integrity both checked clean.

## Project Metadata

- Language: Rust workspace, edition 2024.
- Indexed with fmm: `.fmm.db` present. `fmm validate` reported all 104 indexed files current.
- Size: 104 indexed files, 16,543 LOC.
- Relevant crates: `sm-cli`, `sm-daemon`, `sm-core`, `sm-store`.
- Build system: Cargo workspace in `Cargo.toml`, with workspace dependencies including `serde`, `serde_json`, `toml`, `tokio`, `rusqlite`, `uuid`, `assert_cmd`, `insta`, and `tempfile`.
- Linear artifact: master `ALP-2763`, execution parent `ALP-2764`, workers `ALP-2765` through `ALP-2771`, PER `ALP-2772`, gate `ALP-2773` in `Worker Done`.
- Source plan: `~/.mdx/projects/agent-config-plan.md`.

## Architecture

- CLI spawn requests are built in `crates/sm-cli/src/cli/run.rs::spawn_session`. Current source sends `args.agent_config` directly into `SpawnRequest.agent_config` at `crates/sm-cli/src/cli/run.rs:36-47`.
- MCP `session_run` and `agent_run` share the daemon handler in `crates/sm-daemon/src/mcp_tools.rs::agent_run`. Current source accepts `dir` or fallback `workspace` at `crates/sm-daemon/src/mcp_tools.rs:121-126`, reads `agent_config` at lines 131-148, and sends it into `SpawnRequest`.
- Daemon config resolution lives in `crates/sm-daemon/src/agent_config.rs`. Current `is_path_like` uses `MAIN_SEPARATOR`, `~`, `.`, and `.toml` suffix at lines 56-61. `resolve_agent_config_with_home` resolves the file, validates existence, reads TOML, and returns `ResolvedAgentConfig.path` plus env at lines 26-47.
- Public tool surfaces are source generated from `tools/run.toml`. The file states that `crates/sm-cli/build.rs` generates MCP schema, CLI help constants, the Claude Code skill, and README documentation at `tools/run.toml:1-3`.

## Key Patterns

- Linear is the authoritative execution substrate. Source plans can become historical input once Linear receives pass edits; if PER text still says it reviews against the source plan, plan drift becomes an execution time ambiguity.
- Predicate acceptance should isolate each branch. `./x`, `/x`, and `~/x` do not prove the generic `contains MAIN_SEPARATOR` branch because each also hits another visible path cue.
- The current test harness is parallel safe when tests use per process `Command.env`. Global environment mutation remains risky unless guarded by an existing lock.

## Detailed Findings

### 1. ALP-2767 title hides MCP scope

Live `ALP-2767` is titled `Canonicalize relative --agent-config paths CLI-side against caller cwd`, but its body and Acceptance now cover both CLI and MCP entry points. The worker asks CLI `spawn_session` to canonicalize against caller CWD and MCP `agent_run` or `session_run` to canonicalize against the request `dir` field.

This matters because titles are the selector and human queue summary. A worker title that says CLI only understates half of the accepted scope and can cause an executor to miss MCP tests.

Recommended edit:

> Rename `ALP-2767` to `Canonicalize path-like --agent-config inputs at CLI and MCP entry points`.

Evidence:

- CLI entry point: `crates/sm-cli/src/cli/run.rs::spawn_session`, `crates/sm-cli/src/cli/run.rs:20-71`.
- MCP entry point: `crates/sm-daemon/src/mcp_tools.rs::agent_run`, `crates/sm-daemon/src/mcp_tools.rs:116-164`.
- Current CLI source passes `args.agent_config` directly at `crates/sm-cli/src/cli/run.rs:36-47`.
- Current MCP source reads `agent_config` and passes it into `SpawnRequest` at `crates/sm-daemon/src/mcp_tools.rs:131-148`.

### 2. ALP-2766 acceptance does not isolate the separator branch

`ALP-2766` says the predicate should classify path mode when a value contains `MAIN_SEPARATOR`, starts with `~`, or starts with `.`. Its current Acceptance covers `tools.toml`, `./tools.toml`, `/abs/x.toml`, `~/x.toml`, and bare `demo`. Those cases do not isolate a relative path that contains a separator without also starting with `.`, `/`, or `~`.

A worker could implement only leading dot, absolute path, and tilde checks, pass the listed cases, and still fail `configs/tools.toml`. `ALP-2767` depends on that branch for CLI and MCP canonicalization of relative subdirectory paths.

Recommended edit:

> Add Acceptance and verification coverage: `configs/tools.toml` resolves as a path.

Optional secondary coverage:

> `../tools.toml` resolves as a path.

This optional case is useful, but it starts with `.`, so it does not prove the separator branch by itself.

Evidence:

- Current predicate includes the separator branch at `crates/sm-daemon/src/agent_config.rs:56-61`.
- Current resolver delegates path versus name classification through `agent_config_path` at `crates/sm-daemon/src/agent_config.rs:49-54`.
- Source plan describes the future predicate as “contains `MAIN_SEPARATOR`, starts with `~`, or starts with `.`” at `~/.mdx/projects/agent-config-plan.md:50-58`.

### 3. Source plan currency has drifted from live Linear

`~/.mdx/projects/agent-config-plan.md` still reads like the pre filing consensus document, while live Linear now carries six passes of amendments. The drift is substantive because `ALP-2772` says post execution review confirms the worker signals against the source plan. A stale source plan can make accepted Linear scope look like a deviation during PER.

Specific stale surfaces:

- Plan status still says `awaiting clean re-sign-off` at `~/.mdx/projects/agent-config-plan.md:6`.
- Scope lists Step 3 as `CLI-side path canonicalization`, not CLI plus MCP, at `~/.mdx/projects/agent-config-plan.md:16-24`.
- Step 3 only describes CLI `spawn_session`; no MCP `agent_run` or `session_run` canonicalization appears at `~/.mdx/projects/agent-config-plan.md:62-70`.
- Step 4 describes typed deserialization but does not mention the direct `serde` dependency now required by `ALP-2768`; see `~/.mdx/projects/agent-config-plan.md:72-85`.
- Step 5 mentions generated schemas and snapshots, but not the full build.rs generated output lockstep now encoded in `ALP-2769`; see `~/.mdx/projects/agent-config-plan.md:87-97`.
- Step 6 does mention generated help, templates, and README, but only for CLI help parity; it does not clarify the lockstep rule now repeated across `ALP-2769` and `ALP-2770`; see `~/.mdx/projects/agent-config-plan.md:98-106`.

Recommended resolution:

1. Preferred: update `~/.mdx/projects/agent-config-plan.md` so it reflects the live Linear tree.
2. Acceptable alternative: amend Linear references to say the plan is historical input, and live Linear issue bodies are authoritative for execution and PER.

### 4. No issue: test parallel safety

No new parallel safety defect was found for the pass 5 and pass 6 MCP path tests. The existing `DaemonFixture` isolates daemon state per test:

- Per test tempdir, `RTM_SOCKET_PATH`, `RTM_DB_PATH`, `RTM_HOME`, daemon `SM_HOME`, daemon `HOME`, and PATH are set in child process env at `crates/sm-cli/tests/common/mod.rs:27-65`.
- `spawn_mcp` creates a separate MCP child process per fixture at `crates/sm-cli/tests/common/mod.rs:67-75`.
- CLI commands inherit fixture scoped `SM_HOME` and `HOME` via `DaemonFixture::command` at `crates/sm-cli/tests/common/mod.rs:100-106`.
- Fixture shutdown stops smd and rtmd per fixture at `crates/sm-cli/tests/common/mod.rs:118-134`.
- The MCP request helper uses one stdin/stdout pair on one fixture owned child at `crates/sm-cli/tests/common/mod.rs:158-171`.

The caller-HOME tilde test can be implemented with `Command.env("HOME", caller_home)` on the child command. That avoids global process environment mutation and should remain safe under Cargo's parallel test runner.

### 5. No issue: PER mirror integrity

Live `ALP-2772` mirrors the current Acceptance bullets for `ALP-2765` through `ALP-2771`, including the post pass MCP bullets in `ALP-2767`, the direct `serde` dependency bullet in `ALP-2768`, and the generated output lockstep bullets in `ALP-2769` and `ALP-2770`.

The only related title drift is the `ALP-2767` heading. The mirrored Acceptance surface itself is intact.

## Dependencies

Critical dependencies for this review:

- Linear MCP for live issue state and comments.
- helioy-bus for peer consensus coordination.
- fmm MCP for file topology, symbol outlines, symbol reads, and dependency graphs.
- Local `fmm validate` for index freshness.

## Relevance to Helioy

These findings prevent a Nancy execution worker from losing MCP scope due to a stale title, under testing the shared predicate branch that MCP and CLI canonicalization rely on, or relitigating plan drift during post execution review. The fixes keep Linear, plan docs, and generated surface responsibilities aligned before execution begins.

## Bus Outcome

Round 1 conditional sign-off was sent to Pane A and CCed to the orchestrator on topic `agent-config-plan-review-pass7`.

Sign-off phrase sent:

> I sign off conditional on the following changes:

The three requested changes were the `ALP-2767` title update, the `ALP-2766` separator only relative path case, and source plan currency resolution.

After the orchestrator applied the edits, live Linear was re-read for `ALP-2766`, `ALP-2767`, `ALP-2772`, `ALP-2763`, and `ALP-2773`, and the plan doc was re-read from disk.

Verified:

- `ALP-2767` title is now `Canonicalize path-like --agent-config inputs at CLI and MCP entry points`.
- `ALP-2766` Acceptance includes `configs/tools.toml` as the separator-only predicate case and Verification says six cases.
- `ALP-2772` mirrors the new `ALP-2766` bullet exactly and states live Linear is authoritative over the source plan snapshot.
- `~/.mdx/projects/agent-config-plan.md` opens with the 2026-05-22 planning snapshot and Linear-authoritative header.

Final sign-off emitted to Pane A and CCed to the orchestrator:

> I sign off on ALP-2763 as currently filed

## Open Questions

- None from Pane B. Orchestrator owns pass persistence and next-pass or stop decision.
