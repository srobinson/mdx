---
title: Agent config plan pass 2 review for session-matters
type: research
tags: [session-matters, linear-review, moe, agent-config, rust]
summary: Pass 2 Linear review found five conditional fixes before ALP-2763 should be treated as ready.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

`session-matters` is the Helioy control plane for durable agent sessions. A live pass 2 MoE review of Linear master `ALP-2763`, "Make `sm run --agent-config` honest and debuggable", found the Linear tree structurally sound but not yet clean. The consensus conditional set is now five items: remove an `ALP-2767` prescriptive implementation sentence, add the `DaemonFixture` runtime binary precondition to `ALP-2767` and `ALP-2771`, fix `ALP-2772` Acceptance mirroring drift for `ALP-2765`, make `ALP-2769` snapshot verification copy-paste safe, and name the concrete `ALP-2767` observable for the absolute path claim.

## Project Metadata

* Language: Rust workspace.
* Indexed surface: 104 files, 16,543 LOC.
* fmm status: `.fmm.db` is present and `fmm validate` passed for all 104 files on 2026-05-23.
* Build and verification surface: Cargo, Just, `cargo-insta`, runtime-matters `rtm` for CLI integration fixtures.
* Relevant commands observed in the plan: `cargo test -p sm-daemon`, `cargo test -p sm-store`, `cargo test -p sm-cli`, `cargo test -p sm-core`, `cargo insta accept`, and `cargo run -p sm-cli --bin sm -- run --help | grep -F ...`.

## Architecture Context

The reviewed plan touches the `sm run --agent-config` path across four layers:

* CLI request construction in `crates/sm-cli/src/cli/run.rs`. `spawn_session` constructs `SpawnRequest` and currently forwards `args.agent_config` at lines 20 to 71, with the field assignment at line 46.
* Daemon resolution in `crates/sm-daemon/src/agent_config.rs`. `resolve_agent_config` reads `HOME` at lines 16 to 24. `agent_config_path` and `is_path_like` resolve name versus path behavior at lines 49 to 61. `agent_env` performs the current hand walked TOML read at lines 73 to 96.
* Daemon persistence in `crates/sm-daemon/src/handler.rs`. `DaemonState::spawn` resolves agent config at line 142, builds the launch at line 143, and currently persists `request.agent_config` into `Session.agent_config` at line 176.
* Session record shape in `crates/sm-core/src/session.rs`. `Session.agent_config` remains `Option<String>` at line 83 inside the `Session` struct at lines 67 to 89.

## Detailed Findings

### Consensus status

Pane A and Pane B confirmed the same five conditional changes on topic `agent-config-plan-review-pass2`. The orchestrator then applied the edits. Pane B re-read live `ALP-2765`, `ALP-2767`, `ALP-2769`, `ALP-2771`, `ALP-2772`, and gate `ALP-2773`; all five changes landed as requested. Pane B sent `I sign off on ALP-2763 as currently filed.` Pane A independently re-read the amended Linear issues, found no new substantive defects, and sent the same clean sign-off. Cosmetic items, including a possible future `blockedBy` convention for PER issues, were explicitly kept non-blocking.

### Live Linear structure is selector compatible

The live Linear tree matched the required selector shape:

* Master: `ALP-2763`.
* Execution parent: `ALP-2764`, title `Backlog`.
* Gate review: `ALP-2773`, status `Worker Done`.
* Workers and post execution review under `ALP-2764`: `ALP-2765`, `ALP-2766`, `ALP-2767`, `ALP-2768`, `ALP-2769`, `ALP-2770`, `ALP-2771`, `ALP-2772`.
* Gate `Execute:` line listed exactly those eight executable issues.
* The only Linear blocking relation was `ALP-2767` blocked by `ALP-2766`, matching the gate `Required order: ALP-2766 before ALP-2767. All other workers are independent.`

No orphan child or relation mismatch was found.

### Source references resolve

All referenced paths checked during the review existed in the live checkout:

* `crates/sm-daemon/src/handler.rs`
* `crates/sm-core/src/session.rs`
* `crates/sm-store/src/sqlite/sessions.rs`
* `crates/sm-daemon/src/agent_config.rs`
* `crates/sm-cli/src/cli/run.rs`
* `tools/run.toml`
* `crates/sm-daemon/src/mcp_tools.rs`
* `crates/sm-cli/src/mcp/generated_schema/session_run.json`
* `crates/sm-cli/src/mcp/generated_schema/agent_run.json`
* `crates/sm-cli/tests/snapshots/`
* `crates/sm-cli/build.rs`
* `crates/sm-cli/src/cli/generated_help.rs`
* `crates/sm-cli/tests/cli_help_surface_test.rs`
* `crates/sm-cli/tests/cli_get_test.rs`

Key symbols also resolved through fmm: `Session`, `DaemonState::spawn`, `ResolvedAgentConfig`, `resolve_agent_config`, `agent_config_path`, `is_path_like`, `agent_env`, `spawn_session`, `DaemonFixture`, and `TestDaemon`.

