---
title: cm-cli Scope Surface Refactor Analysis
type: research
tags: [context-matters, cm-cli, mcp, cli, scope-refactor]
summary: Vertical integration map for removing public scope_path in favor of scope and reserved cwd_inferred.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

`cm-cli` has a mostly clean vertical path: `tools.toml` is the public contract, `crates/cm-cli/build.rs` generates MCP schemas, CLI help, and skill docs, while thin MCP and CLI adapters delegate to `cm-capabilities`. The `scope_path` name remains public in write, browse, and export surfaces, so removing it requires coordinated changes across contracts, adapters, capability request types, generated artifacts, docs, and protocol tests.

## Project Metadata

- Language: Rust workspace.
- Relevant crates: `cm-cli`, `cm-capabilities`, `cm-core`, `cm-store`.
- Public tool registry: `tools.toml`.
- Generation path: `crates/cm-cli/build.rs` writes `crates/cm-cli/src/mcp/generated_schema.rs`, `crates/cm-cli/src/mcp/generated_schema/*.json`, `crates/cm-cli/src/cli/generated_help.rs`, and `crates/cm-cli/templates/SKILL.md`.
- Commands from project docs: `just check`, `just build`, `just test`, `just fmt`.

## Architecture

### Contract source

`tools.toml` is the source of truth for MCP descriptions, input schemas, CLI help strings, and generated skill docs. Scope related public parameters currently appear as:

- `cx_recall.scope`: already public and accepted as a scope path.
- `cx_store.scope_path`: public MCP name, CLI flag is `--scope`.
- `cx_deposit.scope_path`: public MCP name, CLI flag is `--scope`.
- `cx_browse.scope`: preferred input, supports `auto` or explicit scope path.
- `cx_browse.scope_path`: compatibility exact filter, CLI flag is `--scope-path`.
- `cx_export.scope_path`: public MCP name, CLI flag is `--scope`.

### Generated surfaces

Generated files mirror `tools.toml`:

- `crates/cm-cli/src/mcp/generated_schema.rs` assembles tool list output.
- `crates/cm-cli/src/mcp/generated_schema/cx_browse.json`, `cx_store.json`, `cx_deposit.json`, and `cx_export.json` expose `scope_path` today.
- `crates/cm-cli/src/cli/generated_help.rs` exports help constants such as `STORE_SCOPE_PATH_HELP`, `DEPOSIT_SCOPE_PATH_HELP`, `BROWSE_SCOPE_PATH_HELP`, and `EXPORT_SCOPE_PATH_HELP`.
- `crates/cm-cli/templates/SKILL.md` includes examples using `scope_path` for `cx_store`, `cx_browse`, and `cx_export`.

### MCP path

`crates/cm-cli/src/mcp/server.rs` dispatches `tools/call` to `tools::cx_recall`, `tools::cx_store`, `tools::cx_deposit`, `tools::cx_browse`, and `tools::cx_export`. Each handler parses JSON into a local params struct, then builds a capability request.

- `crates/cm-cli/src/mcp/tools/recall.rs`, symbol `cx_recall`: parses `scope` into `ScopePath`, builds `RecallRequest`.
- `crates/cm-cli/src/mcp/tools/store.rs`, symbol `cx_store`: deserializes directly into `StoreRequest`. `StoreRequest` currently has `scope_path` with serde alias `scope`.
- `crates/cm-cli/src/mcp/tools/deposit.rs`, symbol `cx_deposit`: `CxDepositParams.scope_path` has serde alias `scope`, then builds `DepositRequest.scope_path`.
- `crates/cm-cli/src/mcp/tools/browse.rs`, symbol `cx_browse`: accepts both `scope` and `scope_path`, parses compatibility `scope_path`, then builds `BrowseRequest` with both fields.
- `crates/cm-cli/src/mcp/tools/export.rs`, symbol `cx_export`: accepts `scope_path` and builds `ExportRequest.scope_path`.

### CLI path

`crates/cm-cli/src/cli/cli_def.rs`, symbol `Commands`, defines clap flags. Dispatch is in `crates/cm-cli/src/main.rs`, symbol `run`.

