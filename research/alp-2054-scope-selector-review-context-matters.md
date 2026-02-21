---
title: ALP-2054 Scope Selector Migration Review for context-matters
type: research
tags: [context-matters, alp-2054, scope-selector, mcp, cm-web, review]
summary: Full review of ALP-2054 found no critical or high defects, with two medium acceptance and alignment gaps around CLI store validation and cm-web frontend cwd support.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

ALP-2054 mostly achieves the scope selector migration. Core capability semantics, git worktree aware cwd inference, strict inferred write policy, durable `ScopePath` persistence, migrated MCP schemas, and cm-web server rejection paths are aligned with the spec.

The review found no critical or high severity defects. Two medium issues remain before I would call the migration fully accepted: `cm store --scope auto` exits successfully because the CLI store command is a stub, and the cm-web frontend API cannot pass `cwd` for recall or export although the backend supports those request surfaces.

## Project Metadata

Language: Rust 2024 workspace, TypeScript frontend.

Workspace crates:

1. `cm-core`: domain types and store traits.
2. `cm-store`: SQLite adapter.
3. `cm-capabilities`: shared application layer and scope resolution.
4. `cm-cli`: CLI and MCP server.
5. `cm-web`: web backend and frontend.

Build and verification tools: Cargo, sqlx, tokio, clap, serde, ts-rs, npm frontend tooling, fmm indexed with 324 files and 40,003 LOC.

## Architecture Reviewed

Scope selection now flows through `ScopeSelector` in `cm-capabilities`, then adapters convert public inputs into selectors.

Core invariants checked:

1. `cm-core` keeps exact durable `ScopePath` fields for entries, filters, store traits, and persisted data.
2. Capability request structs use `ScopeSelector` instead of carrying both `scope` and `scope_path`.
3. `cwd_inferred` resolution happens in the capability layer and uses git metadata for linked worktrees.
4. Write capabilities resolve and validate `cwd_inferred` before creating scope chains or entries.
5. Public migrated MCP, CLI, docs, and cm-web server surfaces expose `scope` rather than `scope_path`.

## Key Patterns

### Durable exact paths remain internal

The migration correctly preserves `ScopePath` as the durable storage identity. The public selector changed, not the persistence model. That is visible in `cm-core` domain types and in export output where `scope_path` remains legitimate persisted data.

### Strict inferred write policy

`ResolvedScopeSelection::write_scope_path` delegates to `require_unique_high_confidence_resolution`, so inferred writes require exactly one high confidence candidate before mutation. Store and deposit both resolve and validate before `ensure_scope_chain`.

### Runtime rejection backs up schema migration

The migrated MCP handlers call `reject_removed_scope_inputs`, which rejects `scope_path` and `scope_mode` even though JSON schemas are open objects. This is important because schema removal alone would not prevent stale MCP callers from sending removed fields.

## Detailed Findings

### Medium: `cm store --scope auto` is accepted

`cm store` exposes `--scope`, and generated help describes the migrated selector, but the command handler does not parse or validate supplied flags. It prints guidance for the Curator UI and exits `0`.

Evidence:

1. CLI command exposes `scope` for store: `crates/cm-cli/src/cli/cli_def.rs:123-151`.
2. Generated store scope help says exact path or `cwd_inferred`: `crates/cm-cli/src/cli/generated_help.rs:27`.
3. Handler ignores all store arguments and returns `Ok(())`: `crates/cm-cli/src/cli/store.rs:23-55`.
4. Local smoke command:

```sh
./target/debug/cm store --title T --body B --kind fact --scope auto
```

Observed result: printed Curator guidance and exited `0`.

Why this matters: ALP-2054 says public `auto` inputs must be rejected on migrated surfaces. Since `cm store` exposes a public `--scope` flag, accepting `--scope auto` is an acceptance gap even though it does not mutate data.

Suggested fix: either remove the unused store flags from the CLI stub, or validate the parsed `scope` before printing the stub response. The simpler fix is to parse `ScopeSelector::parse` for any supplied store scope and return an error for `auto`.

### Medium: cm-web frontend API cannot pass `cwd` for recall or export

The backend accepts and resolves `cwd` for recall and export when `scope=cwd_inferred`, but the typed frontend API cannot express those requests.

Backend evidence:

1. Recall query parser captures `cwd`: `crates/cm-web/src/api/agent.rs:121-166`.
2. Scope parser applies cwd only to `cwd_inferred`: `crates/cm-web/src/api/agent.rs:65-82` and `crates/cm-web/src/api/agent.rs:84-109`.
3. Export resolves `scope` plus `cwd`: `crates/cm-web/src/api/export.rs:15-49`.
4. Vertical export test covers `scope=cwd_inferred&cwd=/tmp/helioy/context-matters`: `crates/cm-web/tests/parity/scope_migration.rs:96-108`.

Frontend gap:

1. `RecallParams` has no `cwd`: `crates/cm-web/frontend/src/api/client.ts:161-168`.
2. `api.entries.recall` serializes no `cwd`: `crates/cm-web/frontend/src/api/client.ts:227-236`.
3. `api.agent.recall` serializes no `cwd`: `crates/cm-web/frontend/src/api/client.ts:273-282`.
4. `api.export` only accepts `scope?: string`: `crates/cm-web/frontend/src/api/client.ts:324-326`.

Impact: raw HTTP supports the intended selector semantics, but the product frontend client cannot use cwd based recall or export. This is an alignment issue with ALP-2061 and the vertical scope migration story.

Suggested fix: add optional `cwd?: string` to `RecallParams`, serialize it in both recall calls, and change export to accept either `(scope?: string)` plus optional cwd or an options object with `{ scope, cwd }`. Add frontend contract tests for recall and export cwd serialization.

### Low: Generated MCP input schemas are open objects

All generated input schemas omit `additionalProperties: false`. Runtime rejection protects the migrated scoped tools, but schema clients cannot prevalidate stale removed fields.

Evidence:

1. Schema generation creates object schemas without closing additional properties: `crates/cm-cli/build.rs:212-215`.
2. Local schema probe showed `additionalProperties=None` for `cx_browse`, `cx_recall`, `cx_store`, `cx_deposit`, `cx_export`, and other tools.

Why this matters: generated schemas are part of the public artifact refresh. Open schemas are acceptable only if runtime rejection is treated as the source of truth. If strict schema validation is desired, set `additionalProperties: false` and keep runtime rejection as defense in depth.

### Low: MCP and CLI help could show one concrete `cwd_inferred` command

Docs mention `cwd_inferred` and correctly explain that it replaces `auto`, but examples mostly use exact scope paths.

Evidence:

1. Root scope tip mentions browse defaulting to `scope=cwd_inferred`: `crates/cm-cli/src/cli/help_text.rs:65-68`.
2. Browse examples use exact paths: `crates/cm-cli/src/cli/help_text.rs:83-90`.
3. Deposit examples use exact paths: `crates/cm-cli/src/cli/help_text.rs:124-130`.
4. Export examples use exact paths: `crates/cm-cli/src/cli/help_text.rs:140-145`.

Suggested improvement: add one concrete command such as:

```sh
cm browse --scope cwd_inferred --cwd /path/to/repo
```

This would make the new reserved value visible in help examples, not only in option prose.

### Low: non-scope MCP tools ignore removed scope inputs despite broad docs wording

The five migrated scope tools reject removed inputs through `reject_removed_scope_inputs`. Non-scope tools such as `cx_stats`, `cx_get`, `cx_forget`, and `cx_update` do not call that helper. For example, `cx_stats` with `scope_path` returns normal stats.

Evidence:

1. Rejection helper: `crates/cm-cli/src/shared.rs:108-119`.
2. Migrated scoped handlers call it, for example browse, recall, export, store, and deposit.
3. Non-scope handlers do not call it: `crates/cm-cli/src/mcp/tools/get.rs`, `crates/cm-cli/src/mcp/tools/update.rs`, `crates/cm-cli/src/mcp/tools/forget.rs`, `crates/cm-cli/src/mcp/tools/stats.rs`.

I do not count this as an ALP-2054 acceptance failure because the migration spec explicitly excludes `cx_get`, `cx_stats`, `cx_update`, and `cx_forget` from scope selection. It is still a docs and caller experience issue because `tools.toml` says public requests should not send `scope_path`, `scope_mode`, or `scope="auto"`.

Suggested fix: either reject removed scope fields in every MCP handler, or narrow the docs wording to the five migrated scope selecting tools.

### Low: coverage misses positive recall cwd and frontend export cwd cases

Coverage is strong for search, export, body rejection, and old query field rejection. Missing positive cases remain:

1. `/api/agent/recall?scope=cwd_inferred&cwd=...`.
2. `/api/entries/recall?scope=cwd_inferred&cwd=...`.
3. Frontend contract for recall with `cwd`.
4. Frontend contract for export with `cwd`.

