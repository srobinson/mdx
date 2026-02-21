---
title: "ALP-1279 Iteration 17 Review: Watch-mode deletion cleanup"
type: sessions
tags: [review, mdcontext, watch-mode, link-index]
summary: "Fixed stale backward link entries persisting after file deletion in watch mode. 1 issue found and fixed."
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

Reviewed iteration #17 of ALP-1279 (Review Feedback Mar 13 2026). Two commits in scope:

1. `8aedf50` — Reverted `shouldUseColor()` guard on progress bars back to plain `isTTY` check
2. `ba035fd` — Added deleted-file cleanup to watch-mode incremental reindex

The NO_COLOR revert is correct: progress bars use cursor control sequences, not ANSI color, so the no-color.org convention does not apply. The deleted-file cleanup had one gap.

## Issues Found and Fixed

### 1. Stale backward link entries on file deletion (`indexer.ts`)

**File:** `src/index/indexer.ts`, line ~428
**Commit:** `229862f`

The deleted-file cleanup correctly removed:
- Sections from `mutableSections`, `mutableByDocument`, `mutableByHeading`
- Forward links from `mutableForward` and corresponding backward references
- The document entry from `mutableDocuments`

But it did NOT remove `mutableBackward[deletedRelativePath]`. When other files link to a deleted file, the backward entry (listing those source files) persisted in the saved link index. `getIncomingLinks()` for the deleted path would return phantom sources.

**Fix:** Added `delete mutableBackward[relativePath]` after forward link cleanup. Added assertion in the existing link-removal test verifying incoming links are also cleared.

## Patterns Observed

The section cleanup and link cleanup blocks in the deletion handler are structurally identical to the existing "clean up old sections before adding new ones" block at line 540. Consistent pattern.

## Open Items

None. All 1294 tests pass, types clean.
