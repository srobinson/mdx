---
title: Scope alias handling for context-matters write tools
type: research
tags: [context, mcp, scope, rust]
summary: cx_store and cx_deposit now accept scope as an alias for scope_path, preventing accidental writes to global.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

context-matters is a Rust workspace for a structured context store served over MCP. A caller supplied `scope` to `cx_store` and `cx_deposit`, but the handlers only deserialized `scope_path`; serde ignored the unknown field and defaulted writes to `global`.

The fix adds a serde alias so `scope` maps to `scope_path` for both write tools, while preserving existing `scope_path` callers.

## Project Metadata

- Language: Rust 2024 workspace, with a TypeScript frontend under `crates/cm-web/frontend`.
- Workspace members: `cm-core`, `cm-store`, `cm-capabilities`, `cm-cli`, `cm-web`.
- Key dependencies: `serde`, `serde_json`, `sqlx`, `uuid` v7, `blake3`, `chrono`, `tokio`, `axum`.
- Build and verification: `just check`, `just test`.
- Structural index: `.fmm.db` exists at repository root.

## Architecture

- `cm-core`: domain types including `ScopePath` validation.
- `cm-capabilities`: shared capability logic used by CLI and MCP handlers.
- `cm-cli`: CLI and MCP server adapters.
- `cm-store`: SQLite persistence.

The write path is thin at the MCP layer. `cx_store` parses JSON into `StoreRequest`, delegates to `cm_capabilities::store::store`, and renders an acknowledgement. `cx_deposit` parses JSON into `CxDepositParams`, maps that to `DepositRequest`, then delegates to `cm_capabilities::deposit::deposit`.

## Key Patterns

- MCP handlers should keep parsing and projection thin, with write logic in `cm-capabilities`.
- Compatibility aliases belong at the serde boundary, so old and short parameter names share one internal field.
- Regression tests should assert the acknowledgement scope, since the original failure looked like success while writing to the wrong scope.

## Detailed Findings

### Root cause

`cx_store` deserialized into `StoreRequest.scope_path` with a default of `global`. Unknown JSON fields were ignored, so a payload containing `scope` did not set `scope_path` and the write continued at `global`.

- `crates/cm-capabilities/src/store.rs:32` to `34`: `scope_path` now has `#[serde(default = "default_scope_path", alias = "scope")]`.
- `crates/cm-cli/src/mcp/tools/deposit.rs:29` to `31`: `CxDepositParams.scope_path` now has `#[serde(default = "default_scope", alias = "scope")]`.

### Regression coverage

- `crates/cm-cli/tests/tools_integration/store.rs:87` to `105`: `store_accepts_scope_alias` calls `cx_store` with `scope` and asserts the ack contains `global/project:helioy/repo:manicure`.
- `crates/cm-cli/tests/tools_integration/deposit.rs:62` to `80`: `deposit_accepts_scope_alias` calls `cx_deposit` with `scope` and asserts the ack contains `global/project:helioy/repo:manicure`.

The tests failed before the alias patch and passed after it.

## Dependencies

- `serde` supplies the `alias` attribute used for compatibility deserialization.
- `cm_core::ScopePath` still validates the canonical scope path after deserialization.
- The existing scope chain creation logic remains unchanged.

## Relevance to Helioy

This closes a sharp edge for agents writing memory into Helioy repository scopes. Agents can now use the shorter `scope` parameter for `cx_store` and `cx_deposit` without accidentally storing durable notes in `global`.

## Verification

- `cargo test -p cm-cli --test tools_integration scope_alias`
- `cargo test -p cm-capabilities store`
- `cargo test -p cm-cli --test tools_integration`
- `cargo fmt && just check`
- `just test`, 587 passed

## Open Questions

- Unknown MCP parameters are still generally ignored unless a handler uses stricter deserialization. A future hardening pass could reject unknown write parameters, but `StoreRequest` uses flattened metadata, so that change needs care.
- The generated MCP schema still documents `scope_path` as the canonical parameter. This patch adds runtime compatibility for `scope`; a later documentation pass could expose aliases explicitly if desired.
