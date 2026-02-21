---
title: ALP-2054 MCP CLI Help And Generated Artifact Review
type: research
tags: [context-matters, alp-2054, mcp, cli, scope-migration, review]
summary: Lane B review found migrated MCP scope tools aligned, with gaps in CLI store validation and non-scope MCP legacy input rejection.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

ALP-2054 migrated the primary scoped MCP request surfaces to `scope` and `cwd_inferred`. The generated MCP schemas, `tools.toml`, generated CLI help, and MCP handlers for `cx_browse`, `cx_recall`, `cx_store`, `cx_deposit`, and `cx_export` are mostly aligned. I found two behavior gaps worth fixing before treating the public contract as fully closed.

## Project Metadata

- Language: Rust workspace.
- Reviewed packages: `cm-cli`, `cm-capabilities`.
- Generated artifacts: `crates/cm-cli/src/mcp/generated_schema/*.json`, `crates/cm-cli/src/cli/generated_help.rs`, `crates/cm-cli/templates/SKILL.md`.
- Generation source: `tools.toml`, read by `crates/cm-cli/build.rs`.
- Verification date: 2026-04-28.

## Architecture

- `tools.toml` owns MCP descriptions, CLI help snippets, parameter names, and output schemas.
- `crates/cm-cli/build.rs` generates MCP tool JSON files, `generated_schema.rs`, generated CLI help constants, and the Skill template.
- MCP handlers in `crates/cm-cli/src/mcp/tools/*.rs` parse JSON request arguments and delegate to `cm-capabilities`.
- `cm-capabilities::scope::ScopeSelector` accepts exact paths and `cwd_inferred`; it rejects `auto` during parse.

## Detailed Findings

### Medium: `cm store --scope auto` is accepted by the CLI stub

`cm store` exposes `--scope <SCOPE>` through the public clap surface and generated help, but the handler is a stub that drops all parsed flags and exits successfully.

Evidence:

- Public store scope flag is exposed at `crates/cm-cli/src/cli/cli_def.rs:123-151`.
- Help says the flag is a scope selector at `crates/cm-cli/src/cli/generated_help.rs:27`.
- The stub documents that flags are silently dropped at `crates/cm-cli/src/cli/store.rs:1-15` and returns success at `crates/cm-cli/src/cli/store.rs:23-55`.
- Command run: `target/debug/cm store --title T --body B --kind fact --scope auto`.
- Observed result: printed the Curator UI message and exited `0`.

Why it matters:

The public migration docs say `scope="auto"` inputs are rejected on migrated CLI surfaces. This command is non-mutating, so no data is corrupted, but it is still a public CLI request surface that accepts a removed value.

Suggested fix:

Either remove functional looking store flags from the stub, or validate `--scope` before printing the stub message. If `store` remains a documented CLI request surface, `auto` should fail the same way as browse, recall, deposit, and export.

### Medium: Non-scope MCP tools ignore removed scope inputs

MCP handlers that do not use scope do not consistently reject removed public scope fields. The most visible case is `cx_stats`, which reads `tag_sort` directly and ignores everything else.

Evidence:

- Shared rejection helper exists at `crates/cm-cli/src/shared.rs:108-119`.
- Scoped handlers call it, for example `cx_browse` at `crates/cm-cli/src/mcp/tools/browse.rs:56-68`, `cx_recall` at `crates/cm-cli/src/mcp/tools/recall.rs:38-51`, and `cx_export` at `crates/cm-cli/src/mcp/tools/export.rs:36-44`.
- `cx_get` does not call it at `crates/cm-cli/src/mcp/tools/get.rs:10-17`.
- `cx_update` does not call it at `crates/cm-cli/src/mcp/tools/update.rs:10-19`.
- `cx_forget` does not call it at `crates/cm-cli/src/mcp/tools/forget.rs:11-19`.
- `cx_stats` does not parse with a deny unknown fields struct and ignores unknown fields at `crates/cm-cli/src/mcp/tools/stats.rs:11-18`.
- Command run: Python MCP smoke test against `target/debug/cm serve` with `CM_DATA_DIR` pointing at a temp dir.
- Observed result: `cx_stats` with `{"scope_path":"global"}` returned normal stats. `cx_get`, `cx_forget`, and `cx_update` ignored `scope_path` and failed later on unrelated validation.

Why it matters:

If the public contract means every MCP tool rejects removed scope selection inputs, these handlers are a gap. If the intended contract only covers tools that previously had scope inputs, then this is testable ambiguity in the docs.