- `Recall` exposes `--scope`, then `crates/cm-cli/src/cli/recall.rs`, symbol `run`, parses it into `RecallRequest.scope`.
- `Browse` exposes `--scope`, `--scope-path`, `--scope-mode`, and `--cwd`, then `crates/cm-cli/src/cli/browse.rs`, symbol `run`, builds `BrowseRequest` with both `scope` and `scope_path`.
- `Store` declares `--scope` but is not operational. `crates/cm-cli/src/cli/store.rs`, symbol `run`, prints that direct CLI storage is not exposed.
- `Deposit` exposes `--scope`, stores it in a local `scope_path` variable, then `crates/cm-cli/src/cli/deposit.rs`, symbol `run`, calls `resolve_scope` and builds `DepositRequest.scope_path`.
- `Export` exposes `--scope`, stores it in a local `scope_path` variable, then `crates/cm-cli/src/cli/export.rs`, symbol `run`, builds `ExportRequest.scope_path`.

### Capability path

The public adapter names feed request structs in `cm-capabilities`:

- `crates/cm-capabilities/src/recall/types.rs`, symbol `RecallRequest`: already uses `scope: Option<ScopePath>`.
- `crates/cm-capabilities/src/store.rs`, symbol `StoreRequest`: public serde field is `scope_path`, with alias `scope`.
- `crates/cm-capabilities/src/deposit.rs`, symbol `DepositRequest`: field is `scope_path: String`.
- `crates/cm-capabilities/src/browse.rs`, symbol `BrowseRequest`: has both `scope: Option<String>` and compatibility `scope_path: Option<ScopePath>`.
- `crates/cm-capabilities/src/export.rs`, symbol `ExportRequest`: field is `scope_path: Option<String>`.
- `crates/cm-capabilities/src/scope/resolution.rs`, symbol `resolve_browse_scope`: routes `scope` and `scope_path` through `normalize_browse_scope`.

## Key Patterns

- Thin adapters: MCP and CLI handlers mostly parse inputs, construct capability requests, then project text or JSON output.
- Shared capability logic: `browse`, `recall`, `deposit`, and `export` own validation and store calls.
- Generated contract: changing `tools.toml` plus `build.rs` output is required before protocol tests reflect the new surface.
- Compatibility residue: `scope_path` is already partly hidden from CLI users as `--scope`, but remains visible in MCP schemas, skill docs, test fixtures, request fields, and error text.

## Detailed Findings

### Public `scope_path` occurrences to remove or rename

1. `tools.toml`
   - Rename MCP parameters for `cx_store`, `cx_deposit`, and `cx_export` from `scope_path` to `scope`.
   - Remove `cx_browse.scope_path` entirely.
   - Update `cx_browse.scope` docs so the reserved value is `cwd_inferred`, not `auto`, if that is the intended new contract.
   - Update skill workflow examples that currently call `cx_store(..., scope_path: ...)`.

2. Generated files
   - Regenerate `crates/cm-cli/src/mcp/generated_schema/*.json`.
   - Regenerate `crates/cm-cli/src/cli/generated_help.rs`.
   - Regenerate `crates/cm-cli/templates/SKILL.md`.
   - Verify `cx_browse` input schema no longer contains `scope_path` and that `scope` documents `cwd_inferred`.

3. MCP handlers
   - `crates/cm-cli/src/mcp/tools/browse.rs`, symbol `CxBrowseParams`: remove `scope_path`, reject it explicitly only if you want a clearer breaking change message than serde unknown field behavior.
   - `crates/cm-cli/src/mcp/tools/browse.rs`, symbol `cx_browse`: stop parsing compatibility `scope_path`; build `BrowseRequest` with only `scope`, `scope_mode`, `cwd`, and filters.
   - `crates/cm-cli/src/mcp/tools/deposit.rs`, symbol `CxDepositParams`: rename field to `scope`; decide whether to keep serde alias `scope_path` temporarily. For a breaking change, do not keep the alias.
   - `crates/cm-cli/src/mcp/tools/export.rs`, symbol `CxExportParams`: rename field to `scope` and pass it to the capability request.
   - `crates/cm-cli/src/mcp/tools/store.rs`, symbol `cx_store`: because it deserializes directly into `StoreRequest`, the capability request type must change or a boundary specific MCP params type should be introduced.

