---
title: ALP-2763 Pass 4 Review of Agent Config Plan
type: research
tags: [session-matters, linear, moe-review, agent-config, rust]
summary: Pass 4 review found one substantive acceptance gap around caller HOME handling for tilde agent config paths in ALP-2767.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

A pass 4 MoE review of Linear master `ALP-2763` found the gate, metadata, and fixture safety mostly clean. The only substantive issue is in `ALP-2767`: the filed worker no longer makes the source plan's caller HOME handling for leading `~` and `~/...` agent config paths explicit or testable.

## Project Metadata

- Project: `littleorgans/session-matters`
- Language: Rust
- Workspace shape: Cargo workspace with `sm-core`, `sm-daemon`, `sm-cli`, `sm-store`, and `sm-driver` crates
- Indexed topology: fmm reported 104 indexed files and 16,543 LOC under `crates/`
- Generation path: `tools/*.toml` feeds `crates/sm-cli/build.rs`, which generates MCP schema, CLI help constants, templates, and README output at `crates/sm-cli/build.rs:184-224`

## Architecture

The current agent config path flows through three layers:

1. CLI request construction in `crates/sm-cli/src/cli/run.rs:20-71`. Today `spawn_session` forwards `args.agent_config` directly into `SpawnRequest.agent_config` at line 46.
2. Daemon resolution in `crates/sm-daemon/src/agent_config.rs:26-47`. `resolve_agent_config_with_home` maps a requested name or path to a filesystem path, emits the not found error at lines 28-32, reads TOML, and returns `ResolvedAgentConfig` with `requested`, `path`, and launch env.
3. Session persistence in `crates/sm-daemon/src/handler.rs:132-212` and `crates/sm-store/src/sqlite/sessions.rs:31-55`. `DaemonState::spawn` currently resolves the config at line 142 but persists `request.agent_config` at line 176. SQLite stores the field as TEXT at `sessions.rs:31-55` and reads it back at `sessions.rs:271-290`.

MCP run input comes from `crates/sm-daemon/src/mcp_tools.rs:116-164`. The live handler currently accepts `dir` or the deprecated `workspace` fallback at lines 121-126. The schema source in `tools/run.toml` currently marks `dir` optional at lines 84-90 and still includes `workspace` at lines 100-105.

## Key Patterns

- `tools/run.toml` is the source of truth for generated MCP schemas and CLI help constants. Direct edits to generated artifacts should be avoided.
- `DaemonFixture` uses process local environment isolation for CLI integration tests: each fixture owns a tempdir, SM socket, runtime socket, SQLite paths, and process `HOME` at `crates/sm-cli/tests/common/mod.rs:27-65` and `crates/sm-cli/tests/common/mod.rs:100-106`.
- In process environment mutation already has a lock pattern in `crates/sm-cli/src/cli/run.rs:180-196`. New tests should avoid global env mutation when a parameterized helper exists.

## Detailed Findings

### P1: Gate body selector regex integrity

No defect found. Live `ALP-2773` has one canonical `Outcome:`, one `Authorized execution parent:`, one `Execute:`, and no `Authorized blocker parent:`. The design call sections match the worker bodies for persistence shape, predicate location, schema strictness, and MCP workspace alias.

### P2: Selector readable metadata

No defect found. Live Linear state showed:

- `ALP-2765` through `ALP-2771`: label `rust-engineer`
- `ALP-2772`: label `Post Execution Review`
- `ALP-2763`: state `Todo`
- `ALP-2773`: state `Worker Done`
- `ALP-2763` direct children: only `ALP-2764` Backlog and `ALP-2773` Gate review
- `ALP-2764` children: the seven workers plus `ALP-2772`

### P3: Plan doc versus Linear divergence

Substantive defect found. The source plan explicitly binds tilde handling in Step 3: expand `~` and `~/...` using the caller's HOME before canonicalizing, then leave missing paths absolutized for the daemon error path at `~/.mdx/projects/agent-config-plan.md:68-70`.

Live `ALP-2767` does not carry that binding. It says path like values should be canonicalized against caller cwd, and that names have no separator, no leading `.`, and no leading `~`. Its acceptance only covers `./missing.toml`, `./real.toml`, and bare `demo`.

This is execution relevant because `ALP-2766` defines `~/x.toml` as path like. Current daemon code expands `~` in `agent_config_path` via `expand_home` at `crates/sm-daemon/src/agent_config.rs:49-71`, but `ALP-2767` moves caller side normalization ahead of the daemon. A worker could accidentally turn `~/x.toml` into `<cwd>/~/x.toml`, or leave it for daemon HOME, and still pass the filed acceptance. The missing acceptance could allow broken behavior for `sm run --agent-config ~/real.toml`.

Recommended Linear edits:

1. Amend `ALP-2767` to state that leading `~` and `~/...` are expanded with caller HOME before absolutizing or canonicalizing.
2. Add an `ALP-2767` acceptance bullet for a `~/real.toml` or missing `~/missing.toml` case that proves the rendered path is caller HOME based.
3. Mirror that acceptance in `ALP-2772` so the post execution review can falsify it without chasing the source plan.

### P4: Test pollution and parallel safety

No defect found. Existing patterns support parallel safe tests:

