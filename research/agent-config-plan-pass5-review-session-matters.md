---
title: Agent Config Plan Pass 5 Review for session-matters
type: research
tags: [session-matters, linear, moe-review, agent-config, mcp, codegen]
summary: Pass 5 review of ALP-2763 re-read amended Linear issues and signed off clean after all consensus changes landed.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

Pass 5 reviewed the live Linear tree for `ALP-2763` against the current `session-matters` source. The tree is now ready for execution after orchestrator edits applied all three consensus changes: MCP path parity, generated-output coverage for `tools/run.toml`, and the `ALP-2768` serde dependency requirement.

## Project Metadata

- Project: `littleorgans/session-matters`
- Language: Rust, edition 2024
- Build system: Cargo workspace with `crates/sm-core`, `crates/sm-daemon`, `crates/sm-cli`, `crates/sm-store`, `crates/sm-driver`, `crates/sm-paths`
- Structural index: `.fmm.db` present and `fmm validate` passed for 104 indexed files
- Source plan: `~/.mdx/projects/agent-config-plan.md`
- Linear artifact: master `ALP-2763`, backlog `ALP-2764`, workers `ALP-2765` through `ALP-2771`, PER `ALP-2772`, gate `ALP-2773`

## Architecture Context

`sm` is the CLI control surface. `smd` owns session records and handles MCP tools. `sm run` builds a `SpawnRequest` in `crates/sm-cli/src/cli/run.rs::spawn_session`; MCP `session_run` and `agent_run` bypass that CLI path and build their own `SpawnRequest` in `crates/sm-daemon/src/mcp_tools.rs::agent_run`.

Relevant entry points:

- CLI spawn request construction: `crates/sm-cli/src/cli/run.rs:20-71`
- MCP tool routing: `crates/sm-daemon/src/mcp_tools.rs:22-23`
- MCP spawn request construction: `crates/sm-daemon/src/mcp_tools.rs:121-148`
- Daemon agent config resolution: `crates/sm-daemon/src/agent_config.rs:26-47`
- Agent config path mode and home expansion: `crates/sm-daemon/src/agent_config.rs:49-71`
- Session persistence point: `crates/sm-daemon/src/handler.rs:132-212`
- Generated public surface source: `tools/run.toml:1-3`
- Generated output writer: `crates/sm-cli/build.rs:184-224`

## Key Patterns

1. `tools/run.toml` is a source of truth, not a local config file. Build output spans MCP schemas, generated CLI help, generated MCP instructions, templates, and README content.
2. Path normalization must be reasoned by caller path. CLI callers have a shell CWD and HOME. MCP callers supply `dir`, but currently do not pass through CLI normalization.
3. Typed TOML parsing with `#[serde(deny_unknown_fields)]` requires `serde` in the crate that defines the typed struct.

## Detailed Findings

### 1. MCP path semantics remain partial unless made explicit

`ALP-2767` normalizes `--agent-config` only in the CLI path. The current source confirms that `session_run` and `agent_run` use a separate path:

- `call_tool` routes both `agent_run` and `session_run` to `agent_run`: `crates/sm-daemon/src/mcp_tools.rs:22-23`
- `agent_run` reads `agent_config` from arguments and passes it directly into `SpawnRequest`: `crates/sm-daemon/src/mcp_tools.rs:121-148`
- The daemon still resolves path-like values through `agent_config_path` and `expand_home`: `crates/sm-daemon/src/agent_config.rs:49-71`

For an MCP caller, `agent_config = "./foo.toml"` still resolves relative to daemon CWD. `agent_config = "~/foo.toml"` still uses daemon HOME. This preserves the footgun for MCP even after the CLI fix lands.

Recommended resolution:

- Preferred: extend `ALP-2767` or add a worker so MCP path-like `agent_config` values normalize before spawn, with relative paths resolved against MCP `dir` and missing file errors showing that absolute path.
- Acceptable if intentional: add a gate design call that explicitly binds CLI-only scope, add an `ALP-2767` note, and mirror the accepted MCP asymmetry into `ALP-2772` so review can verify it.

### 2. Generated surface coverage is under-specified for `ALP-2769` and `ALP-2770`

Both workers edit `tools/run.toml`, but their Linear bodies list only some generated outputs. Current source says the file feeds more surfaces:

- `tools/run.toml:1-3` states it generates MCP schema, CLI help constants, Claude Code skill, and README documentation.
- `crates/sm-cli/build.rs:184-198` writes generated MCP schema outputs.
- `crates/sm-cli/build.rs:201-224` writes generated MCP instructions, generated CLI help, `templates/SKILL.md`, and `README.md`.

The issue is not worker ordering. It is generated source hygiene. A worker can satisfy local schema or help assertions while leaving other build generated files dirty or unstaged.

Recommended resolution:

Add an acceptance or verification bullet to `ALP-2769` and `ALP-2770`:

