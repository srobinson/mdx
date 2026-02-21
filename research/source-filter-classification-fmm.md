---
title: fmm source filter classification for Rust *_tests.rs files
type: research
tags: [fmm, rust, classification, cli, mcp, alp-2707]
summary: fmm currently classifies Rust *_tests.rs files under src as source because the test suffix set covers _test.rs but not _tests.rs.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

`fmm ls --filter source` means “return indexed files that do not match the configured test file heuristic.” The current heuristic treats `_test.rs` as test but not `_tests.rs`, so Rust test modules such as `crates/fmm-core/src/resolver/workspace_tests.rs` are returned as source. This appears to be pre-existing fmm behaviour exposed by the ALP-2707 road test, not a behaviour introduced by the ALP-2707 parser metadata work.

## Project Metadata

- Language: Rust workspace
- Relevant crates: `fmm-cli`, `fmm-core`, `fmm-store`
- Runtime command inspected: `/Users/alphab/.cargo/bin/fmm`, version `0.2.9+f211ed4`
- Current branch: `nancy/ALP-2707`, ahead of origin by 4 commits with uncommitted ALP-2707 changes
- fmm MCP status: attempted first, but the MCP index was unusable because the index schema version was 6 while the MCP server expected schema version 5. Findings therefore use targeted source reads, git history, CLI output, and SQLite inspection.

## Architecture

### File list filtering path

- CLI `fmm ls` loads the manifest, loads config from the repo root, then calls `collect_entries` with the requested filter: `crates/fmm-cli/src/cli/commands/ls.rs:17-70`.
- CLI filter semantics are implemented in `collect_entries`: `tests` keeps `config.is_test_file(path)`, `source` keeps `!config.is_test_file(path)`, and other values keep all files: `crates/fmm-cli/src/cli/commands/ls.rs:131-162`.
- MCP `fmm_list_files` mirrors the same contract. It validates `filter` as `all`, `source`, or `tests`, then filters via `Config::is_test_file`: `crates/fmm-cli/src/mcp/tools/list_files.rs:12-66` and `crates/fmm-cli/src/mcp/tools/list_files.rs:145-176`.

### Test file classifier

- `Config::is_test_file` is a path and filename heuristic. A file is test if its path contains a configured test segment or its filename ends with a configured suffix: `crates/fmm-core/src/config/mod.rs:19-30` and `crates/fmm-core/src/config/mod.rs:140-154`.
- Default test path segments include `/e2e/`, `/test/`, `/tests/`, `/spec/`, and `/__tests__/`: `crates/fmm-core/src/config/defaults.rs:7-15`.
- Default test filename suffixes include `.spec.ts`, `.test.ts`, `_test.go`, `_test.rs`, `.spec.tsx`, and `.test.tsx`, but not `_tests.rs`: `crates/fmm-core/src/config/defaults.rs:17-29`.
- The Rust parser descriptor likewise declares `_test.rs`, not `_tests.rs`: `crates/fmm-core/src/parser/builtin/rust/mod.rs:300-310`.

### Storage and indexing

- The SQLite `files` table stores path, LOC, modified date, imports, dependencies, named imports, namespace imports, function names, index metadata, and source fingerprint fields. It has no `source_type`, `is_test`, or equivalent classification column: `crates/fmm-store/src/schema.rs:92-110`.
- `PreserializedRow` likewise has no classification field: `crates/fmm-core/src/types.rs:18-32`.
- Serialization writes `rel_path`, `loc`, imports, dependencies, named imports, namespace imports, and function names, not test/source classification: `crates/fmm-core/src/types.rs:60-90` and `crates/fmm-core/src/types.rs:135-149`.
- Store reads populate `FileEntry` from the same file columns only: `crates/fmm-store/src/reader/files.rs:11-31` and `crates/fmm-store/src/reader/files.rs:65-74`.

## Key Patterns

- `--filter source` is not an indexing time type. It is a read time projection over `manifest.files` using `Config::is_test_file`.
- CLI and MCP have duplicated list filtering logic. The bug belongs in the shared classification rules, not in either list command.
- The repo currently mixes convention sources: config defaults include test patterns, and parser descriptors also expose language specific test patterns. For this CLI path, `Config::is_test_file` is the operative classifier.

## Detailed Findings

### Definition of `--filter source`

`--filter source` means “exclude files that `Config::is_test_file` marks as tests.” It does not mean “only files compiled in non test builds,” and it does not consult Rust `#[cfg(test)]` module inclusion.

Evidence:

- CLI filter branch: `crates/fmm-cli/src/cli/commands/ls.rs:158-160`.
- MCP filter branch: `crates/fmm-cli/src/mcp/tools/list_files.rs:164-166`.
- Classifier implementation: `crates/fmm-core/src/config/mod.rs:140-154`.

### Behaviour against `*_tests.rs`

