---
title: Agent Config Plan Pass 3 Review for session-matters
type: research
tags: [session-matters, linear-review, agent-config, moe-review, shell-safety, cli]
summary: Pass 3 fresh eyes review of ALP-2763 found two consensus issues, then signed off clean after live Linear re-read of orchestrator edits.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

`session-matters` is the Helioy session control plane. This pass audited the live Linear tree for `ALP-2763`, "Make `sm run --agent-config` honest and debuggable", against the MoE issue review workflow and current source under `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`.

The fresh review converged on two substantive defects: command-shaped prose still uses unquoted angle placeholders that bash and zsh parse as redirection, and `ALP-2768` promises preservation of the non-string `[env]` error message without a verification test that pins it. The remaining probe surfaces were clean: PER acceptance mirrors match current worker bullets and the cross-worker contracts compose.

## Project Metadata

- Language: Rust.
- Build system: Cargo workspace with generated surfaces from `tools/*.toml` through `crates/sm-cli/build.rs`.
- Indexed topology: fmm reported 104 indexed files and 16,543 LOC under `crates/`.
- Relevant crates: `sm-core`, `sm-daemon`, `sm-cli`, `sm-store`, `sm-driver`.
- Key dependencies: `clap`, `serde`, `serde_json`, `toml`, `rusqlite`, `uuid`, `insta`, `lilo-rm-core`, `lilo-rm-client`.

## Architecture

The reviewed Linear tree has selector-compatible shape:

- Master: `ALP-2763`, status `Todo`.
- Execution parent: `ALP-2764`, title `Backlog`, direct child of `ALP-2763`.
- Gate: `ALP-2773`, title `Gate review: agent-config-plan`, status `Worker Done`, direct child of `ALP-2763`.
- Workers under `ALP-2764`: `ALP-2765` through `ALP-2771`.
- Post execution review: `ALP-2772`, label `Post Execution Review`, under `ALP-2764`.

The `--agent-config` implementation crosses three layers:

1. CLI request creation in `crates/sm-cli/src/cli/run.rs`. `spawn_session` currently forwards `args.agent_config` into `SpawnRequest.agent_config` at lines 36 to 47.
2. Daemon resolution and persistence in `crates/sm-daemon/src/agent_config.rs` and `crates/sm-daemon/src/handler.rs`. `resolve_agent_config_with_home` checks existence before parsing at lines 26 to 47. `DaemonState::spawn` currently persists `request.agent_config` at lines 163 to 177. `spawn_launch` merges resolved config env into launch env at lines 606 to 641.
3. Public tool surfaces from `tools/run.toml` through `crates/sm-cli/build.rs`. `generate_mcp_schema` emits schemas at lines 227 to 254. `generate_cli_help` emits help constants at lines 256 to 289.

## Key Patterns

- `tools/run.toml` remains the source of truth for CLI help and MCP schemas. Generated files must not be edited directly.
- `agent_run` and `session_run` are generated together, so MCP schema acceptance must cover both generated JSON files and both insta snapshots.
- `DaemonFixture` integration tests start real `rtmd` and `smd`. The helper resolves `RTM_TEST_BIN`, then sibling `../runtime-matters/target/debug/rtm`, then `rtm` on PATH at `crates/sm-cli/tests/common/mod.rs:230-239`.
- Current selector parsing accepts either a raw UUID or `id:<uuid>` for `sm get session`, because `Selector::from_str` parses raw UUIDs before `id:` selectors at `crates/sm-core/src/selector.rs:136-148`.

## Detailed Findings

### 1. Substantive: command-shaped angle placeholders are still shell hazards

The pass 3 prompt specifically targeted shell safety. Live issue bodies still contain command-shaped examples with angle placeholders:

- `ALP-2765` Acceptance and the `ALP-2772` mirror use `sm get session id:<uuid>`.
- `ALP-2767` Acceptance and Verification prose, plus the `ALP-2772` mirror, use `--dir <tempdir>` and `sm get session <id> --json`.
- `ALP-2771` Capability uses `--agent-config <missing>` and `--dir <tempdir>`.

Bash and zsh treat unquoted `<id>` and `<tempdir>` as input redirection. `id:<uuid>` is also unsafe, producing a syntax error or redirection parse failure. The `grep -F` probes in `ALP-2770` are safe because the patterns are single quoted.

Required change sent to Pane A and CC'd to the orchestrator:

- Replace command-shaped placeholders with shell-safe env-var placeholders.
- Use examples such as `--dir "$WORKDIR"`, `sm get session "id:$SESSION_ID" --json`, and concrete `--agent-config does-not-exist`.
- Keep `ALP-2772` mirrors exact after changing the worker Acceptance bullets.

### 2. Substantive: ALP-2768 non-string `[env]` verification gap

`ALP-2768` Acceptance bullet 3 promises that an `agent.toml` with a non-string `[env]` value fails with the existing error message. Current source formats that message as `agent config env `{key}` must be a string` at `crates/sm-daemon/src/agent_config.rs:88`. Current tests under `crates/sm-daemon/src/agent_config.rs:99-161` do not pin this case, and `rg` found no assertion for the message substring.

Impact: a straightforward typed `serde` deserialize of `env: BTreeMap<String, String>` could emit serde's default invalid-type message, pass the listed Verification commands, and still regress the promised error contract.

