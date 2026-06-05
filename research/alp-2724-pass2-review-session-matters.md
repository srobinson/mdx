---
title: ALP-2724 Pass 2 Issue Review for session-matters
type: research
tags: [session-matters, linear, moe-review, cli, verification]
summary: 'Pass 2 review found two substantive issue-tree defects: unsafe PER help command examples and uncovered tools.toml file-size pressure.'
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

The ALP-2724 Linear tree is structurally close to executable, with the master, gate, Backlog parent, six workers, and PER all present in the expected selector shape. Pass 2 found two substantive defects that should be corrected before execution: PER manual help checks omit `--help`, and W5 can push `tools.toml` over the 700 LOC project limit without `just check` catching it.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Build system: Cargo workspace with `just` tasks
- Verified index: `.fmm.db` present; `fmm validate` reported all 98 files indexed and current
- Required done gate in project docs: `just check && just build && just test`

## Architecture

The reviewed work targets the `sm` CLI layer and runtime driver boundary:

- CLI grammar: `crates/sm-cli/src/cli/cli_def.rs`, 253 LOC
- Read surface: `crates/sm-cli/src/cli/get.rs`, 80 LOC
- Delete surface: `crates/sm-cli/src/cli/delete.rs`, 46 LOC
- Namespace surface: `crates/sm-cli/src/cli/namespace.rs`, 114 LOC
- Run surface: `crates/sm-cli/src/cli/run.rs`, 176 LOC
- Daemon CLI surface: `crates/sm-cli/src/cli/daemon.rs`, 153 LOC
- Generated help artifact: `crates/sm-cli/src/cli/generated_help.rs`, 166 LOC
- Runtime driver bridge: `crates/sm-driver/src/rtmd.rs`, 395 LOC
- Help generation source: `tools.toml`, 635 LOC

`crates/sm-cli/tests/common/mod.rs` provides an isolated test fixture that starts RTM and SMD under temp directories, sets `SM_HOME`, `HOME`, `RTM_SOCKET_PATH`, and `RTM_DB_PATH`, and tears both daemons down in `Drop`. This supports stateful tests for W3 and W4 if workers keep using the fixture.

## Key Patterns

- The Linear gate uses the selector-compatible shape: master `ALP-2724`, gate `ALP-2726`, execution parent `ALP-2725`, workers `ALP-2727` through `ALP-2732`, and PER `ALP-2733`.
- Worker verification is standardized on `just check && just build && just test`.
- `just check` runs `fmt`, `clippy-fix`, and `check-loc`; the LOC script currently checks Rust files under `crates` only.
- Existing integration tests isolate daemon state through temp homes and sockets, reducing leftover state risk when workers reuse the fixture.

## Detailed Findings

### Finding 1: PER help checks are not copy-paste safe

`ALP-2733` acceptance #3 asks the reviewer to manually check representative help output, but lists commands as bare invocations: `sm create session`, `sm delete session`, `sm run`, `sm daemon`, and similar. These are not safe help checks when copy-pasted. Some can create or delete sessions, require daemon or runtime state, or mutate tmux/runtime state.

Required correction: change the PER command list to explicit help invocations, for example `sm create session --help`, `sm delete session --help`, `sm run --help`, `sm daemon --help`, and `sm config set-context --help` if landed.

### Finding 2: `tools.toml` file-size pressure is not covered by verification

`tools.toml` is currently 635 LOC and W5 owns changes to the help generation source plus generated help artifacts. The project hard limit is 700 LOC, so W5 has only 65 lines before it must refactor or split. `scripts/check-loc-limit.sh` only checks Rust files under `crates`, so `just check` would not catch `tools.toml` exceeding 700 LOC.

Required correction: add W5 acceptance or verification language that keeps `tools.toml` at or below 700 LOC, or refactors the help source before exceeding the cap, with a check that covers `tools.toml`.

### Non-findings

- Worker acceptance help commands that already include `--help` are copy-paste safe and do not need daemon preconditions.
- No GNU versus BSD shell command differences were found in issue-level verification, which is limited to `just check && just build && just test`.
- W3 and W4 stateful tests appear implementable with existing isolated fixture teardown.
- PER lifecycle contingency is internally consistent enough to review: W5 records lifecycle CLI absence, PER #7 decides escalation, and PER #5(f) catches docs/help drift.

## Dependencies

Critical tooling and dependency surfaces:

- `just`: command runner for build, check, and test gates
- Cargo workspace: Rust build and test execution
- `cargo nextest`: workspace test runner in `just test`
- `fmm`: structural index used for file topology and outlines
- Linear MCP: authoritative issue state and comments
- helioy-bus: peer review coordination

## Relevance to Helioy

This review reinforces two recurring Helioy workflow rules: issue verification commands must be copy-paste safe, and project hard limits must be checked by automation when workers can exceed them. For CLI waves, PERs should spell help checks with `--help` even when surrounding prose says “help output”.

## Open Questions

- Whether the orchestrator will apply both conditional changes directly to Linear.
- Whether the peer agrees that the `tools.toml` LOC pressure is substantive enough to amend W5, rather than relying on worker judgment.
