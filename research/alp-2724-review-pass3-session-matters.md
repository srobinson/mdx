---
title: ALP-2724 Review Pass 3 Findings for session-matters
type: research
tags: [session-matters, linear, cli, mcp, help-generation]
summary: Pass 3 found two substantive W4b contract holes around decomposed help-source loading and full generated artifact parity.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

MoE pass 3 reviewed the live ALP-2724 Linear tree and current `session-matters` source. The review conditionally signed off on the tree, with two required ALP-2735 amendments covering the shared runtime registry and full generated MCP/doc artifact parity after `tools.toml` decomposition.

## Project Metadata

- Language: Rust
- Build system: Cargo workspace with `just check && just build && just test` as the required gate
- Indexed: `.fmm.db` exists in the repo root
- Relevant sources: `tools.toml`, `crates/sm-cli/build.rs`, `crates/sm-core/src/tool_contracts.rs`, generated CLI/MCP artifacts under `crates/sm-cli/src/`

## Architecture

`tools.toml` is the current single source for public tool contracts. `crates/sm-cli/build.rs` reads it and generates CLI help constants, MCP schema files, MCP generated instructions, skill templates, and README sections. Runtime code also uses the same contract model through `sm_core::tool_contracts::contract_registry()`.

## Detailed Findings

### 1. ALP-2735 omits the shared runtime registry

ALP-2735 requires deleting the root `tools.toml` and updating the build script to glob `tools/*.toml`. Current source also embeds `tools.toml` in `crates/sm-core/src/tool_contracts.rs` through `include_str!("../../../tools.toml")`, then parses that embedded string in `contract_registry()`. Updating only `crates/sm-cli/build.rs` would leave `sm-core` broken or stale after root `tools.toml` is removed.

Recommended amendment: add `crates/sm-core/src/tool_contracts.rs` as a stable entry point and require the shared registry loader used by runtime code and MCP handlers to consume the decomposed source.

### 2. ALP-2735 parity oracle is too narrow

ALP-2735 acceptance currently asserts byte-identical `crates/sm-cli/src/cli/generated_help.rs` output. The same registry also drives MCP generated schemas, generated server instructions, generated README sections, and daemon MCP contract behavior. ALP-2634 explicitly shipped generated MCP schemas, instructions, and snapshots, so W4b needs to protect that surface too.

Recommended amendment: require full registry equivalence and generated artifact parity for `generated_help.rs`, `src/mcp/generated_schema.rs`, `src/mcp/generated_schema/*.json`, `src/mcp/generated_instructions.rs`, and generated README sections, allowing only source path comment text to change from `tools.toml` to `tools/*.toml`.

## Dependencies

Critical dependencies in this finding path:

- `crates/sm-cli/build.rs`: generates CLI help, MCP schemas, instructions, templates, and README from the tool registry.
- `crates/sm-core/src/tool_contracts.rs`: parses the tool contract registry for runtime and daemon consumers.
- `tools.toml`: current monolithic source slated for decomposition by ALP-2735.

## Relevance to Helioy

This review protects the Helioy session control surface from a partial source-layout migration where CLI help remains correct but MCP schemas, generated instructions, README docs, or runtime contract registration drift.

## Open Questions

No further substantive blockers were found in W5's `tools/*.toml` scan wording, ALP-2625 prerequisite alignment, or PER coverage after the W4b restructure, assuming the two ALP-2735 amendments are applied.
