---
title: ALP-2724 Pass 5 Review Findings for session-matters
type: research
tags: [session-matters, linear, cli, review, moe]
summary: Pass 5 cold-read review found two substantive issue-tree gaps around Cargo rebuild invalidation and generated doc/template noun drift.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

A live Linear and source audit of the ALP-2724 issue tree found two substantive gaps. ALP-2735 should bind Cargo rebuild invalidation for decomposed `tools/*.toml` inputs, and ALP-2731 should explicitly include generated documentation and skill template surfaces that still hardcode removed `agent` CRUD commands.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Workspace root: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`
- fmm: `.fmm.db` present, 100 indexed files, 15,034 LOC under `crates/`
- Build and verification gate: `just check && just build && just test`

## Architecture

- CLI build pipeline starts in `crates/sm-cli/build.rs`.
- Runtime contract registry lives in `crates/sm-core/src/tool_contracts.rs`.
- CLI grammar lives in `crates/sm-cli/src/cli/cli_def.rs`.
- Daemon selector error labels flow through `crates/sm-daemon/src/handler.rs`.
- Generated documentation and MCP instruction text flow through `crates/sm-cli/src/tool_docs.rs` and committed templates under `crates/sm-cli/templates/`.

## Key Patterns

- `tools.toml` is currently a single source consumed by both the CLI build script and `sm-core` runtime registry.
- The issue tree intentionally preserves MCP `agent_*` compatibility aliases while removing `agent` and `agents` from the CRUD CLI surface.
- Build system changes that glob new input files must also define Cargo invalidation semantics, otherwise incremental builds can reuse stale generated output.

## Detailed Findings

### 1. ALP-2735 should explicitly bind Cargo rebuild invalidation

Current source only invalidates the monolithic input:

- `crates/sm-cli/build.rs:18` emits `cargo:rerun-if-changed=../../tools.toml`.
- `crates/sm-cli/build.rs:25-27` reads and parses `../../tools.toml`.
- `crates/sm-core/src/tool_contracts.rs:13-18` initializes the registry from the embedded `TOOLS_TOML` string.

ALP-2735 acceptance #7 requires the build pipeline to tolerate new `tools/*.toml` files without further code changes. That should explicitly require `cargo:rerun-if-changed` coverage for the `tools/` directory and each discovered `tools/*.toml` file, or an equivalent generated manifest/input path. Without that contract, an implementation can aggregate the new files but still leave stale generated artifacts during incremental builds.

### 2. ALP-2731 should explicitly cover generated docs and skill templates with removed CRUD forms

Live source still hardcodes removed CRUD CLI forms in generated documentation sources and templates:

- `crates/sm-cli/src/tool_docs.rs:21` uses `sm get agents`.
- `crates/sm-cli/src/tool_docs.rs:64-65` uses `sm get agent`, `sm get agents`, and `sm delete agent`.
- `crates/sm-cli/templates/SKILL.md:16-23` maps `session_list`, `session_get`, and `session_delete` to old `sm get agents`, `sm get agent`, and `sm delete agent` CLI forms.

ALP-2731 mentions generated README sections and no removed surfaces, but its falsifying static check is framed around `AGENT_*` constants and generated artifacts. The worker should explicitly cover `tool_docs.rs` and committed skill template outputs. PER should mirror these surfaces if they are committed deliverables.

### Probe Outcomes Without Substantive Findings

- Snapshot directory contains `agent_*` MCP alias snapshots and `agent_config` references. These are MCP compatibility or runtime config terms, not CRUD CLI noun drift.
- W5 acceptance #9 is sufficient for snapshot regeneration after source and tests are corrected.
- Cargo package metadata and crate-level rustdoc probes did not surface semantic `agent` CRUD references.
- Tracing and log macro probes did not surface semantic `agent` CRUD message templates in `sm-cli`, `sm-daemon`, or `sm-core`.

## Peer Convergence

After the first audit position, the Claude peer independently returned the same two substantive conditional signoff items: ALP-2735 needs explicit Cargo rerun trigger coverage for decomposed `tools/` inputs, and ALP-2731 needs generated documentation plus packaged skill template coverage for removed CRUD CLI forms, mirrored in PER. No additional substantive findings were raised by either pane.

## Round 2 Re verification

The orchestrator applied consensus edits to ALP-2735, ALP-2731, and ALP-2733. I re-fetched all three issues live via Linear MCP. ALP-2735 now binds Cargo `rerun-if-changed` coverage in acceptance #8; ALP-2731 now covers `crates/sm-cli/src/tool_docs.rs` and `crates/sm-cli/templates/SKILL.md` in acceptance #9 and #10; ALP-2733 mirrors both in acceptance #7 and #8. I sent the exact clean sign-off phrase: `I sign off on the ALP-2724 tree as currently filed`.

## Dependencies

- `mcp__linear__`: fetched ALP-2724, ALP-2725, ALP-2726, ALP-2727, ALP-2728, ALP-2729, ALP-2730, ALP-2735, ALP-2731, ALP-2732, and ALP-2733 live.
- `mcp__fmm__`: used for topology, file outlines, and targeted symbol reads before shell probes.
- `rg` and `find`: used for non-source snapshot and literal-string probes not covered by fmm.

## Relevance to Helioy

The findings protect Nancy execution quality for Helioy issue trees. They prevent hidden incremental-build drift after a help-source layout change and ensure public generated documentation does not keep teaching removed CRUD forms.

## Open Questions

- Whether `crates/sm-cli/templates/SKILL.md` is a committed deliverable or a generated artifact. If it is committed, PER should inspect it directly.
- Which implementation strategy ALP-2735 will choose for `sm-core` registry reconciliation, and where the final invalidation manifest should live.