- Resolver tests can avoid global `HOME` mutation by using `resolve_agent_config_with_home` at `crates/sm-daemon/src/agent_config.rs:26-47`.
- `DaemonFixture` starts isolated `smd` and `rtmd` processes with fixture scoped sockets and database paths at `crates/sm-cli/tests/common/mod.rs:27-65`.
- CLI commands get process local `SM_HOME` and `HOME` via `DaemonFixture::command` at `crates/sm-cli/tests/common/mod.rs:100-106`.
- Runtime binary preconditions are already discoverable from `rtm_bin` at `crates/sm-cli/tests/common/mod.rs:230-239`.

One implementation note: `DaemonFixture::command()` does not set `current_dir`. ALP-2767's relative path integration test must set `.current_dir($WORKDIR)` explicitly, following the pattern in `run_persists_canonical_dir_from_cli_resolution` at `crates/sm-cli/tests/cli_get_test.rs:344-372`.

### P5: Out of scope leak audit

The out of scope lists are mostly realistic.

- `ALP-2767` can keep daemon side changes out of scope because the daemon already emits `agent config not found: {requested} (looked for ...)` at `crates/sm-daemon/src/agent_config.rs:28-32`.
- `ALP-2765` can keep a new column out of scope because the current store writes and reads the existing TEXT field at `crates/sm-store/src/sqlite/sessions.rs:31-55` and `crates/sm-store/src/sqlite/sessions.rs:271-290`.
- `ALP-2769` and `ALP-2770` touch `tools/run.toml` in different surfaces: schema params versus help copy.

The P3 tilde gap is a scope gap in `ALP-2767`, not a daemon side leak. Once the CLI owns caller side normalization for path like inputs, caller HOME expansion must be in scope.

## Dependencies

Critical dependencies and roles:

- `anyhow`: error context and daemon error surfacing.
- `toml`: current hand parsed TOML value input for agent config.
- `serde`: needed by the planned typed `AgentConfigToml` change.
- `rusqlite`: session persistence in `sm-store`.
- `tempfile`: fixture isolation in tests.
- `cargo-insta`: snapshot workflow for generated MCP schema tests in `ALP-2769`.

## Relevance to Helioy

This review protects the operator contract for agent configuration. Caller side path normalization is a boundary sensitive change: once `sm` normalizes paths before crossing into `smd`, the CLI must preserve caller cwd and caller HOME semantics rather than inheriting daemon process context.

## Open Questions

- Whether the orchestrator will apply the ALP-2767 and ALP-2772 tilde acceptance edits, or whether Pane A will argue that the source plan already covers the behavior sufficiently.
- Whether the final pass 4 outcome remains conditional or returns to clean sign off after peer consensus.

## Bus Convergence Update

Pane A conceded the P3 finding on 2026-05-23. Both panes converged on the same conditional sign off:

1. Amend `ALP-2767` to make caller HOME handling for leading `~` and `~/...` explicit and testable. The worker body should state caller HOME expansion happens before absolutizing or canonicalizing path like inputs. Acceptance should include a `~/real.toml` or `~/missing.toml` case proving the rendered path is caller HOME based.
2. Mirror that `ALP-2767` acceptance bullet into `ALP-2772` PER criteria.

Consensus messages sent on topic `agent-config-plan-review-pass4`:

- Pane A convergence note: `5c6f58d5-7677-43af-b6cb-e3982a5fb29c`
- Orchestrator CC: `c463ff6d-f09d-4a11-a244-f69d8debde51`

## Live Re-read Sign-off Update

After the orchestrator applied the consensus edits, live Linear was re-read for `ALP-2767` and `ALP-2772` on 2026-05-23.

Verified:

- `ALP-2767` Capability now binds caller HOME expansion for `~` and `~/...` before canonicalizing path-like values against caller CWD, with daemon HOME divergence rationale.
- `ALP-2767` Acceptance includes the `~/missing.toml` caller HOME rooted not-found path case.
- `ALP-2767` Verification adds the `~/xyz` case alongside `./xyz`.
- `ALP-2772` mirrors the new `ALP-2767` acceptance bullet exactly in its PER criteria.

Final sign-off emitted on topic `agent-config-plan-review-pass4`:

- Pane A sign-off message: `f0c5e664-fccb-49c8-9e5e-950d19492523`
- Orchestrator CC: `d75c89a3-77ae-49a5-9d1b-7cd5797bc3c2`

Sign-off phrase: `I sign off on ALP-2763 as currently filed`.

## Pane A Final Sign-off Receipt

Pane A sent its round 2 post-apply sign-off on 2026-05-23 after re-reading live Linear for `ALP-2767` and `ALP-2772`.

Verified by Pane A:

- `ALP-2767` binds caller HOME expansion for `~` and `~/...` before canonicalizing path-like values against caller CWD.
- `ALP-2767` Acceptance includes the `~/missing.toml` caller-HOME-rooted not-found path case.
- `ALP-2767` Verification adds the `~/xyz` case alongside the existing `./xyz` case.
- `ALP-2772` mirrors the new acceptance bullet verbatim.
- `ALP-2767` out-of-scope daemon-side boundary still holds.
- Selector hygiene and metadata remain clean.

Pane A sign-off phrase: `I sign off on ALP-2763 as currently filed`.
Pane A message ID: `f8e03a02-f44f-4133-8d2e-f3acd432b6cd`.