4. CLI flags
   - `crates/cm-cli/src/cli/cli_def.rs`, symbol `Commands`: remove `Browse.scope_path` and the `--scope-path` flag.
   - Keep CLI `--scope` for store, deposit, browse, export. The variable names can be renamed from `scope_path` to `scope` for clarity.
   - `crates/cm-cli/src/cli/browse.rs`, symbol `run`: remove the `scope_path` argument and request field.
   - `crates/cm-cli/src/cli/deposit.rs`, symbol `run`: rename parameter and local variable to `scope`, then pass normalized value to the capability.
   - `crates/cm-cli/src/cli/export.rs`, symbol `run`: rename parameter to `scope`.
   - `crates/cm-cli/src/main.rs`, symbol `run`: update command match arms and argument forwarding.

5. Capability request types
   - `crates/cm-capabilities/src/store.rs`, symbol `StoreRequest`: rename public field to `scope`. Internally it can still parse into a `ScopePath` value. If external JSON compatibility must be broken, remove serde alias `scope_path`.
   - `crates/cm-capabilities/src/deposit.rs`, symbol `DepositRequest`: rename `scope_path` to `scope`, or introduce a parsed internal field later in the function.
   - `crates/cm-capabilities/src/browse.rs`, symbol `BrowseRequest`: remove `scope_path` and rely on `scope` only.
   - `crates/cm-capabilities/src/export.rs`, symbol `ExportRequest`: rename `scope_path` to `scope`.
   - Preserve storage model names like `Entry.scope_path` and `ScopePath` unless this refactor also targets persistence and export shape. The requested change says public surface, not internal model.

6. Browse scope resolution
   - `crates/cm-capabilities/src/scope/resolution.rs`, symbol `normalize_browse_scope`: replace `auto` with `cwd_inferred` as the reserved inference value.
   - `crates/cm-capabilities/src/scope/resolution.rs`, symbol `resolve_auto_scope`: rename to match `cwd_inferred` semantics if desired.
   - `crates/cm-capabilities/src/scope/types.rs`, symbol `BrowseScopeInput`: consider renaming `Auto` to `CwdInferred`.
   - Response metadata currently emits `requested_scope: "auto"`. Decide whether this should become `cwd_inferred` for the new contract. It should, if clients are expected to round trip or compare requested scope.

7. Text projections and advisories
   - `crates/cm-capabilities/src/projection/browse_view.rs` renders query and narrow hints with `scope` and `cx_browse(...)`. Update tests if output changes from `scope=auto` to `scope=cwd_inferred`.
   - Default browse advisory currently says no scope specified, using `scope='auto'`. Update constant source in browse capability or projection support to `scope='cwd_inferred'`.
   - Error messages in `crates/cm-capabilities/src/scope/resolution.rs` mention `scope_path`. Remove conflict errors if `scope_path` is gone. Add a reserved value error for invalid uses if needed.

### Tests that will need focused changes

- `crates/cm-cli/tests/mcp_protocol/tools_list.rs`: currently asserts `cx_browse` input schema contains `scope_path`. Change to assert absence and validate `scope` docs or enum behavior.
- `crates/cm-cli/tests/browse_scope_tests.rs`: rename default expectations from `scope=auto` to `scope=cwd_inferred`, remove `browse_scope_path_stays_exact_without_resolution`, replace with explicit `scope` exact filter test, and remove conflict test involving `scope_path`.
- `crates/cm-cli/tests/cli_integration.rs`: `browse_scope_path_filters_exact_scope` should become `browse_scope_filters_exact_scope` using `browse --scope global/project:helioy -j`.
- `crates/cm-cli/tests/cli_flags.rs`: browse help assertion must no longer expect compatibility exact scope path.
- `crates/cm-cli/tests/adapter_error_parity.rs`: replace MCP invalid `scope_path` browse call with invalid `scope`; update deposit inputs from `scope_path` to `scope`.
- `crates/cm-cli/tests/tools_integration/store.rs`: update MCP store payloads from `scope_path` to `scope`; invalid scope test should still assert `Invalid scope_path` only if internal error text remains, otherwise update to public `Invalid scope`.
- `crates/cm-cli/tests/tools_integration/deposit.rs`: update payloads to `scope`.
- `crates/cm-cli/tests/tools_integration/export.rs` and `crates/cm-cli/tests/mcp_protocol/export.rs`: update calls to `cx_export` with `scope` where filtered export is exercised.
- `crates/cm-capabilities/tests/browse_scope/*`: remove compatibility tests for simultaneous `scope` and `scope_path`; replace with `scope` exact path and `cwd_inferred` tests.
- Snapshot tests that capture `scope=auto`, advisory text, generated help, or schema JSON will need updates.