Evidence:

1. Existing vertical scope migration tests: `crates/cm-web/tests/parity/scope_migration.rs:9-241`.
2. Existing recall parity tests cover basic and exact scope recall: `crates/cm-web/tests/parity/recall.rs:8-78`.
3. Frontend contract covers browse, search, agent browse, export, create, and merge, but not recall cwd or export cwd: `crates/cm-web/frontend/src/api/scope-contract.test.ts:12-32`.

## Acceptance Review

Passed:

1. Public migrated request surfaces use `scope` for the main scope selecting tools.
2. `scope: "cwd_inferred"` resolves through git metadata for linked worktrees.
3. Migrated MCP and cm-web server surfaces reject `scope_path`, `scope_mode`, and `scope="auto"` in tested paths.
4. `cx_store` and `cx_deposit` require one unique high confidence inferred scope before writes.
5. Rejected inferred writes are tested to create no entries and no scope chain rows.
6. Domain and persistence types keep exact `ScopePath` where data is stored or queried.
7. Generated MCP schemas, tools docs, skill docs, README, PROJECT, TLDR, and CHANGELOG are mostly aligned.

Not fully accepted until fixed or waived:

1. CLI `cm store --scope auto` should reject `auto` if `cm store` remains a migrated public `--scope` surface.
2. cm-web frontend request API should expose `cwd` for recall and export or the documentation should narrow the expected frontend support.

## Verification Performed

Delegated agents ran the following notable checks:

1. `fmm validate`.
2. `cargo fmt --all -- --check`.
3. `cargo clippy --workspace --all-targets -- -D warnings`.
4. `cargo nextest run -p cm-core`.
5. `cargo nextest run -p cm-capabilities`.
6. `cargo nextest run -p cm-cli`.
7. `cargo nextest run -p cm-store`.
8. `cargo test --workspace --doc`.
9. `cargo test -p cm-web scope_migration -- --nocapture`.
10. `cargo test -p cm-web --test frontend_scope_contract -- --nocapture`.
11. `npm --prefix crates/cm-web/frontend run typecheck`.
12. Targeted MCP protocol tests for rejected `scope_path`, `auto`, and unknown fields.

I spot checked:

1. `fmm validate`: passed.
2. `cargo test -p cm-web scope_migration -- --nocapture`: passed, 8 tests.
3. `cargo test -p cm-cli public_scope_artifacts_do_not_expose_removed_request_terms -- --nocapture`: passed.
4. `cargo test -p cm-cli protocol_migrated_scope_tools_reject_scope_path -- --nocapture`: passed.
5. `cargo test -p cm-cli protocol_migrated_scope_tools_reject_auto_scope -- --nocapture`: passed.
6. `./target/debug/cm store --title T --body B --kind fact --scope auto`: reproduced acceptance of `auto`, exit `0`.
7. Generated schema probe: confirmed no migrated input schema exposes `scope_path`, but all input schemas are open objects.
8. `git status --short`: clean.

I did not run `just check` because the project definition runs `cargo clippy --fix --allow-dirty`, which is mutating. Read only equivalents were run instead.

## Dependencies

Critical dependencies involved in this review:

1. `clap`: CLI surface and generated help.
2. `serde` and `serde_json`: MCP and web request parsing.
3. `axum`: cm-web request routing.
4. `ts-rs`: frontend type generation for persisted response models.
5. `sqlx`: persistence layer, unchanged for this migration.
6. `git` metadata commands: cwd inference and linked worktree normalization.

## Relevance to Helioy

This migration directly affects Helioy memory reliability. The old mixed `scope` and `scope_path` contract allowed successful writes to land in `global`. ALP-2054 largely fixes that by making public selector semantics explicit and preserving `ScopePath` only for durable exact data.

The remaining CLI and frontend gaps matter because Helioy agents depend on predictable public surfaces. A caller seeing `scope` accepted everywhere should not have one command silently accept removed `auto`, and the frontend should be able to exercise the same cwd based resolution semantics as the backend.

## Open Questions

1. Should non-scope MCP tools reject stale scope fields globally, or should docs explicitly limit rejection guarantees to migrated scope selecting tools?
2. Should generated MCP schemas close all input objects with `additionalProperties: false`, or is runtime rejection the intended compatibility boundary?
3. Is `cm store` intended to remain a public stub with full store flags, or should the flags be removed until the command actually writes?
