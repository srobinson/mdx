---
title: FMM list files glob pattern fix
type: sessions
tags: [backend, fmm, mcp, cli, glob, alp-2707]
summary: Fixed MCP list files filename glob matching and aligned it with CLI behavior.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented ALP 2707 glob pattern fix for `fmm_list_files`. The MCP surface now uses the same shell style filename glob matcher as the CLI instead of a custom recursive matcher that failed for embedded wildcard patterns like `*preflight*`.

Key decisions:

* Moved filename glob matching into `crates/fmm-cli/src/filename_glob.rs` as the shared source of truth.
* Routed both `fmm ls --pattern` and MCP `fmm_list_files(pattern)` through `FilenameGlob`.
* Removed the custom recursive matcher from `crates/fmm-cli/src/mcp/tools/common.rs`.
* Kept matching scoped to basenames, not full paths.
* Kept invalid glob handling explicit and consistent: CLI returns `Invalid --pattern glob`, MCP returns `ERROR: Invalid pattern glob`.

Commit pushed:

* `8d547cb` `fix(mcp): align list_files filename glob matching`

Reviewer signoff received:

* `I sign off on the glob-pattern fix as currently filed`

## API Contract

No HTTP API contract changed.

Tool contract affected:

```typescript
interface FmmListFilesRequest {
  directory?: string;
  pattern?: string; // Shell style filename glob, matched against basename only
  limit?: number;
  offset?: number;
  sort_by?: "name" | "path" | "loc" | "exports" | "downstream" | "modified";
  order?: "asc" | "desc";
  group_by?: "subdir";
  filter?: "all" | "source" | "tests";
}
```

Behavioral contract:

* `*preflight*` matches `spawn_preflight.rs`.
* `?` matches one filename character.
* Character classes such as `[ab]*.ts` are supported by `glob::Pattern`.
* Invalid glob syntax surfaces an error rather than silently returning zero matches.

## Database Changes

No database schema changes, migrations, or index format changes.

The local `.fmm.db` was refreshed by verification tooling and validated after the implementation.

## Security Considerations

No auth or network surface changed.

Input hardening improved for the `pattern` parameter:

* CLI compiles the glob before filtering and reports invalid syntax.
* MCP compiles the glob before filtering and reports invalid syntax.
* Matching remains basename scoped, which avoids unintended full path pattern expansion.

## Performance Notes

The matcher is compiled once per `fmm_list_files` call, then reused for every candidate filename. This avoids compiling the glob inside the manifest iteration.

Verification run:

```sh
just gen-docs
INSTA_UPDATE=always just test
just check
just test
./target/debug/fmm validate
./target/debug/fmm ls --pattern '*space*' --sort-by name --limit 3
# MCP fmm_list_files with pattern '*space*'
./target/debug/fmm ls --pattern '['
# MCP fmm_list_files with invalid pattern '['
```

Results:

* `just check` clean.
* `just test`: 1226 tests run, 1226 passed, 3 skipped.
* `./target/debug/fmm validate`: all indexed files up to date.
* CLI and MCP both returned 9 files for `*space*`.
* CLI and MCP both surfaced invalid glob diagnostics for `[`.

## Open Items

None for this item.
