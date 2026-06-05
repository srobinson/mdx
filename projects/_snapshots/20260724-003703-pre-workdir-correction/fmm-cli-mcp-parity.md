---
title: fmm CLI MCP Parity Scope
type: projects
tags: [fmm, cli, mcp, parity, linear]
summary: Scope and issue breakdown for making fmm CLI behavior match the MCP tool surface.
status: active
project: fmm
confidence: high
created: 2026-04-20
updated: 2026-04-21
---

# fmm CLI MCP Parity Scope

## Purpose

Bring the `fmm` CLI into practical parity with the MCP tool surface. Parity means each MCP tool has a CLI equivalent with the same important arguments, comparable behavior, and tests that prevent drift.

This is about the navigation surface only. It does not include new MCP tools, protocol changes, storage changes, or parser expansion.

## Current State

The CLI already exposes the same eight navigation concepts as MCP:

- `fmm_lookup_export` maps to `fmm lookup`
- `fmm_list_exports` maps to `fmm exports`
- `fmm_dependency_graph` maps to `fmm deps`
- `fmm_read_symbol` maps to `fmm read`
- `fmm_file_outline` maps to `fmm outline`
- `fmm_search` maps to `fmm search`
- `fmm_list_files` maps to `fmm ls`
- `fmm_glossary` maps to `fmm glossary`

The remaining gaps are argument coverage and behavior drift. Several intended CLI flags are already declared in `crates/fmm-cli/tools.toml`, but are not wired through `Commands` and dispatch.

## Linear Issues

Parent:

