---
title: ALP-2082 and ALP-2086 Review for context-matters
type: research
tags: [context-matters, review, cm-web, alp-2082, alp-2086]
summary: Review found ALP-2082 and ALP-2086 acceptance criteria satisfied with no blocking findings.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed HEAD against `origin/nancy/ALP-2054` for ALP-2082 and ALP-2086 only. Both issues pass acceptance based on targeted diff inspection, fmm structural reads, backend path tracing, and verification commands.

## Project Metadata

- Project: `context-matters`
- Area: `crates/cm-web`
- Languages: Rust backend, TypeScript React frontend
- Relevant frontend script: `pnpm --dir crates/cm-web/frontend run typecheck`
- Relevant Rust tests: `cargo test -p cm-web --test frontend_scope_contract`, `cargo test -p cm-web --test parity recall`
- fmm indexing: available and used for structural orientation.

## Architecture

- Frontend API client lives in `crates/cm-web/frontend/src/api/client.ts`.
- `/api/agent/recall` is routed by `crates/cm-web/src/api/agent.rs:34` to `recall_handler` at `agent.rs:220`.
- `/api/entries/recall` is routed by `crates/cm-web/src/api/entries.rs:34` to `recall` at `entries.rs:162`, which delegates to `agent::execute_recall`.
- Export is routed by `crates/cm-web/src/api/mod.rs:24` to `crates/cm-web/src/api/export.rs:15`.
- Backend scope parsing is shared through `agent::parse_scope_query`, `agent::parse_recall_query`, and `agent::parse_scope_selector`.

## Detailed Findings

### ALP-2082: PASS

Acceptance evidence:

- `RecallParams` includes optional `cwd?: string` at `crates/cm-web/frontend/src/api/client.ts:161` to `169`.
- `api.entries.recall` serializes `cwd` through `toSearchParams` at `client.ts:233` to `244`.
- `api.agent.recall` serializes `cwd` through `toSearchParams` at `client.ts:280` to `291`.
- `api.export` now accepts either the legacy string scope or `{ scope, cwd }`, preserving call site compatibility while allowing `scope=cwd_inferred` with `cwd`, at `client.ts:332` to `340`.
- Frontend type contract exercises recall cwd and export cwd in `crates/cm-web/frontend/src/api/scope-contract.test.ts:11` to `24`.
- Backend recall parsing accepts `cwd` at `crates/cm-web/src/api/agent.rs:121` to `166`, then builds a scoped `RecallRequest` through `parse_scope_selector` at `agent.rs:192`.
- Backend export accepts `cwd` through `parse_scope_query` and `parse_scope_selector` at `crates/cm-web/src/api/export.rs:15` to `49`.

Verification:

- `pnpm --dir crates/cm-web/frontend run typecheck` passed.
- `cargo test -p cm-web --test frontend_scope_contract` passed.

### ALP-2086: PASS

Acceptance evidence:

- Positive backend parity coverage exists for `/api/agent/recall?query=Smart&scope=cwd_inferred&cwd=/tmp/helioy/context-matters` in `crates/cm-web/tests/parity/recall.rs:63` to `91`.
- Positive backend parity coverage exists for `/api/entries/recall?query=Smart&scope=cwd_inferred&cwd=/tmp/helioy/context-matters` in `crates/cm-web/tests/parity/recall.rs:94` to `122`.
- Both parity tests compare endpoint output to the shared capability layer using `ScopeSelector::cwd_inferred(Some(...))`.
- Frontend source level contract asserts recall and export cwd coverage in `crates/cm-web/tests/frontend_scope_contract.rs:54` to `67`.

Verification:

- `cargo test -p cm-web --test parity recall` passed with the two new cwd inferred recall tests and existing recall parity tests.

## Quality and Regression Notes

- No blocking findings.
- The frontend `api.export(scope)` string signature remains compatible with existing callers while adding object form support for cwd.
- DRY is acceptable. Recall endpoint behavior stays centralized through `agent::execute_recall`; entries recall delegates to the same helper.
- Backend export reuses shared scope parsing helpers instead of duplicating query parsing.
- Nonblocking: frontend coverage remains type/source contract coverage rather than a runtime URL serialization test. The implementation is straightforward and verified by source inspection, but a future JS test with mocked `fetch` would catch accidental query string regressions more directly.

## Dependencies

- `URLSearchParams` provides frontend query serialization in `client.ts:48` to `70`.
- `cm_capabilities::scope::ScopeSelector` and `resolve_scope_selection` provide cwd inferred scope resolution.
- `cm_capabilities::recall::RecallRequest` is the shared recall capability request type.

## Open Questions

- None for ALP-2082 or ALP-2086.
