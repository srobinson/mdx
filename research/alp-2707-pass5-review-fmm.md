---
title: ALP-2707 Pass 5 Issue Review
type: research
tags: [fmm, linear, issue-review, moe, outline]
summary: Fresh-eyes review found six conditional fixes, then verified the applied edits and signed off on pass 5.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

ALP-2707 defines the `fmm_file_outline` default density uplift: default-on signature, visibility, declaration kind, inline freshness annotation, and removal of legacy suffix markers. Pass 5 found no new implementation blockers beyond six issue-spec corrections needed for worker self-sufficiency, documentation anchoring, release-please changelog mechanics, and performance guardrail calibration.

## Project Metadata

- Language: Rust workspace with CLI and MCP server.
- Indexed topology: 399 files, 57,438 LOC via `fmm_list_files(group_by: subdir)`.
- Major buckets: `crates/` 375 files, `fixtures/` 23 files, `npm/` 1 file.
- Verification runner: project `CLAUDE.md` requires `just test`, `just check`, `just ci`; direct `cargo test` is forbidden.
- Release automation: `release-please-config.json` uses `release-type: simple`; visible changelog sections are `feat`, `fix`, and `perf`.

## Architecture

Relevant live code shape:

- `crates/fmm-core/src/format/yaml_formatters.rs`: `format_file_outline` spans lines 22-259, 238 lines, and is the renderer refactor target.
- `crates/fmm-core/src/parser/builtin/python/mod.rs`: 620 LOC, close to the repo 700 LOC ceiling.
- `crates/fmm-store/src/schema.rs`: owns `SCHEMA_VERSION`, `ensure_schema`, drop and recreate helpers, and `CREATE_SCHEMA_SQL`.

ALP-2707 Linear tree:

- Master: ALP-2707.
- Execution parent: ALP-2708.
- Gate: ALP-2709, `Worker Done`.
- Workers: ALP-2717 through ALP-2721.
- Post execution review: ALP-2722.

## Detailed Findings

### 1. Worker dependency notes are not self-sufficient

ALP-2717 §Dependency notes says `Blocks W2, W3, W4, W5`. ALP-2719 §Dependency notes says `Blocked by W1. Parallel with W2, W4, W5`. The W notation is not defined in those worker bodies. ALP-2718, ALP-2720, and ALP-2721 use explicit ALP IDs, so ALP-2717 and ALP-2719 should be rewritten to use issue IDs.

### 2. ALP-2721 has pointer-only canonical visibility values

ALP-2709 enumerates the canonical visibility set: `public, crate, protected, private, non_exported`. ALP-2721 restates only `the five canonical values`, which forces the renderer worker to chase ALP-2709 or another worker. ALP-2721 should enumerate the five values directly.

### 3. README target is ambiguous

Live `README.md` has `## MCP Tools` at line 82 and only a table row for `fmm_file_outline` at line 102. There is no `## fmm_file_outline` section. ALP-2721 and ALP-2722 should agree on whether the worker creates a new section or extends the MCP tools row. The PER anchor must match the worker acceptance wording.

### 4. CHANGELOG mechanism is underspecified

`CHANGELOG.md` contains released sections only, with no Unreleased heading. `release-please-config.json` marks `feat`, `fix`, and `perf` as visible changelog sections, while `docs`, `refactor`, `chore`, `test`, and `ci` are hidden. ALP-2721 and ALP-2722 should name release-please as the mechanism and specify a breaking feature commit shape, such as `feat!:` or `feat:` with a `BREAKING CHANGE:` footer, rather than directing manual CHANGELOG edits.

### 5. Performance wall-time tolerance is too coarse unless labeled as an outer bound

The consensus ledger estimates signature overhead at less than 1 microsecond per export and visibility plus kind as no parse overhead. The README claims about 1,500 files per second and less than 1 ms per file parse. For this 399 file, 57,438 LOC repo, the index size guardrail is defensible against the 50K LOC consensus estimate, but the ALP-2722 `≤2x` wall-time threshold is a round-number outer bound, not calibrated to expected overhead. ALP-2722 should tighten it or explicitly label it as a coarse outer-bound guardrail while recording the expected overhead.

## Dependencies

Critical files and artifacts reviewed:

- `README.md` lines 82-102 and 171-176.
- `CHANGELOG.md` release section shape.
- `release-please-config.json` lines 1-32.
- `~/.mdx/projects/fmm-uplift-consensus.md` lines 21-36 and 112-119.
- Linear issues ALP-2707 through ALP-2722 and issue comments.

## Relevance to Helioy

This review hardens autonomous Nancy issue execution by removing pointer-only instructions and ensuring workers can be executed from their own issue bodies. The release-please finding also protects Helioy release flow from manual changelog drift.

## Round 2 Verification

The orchestrator applied all six pass 5 edits. Live re-fetch of ALP-2717, ALP-2719, ALP-2721, and ALP-2722 verified:

- ALP-2717 and ALP-2719 dependency notes now use ALP IDs instead of W notation.
- ALP-2721 enumerates `public, crate, protected, private, non_exported` in the backwards compatibility restatement.
- ALP-2721 and ALP-2722 now agree that README work must update the existing `fmm_file_outline` table row and add a new `## fmm_file_outline` sub-section beneath the table with an example output block.
- ALP-2721 and ALP-2722 now name release-please, forbid manual `CHANGELOG.md` edits, and specify `feat!:` or `feat:` plus `BREAKING CHANGE:` footer as the release-notes path.
- ALP-2722 now uses a ≤25% practical wall-time tolerance with expected-overhead documentation and keeps ≥2x as a hard-fail outer-bound guardrail.

Signoff sent to peer and orchestrator: `I sign off on the ALP-2707 filed tree as currently applied (pass-5)`.

## Open Questions

None for pass 5.