- [ALP-1887](https://linear.app/alphabio/issue/ALP-1887/bring-fmm-cli-to-parity-with-mcp-navigation-tools): Bring fmm CLI to parity with MCP navigation tools

Children:

- [ALP-1888](https://linear.app/alphabio/issue/ALP-1888/add-fmm-exports-file-for-mcp-list-exports-parity): Add `fmm exports --file` for MCP list exports parity
- [ALP-1889](https://linear.app/alphabio/issue/ALP-1889/add-mcp-search-flags-to-fmm-search): Add MCP search flags to `fmm search`
- [ALP-1890](https://linear.app/alphabio/issue/ALP-1890/align-fmm-read-with-mcp-read-symbol-behavior): Align `fmm read` with MCP read symbol behavior
- [ALP-1891](https://linear.app/alphabio/issue/ALP-1891/align-fmm-glossary-with-mcp-precision-behavior): Align `fmm glossary` with MCP precision behavior
- [ALP-1892](https://linear.app/alphabio/issue/ALP-1892/add-cli-mcp-parity-tests-and-help-cleanup): Add CLI MCP parity tests and help cleanup

## Contract Matrix

| MCP tool | CLI command | Status | Required work |
| --- | --- | --- | --- |
| `fmm_lookup_export` | `fmm lookup` | Complete | Keep as is. |
| `fmm_list_exports` | `fmm exports` | Partial | Add `--file` and route to file export listing. |
| `fmm_dependency_graph` | `fmm deps` | Complete | Keep as is. |
| `fmm_read_symbol` | `fmm read` | Partial | Add MCP private method fallback and large class redirect behavior. |
| `fmm_file_outline` | `fmm outline` | Complete | Keep as is. |
| `fmm_search` | `fmm search` | Partial | Add `--limit`, `--min-loc`, and `--max-loc`. Keep `--loc` as CLI shorthand. |
| `fmm_list_files` | `fmm ls` | Complete | Keep as is. |
| `fmm_glossary` | `fmm glossary` | Partial | Add MCP precision model, truncation behavior, and shared formatting. |

## Implementation Plan

### 1. Add `fmm exports --file`

MCP accepts `fmm_list_exports({ file })`. The CLI currently has `pattern`, `--dir`, `--limit`, `--offset`, and `--json`, but no file scoped listing flag.

Work:

- Add `file: Option<String>` to `Commands::Exports`.
- Dispatch the new field through `main.rs`.
- Update `cli::exports` to accept `file`.
- When `--file` is present, return all exports from that file.
- Decide conflict behavior for `--file` with `pattern` or `--dir`. Prefer explicit validation and a clear error.
- Update help text and generated docs.

Acceptance:

- `fmm exports --file src/app.ts` matches MCP file listing behavior.
- JSON output works for `--file`.
- Invalid file returns a clear error.
- Tests cover normal, JSON, and conflicting flag cases.

### 2. Add MCP search flags to CLI

MCP accepts `limit`, `min_loc`, and `max_loc`. The CLI only exposes `--loc` for line count filtering and has no bare search limit.

Work:

- Add `--limit <usize>` to `fmm search`.
- Add `--min-loc <usize>` and `--max-loc <usize>`.
- Preserve `--loc` as an ergonomic CLI shorthand.
- Define conflict behavior when `--loc` is combined with `--min-loc` or `--max-loc`. Prefer explicit validation.
- Pass `limit` into `fmm_core::search::bare_search`.
- Update JSON output tests.

Acceptance:

- `fmm search auth --limit 5` caps fuzzy export results like MCP.
- `fmm search --min-loc 100 --max-loc 500` works.
- `--loc` still works.
- Conflicting LOC flags fail with a clear error.

### 3. Bring `fmm read` behavior in line with MCP

MCP has two behaviors not present in CLI:

- Private method fallback for `ClassName.method` when the method is not in `method_index`.
- Large bare class redirect that returns method hints instead of a misleading partial class body.

Work:

- Extract shared read resolution logic or reuse MCP logic from CLI through a command service.
- For missing dotted methods, locate the exported class file and run `find_private_method_range`.
- For large bare class reads, return `format_class_redirect` unless full source is requested.
- Preserve `--no-truncate`, `--line-numbers`, and `--json`.

Acceptance:

- `fmm read ClassName.privateMethod` works when `fmm outline --include-private` exposes the method.
- Large bare class reads show method level hints by default.
- `fmm read LargeClass --no-truncate` still returns full source.
- JSON behavior is defined and tested for redirect or bypass cases.

### 4. Bring `fmm glossary` behavior in line with MCP

This is the largest gap. MCP has richer precision semantics and response shaping:

- Default limit 10 with hard cap 50.
- `precision: named` by default.
- `precision: call-site` for Layer 3 tree sitter verification.
- Layer 2 named import filtering for bare function names.
- Namespace caller annotations.
- Reexport only annotations.
- Contextual messages when call site refinement finds no direct callers.
- Optional truncation bypass through `truncate: false`.

Work:

- Add `--precision named|call-site`.
- Add a CLI equivalent of MCP `truncate: false`, preferably `--no-truncate`.
- Move shared glossary computation into a common function used by CLI and MCP.
- Keep CLI color only at the outer formatting layer, if color remains useful.
- Preserve `--json`, but decide whether JSON should expose the enriched fields exactly.

Acceptance:

- `fmm glossary scheduleUpdate --precision named` matches MCP default caller filtering.
- `fmm glossary scheduleUpdate --precision call-site` matches MCP call site verification.
- Reexport only files are annotated.
- Namespace callers are disclosed.
- Limit behavior matches MCP.
- Tests cover named precision, call site precision, truncation, and JSON.

### 5. Add parity tests and drift checks

The current MCP tool tests are stronger than the CLI parity tests. Add CLI level coverage for the cases above.

Work:

- Add CLI tests for every newly wired flag.
- Add fixtures that cover private methods, large classes, bare function precision, namespace imports, and reexports.
- Add a small contract test that compares `tools.toml` declared CLI flags against `Commands` where feasible.
- Confirm generated help includes the new flags.

Acceptance:

- `cargo test -p fmm` passes.
- New tests fail on the current implementation and pass after parity work.
- Help output documents the new flags.

## Linear Issue Breakdown

### Issue 1: CLI MCP parity umbrella

Goal: Track the CLI parity effort and keep linked child issues coherent.

Acceptance:

- Child issues are linked.
- Scope document is linked.
- Completion means all parity issues are closed and tests pass.

### Issue 2: Add `fmm exports --file`

Acceptance:

- CLI flag exists.
- Behavior matches `fmm_list_exports(file)`.
- Tests cover text, JSON, missing file, and conflicts.

### Issue 3: Add MCP search flags to CLI

Acceptance:

- CLI exposes `--limit`, `--min-loc`, and `--max-loc`.
- `--loc` remains supported.
- Tests cover combined term plus filters and conflict validation.

### Issue 4: Align `fmm read` with MCP behavior

Acceptance:

- Private method fallback works.
- Large class redirect works.
- Existing read flags remain intact.
- Tests cover default, no truncate, private method, and JSON.

### Issue 5: Align `fmm glossary` with MCP precision

Acceptance:

- CLI exposes precision selection and no truncate behavior.
- CLI and MCP share glossary computation.
- Named precision and call site precision are tested.
- Namespace and reexport annotations are preserved.

### Issue 6: Add parity tests and help generation cleanup

Acceptance:

- CLI help includes the new flags.
- Generated docs reflect the actual CLI.
- A drift check exists for `tools.toml` versus `Commands`, if practical.

## Open Decisions

- Linear team, project, labels, priority, cycle, and assignee are still needed before ticket creation.
- Decide whether `fmm search --loc` can combine with `--min-loc` and `--max-loc`, or whether that should be rejected.
- Decide whether `fmm exports --file` can combine with `pattern` as an in file filter, or whether `--file` is exclusive.
- Decide JSON shape for `fmm read` large class redirect.
- Decide whether CLI glossary text should use the exact MCP YAML formatter or a colored human formatter with the same data.

## Suggested Sequencing

1. Wire low risk flags first: `exports --file`, search limit and LOC flags.
2. Extract shared read logic.
3. Extract shared glossary logic.
4. Add contract tests and regenerate help.
5. Create or update Linear issues from this document.

## Agent Use

No agent pass is required for the initial issue set. A targeted agent pass would be useful after ticket creation for two bounded reviews:

- Confirm test fixtures cover all MCP only behavior.
- Confirm shared CLI and MCP services are the right abstraction boundary.
