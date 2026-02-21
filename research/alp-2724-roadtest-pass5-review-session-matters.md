---
title: ALP-2724 Road Test Pass 5 Review
type: research
tags: [session-matters, linear, cli, mcp, review]
summary: Pass 5 horizontal and vertical review found one substantive vertical gap in label visibility across enumerated MCP session output schemas.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Reviewed the ALP-2724 road test wave as a product surface, with emphasis on gate coherence and vertical traces for `sm get session --show-labels` and `sm capture`. The gate body is coherent and the capture trace is covered, but the label visibility trace has one substantive MCP contract gap across session_get, session_list, and session_run schemas.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Workspace: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters-worktrees/nancy-ALP-2724`
- Structural index: `.fmm.db` present, but `fmm validate` reported all 105 checked files need reindexing, so this review used filesystem inspection as instructed by the warroom brief.

## Architecture

The relevant path is CLI clap definitions in `crates/sm-cli/src/cli/cli_def.rs`, CLI dispatch in `crates/sm-cli/src/cli/get.rs` and `capture.rs`, request contracts in `crates/sm-core/src/proto.rs`, daemon handling in `crates/sm-daemon/src/handler.rs`, MCP bridge handling in `crates/sm-daemon/src/mcp_tools.rs`, and generated MCP schemas under `crates/sm-cli/src/mcp/generated_schema/`.

## Detailed Findings

### Finding: label visibility has a vertical MCP output schema gap

Evidence:

- `sm_core::Session` carries `labels: Vec<Label>` in `crates/sm-core/src/session.rs`.
- MCP `session_get`, `session_list`, and `session_run` return full session values through `crates/sm-daemon/src/mcp_tools.rs`.
- Current generated MCP output schemas omit `labels` in `crates/sm-cli/src/mcp/generated_schema/session_get.json`, `session_list.json`, and `session_run.json`.
- ALP-2745 owns the label model and `sm get session --show-labels`, but its acceptance only makes CLI rendering and JSON output explicit. It does not explicitly require generated MCP output schemas and their snapshot tests to advertise labels. The source of truth is the `output_schema` blocks in `tools/session.toml` and `tools/run.toml`, rendered by `crates/sm-cli/build.rs`.

Impact: MCP clients can receive labels in data while the published schema says labels do not exist. That undermines the label inspection surface and can let the worker pass while the MCP contract remains stale.

Recommended change:

1. Amend ALP-2745 acceptance to require labels in every enumerated session-record MCP output schema: `session_get`, `session_list`, and `session_run`, with snapshot or schema tests updated accordingly.
2. Amend ALP-2745 affected entry points to name `tools/session.toml`, `tools/run.toml`, `crates/sm-cli/build.rs`, and the generated `session_get.json`, `session_list.json`, and `session_run.json` outputs.
3. Amend ALP-2733 PER acceptance to verify the same schema coverage, so the terminal review mirrors the worker contract.
4. No change is needed for opaque object outputs such as capture, label, or delete, because they do not enumerate a stale session property bag.

## Dependencies

Reviewed live Linear state for ALP-2724, ALP-2726, ALP-2733, ALP-2743, ALP-2744, ALP-2745, ALP-2746, ALP-2747, ALP-2748, ALP-2749, and ALP-2752. Read `helioy-tools:linear-workflows` and `moe-issue-review-workflow.md` before reasoning.

## Relevance to Helioy

This is a contract integrity issue across Helioy's CLI, MCP, and daemon layers. The issue is small but material because MCP schemas are part of the machine consumed surface and must not drift from returned session records.

## Open Questions

- None for this pass. The capture vertical trace appears adequately covered by ALP-2748 plus PER criteria.

## Final Pass 5 Sign-off

After re-fetching live Linear state for ALP-2745, ALP-2746, ALP-2733, and ALP-2726, the consensus changes were confirmed applied. ALP-2745 owns the cross-tool label schema invariant across `session_get`, `session_list`, and `session_run`; ALP-2746 coordinates on `tools/run.toml` without owning the output schema block; ALP-2733 mirrors the PER check. Final sign-off sent on bus topic `2724-roadtest-review-pass5` with the exact clean phrase requested.
