---
title: ALP-2707 pass 4 issue review
type: research
tags: [fmm, linear, issue-review, moe, outline-density]
summary: Fresh pass 4 review of the ALP-2707 filed Linear tree found five conditional fixes around shell portability, teardown, timing, and falsifiability.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

ALP-2707 plans the Tier 1 `fmm_file_outline` default density uplift: default `signature`, `visibility`, `kind`, removal of suffix annotations, and inline freshness when the queried file is stale. The filed tree is structurally sound, but pass 4 found five issue body fixes needed before clean signoff.

## Project Metadata

- Language: Rust workspace.
- Crates: `crates/fmm-core`, `crates/fmm-cli`, `crates/fmm-store`.
- Build system: Cargo with `just` workflow wrappers.
- Required verification policy: project `CLAUDE.md` requires `just test`, `just check`, and `just ci`; direct `cargo test` is forbidden except as part of the `just test` recipe for doctests.
- Structural index: `.fmm.db` present and fmm MCP was used for topology and source outlines.

## Architecture

The ALP-2707 plan touches all stages of fmm's outline pipeline:

1. Storage and record types add nullable `signature`, `visibility`, and declaration kind columns.
2. Rust, TypeScript, and Python parsers populate those fields.
3. The YAML renderer changes default `fmm_file_outline` output and removes legacy suffix annotations.
4. CLI, MCP help, README, CHANGELOG, and snapshots document and lock the new contract.
5. PER verifies schema migration, parser fidelity, renderer shape, freshness, boundaries against ALP-2699 and ALP-2704, performance, and verification policy.

## Key Patterns

- Linear gate shape is selector compatible: master ALP-2707, execution parent ALP-2708, accepted gate ALP-2709, workers ALP-2717 through ALP-2721, PER ALP-2722.
- Current source confirms `ensure_schema` drops and recreates mismatched indexes in `crates/fmm-store/src/schema.rs:8-21`.
- Current source confirms `format_file_outline` is the oversized renderer at `crates/fmm-core/src/format/yaml_formatters.rs:22-259`, with legacy suffix handling at lines 187-204 and the separate `non_exported:` section at lines 241-255.

## Detailed Findings

### 1. ALP-2722 sqlite command is not copy-paste safe

ALP-2722's visibility coverage artifact cites `sqlite3 .fmm.db \"SELECT DISTINCT visibility FROM exports\"`. Because the markdown body contains escaped quotes, copying it into bash or zsh can pass literal quote characters and split the SQL across argv. Replace it with single-quoted SQL, for example `sqlite3 .fmm.db 'SELECT DISTINCT visibility FROM exports;'`, and add the equivalent methods query.

Also state `sqlite3` as an explicit manual-verification binary. The main workflow otherwise guarantees only the project toolchain and the `just` recipes.

### 2. Manual freshness reproducer lacks teardown discipline

ALP-2721 and ALP-2722 ask the reviewer to copy a parser fixture to a scratch path, run `fmm generate`, mutate the file, run `fmm validate`, run `fmm outline`, then regenerate. The bodies do not require `mktemp -d`, a trap cleanup, proof the scratch directory is outside the repo, or final `git status --short` and `fmm validate` evidence.

Add explicit teardown so PER does not leave stale `.fmm.db` files, scratch dirs, or mutated fixtures behind.

### 3. ALP-2722 timing command is platform ambiguous and mutates repo state

The performance bullet says `time fmm generate --force`, but shell `time`, BSD `/usr/bin/time`, and GNU `/usr/bin/time` format results differently. The acceptance criterion compares wall time, so the issue should specify a stable command such as `/usr/bin/time -p fmm generate --force` and tell the reviewer to record `real`.

Because `fmm generate --force` rewrites `.fmm.db`, the bullet should require a throwaway worktree or final restoration and clean working tree proof.

### 4. ALP-2717 renderer unchanged criterion needs an artifact

ALP-2717 says a fresh `fmm_file_outline` call returns the same content as before W1. That is the right constraint, but it is not falsifiable without an artifact. Require a saved or snapshot output before W1 and after W1, such as `fmm outline crates/fmm-store/src/writer.rs`, normalized only if necessary.

### 5. ALP-2722 subjective bullets need inspection artifacts

ALP-2722 includes subjective pass conditions: `No duplication introduced` and `Renderer leaves a parameterizable density-mode extension point`. Require concrete artifacts:

- Reviewer note naming extracted helpers.
- Evidence `format_file_outline` and helpers are under 150 lines.
- `wc -l` evidence modified files remain under 700 lines.
- A source citation showing the density parameter or seam ALP-2704 can reuse without changing the ALP-2707 default shape.

## Dependencies

Critical tools and binaries observed in the plan:

