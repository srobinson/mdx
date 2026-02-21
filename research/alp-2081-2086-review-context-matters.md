---
title: ALP 2081 through ALP 2086 Review for context-matters
type: research
tags: [context-matters, alp-2054, review, scope-migration, mcp, cm-web]
summary: Review found all six ALP 2054 follow-up issues accepted with no blocking findings.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Reviewed ALP-2081 through ALP-2086 on `nancy/ALP-2054`, comparing `HEAD 6266142` against `origin/nancy/ALP-2054 9f341c5`. All six issues satisfy acceptance criteria with no blocking findings.

## Project Metadata

- Project: `context-matters`
- Language: Rust workspace with TypeScript frontend
- Relevant crates: `cm-cli`, `cm-web`, `cm-capabilities`
- Structural index: `.fmm.db` present in worktree
- Verification run from `/Users/alphab/Dev/LLM/DEV/helioy/context-matters-worktrees/nancy-ALP-2054`

## Architecture

The reviewed work continues the ALP-2054 public scope migration. Scope selection behavior is centralized in `cm_capabilities::scope::ScopeSelector`, exposed through CLI handlers, MCP handlers, and cm-web HTTP surfaces.

Key boundaries checked:

- CLI public request flags in `crates/cm-cli/src/cli/*`
- MCP generated schemas from `tools.toml` through `crates/cm-cli/build.rs`
- MCP runtime validation in `crates/cm-cli/src/mcp/tools/*`
- cm-web typed client and parity tests in `crates/cm-web/frontend/src/api/client.ts` and `crates/cm-web/tests/parity/*`

## Detailed Findings

### ALP-2081: Reject removed auto selector in cm store stub

Status: PASS.

Evidence:

- `cm store` passes parsed `scope` into the store stub in `crates/cm-cli/src/main.rs:115` to `117`.
- The stub validates the selector before printing Curator guidance in `crates/cm-cli/src/cli/store.rs:25` to `28`.
- Shared parsing rejects `auto` with a clear message in `crates/cm-capabilities/src/scope/types.rs:71` to `75`.
- Tests cover `cm store --scope auto` failure and current selector success in `crates/cm-cli/tests/cli_integration.rs:109` to `129`.

Nonblocking note: comments in `crates/cm-cli/src/cli/store.rs` still describe the stub as always returning `Ok(())` or being infallible. That is now false for invalid scope input.

### ALP-2082: Expose cwd selector support in cm-web frontend recall and export APIs

Status: PASS.

Evidence:

- `RecallParams` includes optional `cwd` in `crates/cm-web/frontend/src/api/client.ts:161` to `169`.
- `api.entries.recall` serializes `cwd` in `crates/cm-web/frontend/src/api/client.ts:233` to `244`.
- `api.agent.recall` serializes `cwd` in `crates/cm-web/frontend/src/api/client.ts:280` to `291`.
- `api.export` preserves string compatibility while accepting `{ scope, cwd }` in `crates/cm-web/frontend/src/api/client.ts:332` to `339`.
- Type contract coverage appears in `crates/cm-web/frontend/src/api/scope-contract.test.ts:14` to `26`.

Nonblocking note: frontend coverage is type and source based. A future mocked fetch test would catch query serialization regressions more directly.

### ALP-2083: Close generated MCP input schemas or document runtime validation boundary

Status: PASS.

Evidence:

- `crates/cm-cli/build.rs:210` to `216` emits `additionalProperties: false` in generated MCP input schemas.
- Generated schema files include closed top level input schemas, for example `crates/cm-cli/src/mcp/generated_schema/cx_get.json` and `cx_stats.json`.
- The tools list protocol test asserts every listed tool schema is closed in `crates/cm-cli/tests/mcp_protocol/tools_list.rs:117` to `126`.
- Generated public artifact checks assert the same for migrated scope schemas in `crates/cm-cli/tests/mcp_protocol/tools_list.rs:198` to `210`.

Nonblocking note: runtime validation is not universal for every unknown field. `cx_stats` still ignores unrelated unknown fields in direct JSON-RPC calls. This is acceptable for ALP-2083 because the chosen boundary is closed generated schemas, but future stricter runtime parity would need generic request schema validation or per-tool `deny_unknown_fields` parsing.

### ALP-2084: Add concrete cwd_inferred examples to CLI and MCP help docs

Status: PASS.

Evidence:

- CLI browse help includes `cm browse --scope cwd_inferred --cwd /path/to/repo` in `crates/cm-cli/src/cli/help_text.rs:85` to `89`.
- `tools.toml:47` to `53` and `crates/cm-cli/templates/SKILL.md:67` to `73` include equivalent `cx_browse(scope: "cwd_inferred", cwd: "/path/to/repo")` guidance.
- CLI and generated doc tests assert these examples in `crates/cm-cli/tests/cli_flags.rs:105` to `116` and `crates/cm-cli/tests/mcp_protocol/tools_list.rs:249` to `260`.
- No positive public examples were found recommending `scope_path` or `scope=auto`. Remaining occurrences are negative guidance, response schema fields, or tests.

### ALP-2085: Align removed scope field handling on non-scope MCP tools

Status: PASS.

Evidence:

