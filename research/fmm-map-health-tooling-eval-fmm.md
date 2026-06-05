---
title: fmm agent map and code health tooling evaluation
type: research
tags: [fmm, codebase-analysis, mcp, cli, code-health, map]
summary: fmm has strong structural primitives for agent generated maps and health triage, but lacks first class map, Git diff, clone detection, and health report commands.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# fmm agent map and code health tooling evaluation

This research mirror summarizes the full report at `~/.mdx/projects/fmm-eval-codex--brainstorm.md`.

## Executive Summary

fmm can power useful agent authored MAP.md and code health triage today because it exposes topology, outlines, symbol reads, dependency graphs, cycles, glossary impact, search, and similarity through both CLI and MCP. The main gaps are higher order workflows: a canonical map model, Git SHA aware snapshots, structural diffs, bulk clone detection, complexity metrics, architecture rules, and ranked health reports.

## Project Metadata

- Language: Rust, edition 2024.
- Workspace crates: `fmm`, `fmm-core`, `fmm-store`, all version `0.3.6`.
- Build system: Cargo workspace, `just` recipes.
- Main dependencies: tree-sitter language crates, `clap`, `rusqlite`, `serde`, `rayon`, `ignore`, `notify`, `chrono`, `regex`, `glob`.
- Current SHA: `5f8a1296d72f507a2e4bd1950001a442dc6b31fc`.
- Index status: `.fmm.db` exists and `fmm validate` reports all 416 source files current.

## Architecture

- `crates/fmm-cli` owns CLI commands, MCP server dispatch, and generated help/schema surfaces. `Commands` is defined in `crates/fmm-cli/src/cli/mod.rs:60-719`. MCP dispatch is in `McpServer.handle_tool_call` at `crates/fmm-cli/src/mcp/mod.rs:308-393`.
- `crates/fmm-core` owns parser registry, manifest, graph, search, similarity, resolver, and formatting modules. Public modules are listed in `crates/fmm-core/src/lib.rs:1-17`.
- `crates/fmm-store` owns SQLite persistence. The schema stores files, exports, methods, reverse dependencies, workspace packages, and metadata in `crates/fmm-store/src/schema.rs:92-171`.

## Key Patterns

- fmm is strongest when used as structural context before broad file reads. `fmm_list_files`, `fmm_file_outline`, `fmm_dependency_graph`, and `fmm_glossary` provide precise starting points.
- Similarity is deterministic and symbol focused. `find_similar` ranks name tokens, signature shape, declaration kind, and dependency neighborhood in `crates/fmm-core/src/similarity.rs:102-170`.
- Freshness is filesystem and fingerprint based, not Git based. Generate and validate use mtime/content fingerprints, while `FMM_GIT_SHA` only affects binary version stamping.

## Detailed Findings

See `~/.mdx/projects/fmm-eval-codex--brainstorm.md` for the complete A to D report requested by the orchestrator.

### Task 1 verdict

Partial. A fine tuned agent can write a useful first MAP.md with fmm today, but fmm lacks a first class map model plus Git SHA and structural diff support.

### Task 2 verdict

Partial. A fine tuned agent can produce useful health triage leads with fmm today, but fmm lacks bulk clone detection, complexity metrics, and a ranked health report.

## Dependencies

Critical dependencies include tree-sitter language parsers for extraction, `rusqlite` for the local index, `clap` for CLI surfaces, `serde`/`serde_json` for typed output, `rayon` for parallel indexing, and `notify` for watch mode.

## Relevance to Helioy

The report gives a buildable roadmap for turning fmm from a navigation substrate into a map and code health substrate for Helioy agents. The highest leverage additions are `fmm map`, Git stamped snapshots, `fmm diff`, and `fmm health`.

## Open Questions

- Should MAP.md be authored entirely by fmm, by an agent using fmm JSON, or by a hybrid `fmm map --json` plus agent prose step?
- Should snapshots live in `.fmm.db`, separate `.fmm/snapshots/*.db`, or committed JSON artifacts?
- Which architecture rules should ship as defaults versus project config?