## Concrete Issue Breakdown

### Issue 1: Update public tool contract in `tools.toml`

Scope:
- Rename public write and export parameters to `scope`.
- Remove `cx_browse.scope_path`.
- Replace `auto` with reserved `cwd_inferred` for browse inference.
- Update skill examples and workflow text in the same source file.

Acceptance:
- Generated MCP schema for `cx_browse` has no `scope_path` input.
- Generated MCP schemas for `cx_store`, `cx_deposit`, and `cx_export` expose `scope` rather than `scope_path`.
- Generated skill docs contain no public `scope_path` examples except storage or export result fields if intentionally retained.

### Issue 2: Refactor capability request types and browse scope normalization

Scope:
- Rename public request fields in `StoreRequest`, `DepositRequest`, `BrowseRequest`, and `ExportRequest`.
- Remove `BrowseRequest.scope_path`.
- Update `normalize_browse_scope` to support `cwd_inferred` and explicit scope paths through `scope`.
- Preserve internal `ScopePath` domain type and persisted `Entry.scope_path` unless separately scoped.

Acceptance:
- `scope="global/project:helioy"` filters exactly where prior compatibility `scope_path` did.
- `scope="cwd_inferred"` resolves via cwd and emits resolution metadata.
- `scope_path` is not accepted at public capability serde boundaries if this is truly breaking.

### Issue 3: Refactor MCP and CLI adapters

Scope:
- Update `CxBrowseParams`, `CxDepositParams`, `CxExportParams`, and direct `StoreRequest` deserialization path.
- Update `Commands`, `main::run`, and CLI run signatures.
- Remove `cm browse --scope-path`.
- Keep `--scope` behavior for CLI browse, deposit, export, and store help.

Acceptance:
- MCP `tools/call` succeeds for `cx_store`, `cx_deposit`, `cx_browse`, and `cx_export` using `scope`.
- MCP `cx_browse` rejects or ignores old `scope_path` according to the chosen breaking policy. Prefer reject with a precise error.
- CLI help has no `--scope-path`.

### Issue 4: Update docs, templates, and user examples

Scope:
- Regenerate `crates/cm-cli/templates/SKILL.md`.
- Update README, TLDR, and PROJECT only if public examples mention old input names. Current top level docs are mostly tool lists, but generated skill docs have multiple old examples.
- Update advisory and help wording from `auto` to `cwd_inferred`.

Acceptance:
- `rg "scope_path|scope-path|scope=auto" tools.toml crates/cm-cli/templates README.md TLDR.md PROJECT.md` returns only intentional internal result field references.

### Issue 5: Protocol and integration test migration

Scope:
- Update MCP tools list schema assertions.
- Update browse scope tests, CLI integration tests, CLI flag tests, adapter parity tests, and tool integration payloads.
- Update snapshots and generated schema fixtures.

Acceptance:
- `cargo test -p cm-cli` passes.
- `cargo test -p cm-capabilities` passes.
- `just check` passes.

## Dependencies

- `clap` and `clap_complete`: CLI flags and help.
- `serde` and `serde_json`: MCP parameter parsing, generated schemas, structured content.
- `cm-core::ScopePath`: internal validation and storage model.
- `cm-capabilities`: shared capability layer for read, write, projection, and scope inference.
- `sqlx` through `cm-store`: backing storage, not directly impacted by public parameter rename.

## Relevance to Helioy

This refactor makes context memory tool surfaces less leaky. Agents should think in terms of `scope`, with `cwd_inferred` as an explicit reserved inference mode, while `scope_path` remains an internal storage field. That aligns cm with the wider Helioy convention that tools expose intent and hide persistence details.

## Open Questions

1. Should `cx_export` output keep `entries[].scope_path`? Recommendation: yes, unless the export format itself is part of the breaking public change.
2. Should old `scope_path` inputs produce a custom error, or fail by unknown field behavior? Recommendation: custom error during the first breaking release for clearer migration.
3. Should `cx_store` keep serde alias `scope_path`? Recommendation: no, if the task requires removing public `scope_path`.
4. Should no scope on `cx_browse` default to `cwd_inferred` exactly, replacing prior `auto` output in advisories and `requested_scope`? Recommendation: yes, to make the reserved value coherent.
