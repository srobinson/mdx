---
title: ALP-2640 Signoff Audit for Context Matters
type: research
tags: [context-matters, linear, planning, scope-inference, peer-review]
summary: Peer audit verified all six consensus changes and signed off on ALP-2640 as currently filed.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-21
updated: 2026-05-21
---

## Executive Summary

ALP-2640 is structurally ready after applying the six consensus fixes to ALP-2638 and ALP-2639. Final re-read via Linear verified the issue bodies, and pane B sent `I sign off on ALP-2640 as currently filed`.

## Project Metadata

- Language: Rust workspace, edition 2024.
- Workspace crates: `cm-core`, `cm-store`, `cm-capabilities`, `cm-cli`, `cm-web`.
- Build system: Cargo plus `just`.
- Key verification commands from `justfile`: `just check`, `just build`, `just test`.
- fmm index present: `.fmm.db` exists and fmm tools returned indexed structure.

## Architecture Relevant to ALP-2640

- `crates/cm-core/src/types/scope.rs`: owns `ScopeKind`, `ScopePath`, and validation rules. `ScopePath::validate` currently rejects non increasing scope kinds at lines 111 to 152, with the ordering predicate at lines 137 to 142.
- `crates/cm-capabilities/src/scope/resolution.rs`: owns scope resolution. `resolve_scope_selection` dispatches `ScopeSelector::CwdInferred` through `resolve_cwd_inferred_scope` at lines 27 to 55. `score_candidate` currently handles repo basename and one project parent or cwd project match at lines 315 to 361.
- `crates/cm-capabilities/src/scope/segments.rs`: `scope_segments` currently stores one project segment by overwriting `segments.project` at lines 9 to 22.

## Detailed Findings

### Linear structure

- `ALP-2640` direct open children are exactly `ALP-2645` and `ALP-2641`.
- `ALP-2645` is the gate review issue and remains `Todo` pending signoff.
- `ALP-2641` is the Backlog execution parent.
- `ALP-2641` children are `ALP-2638`, `ALP-2639`, and `ALP-2642`.
- `ALP-2638` blocks `ALP-2639`, matching the gate’s required order.
- `ALP-2642` has the `Post Execution Review` label.

### Final signoff verification

On the final Linear re-read, ALP-2638 no longer contained the TOML block, literal error string, or stale capture footer. It had worker-local Acceptance and Verification sections covering config strategy selection, dispatch through `resolve_scope_selection`, `filesystem` compatibility, `custom` actionable error behavior, and `just check` plus `just test`.

ALP-2639 no longer cited `crates/cm-core/src/types/scope.rs:137-142`, used `crates/cm-core/src/types/scope.rs` plus `ScopePath::validate`, resolved membership discovery as filesystem as truth with no relitigation, removed the stale capture footer, referenced workspace-root `tools.toml` consumed by `crates/cm-cli/build.rs`, and included Acceptance and Verification sections matching the gate.

Final bus response sent to pane A and CC to orchestrator: `I sign off on ALP-2640 as currently filed`.

### Conditional signoff items sent on the bus

1. Remove the pinned line range from ALP-2639. `crates/cm-core/src/types/scope.rs:137-142` violates the universal issue rule against line numbers. Use the file plus `ScopePath::validate` as the stable entry point.
2. Update ALP-2639 so the open membership discovery section is no longer open. The gate resolves it as filesystem as truth, but the worker body still says “Pick one before implementation.”
3. Remove the stale “Capture only. Needs triage before execution.” footer from ALP-2638 and ALP-2639. Those issues are now under Backlog ALP-2641 and listed in the gate Execute line.
4. Add worker-local acceptance or verification sections to ALP-2638 and ALP-2639 that mirror the gate contracts. The gate and PER have the right checks, but worker bodies still read like capture notes.
5. Correct ALP-2639's `crates/cm-cli/tools.toml` reference to workspace root `tools.toml`, or phrase it as the workspace `tools.toml` consumed by `crates/cm-cli/build.rs`. fmm confirmed `build.rs` reads `../../tools.toml`, and filesystem checks confirmed root `tools.toml` exists while `crates/cm-cli/tools.toml` does not.
6. Rewrite ALP-2638's TOML block and literal error string as capability and observable behavior rather than prescribed wire shape and wording.

### Verification notes

- `justfile` confirms `just check` runs formatting, clippy with warnings as errors, and frontend checks.
- `justfile` confirms `just test` runs `cargo nextest run --workspace`.
- Existing relevant test locations include `crates/cm-capabilities/tests/scope_selector_tests.rs` and `crates/cm-capabilities/tests/browse_scope/cwd_inferred_resolution.rs`.

## Dependencies

- `cm-core` provides core scope types and validation.
- `cm-capabilities` provides request handling, scope selector parsing, and cwd inferred resolution.
- `cm-cli/tools.toml` centralizes tool documentation and must be updated for user visible project nesting prose.

## Relevance to Helioy

The audit applies the selector compatible Linear shape used for autonomous Nancy work. The conditional issues prevent planner language and stale capture markers from creating ambiguity when Nancy selects and executes the worker issues.

## Open Questions

- Whether ALP-2642 should also have explicit Linear dependency relations after both workers. The gate body says PER runs last, but no Linear relation was present in the issue relation payload.
