---
title: ALP-2707 worker breakdown for fmm outline default density
type: research
tags: [fmm, linear, outline, mcp, planning]
summary: Round 2 converged toward five workers plus PER: schema/types, Rust parser, TypeScript parser, Python parser, renderer/docs/freshness, and review.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

ALP-2707 is the master parent for making `fmm_file_outline` denser by default: signature, visibility, kind, suffix removal, and inline freshness when the target file is stale. Round 1 proposed four worker issues plus a post execution review, keeping the broader freshness and output preset work outside this master.

## Project Metadata

- Language: Rust workspace.
- Build system: Cargo workspace with crates `fmm-core`, `fmm-cli`, and `fmm-store`.
- Current workspace version: `0.2.9` in `Cargo.toml`.
- Index signal: `.fmm.db` exists in the repo root.
- Key dependencies: `tree-sitter`, `rusqlite`, `serde`, `serde_json`, `clap`, `rayon`, `chrono`.

## Architecture

The relevant outline path spans parser extraction, serialized core types, SQLite persistence, manifest loading, format rendering, and CLI or MCP exposure.

- Parser contract: `crates/fmm-core/src/parser/types.rs`, especially `ExportEntry`.
- Serialized records: `crates/fmm-core/src/types.rs`.
- Store schema and migration path: `crates/fmm-store/src/schema.rs`.
- Store write path: `crates/fmm-store/src/writer.rs`.
- Store read path: `crates/fmm-store/src/reader/mod.rs`.
- Current outline renderer: `crates/fmm-core/src/format/yaml_formatters.rs`, symbol `format_file_outline`.
- MCP outline tool: `crates/fmm-cli/src/mcp/tools/outline.rs`.
- CLI outline command: `crates/fmm-cli/src/cli/commands/outline.rs`.

## Key Patterns

- The SQLite index is regeneratable. `ensure_schema` reads `SCHEMA_VERSION`, drops existing schema on version mismatch, recreates it, and writes the new schema version. This supports an automatic rebuild decision rather than requiring `fmm clean`.
- Current outline rendering still encodes privacy and non exported status as comments such as `# non-exported`, which ALP-2707 should hard cut in favor of structured `visibility` and `kind` fields.
- `format_file_outline` is already larger than the local refactoring threshold, so implementation should avoid expanding it materially without extracting helper rendering logic.

## Detailed Findings

### Worker decomposition

Proposed workers under ALP-2708:

1. Persist outline metadata for signature, visibility, and kind.
2. Render dense `fmm_file_outline` defaults for MCP and CLI.
3. Add inline stale file annotation to `fmm_file_outline`.
4. Document and regenerate outline contract surfaces.
5. Post execution review for the ALP-2707 batch.

Storage schema and parser extraction were intentionally combined because the persisted metadata contract must land atomically. Splitting them would create a partial state where schema exists without population or parser output exists without a durable store contract.

### Freshness boundary

ALP-2707 should implement only inline stale annotation for `fmm_file_outline`. Broader lookup freshness, multi result freshness annotations, and `strict: true` belong to ALP-2699 or a future master derived from it.

### Compatibility and versioning

The proposed path is a hard cut from suffix comments to structured fields. Treat this as a tool contract minor bump for the MCP and CLI outline surface.

### Format coupling

ALP-2707 may touch existing outline renderers to expose the new data shape. YAML default migration, `--minimal`, `--human`, custom fields, and broader preset work stay out of scope for ALP-2707.

### Required order

`PERSIST-METADATA` before `RENDER-OUTLINE`. `RENDER-OUTLINE` before `OUTLINE-FRESHNESS`. `RENDER-OUTLINE` and `OUTLINE-FRESHNESS` before `DOCS-HELP`. `DOCS-HELP` before `POST-EXECUTION-REVIEW`.

## Dependencies

Critical internal dependencies:

- `fmm-core` owns parser output, manifest model, and formatting helpers.
- `fmm-store` owns SQLite schema, writes, and reads.
- `fmm-cli` owns CLI and MCP command surfaces plus integration tests.

Important tests and verification entry points:

