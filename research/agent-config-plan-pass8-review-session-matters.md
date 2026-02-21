---
title: ALP-2763 agent config plan pass 8 review
type: research
tags: [session-matters, linear, moe-review, agent-config, rust]
summary: Pass 8 fresh eyes review found no substantive blockers in the ALP-2763 Linear tree.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Executive Summary

Pass 8 reviewed the live Linear tree for `ALP-2763`, `Make sm run --agent-config honest and debuggable`, against selector-compatible shape, Universal Issue Rules, source reference integrity, verification determinism, acceptance falsifiability, plan document coherence, and worker label suitability. The result was clean signoff: no substantive blockers were found. One cosmetic residue remains in the superseded planning snapshot, but the snapshot header makes Linear authoritative and prevents execution ambiguity.

## Project Metadata

* **Project:** `littleorgans/session-matters`
* **Language:** Rust workspace
* **Indexed shape:** fmm validated `.fmm.db` successfully on 2026-05-23, covering 104 indexed files and 16,543 LOC.
* **Crate layout:** `crates/sm-cli` 50 files, `crates/sm-daemon` 21 files, `crates/sm-core` 15 files, `crates/sm-store` 11 files, `crates/sm-driver` 6 files, `crates/sm-paths` 1 file.
* **Relevant tools:** Linear MCP for live issue state, fmm for source topology, `cargo`, `cargo-insta`, `just`, `rtm` for verification prerequisites.

## Architecture

`session-matters` is the session control plane. `smd` owns durable session records and the MCP surface, while `sm` is the local CLI. The `ALP-2763` plan targets the `--agent-config` path through CLI request construction, MCP request construction, daemon resolution, persistence, generated schemas, generated help, and post execution review coverage.

Relevant source entry points resolve in current source:

* `crates/sm-daemon/src/handler.rs`: `DaemonState::spawn` constructs and persists `Session`; current `agent_config` assignment is at lines 132 to 212, with the field set at line 176.
* `crates/sm-daemon/src/agent_config.rs`: current resolver helpers and `is_path_like` live at lines 16 to 96; current `is_path_like` is lines 56 to 61.
* `crates/sm-daemon/src/mcp_tools.rs`: `agent_run` reads `dir` or `workspace` and constructs `SpawnRequest` at lines 116 to 164.
* `crates/sm-cli/src/cli/run.rs`: `spawn_session` constructs the CLI side `SpawnRequest` at lines 20 to 71.
* `crates/sm-core/src/session.rs`: `Session.agent_config: Option<String>` is line 83.
* `crates/sm-store/src/sqlite/sessions.rs`: `session_from_row` reads `agent_config` at lines 271 to 298, specifically line 290.
* `crates/sm-cli/build.rs`: generated schema output is lines 184 to 199, docs and help output is lines 201 to 225, generated CLI help rendering is lines 256 to 289.
* `crates/sm-cli/tests/common/mod.rs`: `rtm_bin` verification prerequisite lookup is lines 230 to 239.

## Key Patterns

* The filed workers use source files and symbols as entry points rather than brittle line anchors in Linear bodies.
* The generated surface is guarded by source of truth changes in `tools/run.toml`, build output regeneration, snapshots, and `cargo build && git diff --exit-code`.
* The PER mirrors every worker Acceptance section exactly, which gives post execution reviewers a self-contained checklist.
* The gate encodes selector authority through a single `Execute:` line and one structural dependency, `ALP-2766` before `ALP-2767`.

## Detailed Findings

### Live Linear structure

Live Linear state was read for `ALP-2763` through `ALP-2773`.

* Master: `ALP-2763`, status `Todo`.
* Execution parent: `ALP-2764`, title `Backlog`, parent `ALP-2763`, status `Todo`.
* Workers: `ALP-2765` through `ALP-2771`, all parented to `ALP-2764`, all status `Todo`, all labeled `rust-engineer`.
* PER: `ALP-2772`, parent `ALP-2764`, status `Todo`, label `Post Execution Review`.
* Gate: `ALP-2773`, title `Gate review: agent-config-plan`, parent `ALP-2763`, status `Worker Done`.
* Comments: no comments were present on `ALP-2763` through `ALP-2773` at review time.