- `cx_get`, `cx_update`, `cx_forget`, and `cx_stats` now call `reject_removed_scope_inputs(args)?` before normal handling in:
  - `crates/cm-cli/src/mcp/tools/get.rs:12` to `14`
  - `crates/cm-cli/src/mcp/tools/update.rs:12` to `14`
  - `crates/cm-cli/src/mcp/tools/forget.rs:18` to `22`
  - `crates/cm-cli/src/mcp/tools/stats.rs:11` to `18`
- Protocol coverage for all four tools is in `crates/cm-cli/tests/mcp_protocol/tool_calls.rs:166` to `204`.
- Shared rejection logic lives in `crates/cm-cli/src/shared.rs:107` to `119`.

### ALP-2086: Add missing positive cwd_inferred coverage for cm-web recall and frontend export

Status: PASS.

Evidence:

- Positive `/api/agent/recall?scope=cwd_inferred&cwd=...` coverage appears in `crates/cm-web/tests/parity/recall.rs:62` to `91`.
- Positive `/api/entries/recall?scope=cwd_inferred&cwd=...` coverage appears in `crates/cm-web/tests/parity/recall.rs:93` to `122`.
- Both tests compare HTTP output to capability recall using `ScopeSelector::cwd_inferred(Some(...))`.
- Frontend recall and export cwd contract coverage is asserted in `crates/cm-web/tests/frontend_scope_contract.rs:52` to `67`.

## Verification

Commands run successfully:

```sh
cargo test -p cm-cli
cargo test -p cm-web
cd crates/cm-web/frontend && pnpm run typecheck
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
```

`git status --short` was clean after verification.

## Key Patterns

- Scope selector validation remains centralized through `ScopeSelector::parse` and `ScopeSelector::with_cwd`.
- MCP public schema closure is generated from `tools.toml` rather than hand patched.
- cm-web parity tests compare HTTP behavior to capability requests, keeping frontend and backend contracts tied to the domain layer.

## Dependencies

- `cm-capabilities` provides scope parsing, resolution, recall, browse, and export capabilities.
- `cm-cli` provides CLI and MCP request surfaces.
- `cm-web` provides HTTP API parity and typed frontend client support.
- `pnpm` and TypeScript validate frontend type contract coverage.

## Relevance to Helioy

The follow-up work closes public contract gaps in the context store migration from removed `auto` and `scope_path` request inputs to `scope` with `cwd_inferred`. This improves agent interoperability because Codex, Nancy, and other Helioy agents can now rely on the same selector semantics across CLI, MCP, cm-web, and generated docs.

## Follow Up Review: Commit 3a83df4

Reviewed `3a83df4 nancy[ALP-2054]: Resolve post-completion scope feedback`. Verification passed with nonmutating equivalents for `just check` plus build, full nextest, doctests, and frontend typecheck.

Commands run successfully:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo build --workspace
cargo nextest run --workspace
cargo test --workspace --doc
cd crates/cm-web/frontend && pnpm run typecheck
```

`cargo nextest run --workspace` reported 648 tests run, 648 passed. `git status --short` remained clean.

Follow up item status:

1. Store comments: Partially addressed. Function and unit test comments are fixed in `crates/cm-cli/src/cli/store.rs:23` to `25` and `68` to `69`, but the module comment still says invocation prints guidance and exits 0 in `crates/cm-cli/src/cli/store.rs:8` to `9`. That remains false for invalid scope input.
2. `cx_stats` runtime parity: Addressed. `crates/cm-cli/src/mcp/tools/stats.rs:13` to `15` rejects removed scope inputs and unknown fields before handling `tag_sort`. Protocol coverage exists in `crates/cm-cli/tests/mcp_protocol/tool_calls.rs:206` to `229`.
3. Frontend cwd source contract: Addressed within the repo's no JS test runner boundary. `crates/cm-web/tests/frontend_scope_contract.rs:80` to `110` checks `client.ts` source slices for `entries.recall`, `agent.recall`, and `export` cwd serialization.
4. Stale test name: Addressed. `store_scope_auto_creates_scope_chain` was renamed to `store_exact_scope_creates_scope_chain` in `crates/cm-cli/tests/tools_integration/store.rs`.

Current residual finding: resolved by commit `b15b232`.

## Follow Up Review: Commit b15b232

Reviewed `b15b232 nancy[ALP-2054]: Remove remaining stale store stub comment`. The final stale store stub comment is resolved. `crates/cm-cli/src/cli/store.rs:8` to `9` now says valid invocations print Curator guidance and exit 0, while `crates/cm-cli/src/cli/store.rs:23` to `25` documents scope validation before printing.

Fresh verification passed:

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
rg -n 'always return|infallible|exits 0|Returns `Ok|return `Ok|stub is by definition|invocation prints.*exits 0|silently dropped' crates/cm-cli/src/cli/store.rs crates/cm-cli/tests/tools_integration/store.rs crates/cm-cli/src/mcp/tools/stats.rs crates/cm-web/tests/frontend_scope_contract.rs
```

The stale wording search returned no matches, and `git status --short` remained clean. All four post-completion feedback items are now verified resolved.

## Open Questions

- Should MCP runtime reject all unknown fields to match `additionalProperties: false`, or is schema-level rejection sufficient?
- Should frontend API tests include mocked fetch URL assertions for recall and export cwd serialization?
- Should stale comments and misleading test names around old auto semantics be cleaned in a small follow-up?
