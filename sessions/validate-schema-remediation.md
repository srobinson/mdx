---
title: Validate schema remediation hint
type: sessions
tags: [backend, fmm, cli, validation, testing]
summary: Corrected fmm schema mismatch remediation hints to use plain generate and added regression coverage.
status: active
source: backend-engineer
confidence: high
created: 2026-05-23
updated: 2026-05-23
---

## Summary

Implemented, reviewed, and pushed commit `c4ba6f4ba4ee66fa367adb53d6ca6844016d8820` on branch `nancy/ALP-2707`.

The change corrects stale schema and version mismatch remediation hints from `fmm generate --force` to `fmm generate`, matching the existing `open_or_create` and `ensure_schema` auto rebuild path. Added CLI regression coverage for validate failure, happy path output, and plain generate recovery.

Phase B signoff was received from `nancy-ALP-2707:helioy-tools:engineering-code-reviewer:6:2.2` with the exact phrase: `I sign off on the validate-schema fix as currently filed`.

The branch was pushed to `origin/nancy/ALP-2707`.

## API Contract

No HTTP API changes.

CLI behavior contract:

* `fmm validate <path>` returns nonzero when the index schema version does not match the running binary.
* The schema mismatch error includes both versions and recommends `fmm generate`.
* `fmm validate <path>` still returns zero for a matching schema and reports all files indexed and up to date.
* `fmm generate <path>` with `force=false` repairs a stale schema index through the existing auto rebuild path.

## Database Changes

No persistent schema changes.

The implementation relies on the existing regeneratable SQLite index migration path:

* `fmm generate` opens the store through `SqliteStore::open_or_create`.
* `open_or_create` calls `ensure_schema`.
* `ensure_schema` drops and recreates stale or missing schema metadata, then writes the current schema version.

## Security Considerations

No auth, authorization, or network surface changes.

All database operations remain parameterized in the new tests. The production change is limited to diagnostic strings.

## Performance Notes

No production hot path change beyond message text.

Verification run:

* `just check` passed.
* `just test` passed: 1245 tests passed, 3 skipped, doc tests ok.
* `./target/debug/fmm generate .` followed by `./target/debug/fmm validate .` passed for 408 indexed files.
* Post push `git status --short --branch` showed `## nancy/ALP-2707...origin/nancy/ALP-2707` with no dirty files.

## Open Items

None for this task.
