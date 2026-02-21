---
title: ALP 2083 and ALP 2085 MCP Review for Context Matters
type: research
tags: [context-matters, mcp, code-review, alp-2083, alp-2085]
summary: Focused review found both ALP 2083 and ALP 2085 passing with no blocking findings.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-2054` against `origin/nancy/ALP-2054` for ALP 2083 and ALP 2085 only. Both issues pass the stated acceptance criteria. No target codebase files were modified.

## Project Metadata

- Language: Rust workspace, plus cm-web frontend checks.
- Relevant crate: `crates/cm-cli`.
- Build and verification: `cargo test -p cm-cli --test mcp_protocol_test`, `just check`.
- fmm indexed: yes, structural orientation used fmm first.

## Architecture

The reviewed changes sit in the MCP boundary:

- `tools.toml` remains the source of truth for public tool documentation.
- `crates/cm-cli/build.rs` generates MCP input schemas into `crates/cm-cli/src/mcp/generated_schema/*.json`.
- `crates/cm-cli/src/mcp/tools/*.rs` handlers perform runtime preflight for removed public scope inputs before capability calls.
- `crates/cm-cli/tests/mcp_protocol/*.rs` verifies protocol level schemas, request handling, and generated artifact boundaries.

## Key Patterns

- MCP input schema generation is centralized in `generate_mcp_schema`, which now emits top level `additionalProperties: false` for every generated tool input schema at `crates/cm-cli/build.rs:212`.
- Removed public scope fields are rejected through shared preflight `reject_removed_scope_inputs`, called before normal parsing or domain validation in non-scope tools.
- Public request boundary docs explicitly distinguish request inputs from persisted or response data fields, allowing `scope_path` and `scope_mode` in output schemas where they identify stored data.

## Detailed Findings

### ALP 2083: PASS

Acceptance: decide on closed MCP schemas or document runtime boundary. If strict, generated input schemas include `additionalProperties: false` and reproducibility tests pass.

Evidence:

- `build.rs` emits `"additionalProperties": false` into every generated input schema at `crates/cm-cli/build.rs:212` to `crates/cm-cli/build.rs:216`.
- Generated schema examples confirm the emitted field:
  - `crates/cm-cli/src/mcp/generated_schema/cx_get.json:3` to `crates/cm-cli/src/mcp/generated_schema/cx_get.json:17`.
  - `crates/cm-cli/src/mcp/generated_schema/cx_stats.json:3` to `crates/cm-cli/src/mcp/generated_schema/cx_stats.json:15`.
- A direct `jq` check over all `crates/cm-cli/src/mcp/generated_schema/*.json` showed each tool input schema has `additionalProperties` set to `false`: `cx_browse`, `cx_deposit`, `cx_export`, `cx_forget`, `cx_get`, `cx_recall`, `cx_stats`, `cx_store`, `cx_update`.
- Protocol tests assert the advertised tools list carries this constraint for every tool at `crates/cm-cli/tests/mcp_protocol/tools_list.rs:117` to `crates/cm-cli/tests/mcp_protocol/tools_list.rs:126`.
- Reproducibility and boundary tests assert generated migrated scope schemas remain current at `crates/cm-cli/tests/mcp_protocol/tools_list.rs:198` to `crates/cm-cli/tests/mcp_protocol/tools_list.rs:238`.
- Documentation records the public request boundary in `tools.toml:47` to `tools.toml:53`.

Verification:

- `cargo test -p cm-cli --test mcp_protocol_test`: passed, 14 tests.
- `just check`: passed. It reported no frontend fixes applied and left `git status --short` clean.

### ALP 2085: PASS

Acceptance: decide stale scope field handling for non-scope MCP tools. If global rejection, preflight applies to non-scope tools and protocol tests cover `cx_stats`, `cx_get`, `cx_update`, `cx_forget`.

Evidence:

- `cx_get` calls `reject_removed_scope_inputs(args)?` before parsing at `crates/cm-cli/src/mcp/tools/get.rs:12` to `crates/cm-cli/src/mcp/tools/get.rs:14`.
- `cx_update` calls the same preflight before parsing at `crates/cm-cli/src/mcp/tools/update.rs:12` to `crates/cm-cli/src/mcp/tools/update.rs:14`.
- `cx_forget` calls the same preflight before parsing at `crates/cm-cli/src/mcp/tools/forget.rs:19` to `crates/cm-cli/src/mcp/tools/forget.rs:22`.
- `cx_stats` calls the same preflight before reading `tag_sort` at `crates/cm-cli/src/mcp/tools/stats.rs:11` to `crates/cm-cli/src/mcp/tools/stats.rs:18`.
- Protocol coverage includes all four non-scope tools in `protocol_non_scope_tools_reject_removed_scope_inputs` at `crates/cm-cli/tests/mcp_protocol/tool_calls.rs:166` to `crates/cm-cli/tests/mcp_protocol/tool_calls.rs:204`.
- The test asserts responses contain `has been removed`, which confirms stale field rejection happens before domain errors such as empty ID arrays or missing entries.

## Dependencies

- `serde_json` builds and inspects schema JSON.
- `serde` deserializes MCP request structs.
- `cm_capabilities` provides capability request types and domain operations.
- `cm_core` provides `ContextStore` and write context abstractions.

## Relevance to Helioy

This change tightens the public MCP surface for context-matters, which is the primary memory layer in Helioy. The generated schema boundary should reduce stale field drift across Codex tools, cm-web, and future agents that rely on `cx_*` tools.

## Open Questions

- Non-scope handlers still do not globally reject arbitrary unknown fields at runtime. For example, a direct JSON-RPC call to `cx_stats` with `bogus_field` succeeds because strictness is currently expressed through advertised MCP schemas, not a universal runtime validator. This is nonblocking for ALP 2083 as stated, but should be clarified if future work requires server side strict validation for every unknown field.