- `just`, `cargo`, `fmm`: core workflow.
- `sqlite3`: manual storage inspection in ALP-2722, should be named explicitly.
- `/usr/bin/time` or equivalent: performance measurement, should be made portable.
- `git`: log audit and clean tree evidence.

## Relevance to Helioy

The review reinforces Helioy's Linear workflow conventions: issue bodies must be executable by Nancy, shell commands must be copy-paste safe, and manual verification must include teardown. It also protects fmm as a Helioy navigation primitive by keeping default outline output deterministic and agent-friendly.

## Open Questions

- Whether orchestrator will patch the Linear bodies directly or request another review round first.
- Whether the final accepted PER should include exact shell snippets for scratch setup and cleanup.

## Round 1 Peer Convergence Addendum

Peer round 1 converged on teardown, sqlite3 precondition, ALP-2704 extension seam falsifiability, portable timing, and snapshot artifact tightening. Two updates were incorporated:

- Corrected sqlite quoting rationale: the escaped quotes observed in Linear MCP output are JSON transport escaping, not necessarily rendered Linear markdown. The recommended outcome remains single-quoted SQL for robust copy paths and an explicit `sqlite3` precondition.
- Added documentation anchor specificity: ALP-2722 should not rely on `consistent with output`; it should require concrete README, CHANGELOG, MCP description, and CLI help anchors or examples that name `signature:`, `visibility:`, `kind:`, and the removed suffix annotations.

## Consolidated Conditional Set

Both pass 4 panes ratified this 7 item set:

1. ALP-2721 and ALP-2722 freshness reproducer: scratch teardown via `$(mktemp -d)` outside repo; final cleanup; `git status --short` evidence.
2. ALP-2722 visibility and declaration-kind verification artifacts: `sqlite3` named as required manual-verification binary, or reframed as optional behind the storage-layer assertion, plus single-quoted SQL.
3. ALP-2722 ALP-2704 boundary: replace `parameterizable density-mode extension point` with a specific seam citation in `crates/fmm-core/src/format/yaml_formatters.rs`.
4. ALP-2722 renderer contract: replace `consistent with output` with named README, CHANGELOG, MCP description, and CLI help anchors.
5. ALP-2722 performance: `/usr/bin/time -p fmm generate --force`, record `real`; use throwaway worktree or final restore plus `git status --short` evidence after `.fmm.db` mutation.
6. ALP-2717 acceptance #2: explicitly cite `crates/fmm-cli/src/mcp/snapshots/fmm__mcp__snapshot_tests__fmm_file_outline.snap` as the before/after artifact.
7. ALP-2722 code hygiene: replace `No duplication introduced` with `No helper added in W1-W5 duplicates an existing helper in the same crate.`

## Round 2 Signoff

Orchestrator reported all seven pass 4 edits applied. I re-fetched ALP-2717, ALP-2721, and ALP-2722 via Linear MCP and re-read the consensus doc plus source entry points before signoff.

Observed amendments:

- ALP-2717 acceptance #2 now cites `crates/fmm-cli/src/mcp/snapshots/fmm__mcp__snapshot_tests__fmm_file_outline.snap` as the W1 no-renderer-change artifact.
- ALP-2721 clarifies `format_file_outline` is a single 238 LOC function at `crates/fmm-core/src/format/yaml_formatters.rs:22-259`, no helpers yet, and includes teardown-clean freshness steps.
- ALP-2722 includes manual binary preconditions, single-quoted sqlite commands, documentation anchors, teardown-clean freshness recipe, density seam citation requirement, helper duplication artifact, and `/usr/bin/time -p` performance measurement in a throwaway worktree.

Final bus signoff sent to peer and orchestrator:

`I sign off on the ALP-2707 filed tree as currently applied (pass-4)`

## Round 2 Addendum: Dependency Prose Drift

Peer identified one trailing issue after clean signoff. I re-fetched ALP-2722 live and confirmed:

- `## Dependency notes` prose says `Blocked by ALP-2717, ALP-2718, ALP-2719, ALP-2720, ALP-2721.`
- Linear `blockedBy` contains ALP-2718, ALP-2719, ALP-2720, and ALP-2721 only.

The selector graph is transitively safe because ALP-2721 blocks on ALP-2717, but prose and structural relations should not diverge. Revised signoff: conditional on removing ALP-2717 from ALP-2722 dependency prose, or adding the redundant direct edge. Preferred fix is prose removal.

## Final Signoff After N1 Fix

Orchestrator applied N1. I re-fetched ALP-2722 and confirmed `## Dependency notes` now lists direct blockers ALP-2718, ALP-2719, ALP-2720, and ALP-2721, with ALP-2717 described as reaching the PER transitively through ALP-2721. This matches the structural `blockedBy` relation.

Final signoff sent to peer and orchestrator:

`I sign off on the ALP-2707 filed tree as currently applied (pass-4)`