> After editing `tools/run.toml`, run the normal build or test generator path and commit every generated output dirtied by `crates/sm-cli/build.rs`, including generated instructions, generated help, generated schemas, templates, README, and snapshots when changed.

### 3. `ALP-2768` needs a direct serde dependency in `sm-daemon`

`ALP-2768` requires a typed `AgentConfigToml` using `#[serde(deny_unknown_fields)]`. Current `sm-daemon` dependencies include `serde_json` and `toml`, but not `serde`: `crates/sm-daemon/Cargo.toml:8-23`.

Without a direct `serde.workspace = true` dependency or equivalent, the stated implementation shape should fail `cargo test -p sm-daemon`, or the executor will need to avoid the typed serde design the issue mandates.

Recommended resolution:

Add `crates/sm-daemon/Cargo.toml` to `ALP-2768` entry points and acceptance, requiring the direct serde dependency needed for the typed parser.

### 4. PER mirror integrity passed

The `ALP-2772` per-worker subsections mirror the current Acceptance bullets for `ALP-2765` through `ALP-2771`. No drift was found, including the pass 4 tilde acceptance added to `ALP-2767` and mirrored under `ALP-2772 ### ALP-2767`.

### 5. Worker order dependencies appear correct

The gate currently states `ALP-2766` before `ALP-2767`; all other workers are independent. Current source supports that at the dependency level:

- `ALP-2767` depends on the predicate lifted by `ALP-2766`.
- `ALP-2769` and `ALP-2770` both edit `tools/run.toml`, but different parameter surfaces.
- `ALP-2766` and `ALP-2768` both touch `crates/sm-daemon/src/agent_config.rs`, but different functions.

No additional Linear dependency edge is required.

### 6. Tilde double expansion risk passed

`expand_home` only expands exact `~` and `~/...`: `crates/sm-daemon/src/agent_config.rs:63-71`. An absolute caller-side path falls through to `PathBuf::from(value)`, so CLI-expanded absolute paths do not double-expand in the daemon.

### 7. Error message lineage passed

The relevant messages come from separate sites:

- Not found: `crates/sm-daemon/src/agent_config.rs:29-32`
- Non-string env value: `crates/sm-daemon/src/agent_config.rs:85-89`

`ALP-2768` rewrites parsing after the not-found check, so it should not affect `ALP-2771`'s not-found grep. Its own acceptance guards the preserved `agent config env` format.

## Dependencies

Critical dependencies in this review:

- `serde`: required by the typed TOML parser design in `ALP-2768`
- `toml`: current parser dependency in `sm-daemon`
- `cargo-insta`: required by `ALP-2769` schema snapshot verification
- `build.rs`: generator for schema, help, instructions, templates, and README surfaces
- `DaemonFixture`: CLI integration harness that requires `RTM_TEST_BIN`, sibling `../runtime-matters/target/debug/rtm`, or `rtm` on PATH

## Relevance to Helioy

This review protects the session control plane from planner drift before autonomous execution. The highest value lesson is that generated surfaces and non-CLI callers must be treated as first class execution paths when a flag is also exposed as an MCP parameter.

## Open Questions

None for pass 5. If the Linear tree changes again, re-read live state before any further signoff.

## Bus Actions

- Sent round 1 conditional signoff to Pane A and CC'd orchestrator on topic `agent-config-plan-review-pass5`.
- Received Pane A round 1 position. Pane A found only the MCP semantics gap and proposed a doc-only scope decision.
- Sent round 2 reply asking Pane A to accept generated surface coverage and the serde dependency gap, while allowing MCP scope documentation if broad enough to make the asymmetry reviewable.
- Received Pane A round 3 reaffirming full convergence on the three conditions: MCP path semantics, generated-surface coverage, and ALP-2768 serde dependency.
- Acknowledged final consensus to Pane A and CC'd orchestrator.
- Received Pane A confirmation that crossed round 3 messages were equivalent and pass 5 is complete from Pane A side.
- Sent final stop-state acknowledgement to Pane A and CC'd orchestrator.
- Received orchestrator notice that all three consensus changes were applied. Re-read live Linear for `ALP-2767`, `ALP-2768`, `ALP-2769`, `ALP-2770`, `ALP-2772`, and `ALP-2773`.
- Verified `ALP-2767` now covers CLI and MCP path canonicalization and `ALP-2772` mirrors it.
- Verified `ALP-2768` now requires the direct serde dependency and `ALP-2772` mirrors it.
- Verified `ALP-2769` and `ALP-2770` now require full build.rs generated-surface lockstep and `ALP-2772` mirrors both plus cross-cutting checks.
- Sent clean signoff to Pane A and CC'd orchestrator: `I sign off on ALP-2763 as currently filed`.
- Received Pane A clean signoff after its live Linear re-read. Acknowledged Pane A and CC'd orchestrator that both panes now sign off on `ALP-2763` as currently filed.