Selector-compatible shape holds. The gate `Execute:` list is exactly `ALP-2765, ALP-2766, ALP-2767, ALP-2768, ALP-2769, ALP-2770, ALP-2771, ALP-2772`. The required order states `ALP-2766 before ALP-2767`; Linear relations confirm `ALP-2766` blocks `ALP-2767`.

### Cross-reference integrity

The PER subsections for `ALP-2765` through `ALP-2771` were compared against each worker issue's live Acceptance section. All seven subsections matched exactly after whitespace normalization.

Gate design call references resolve against worker content:

* Persistence shape maps to `ALP-2765`, which requires resolved filesystem path persistence.
* Predicate location maps to `ALP-2766`, which moves `is_path_like` to `sm-core`, and `ALP-2767`, which depends on it.
* Schema strictness maps to `ALP-2768`, including `serde(deny_unknown_fields)` and `[env]` precedence.
* MCP workspace alias removal maps to `ALP-2769`, including `dir` required and `workspace` input removal.

No stale worker ID, stale quoted acceptance text, missing PER subsection, or gate ordering drift was found.

### Verification determinism

Verification commands were reviewed for copy paste safety and flake risk.

* `cargo build && git diff --exit-code` is a deterministic generated output lockstep guard for `tools/run.toml` changes.
* `cargo insta test --accept -p sm-cli` is appropriate for snapshot regeneration, and `ALP-2769` names `cargo-insta` as a precondition.
* `cargo run -p sm-cli --bin sm -- run --help | grep -F ...` uses fixed string search and safe single quoted patterns.
* `DaemonFixture` based tests depend on `RTM_TEST_BIN`, sibling `../runtime-matters/target/debug/rtm`, or `rtm` on `PATH`; `ALP-2767`, `ALP-2771`, and the PER document that precondition. The referenced helper confirms that lookup order in `crates/sm-cli/tests/common/mod.rs:230-239`.
* Local preflight confirmed both `cargo-insta` and `rtm` were available in the current environment.

No verification block required a conditional edit.

### Acceptance falsifiability

Every worker Acceptance bullet is falsifiable from one of these concrete observables:

* File content: `tools/run.toml`, generated schemas, generated help, handler source, direct dependencies.
* Command exit code: `cargo test`, `cargo build`, `git diff --exit-code`, `cargo insta`.
* Command output substring: `sm run --help` grep checks.
* Structured output: `sm get session "id:$SESSION_ID" --json` and `Session.agent_config` fields.
* Named test behavior: `agent_config_env_reaches_spawn_driver`, new daemon tests, MCP protocol harness tests, help surface tests.

The PER can verify the outcome without subjective interpretation.

### Plan document coherence

`~/.mdx/projects/agent-config-plan.md` has a strong superseded header at line 3: it describes the file as a 2026-05-22 planning snapshot, names the live Linear tree, and states that Linear is authoritative. Line 8 still says the snapshot is awaiting clean re signoff. That is cosmetic historical residue under the header's framing, not a blocker for execution or review.

### Multi-crate worker label consistency

All seven workers use the Linear `rust-engineer` Agent Role label. The label exists and is suitable for Nancy dispatch. Multi-crate scope is already encoded in each worker's entry points and verification commands. Adding labels such as `multi-crate` or per-crate hints would not change dispatch behavior and would add routing noise.

## Dependencies

Critical dependencies and what they provide:

* `cargo`: package build and test execution.
* `cargo-insta`: snapshot update and acceptance for MCP schema snapshots.
* `rtm`: runtime-matters binary needed by `DaemonFixture` integration tests.
* fmm: indexed source topology, symbol outlines, exact symbol reads, dependency graphs.
* Linear: source of truth for issue shape, gate status, parentage, labels, and relations.

## Relevance to Helioy

The `ALP-2763` issue tree is ready for Nancy execution under the existing selector-compatible structure. The pass 8 review found no execution-changing defect. The cosmetic plan snapshot residue can remain because the live Linear tree is authoritative.

## Open Questions

None for execution. Optional cleanup: update `~/.mdx/projects/agent-config-plan.md:8` to remove the obsolete awaiting re signoff text if someone wants the historical snapshot to read cleaner.