### Conditional issue 1: `ALP-2767` leaks implementation prescription

`ALP-2767` Entry points contains the sentence beginning: `After expanding ~ and ~/... against the caller's HOME, fs::canonicalize if the file exists...`. That names an implementation algorithm. The gate only binds shared predicate ownership and the observable path behavior. This violates the Universal Issue Rule that worker issues describe capability and observable behavior rather than function bodies or implementation details.

Recommended edit:

* Replace the sentence with capability level text: `Path-like values are normalized against the caller environment before the spawn request is sent. Existing files resolve to an absolute path; missing files still reach the daemon as a caller-side absolute lookup path so the existing not-found error remains useful.`

This preserves the acceptance target while leaving implementation choice to the worker.

### Conditional issue 2: `ALP-2767` and `ALP-2771` hide the `rtm` precondition

Both `ALP-2767` and `ALP-2771` rely on `DaemonFixture` through `cargo test -p sm-cli`. `DaemonFixture` starts runtime-matters as part of the fixture:

* `DaemonFixture::start_with_path_prefix` starts `rtm daemon start` with `RTM_SOCKET_PATH`, `RTM_DB_PATH`, `RTM_HOME`, and a test PATH at `crates/sm-cli/tests/common/mod.rs:27-65`.
* `rtm_bin` resolves the binary from `RTM_TEST_BIN`, sibling `../runtime-matters/target/debug/rtm`, or bare `rtm` on PATH at `crates/sm-cli/tests/common/mod.rs:230-239`.

That is a real hidden verification precondition. A fresh worker can fail before exercising the acceptance target if runtime-matters has not been built and `rtm` is not on PATH.

Recommended edit:

* Add a Verification precondition to `ALP-2767` and `ALP-2771`: `Requires runtime-matters rtm available through RTM_TEST_BIN, sibling ../runtime-matters/target/debug/rtm, or rtm on PATH before running cargo test -p sm-cli.`

`cargo-insta` is also assumed by `ALP-2769`, but the command `cargo insta accept` makes that dependency explicit enough for a Rust worker to diagnose.

### Conditional issue 3: `ALP-2772` claims verbatim Acceptance mirroring that is not true for `ALP-2765`

`ALP-2772` says: `Per-worker subsections mirror each worker's Acceptance bullets verbatim.` `ALP-2765` does not have Acceptance bullets, it has prose. The `ALP-2772` subsection for `ALP-2765` is also not a verbatim mirror because it imports a new daemon test statement from Verification.

Recommended edit:

* Either make `ALP-2765` Acceptance bulleted and mirror it exactly in `ALP-2772`, or change `ALP-2772` wording from `Acceptance bullets verbatim` to `acceptance criteria exactly` and keep the `ALP-2765` subsection aligned to those criteria without importing Verification text as Acceptance.

This matters because the post execution review body is the reviewer contract. The current wording says the body proves one mirroring rule while the live text follows another.

### Conditional issue 4: `ALP-2769` verification is not copy-paste safe

Pane A found and Pane B confirmed a snapshot verification defect in `ALP-2769`. The live Verification block is:

```
cargo test -p sm-cli
cargo insta accept
cargo test -p sm-cli
cargo test -p sm-daemon
```

After the schema regeneration, the first `cargo test -p sm-cli` is expected to fail on `session_run` and `agent_run` snapshot diffs. That is a valid review cycle, but it is not copy-paste safe for an autonomous worker that treats Verification commands as a stopping script. The test surface uses `insta::assert_json_snapshot!` in `crates/sm-cli/tests/mcp_schema_snapshot_test.rs`, and `cargo-insta` exposes a valid `cargo insta test --accept -p sm-cli` command.

Recommended edit:

* Either annotate that the first `cargo test -p sm-cli` is an expected snapshot-diff failure and is the cue to run `cargo insta accept`, or use `cargo insta test --accept -p sm-cli`, then confirm with `cargo test -p sm-cli` and `cargo test -p sm-daemon`.
* If editing the block, list `cargo-insta` CLI availability as a Verification precondition because `cargo insta accept` and `cargo insta test --accept` require the subcommand binary, not just the workspace `insta` dev dependency.

This is a copy-paste safety defect because an executor can stop before accepting and confirming the regenerated snapshots. It also risks leaving `.snap.new` files in `crates/sm-cli/tests/snapshots/` if the sequence aborts between test and accept.

### Conditional issue 5: `ALP-2767` absolute path acceptance lacks a concrete observable

`ALP-2767` Acceptance says the daemon receives an absolute path and bare names are unchanged on the wire. Its Verification block says to use the existing `DaemonFixture` pattern and assert the daemon receives an absolute path. The fixture does not expose direct `SpawnRequest` inspection. Existing CLI integration tests falsify persisted session fields through `sm get session <id> --json`, with `get_session_json` in `crates/sm-cli/tests/cli_get_test.rs:425-433`.

Recommended edit:

