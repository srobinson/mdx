---
title: ALP-2724 Road Test Wave Pass 4 Review
type: research
tags: [session-matters, linear, moe-review, alp-2724]
summary: Pass 4 review found copy paste safety, precondition, protocol note, line-cap, and generated-artifact ownership blockers in the ALP-2724 road-test wave.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Reviewed the ALP-2724 road-test corrective wave live from Linear and current source. fmm is present but unusable in this worktree because the index schema is version 6 while the available fmm tool expects version 5, so source verification used filesystem inspection.

Pass 4 produced a conditional sign-off with five substantive changes: copy-paste-safe verification commands, uniform live-proof preconditions, an explicit ALP-2748 protocol note, a line-cap guard for `handler.rs`, and generated-artifact ownership for tools-touching workers.

## Project Metadata

- Language: Rust.
- Build system: Cargo workspace with `just` wrappers.
- Key crates under review: `sm-cli`, `sm-core`, `sm-daemon`.
- fmm status: `.fmm.db` exists, but `fmm_list_files(group_by="subdir")` failed with `Index schema version 6 does not match fmm schema version 5`.

## Architecture Notes

`session-matters` uses `sm` as the CLI surface, `smd` as the daemon/API server, and `runtime-matters` via rtmd for actual runtime process operations. The capture path currently has three layers:

- `crates/sm-core/src/proto.rs:224-228`: `CaptureRequest` contains `selector` and optional `scrollback_lines`.
- `crates/sm-daemon/src/handler.rs:234-247`: `smd` resolves the selector, takes the first session, then calls the runtime driver with the concrete session id and scrollback lines.
- `crates/sm-cli/src/cli/capture.rs`: CLI constructs the `CaptureRequest` from `--selector`.

The ALP-2748 change therefore tightens CLI, MCP schema, sm-core RPC, and daemon behavior. Based on current source, the smd to rtmd call shape is already concrete session id plus scrollback lines, so no rtmd protocol bump is implied unless implementation discovers a deeper runtime API dependency.

## Detailed Findings

### 1. Verification commands are not copy-paste safe

Linear verification text contains commands with literal angle-bracket placeholders, including `sm get namespace <slug>`, `--target <safe-target>`, `sm get session <id-a>`, `sm capture <session-id>`, and `sm delete session <id>`. In a real shell these parse as redirection.

Affected issues: ALP-2743, ALP-2745, ALP-2746, ALP-2748.

Required change: replace these with variable setup such as `TARGET_A=...`, `SESSION_A=...`, `NS=...`, then quoted variable usage in commands.

### 2. Live proof preconditions are inconsistent

Several workers create or inspect sessions but do not uniformly state the runtime prerequisites. Workers should name whether they require:

- Built binary on PATH or explicit `./target/.../sm`.
- Matching freshly started `smd` for handler or MCP registry changes.
- Compatible `rtmd` running for session creation or capture.
- Runtime binary such as `claude` on PATH.
- Safe tmux targets created or verified free.

Affected issues: ALP-2745, ALP-2746, ALP-2748, ALP-2752.

### 3. ALP-2748 needs explicit protocol statement

Source evidence:

- `crates/sm-core/src/proto.rs:224-228` currently defines capture as selector-based at the sm-core/smd RPC layer.
- `crates/sm-daemon/src/handler.rs:234-247` resolves the selector and calls runtime capture by concrete session id.

Required change: ALP-2748 should state that it changes CLI, MCP schema, sm-core request shape, and smd handler semantics, but does not bump the smd to rtmd capture protocol unless the implementation discovers otherwise.

### 4. `handler.rs` is close to the 700-line cap

Line counts at current HEAD:

- `crates/sm-cli/src/cli/cli_def.rs`: 342.
- `crates/sm-cli/src/cli/run.rs`: 204.
- `crates/sm-cli/build.rs`: 255.
- `crates/sm-cli/src/cli/generated_help.rs`: 118.
- `crates/sm-cli/tests/cli_help_surface_test.rs`: 95.
- `crates/sm-daemon/src/handler.rs`: 682.

ALP-2748 affects `handler.rs`; a net addition over 18 lines would breach the project cap. The worker should either keep the net delta within cap, delete or refactor first, or run after a dependency that reduces the file.

### 5. Tools changes regenerate more artifacts than most worker bodies name