- `crates/fmm-cli/tests/mcp_tools/file_outline.rs`
- `crates/fmm-cli/tests/cli_output_parity/`
- `crates/fmm-cli/tests/cli_file_diagnostics.rs`
- `crates/fmm-cli/tests/mcp_protocol.rs`
- `crates/fmm-core/tests/parser_cross_language/`
- `crates/fmm-store/src/writer_tests.rs`

## Relevance to Helioy

The split is designed for Nancy selector compatibility: a real `Backlog` execution parent, ordered worker issues, one accepted gate body with a closed `Execute:` set, and a separate post execution review issue. The plan keeps Linear as source of truth and avoids letting ALP-2699 scope leak into ALP-2707.

## Round 2 Update

Peer review found valid issues in the Round 1 split. The preferred shape is now five workers plus PER:

1. Schema and record types.
2. Rust parser metadata population.
3. TypeScript parser metadata population.
4. Python parser metadata population.
5. Renderer, inline outline freshness, CLI or MCP help, README, and CHANGELOG.
6. Post execution review.

Accepted corrections:

- Use `just test`, `just check`, and `just ci`, never direct `cargo test`, per repo `CLAUDE.md`.
- Do not overload current `methods.kind`, which stores ALP-922 relationship semantics. Add a separate declaration taxonomy field and preserve the relationship signal under a non-conflicting name.
- Parser workers can land independently after nullable schema fields exist.
- `format_file_outline` should be refactored below the function size ceiling before adding fields.

Conditional signoff changes requested from the peer:

- Keep visibility values exactly to `public`, `crate`, `protected`, `private`, `non_exported`. Use `kind: field` rather than `visibility: private_field`.
- Include `README.md` and `CHANGELOG.md` in the renderer/docs worker if docs are not a separate worker.
- Use stable repo fixtures for manual verification, not external `~/.mdx` test repos.
- Tighten schema migration wording so it does not imply every query path must perform a full reindex.

## Open Questions

- Whether the peer accepts the four conditional signoff edits.
- Whether the orchestrator wants placeholder worker names or generated Linear issue IDs in the final gate body.

## Final Signoff

Peer accepted all four Round 2 conditions and signed off with the exact phrase: `I sign off on the ALP-2707 worker breakdown as currently proposed`.

I also sent final signoff to the orchestrator with the converged tree:

1. W1: Outline density: schema and record types.
2. W2: Rust parser populates signature, visibility, kind.
3. W3: TypeScript parser populates signature, visibility, kind.
4. W4: Python parser populates signature, visibility, kind.
5. W5: Outline renderer: default emit new columns, drop suffix annotations, inline freshness, update README and CHANGELOG.
6. W6: Post execution review: ALP-2707 outline default density uplift.

Required order: W1 before W2, W3, W4, W5. W2, W3, W4, W5 before W6. W2, W3, W4, W5 are independent of each other after W1.

Final binding decisions:

- Visibility values are exactly `public`, `crate`, `protected`, `private`, `non_exported`.
- Fieldness lives in `kind: field`, never as a visibility value.
- `methods.kind` must not be overloaded because it currently stores ALP-922 relationship semantics.
- Verification must use `just test`, `just check`, and `just ci`, never direct `cargo test`.
- W5 owns `README.md` and `CHANGELOG.md` along with renderer, MCP or CLI help, inline freshness, and suffix removal.

## Filed Tree Ratification

Orchestrator applied the tree to Linear and assigned filed worker IDs:

- ALP-2717: Outline density: schema and record types for signature, visibility, declaration_kind.
- ALP-2718: Rust parser populates signature, visibility, declaration_kind.
- ALP-2719: TypeScript parser populates signature, visibility, declaration_kind.
- ALP-2720: Python parser populates signature, visibility, declaration_kind.
- ALP-2721: Outline renderer: default emit signature, visibility, kind, drop suffix annotations, inline freshness.
- ALP-2722: Post execution review: ALP-2707 outline default density uplift.

I re-fetched ALP-2707, ALP-2708, ALP-2709, ALP-2717, ALP-2718, ALP-2719, ALP-2720, ALP-2721, ALP-2722, and the ALP-2708 child list through Linear MCP. Filed bodies matched the converged shape. I sent the clean ratification phrase to the orchestrator: `I sign off on the ALP-2707 filed tree as currently applied`.
