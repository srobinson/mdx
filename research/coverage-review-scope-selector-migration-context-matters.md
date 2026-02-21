---
title: Coverage Review for Scope Selector Migration
type: research
tags: [context-matters, scope, mcp, cm-web, testing, documentation]
summary: Review found the ALP-2054 plan is directionally sound but needs tighter negative validation, web parity, URL migration, fixture, and final verification criteria.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

The scope selector migration plan covers the core capability path, MCP artifacts, cm-web request surfaces, documentation, and final verification. Approval should wait until the Linear issues and spec make rejection behavior, feed URL migration, worktree fixtures, and final verification criteria concrete enough to prevent a silent compatibility leak.

## Project Metadata

Language: Rust workspace with TypeScript React frontend.

Build system: Cargo, nextest, just, pnpm, ts-rs generated frontend types.

Relevant components: `cm-capabilities`, `cm-cli`, `cm-web`, `tools.toml`, generated MCP schema JSON, generated CLI help, frontend feed route state.

## Architecture

Scope selection currently crosses several layers:

1. Capability requests in `crates/cm-capabilities/src/browse.rs`, `store.rs`, `deposit.rs`, `recall/types.rs`, and `export.rs`.
2. MCP adapters and generated schema in `crates/cm-cli/src/mcp/tools/`, `tools.toml`, and `crates/cm-cli/src/mcp/generated_schema/`.
3. CLI flags and help in `crates/cm-cli/src/cli/cli_def.rs`, `generated_help.rs`, and command handlers.
4. cm-web backend query structs in `crates/cm-web/src/api/agent.rs`, `entries.rs`, and `export.rs`.
5. cm-web frontend query serialization in `crates/cm-web/frontend/src/api/client.ts`, feed search state, BrowsePane, FilterBar, and dashboard scope links.

`ScopePath` should remain the internal exact identity for entries, store filters, scope tree rows, exported entity payloads, and durable model fields.

## Detailed Findings

### Verdict

Changes requested.

The Linear plan is close, but several acceptance criteria are too broad. The migration is breaking and must include explicit negative tests that prove `scope_path` is rejected rather than ignored.

### Missing Tests

1. MCP schema and protocol rejection

   Add protocol tests that scan every migrated MCP input schema for forbidden `scope_path`: `cx_browse`, `cx_recall`, `cx_store`, `cx_deposit`, and `cx_export`. Keep an allowlist for output entity schemas where `scope_path` is persisted data.

   Add `tools/call` tests that pass `scope_path` to each migrated tool and assert a validation error. This must be explicit because serde normally ignores unknown fields unless request structs opt into strict handling or adapters validate unknown keys.

2. CLI help and flag behavior

   Add CLI integration tests for `cm browse --help`, `cm store --help`, `cm deposit --help`, and `cm export --help` proving public examples use `--scope` and `cwd_inferred` where relevant.

   Add a regression test that `cm browse --scope-path ...` fails after migration, unless the spec deliberately keeps that CLI flag as a non MCP compatibility exception. The current plan does not state an exception.

3. cm-web backend parity

   Extend ALP-2061 and ALP-2063 to cover `/api/entries/search` and `/api/export`. Both are user facing and currently use `scope_path` request parameters.

   Add rejection tests for `scope_path` on `/api/agent/browse`, `/api/entries`, `/api/entries/search`, `/api/agent/recall`, and `/api/export` if those routes are in scope for the breaking contract.

   Add exact `scope` and `scope=cwd_inferred` parity tests for `/api/entries/search` and export filtering, not only browse.

4. Frontend URL and client state

   Add frontend coverage or type level checks for `FeedSearch`, `validateFeedSearch`, `FeedPage`, `BrowsePane`, dashboard scope links, and `api.export`. Typecheck alone will not prove query names changed because string keys can remain stale.

   Define and test Feed URL migration. Either old `scope_path` URLs are intentionally dropped, or the route maps `scope_path` to `scope` client side before making API requests. The current spec says “migrate” but does not define behavior for old bookmarked URLs.

5. Linked worktree fixture

   Make the fixture shape explicit: create a temporary source git repo, add a linked worktree with `git worktree add`, seed scopes using the source repo name, then call resolution from inside the linked worktree. Assert the resolver selects the source repo scope, not the worktree directory name.

   Add the same fixture through at least one MCP or web vertical path, not only unit level capability tests.

6. Write rejection safety

   Store and deposit tests should prove ambiguous or low confidence `cwd_inferred` performs no durable writes and does not create any scope chain rows. This matters because current deposit semantics allow partial writes after storage starts, so resolver failure must happen before any store mutation.

### Missing Documentation Checks

1. Generated docs should be checked for stale terms: `scope_path`, `scope=auto`, and `auto` as a public reserved scope value. Allow `scope_path` only in stored entity field documentation and historical changelog text.

2. `tools.toml` should be the primary source of truth, with a generated artifact check proving `crates/cm-cli/src/mcp/generated_schema/`, `generated_help.rs`, and `crates/cm-cli/templates/SKILL.md` are reproducible.

3. User docs should include one clear breaking change note: public request surfaces use `scope`; `cwd_inferred` is the only reserved inference value; `scope_path` remains internal persisted data only.

### Precise Issue Edits

ALP-2056: Add fixture requirements for linked git worktrees and require one test where the source repo name differs from the worktree directory name.

ALP-2059: Add “no scope rows and no entries are created after rejected inferred writes” to acceptance criteria.

ALP-2060: Add strict unknown field handling for MCP params. Require `scope_path` rejection tests for all migrated tools. Include `cm browse --scope-path` behavior, or explicitly defer CLI flag compatibility to another issue.

ALP-2061: Add `/api/entries/search`, `/api/export`, frontend `api.export`, feed URL search state, dashboard scope links, and BrowsePane query serialization to the file list and acceptance criteria.

ALP-2062: Add a stale public term scan for generated artifacts. The scan should fail on public `scope_path`, `scope=auto`, or `auto` as the inference selector, except allowlisted output entity fields and changelog history.

ALP-2063: Add vertical tests for MCP, CLI, cm-web backend, and frontend query serialization. Require tests that fail against the old contract.

ALP-2064: Add explicit docs for the compatibility boundary: internal stored fields may still be named `scope_path`; public request inputs use `scope`.

ALP-2065: Add `just test-doc`, generated artifact reproducibility checks, manual rejection smoke calls for `scope_path`, and `git diff --exit-code` after verification. `just check` currently runs formatting and lint commands with write flags, so a clean diff check is required.

### Spec Edits

Clarify whether cm-web JSON bodies for create, update, and merge keep `scope_path` as internal exact persisted data or migrate to `scope`. `NewEntry` is a request body today, so it needs an explicit exception if it remains unchanged.

Clarify whether old Feed URLs containing `scope_path` are rejected, ignored, or client migrated to `scope`.

Clarify whether CLI flags are part of the public breaking contract. If yes, remove `--scope-path` from browse and test failure. If no, document the exception.

## Relevance to Helioy

This migration directly protects Helioy memory routing. The critical risk is silent fallback to `global` or silent ignore of stale `scope_path`, which would place durable agent memory in the wrong scope.

## Open Questions

1. Should cm-web entry creation bodies continue using `scope_path` because they represent stored exact paths?
2. Should old Feed URLs be migrated client side or treated as invalid after the breaking change?
3. Should CLI browse remove `--scope-path`, or is the breaking contract limited to MCP and HTTP query inputs?
