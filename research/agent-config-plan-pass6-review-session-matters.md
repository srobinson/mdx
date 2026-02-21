---
title: ALP-2763 agent config plan pass 6 review
type: research
tags: [session-matters, linear, moe-review, agent-config, mcp]
summary: Pass 6 found two consensus amendments, verified them in live Linear, and signed off on ALP-2763 as currently filed.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

A fresh live review of Linear master `ALP-2763` and workers `ALP-2765` through `ALP-2772` found one execution blocking test harness defect and one gate wording drift. The worker set is otherwise selector compatible, and the post execution review mirrors worker acceptance bullets exactly.

## Project Metadata

- Language: Rust workspace.
- Indexed with fmm: `.fmm.db` present. `fmm validate` reported all 104 files indexed and current.
- Relevant crates: `sm-cli`, `sm-daemon`, `sm-core`, `sm-store`.
- Source plan: `~/.mdx/projects/agent-config-plan.md`.
- Linear artifact: master `ALP-2763`, execution parent `ALP-2764`, gate `ALP-2773`, PER `ALP-2772`.

## Architecture

- `sm-cli` builds `SpawnRequest` in `crates/sm-cli/src/cli/run.rs::spawn_session` and sends it to `smd` over the daemon socket. Current source passes `args.agent_config` directly into the request at `crates/sm-cli/src/cli/run.rs:36-47`.
- `sm-daemon` accepts MCP `agent_run` and `session_run` through `crates/sm-daemon/src/mcp_tools.rs::agent_run`. Current source accepts `dir` or legacy `workspace`, then passes `agent_config` directly into `SpawnRequest` at `crates/sm-daemon/src/mcp_tools.rs:121-148`.
- The daemon resolves configs in `crates/sm-daemon/src/agent_config.rs::resolve_agent_config_with_home`, which calls `agent_config_path`, checks file existence, parses TOML, and returns `ResolvedAgentConfig.path` plus env at `crates/sm-daemon/src/agent_config.rs:26-47`.
- MCP direct dispatch exists as `crates/sm-daemon/src/mcp_tools.rs::call_tool` at lines 16-41, but `crates/sm-daemon/src/lib.rs:7` declares `mod mcp_tools;`, so integration tests outside the crate cannot access it.

## Key Patterns

- fmm was sufficient for structural validation: topology, symbol outlines, exact symbol reads, and dependency checks.
- The existing daemon integration fixture is `TestDaemon` in `crates/sm-daemon/tests/common/mod.rs:219-237`.
- The existing full MCP protocol test harness is in `sm-cli`: `DaemonFixture::spawn_mcp` at `crates/sm-cli/tests/common/mod.rs:67-75` and test helper `call_tool` at `crates/sm-cli/tests/mcp_protocol_test.rs:469-479`.

## Detailed Findings

### 1. ALP-2767 verification names an unavailable daemon MCP harness

ALP-2767 currently asks for an MCP path test “via `mcp_tools::call_tool` against a daemon level fixture.” The direct function exists, but its module is private from integration tests. `crates/sm-daemon/src/lib.rs:7` declares `mod mcp_tools;`, while `call_tool` is inside `crates/sm-daemon/src/mcp_tools.rs:16-41`. A daemon integration test under `crates/sm-daemon/tests/` cannot import `sm_daemon::mcp_tools::call_tool`.

`TestDaemon` exists and gives access to `DaemonState`, but no current daemon test calls `mcp_tools::call_tool`. `rg` found `call_tool` usage only in `mcp_bridge.rs` and `crates/sm-cli/tests/mcp_protocol_test.rs`. The actionable amendment is to replace the verification clause with the existing `sm-cli` MCP protocol harness, or explicitly add an in crate daemon test seam before requiring a daemon direct call.

Recommended ALP-2767 edit:

> Add an MCP path test using the existing MCP protocol harness in `crates/sm-cli/tests/mcp_protocol_test.rs` (`DaemonFixture::spawn_mcp` plus the local `call_tool` helper) that submits `dir` plus relative `agent_config` and asserts the resolved against `dir` absolute path.

### 2. ALP-2773 predicate location design call lags ALP-2767 scope expansion

ALP-2773 says the predicate move lets “the CLI canonicalization (ALP-2767) and the daemon resolution share one source” and warns not to reimplement the predicate “CLI side.” ALP-2767 now covers both CLI and MCP canonicalization. The gate should mention both entry points so the binding design call matches the worker body.

Recommended ALP-2773 edit:

> Lift `is_path_like` from `sm-daemon::agent_config` into `sm-core` so the CLI and MCP canonicalization in ALP-2767 and the daemon resolution share one source. ALP-2767 depends on ALP-2766 landing first; do not reimplement the predicate at either entry point.

### 3. No issue: PER mirror integrity

Live `ALP-2772` mirrors the Acceptance bullets from `ALP-2765` through `ALP-2771` exactly. This includes the MCP path bullets on `ALP-2767`, the direct serde dependency bullet on `ALP-2768`, and the build.rs generated output lockstep bullets on `ALP-2769` and `ALP-2770`.

### 4. No issue: `mcp_tools.rs` file overlap between ALP-2767 and ALP-2769

Both `ALP-2767` and `ALP-2769` touch `crates/sm-daemon/src/mcp_tools.rs::agent_run`, but their semantics are order independent. `ALP-2767` canonicalizes path like `agent_config` values against `dir`; `ALP-2769` removes the legacy `workspace` fallback and requires `dir`. Landing in either order leads to the same final handler after normal merge resolution. A `blockedBy` edge would overstate the relationship.

### 5. No issue: ALP-2767 out of scope precision

ALP-2767 now excludes predicate changes and `crates/sm-daemon/src/agent_config.rs` resolution changes. That leaves the intended entry point input canonicalization in `crates/sm-cli/src/cli/run.rs` and `crates/sm-daemon/src/mcp_tools.rs` in scope without reopening downstream daemon resolution.

## Dependencies

Critical dependencies for this review:

- Linear MCP for live issue state and comments.
- fmm MCP for source topology, symbol outlines, symbol source, and index validation.
- `rg` for confirming call site absence after fmm narrowed the target.

## Relevance to Helioy

This catches an execution time failure before Nancy receives the worker. The fix keeps the issue plan honest: either point the worker at the existing `sm-cli` MCP harness or make the daemon test seam explicit. The gate wording update keeps design call text aligned with the worker body, which reduces relitigation during autonomous execution.

## Final Sign-off

After the orchestrator applied the two consensus edits, live Linear was re-read for `ALP-2767` and `ALP-2773`. `ALP-2767` now points the MCP path test at `crates/sm-cli/tests/mcp_protocol_test.rs` using `DaemonFixture::spawn_mcp` plus the local `call_tool` helper. `ALP-2773` now says the shared predicate supports CLI and MCP canonicalization in `ALP-2767`, and forbids predicate reimplementation at either entry point.

Final bus sign-off emitted on topic `agent-config-plan-review-pass6`:

> I sign off on ALP-2763 as currently filed

## Open Questions

- None from Pane B. Orchestrator owns pass persistence and any next-pass decision.