* Name the concrete observable in `ALP-2767` Verification. For example, the CLI integration test should run `sm run`, capture the session id from stdout, then inspect `sm get session <id> --json` and assert `agent_config` or the chosen persisted observable reflects the caller-side absolute path.
* If the intended observable is different, state that inspection surface explicitly.

This is a falsifiability defect. A reviewer should be able to prove the acceptance claim from the issue body without reverse engineering the test harness.


### Final live re-read evidence

After orchestrator application on 2026-05-23, live Linear showed:

* `ALP-2767` Capability includes caller-environment normalization plus missing-file behavior. Entry points contains only the CLI `spawn_session` entry point and shared `sm-core` predicate dependency. `## Preconditions` names the `RTM_TEST_BIN`, sibling `../runtime-matters/target/debug/rtm`, or `rtm` on PATH requirement. Acceptance and Verification name `sm get session <id> --json` as the observable for `agent_config`.
* `ALP-2771` includes the same `DaemonFixture` / `rtm` precondition.
* `ALP-2769` includes `cargo-insta` CLI availability as a precondition and uses `cargo insta test --accept -p sm-cli`, `cargo test -p sm-cli`, then `cargo test -p sm-daemon`.
* `ALP-2765` Acceptance is now bulleted.
* `ALP-2772` mirrors `ALP-2765` Acceptance exactly and mirrors updated `ALP-2767` Acceptance with the `sm get session <id> --json` observable. Cross-cutting checks include both the `DaemonFixture` `rtm` precondition and the `cargo-insta` precondition.
* `ALP-2773` still authorizes `ALP-2765`, `ALP-2766`, `ALP-2767`, `ALP-2768`, `ALP-2769`, `ALP-2770`, `ALP-2771`, and `ALP-2772`, with `ALP-2766` before `ALP-2767`.

### File size cap pressure is real but not currently blocking

Live LOC checks:

* `crates/sm-daemon/src/handler.rs`: 685 LOC.
* `crates/sm-daemon/src/mcp_tools.rs`: 671 LOC.
* `crates/sm-cli/src/cli/run.rs`: 204 LOC.
* `crates/sm-daemon/src/agent_config.rs`: 161 LOC.
* `crates/sm-cli/tests/cli_help_surface_test.rs`: 331 LOC.
* `crates/sm-daemon/tests/handler.rs`: 552 LOC.
* `crates/sm-cli/tests/cli_get_test.rs`: 469 LOC.
* Largest current `sm-core` source file: `crates/sm-core/src/tool_contracts.rs` at 609 LOC.

`handler.rs` has only 15 lines of headroom and `mcp_tools.rs` has 29. The expected `ALP-2765` handler change can be in place, and the expected `ALP-2769` `mcp_tools.rs` change should remove fallback code. No worker must cross 700 LOC if the implementation stays disciplined. The cap remains a review hazard if a worker adds helpers to either near-limit file.

`scripts/check-loc-limit.sh` produced no failures in the current checkout.

### Teardown discipline is acceptable

For CLI integration tests:

* `DaemonFixture::drop` calls `self.stop()` at `crates/sm-cli/tests/common/mod.rs:138-140`.
* `DaemonFixture::stop` sends `sm daemon stop`, waits on the smd child, sends `rtm daemon stop`, kills rtmd, and waits on rtmd at `crates/sm-cli/tests/common/mod.rs:118-134`.
* `DaemonFixture` owns a `tempfile::TempDir` at `crates/sm-cli/tests/common/mod.rs:10-16`, so sockets and fixture databases are tempdir scoped.

For daemon tests:

* `TestDaemon` owns a tempdir and uses an in-memory `SqliteStore`, with no spawned child process, at `crates/sm-daemon/tests/common/mod.rs:211-237`.

No dirty operator state was found for the planned `ALP-2767`, `ALP-2771`, or `ALP-2765` tests beyond the hidden `rtm` availability precondition above.

## Dependencies

Critical dependencies for this work:

* `runtime-matters` `rtm` binary for CLI integration fixture startup.
* `cargo-insta` for accepting regenerated schema snapshots in `ALP-2769`.
* `tempfile` based fixture cleanup for daemon and CLI tests.
* fmm index for source and symbol verification.

## Relevance to Helioy

This review protects the Nancy selector and agent execution pipeline from a gate that appears ready but still contains review contract drift and hidden test environment assumptions. The same defect classes recur across Helioy planning gates: source of truth drift, implicit fixture preconditions, file size cap pressure, and implementation detail leaking into worker issues.

## Open Questions

* Should `DaemonFixture` verification preconditions be documented once in the workflow or in each worker that depends on `cargo test -p sm-cli`?
* Should the 700 LOC cap tooling fail proactively when a file exceeds a warning threshold such as 650 LOC, so planning gates can require refactor steps before workers reach the hard limit?
* Should `ALP-2772` use a standard PER template that says `acceptance criteria exactly` instead of `Acceptance bullets verbatim` to handle prose Acceptance sections without forcing formatting churn?
