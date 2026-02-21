---
title: ALP-1279 Iteration 5 Review - byHeading duplication fix
type: sessions
tags: [review, mdcontext, indexer, bug-fix, fixtures]
summary: Found and fixed byHeading duplication bug in buildIndex force mode; restored corrupted fixture files
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

Reviewed iteration 5 of ALP-1279 (mdcontext review feedback). Five commits covering test suites (storage, watcher, vector-store, security scenarios) and a brokenLinks array-to-Set optimization. Found one significant production bug and corrupted test fixtures.

## Issues Found and Fixed

### 1. byHeading duplication on force re-index (indexer.ts)

**Severity:** High (data corruption, silently worsening over time)

When `buildIndex` runs with `force: true`, line 266 resets the document index to empty but lines 273-274 preserved the existing section and link indexes. Since the cleanup logic at line 392 checks `if (existingEntry)` against the empty document index, it never fires. Old byHeading entries persist while new ones are appended. Each forced re-index multiplied byHeading array sizes by 3x (number of fixture files).

**Fix:** When `force: true`, also start from empty section and link indexes (matching the document index behavior).

### 2. Corrupted test fixtures (sections.json, documents.json, links.json)

**Severity:** Medium (test pollution, misleading fixture data)

- `sections.json` byHeading arrays had 54 duplicate entries per heading (should be 1)
- `documents.json` had hardcoded absolute worktree path as rootPath
- All three files lost trailing newlines

**Fix:** Restored all three fixture files to their canonical clean state from commit 6f84b61.

## Patterns Observed

- The `server.test.ts` `beforeAll` calls `buildIndex(FIXTURES_DIR, { force: true })` which modifies committed fixture files on disk as a side effect. This is the vector through which fixture corruption accumulates across iterations. The fixtures should either be .gitignored (regenerated per test run) or the test should write to a temp directory.
- The brokenLinks array-to-Set optimization (ALP-1216) was correct and well-scoped.
- All new test files follow consistent patterns: proper temp directory cleanup, Effect-based helpers, comprehensive edge case coverage.

## Open Items

None. All issues resolved with code changes.
