---
title: FMM Git Metadata Index Stamp
type: sessions
tags: [backend, fmm, cli, sqlite, metadata]
summary: Added git SHA, branch, and dirty state stamping to FMM index metadata with CLI status display and tests.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented F1 foundations for recording git provenance in FMM indexes. `fmm generate` now probes the working tree by shelling out to git, persists optional SHA, branch, and dirty state metadata, supports explicit `--sha` override, supports `--no-git` opt out, and surfaces the stamped metadata in `fmm status`.

## API Contract

CLI contract:

- `fmm generate [--sha <SHA>] [--no-git] <root>`
  - `--sha <SHA>` stamps the provided SHA verbatim while still allowing branch and dirty state when git probing is enabled.
  - `--no-git` skips git probing and clears git metadata keys from the index.
  - Non git directories and empty repositories without a resolved HEAD leave git metadata absent.
- `fmm status`
  - Prints a `Git Metadata` section when metadata is present.
  - Displays short SHA, branch or detached state, and dirty status.
  - Reports metadata as absent when the index is not stamped.

Internal store contract:

```rust
pub struct GitMeta {
    pub sha: String,
    pub branch: Option<String>,
    pub dirty: bool,
}

trait FmmStore {
    fn write_meta(&self, git_meta: Option<&GitMeta>) -> Result<()>;
}
```

## Database Changes

No SQLite schema migration was required. The existing `meta` table now uses reserved keys:

- `git_sha`
- `git_branch`
- `git_dirty`

SQLite writes delete stale git metadata before inserting the current values, so `--no-git` and non git roots clear previous stamps cleanly.

## Security Considerations

Git integration uses `std::process::Command` with fixed git arguments and no shell interpolation. Client supplied `--sha` is stored as metadata only and is not executed. Existing parameterized SQLite writes remain in use.

## Performance Notes

Git probing runs once per generate operation using three git commands at most: resolve SHA, resolve branch, and porcelain status. No per file git calls were added, so indexing performance remains bounded by the existing scanner and writer paths.

## Open Items

- The orchestrator will run the final gate for PR #154.
- Future slices can consume these metadata keys for stale index detection or provenance checks.