Suggested fix:

Apply `reject_removed_scope_inputs` at the start of every MCP tool handler, or explicitly scope the public migration docs to the five migrated scope tools.

### Low: Generated input schemas are open objects

The generated MCP input schemas omit `additionalProperties: false` for all tools.

Evidence:

- `crates/cm-cli/build.rs:212-215` creates an object schema with `type` and `properties` only.
- `jq` over `crates/cm-cli/src/mcp/generated_schema/*.json` showed `additionalProperties` as null for every tool.
- Migrated handlers still reject unknown fields at runtime through serde or `reject_unknown_fields`, so this is schema quality, not handler correctness.

Why it matters:

Clients using the public MCP schema cannot prevalidate stale request fields such as `scope_path`. Runtime rejection works for migrated scope tools, but the schema does not encode the closed request contract.

Suggested fix:

Emit `"additionalProperties": false` for generated input schemas, unless MCP client compatibility requires open objects.

### Low: CLI examples mention `cwd_inferred` in text, but not as a concrete command

Help text explains `cwd_inferred`, yet command examples mostly demonstrate exact scope paths.

Evidence:

- Root help mentions browse defaulting to `scope=cwd_inferred` at `crates/cm-cli/src/cli/help_text.rs:65-68`.
- Browse examples use no scope or an exact path at `crates/cm-cli/src/cli/help_text.rs:83-90`.
- Deposit examples use exact path at `crates/cm-cli/src/cli/help_text.rs:124-130`.
- Export examples use exact path at `crates/cm-cli/src/cli/help_text.rs:140-145`.
- Markdown help output has option text for `cwd_inferred`, but no concrete `--scope cwd_inferred --cwd ...` command.

Why it matters:

The migration introduces a new reserved value. A concrete example would reduce agent confusion and satisfy the public documentation emphasis on `cwd_inferred`.

## Positive Findings

- `ScopeSelector::parse` rejects `auto` and points callers to `cwd_inferred` at `crates/cm-capabilities/src/scope/types.rs:65-78`.
- The five migrated MCP scope tools expose `scope` and omit `scope_path` and `scope_mode` in generated input schemas.
- `tools.toml` and generated `SKILL.md` clearly describe the public request boundary and explain that `scope_path` remains valid in persisted response data.
- Build generation is current. Running targeted tests left `git status --short` clean.

## Verification Commands

- `fmm_list_files(group_by: "subdir")`
- `fmm_glossary(pattern: "ScopeSelector", mode: "all", limit: 50)`
- `fmm_file_outline(...)` and `fmm_read_symbol(...)` for MCP handlers, generated schema loader, ScopeSelector, and relevant tests.
- `cargo test -p cm-cli public_scope_artifacts_do_not_expose_removed_request_terms`
- `cargo test -p cm-cli browse_rejects_removed_auto_scope`
- `cargo test -p cm-cli removed_scope_path_flag_is_rejected`
- `cargo test -p cm-cli protocol_migrated_scope_tools`
- `cargo test -p cm-cli protocol_browse_rejects_scope_mode_input`
- `cargo test -p cm-cli snapshot_cx_export`
- `target/debug/cm --help`, `target/debug/cm browse --help`, `target/debug/cm recall --help`, `target/debug/cm export --help`
- `target/debug/cm --markdown-help | rg -n "scope_path|scope_mode|scope=auto|cwd_inferred|--scope|Scope Resolution" -C 1`
- `target/debug/cm browse --scope auto` with temp `CM_DATA_DIR`
- `target/debug/cm store --title T --body B --kind fact --scope auto`
- Python MCP smoke test for removed `scope_path` on `cx_stats`, `cx_get`, `cx_forget`, and `cx_update`.
- `git status --short`

## Dependencies

- `serde` for MCP argument deserialization and unknown field behavior.
- `serde_json` for MCP request and response values.
- `clap` for CLI help and argument rejection.
- `cm-capabilities::scope::ScopeSelector` for exact path and `cwd_inferred` semantics.

## Relevance to Helioy

This migration directly affects agent memory calls. Public docs and tool schemas are the agent interface. Any stale `auto` or `scope_path` behavior will propagate into agent habits and generated prompts.

## Open Questions

- Should removed scope selector fields be rejected by every MCP tool, or only by tools that own scope selection?
- Should `cm store` keep parseable flags while remaining a stub, or should it validate scope inputs before exiting?
- Is `additionalProperties: false` acceptable for the MCP clients currently targeted by context-matters?