Required change: add a unit test where `[env]\nKEY = 42` fails with an error containing `agent config env` and `KEY`, or tighten the Acceptance bullet to the observable substring contract and mirror the wording in `ALP-2772`. Pane A and Pane B prefer the unit test because it makes the contract executable.

### 3. Cross-platform tool behaviour: no additional defect found

The review checked the shell-sensitive commands across the issue set.

- `grep -F '~/.agm/<name>/agent.toml'` is safe under bash and zsh because the pattern is single quoted.
- `grep -F '[env]'` is safe under bash and zsh because the bracket expression is single quoted and `-F` treats it as a fixed string.
- Local `cargo insta test --help` confirms `cargo insta test --accept -p sm-cli` accepts both `--accept` and `-p, --package <PACKAGE>`.
- The Cargo commands use stable Cargo flags with no BSD versus GNU coreutils exposure.

### 4. PER mirror fidelity: no drift found

The live `ALP-2772` per-worker subsections mirror the current Acceptance bullets for the five targeted workers:

- `ALP-2766` predicate cases.
- `ALP-2768` TOML parsing and precedence cases.
- `ALP-2769` MCP schema and snapshot cases.
- `ALP-2770` help surface cases.
- `ALP-2771` CLI not-found integration test cases.

`ALP-2765` and `ALP-2767` also mirrored after the pass 2 edits, but their mirrored command-shaped placeholders need the shell-safety change above.

### 5. Acceptance falsifiability: no sampled defect found

The sampled Acceptance sections are reviewable through concrete observables:

- `ALP-2765`: daemon test plus `sm get session` output can prove resolved path persistence. `Session.agent_config` remains `Option<String>` in `crates/sm-core/src/session.rs:67-89`; store insert and read preserve the text column at `crates/sm-store/src/sqlite/sessions.rs:31-55` and `271-298`.
- `ALP-2766`: five predicate cases are unit-testable in `sm-core`.
- `ALP-2768`: TOML precedence, unknown-key rejection, and non-string `[env]` failures are unit-testable at the `agent_env` boundary. Current code inserts top-level `claude_config_dir` before `[env]` at `crates/sm-daemon/src/agent_config.rs:73-96`.
- `ALP-2770`: `tools/run.toml`, generated help output, and `generated_help_constants_have_source_consumers` are inspectable and testable. The guard test exists at `crates/sm-cli/tests/generated_surface_guard_test.rs:104-115`.
- `ALP-2771`: the CLI integration test can assert nonzero exit plus stderr content under `DaemonFixture`.

### 6. Cross-worker contract integrity: no defect found

`ALP-2767` depends on `ALP-2766` for the shared predicate and does not require a private CLI copy. The missing-file contract also composes with daemon behavior: `resolve_agent_config_with_home` checks `path.is_file()` before reading or parsing, and formats the not-found error with both `requested` and the looked-for path at `crates/sm-daemon/src/agent_config.rs:26-47`.

`ALP-2768` only affects parsing after a file exists, so it does not alter not-found behavior. `ALP-2771` still tests the named missing config path, which should remain unchanged on the wire because bare names are not path-like after `ALP-2766`.

## Dependencies

- `toml` and `serde` support the typed `AgentConfigToml` rewrite.
- `insta` owns schema snapshot acceptance for `session_run` and `agent_run`.
- `clap` consumes generated help constants through `SessionCreateArgs` in `crates/sm-cli/src/cli/cli_def.rs:94-107`.
- `lilo-rm-core` provides caller env and cwd capture used by `spawn_session` at `crates/sm-cli/src/cli/run.rs:20-71`.

## Relevance to Helioy

This plan affects the session control plane used by Helioy agents to launch with per-agent environment. The remaining defect is small but execution-relevant: unsafe placeholders can turn otherwise correct verification examples into shell parse errors for autonomous workers or reviewers.

## Consensus State

Pane A and Pane B converged on two conditional findings:

1. `ALP-2768` must close the bullet 3 Verification gap. Preferred fix: add a unit test where `[env]\nKEY = 42` fails with an error containing `agent config env` and `KEY`. Mirror any wording change into `ALP-2772`.
2. Replace command-shaped angle placeholders across `ALP-2765`, `ALP-2767`, `ALP-2771`, and the `ALP-2772` mirrors. Use `$WORKDIR`, `$SESSION_ID`, quoted selector examples such as `sm get session "id:$SESSION_ID" --json`, and leave quoted literal help text such as `grep -F '~/.agm/<name>/agent.toml'` unchanged.

Pane A and Pane B both signed off on the same two conditions. Pane A confirmed no escalation is needed and both panes are standing by for orchestrator edits and a live re-read before clean re-sign-off.

## Final Live Re-read and Sign-off

After orchestrator edits, Pane B re-read live Linear for `ALP-2765`, `ALP-2767`, `ALP-2768`, `ALP-2771`, and `ALP-2772`. Both consensus edits landed:

- `ALP-2768` Acceptance bullet 3 and Verification now cover `[env]\nKEY = 42` and require an error containing both `agent config env` and the offending key name. `ALP-2772` mirrors the updated bullet exactly.
- Shell-safe placeholders landed in `ALP-2765` Acceptance b3, `ALP-2767` Acceptance b1 and b2 plus Verification, `ALP-2771` Capability, and `ALP-2772` mirrors. Literal quoted help text remains unchanged.

Pane B sent the required clean sign-off to Pane A and CC'd the orchestrator:

`I sign off on ALP-2763 as currently filed`

## Open Questions

None for pass 3.