`crates/sm-cli/build.rs:113-152` writes:

- `crates/sm-cli/src/mcp/generated_schema.rs`.
- JSON schema snapshots under `crates/sm-cli/src/mcp/generated_schema/`.
- `crates/sm-cli/src/mcp/generated_instructions.rs`.
- `crates/sm-cli/src/cli/generated_help.rs`.
- `crates/sm-cli/templates/SKILL.md`.
- Root `README.md`.

Workers that edit `tools/*.toml` or delete `tools/link.toml` should explicitly say that `just build` regenerates these surfaces and that the worker commits all resulting diffs. This is important for `--show-labels`, `sm capture <SESSION_ID>`, alias-pending-schedule-matters copy, and `sm link` removal.

Affected issues: ALP-2744, ALP-2745, ALP-2746, ALP-2748, ALP-2749, ALP-2752.

## Dependencies

The conditional sign-off was sent to:

- Peer: `nancy-ALP-2724:helioy-tools:codebase-analyst:1:3.1`.
- Orchestrator CC: `nancy-ALP-2724:general:1:2.2`.
- Topic: `2724-roadtest-review-pass4`.

## Open Questions

- Await peer response and orchestrator amendments.
- Re-read live Linear before any clean sign-off, since issue bodies may change after the conditional findings are applied.

## Peer Follow-up Findings Verified

After the initial conditional sign-off, the peer reviewer concurred with findings 1 through 5 and proposed two additional substantive findings. Both were verified against live source and accepted into the shared conditional list.

### 6. `tool_docs.rs` owns stale README command examples

`crates/sm-cli/src/tool_docs.rs:6-29` hardcodes the README preamble, including:

- `sm capture --selector id:<session-id>`.
- `sm logs id:<session-id>`.

Because `crates/sm-cli/build.rs` renders `README.md` from `tool_docs.rs`, generated README output can remain stale unless the Rust source is updated. ALP-2747 or the assigned worker should add `crates/sm-cli/src/tool_docs.rs` to affected files and verify no stale CLI command shapes remain in the hardcoded README preamble.

### 7. `tools/run.toml` owns stale `link` workflow narrative

`tools/run.toml:5-20` contains the `[skill] workflow` source, including the line `Use logs for daemon-spawned headless transcripts, and link only for unmanaged sessions.` This flows into `crates/sm-cli/templates/SKILL.md` and `crates/sm-cli/src/mcp/generated_instructions.rs`.

ALP-2752 should name `tools/run.toml` explicitly so removal of `sm link` covers the narrative source, not only `tools/link.toml`, CLI dispatch, MCP registry, and generated outputs.

## Current Sign-off Position

Both reviewers have converged on a seven-item conditional list for pass 4. If the orchestrator applies all seven changes, re-read live Linear before issuing a round-2 clean sign-off.

## Round 2 Clean Sign-off

The orchestrator reported all seven pass-4 consensus items applied. Re-read live Linear state for ALP-2726, ALP-2743, ALP-2744, ALP-2745, ALP-2746, ALP-2747, ALP-2748, ALP-2749, and ALP-2752.

Verification summary:

- ALP-2743 through ALP-2749 and ALP-2752 now carry codegen regenerate-and-commit acceptance where applicable.
- ALP-2745, ALP-2746, ALP-2748, and ALP-2752 now state setup preconditions and teardown discipline for daemon-affecting manual proof.
- ALP-2743, ALP-2745, ALP-2746, and ALP-2748 verification sections use variable-assignment style rather than literal angle-bracket placeholder commands.
- ALP-2748 now includes the daemon-runtime protocol note, `sm-core` request shape entry point, file-size cap guard, and before/after `wc -l` PR requirement.
- ALP-2747 now owns `crates/sm-cli/src/tool_docs.rs::README_PREAMBLE` and has acceptance for stale README preamble command shapes.
- ALP-2752 now explicitly owns `tools/run.toml` skill-workflow narrative edits and generated downstream removal of `link` references.
- Gate ALP-2726 now records pass-4 findings in Warroom traceability and the docs source-of-truth rule includes README preamble ownership.

Clean sign-off sent on bus topic `2724-roadtest-review-pass4`:

`I sign off on the ALP-2724 road-test wave (ALP-2743..ALP-2749, ALP-2752) as currently filed`
