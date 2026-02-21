---
title: ALP-1146 Iteration 2 Clinical Review
type: sessions
tags: [review, echoecho, admin, bug-fix]
summary: Fixed eternal spinner and alert button order in route detail (same bugs previously fixed in building detail)
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

Reviewed 8 files changed across 5 commits in iteration 2 of ALP-1146 (user found bugs). Changes covered: building list tappability (ALP-1149), hazards screen fixes (ALP-1150), route thumbnail zoom and building overlays (ALP-1147), STT destination timeout and listening indicator (ALP-1151), and a prior review fix for building detail.

## Issues Found and Fixed

1. **Route detail eternal spinner** (`apps/admin/app/route/[id].tsx`): When route fetch failed or returned 404, `isLoading` became false but `route` stayed null. The guard `if (isLoading || !route)` kept showing a spinner forever. Added `loadError` state and an error view with back navigation, matching the pattern already applied to building detail in commit 5b0a032.

2. **Route detail Alert button order** (`apps/admin/app/route/[id].tsx`): Both `handleStatusChange` and `handleDelete` placed the destructive action button before Cancel. On Android this positions the destructive action on the left. Reordered to Cancel first, matching every other Alert in the codebase and the fix already applied to building detail.

## Patterns Observed

The previous review (commit 5b0a032) correctly identified the eternal spinner and alert button order bugs in building detail but did not check whether the same patterns existed elsewhere. Route detail had identical code and identical bugs. When fixing a pattern bug, always grep for other instances of the same pattern across the codebase.

## Open Items

None. All changes typecheck cleanly.