Current classifier treats `crates/fmm-core/src/resolver/workspace_tests.rs` as source because:

- The path is under `src/resolver`, so it does not contain `/test/`, `/tests/`, `/spec/`, `/e2e/`, or `/__tests__/`.
- The filename ends with `_tests.rs`, not `_test.rs`.
- There is no `.fmmrc.toml` in the worktree overriding `test_patterns`.

Observed command output from the current worktree:

```text
fmm ls --filter source --pattern workspace_tests.rs
summary: 1 files · 679 LOC · largest: crates/fmm-core/src/resolver/workspace_tests.rs (679 LOC)

fmm ls --filter tests --pattern workspace_tests.rs
summary: 0 files · 0 LOC
```

SQLite confirms the row exists as a normal file row, with no classification column:

```text
select path, loc from files where path='crates/fmm-core/src/resolver/workspace_tests.rs';
crates/fmm-core/src/resolver/workspace_tests.rs|679
```

The file is clearly a test module in Rust source structure. It is included only under `#[cfg(test)]` via `#[path = "workspace_tests.rs"] mod workspace_tests;` in `crates/fmm-core/src/resolver/workspace.rs:489-491`.

The problem is broader than this file. The current worktree has 14 `crates/**/src/*_tests.rs` files, and all appear under `fmm ls --filter source --pattern '*_tests.rs'`.

### Provenance

- `git diff main...HEAD` scoped to the list filter and classifier files shows no changes to `crates/fmm-cli/src/cli/commands/ls.rs`, `crates/fmm-cli/src/mcp/tools/list_files.rs`, `crates/fmm-core/src/config/defaults.rs`, or `crates/fmm-core/src/config/mod.rs`.
- The only scoped diff is Rust parser metadata extraction in `crates/fmm-core/src/parser/builtin/rust/mod.rs`; it does not change the `_test.rs` suffix.
- `git blame` on the Rust descriptor suffix shows `_test.rs` was introduced in commit `b15d1fb` on 2026-03-16, before ALP-2707.
- `crates/fmm-core/src/resolver/workspace_tests.rs` dates to `a8f30dc`, also outside ALP-2707.

Conclusion: this was pre-existing behaviour exposed by the road test, not introduced by ALP-2707 workers or correctives.

### Verdict and remediation

Verdict: defect.

Reasoning: fmm advertises `--filter source` as excluding test files. Rust `src/foo_tests.rs` files included under `#[cfg(test)]` are test files in this codebase, and fmm currently returns them as source solely because its suffix list handles singular `_test.rs` but not plural `_tests.rs`.

Recommended remediation:

1. Add `_tests.rs` to the Rust test filename suffixes used by the operative classifier. The minimum fix is `crates/fmm-core/src/config/defaults.rs::default_test_filename_suffixes`.
2. For descriptor consistency, add `_tests.rs` to `crates/fmm-core/src/parser/builtin/rust/mod.rs::DESCRIPTOR` and update convention or parser registry tests that assert language test patterns.
3. Add regression coverage that `fmm ls --filter source --pattern '*_tests.rs'` excludes Rust test modules and `fmm ls --filter tests --pattern '*_tests.rs'` includes them.
4. Treat this as a shared source/test partition defect, not only an `ls` defect. Fresh peer consensus verified the same `Config::is_test_file` suffix gap affects CLI `ls`, `deps`, and `cycles`, plus MCP `fmm_list_files`, `fmm_dependency_graph`, and `fmm_dependency_cycles`. The centralized suffix fix corrects all six without per-command changes.

## Dependencies

- `glob`: CLI filename pattern matching for `fmm ls --pattern`.
- `rusqlite`: SQLite store schema and query layer.
- `serde_json`: persistence of JSON list fields in the `files` row.

## Relevance to Helioy

This affects road-test trust in fmm as a structural navigation tool. Source/test partition accuracy matters for large file triage, outline density work, dependency blast radius, and agent review workflows that use `--filter source` to avoid spending context on test fixtures.

## Open Questions

- Should fmm consolidate CLI/MCP list filtering behind one shared helper to avoid future divergence?
- Should source/test classification become a persisted store field, or should it remain read time so `.fmmrc.toml` changes apply without reindexing?
- Should Rust classification also detect `#[cfg(test)] #[path = "..."] mod ...;` inclusions, or is filename and path based classification sufficient?
- Should list filtering eventually use the convention registry? Fresh peer review found `ConventionRegistry::is_test_file` is used by glossary classification via `crates/fmm-core/src/manifest/glossary_builder.rs`, but `fmm ls` and `fmm_list_files` currently use `Config::is_test_file` directly. Do not conflate those classifier surfaces when filing the defect.
- Do not add `/tests` without a trailing slash as part of this fix. The observed defect is solved by the `_tests.rs` suffix, while `/tests` risks overmatching directory names such as `foo_tests_helper`.
