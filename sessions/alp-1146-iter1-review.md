---
title: ALP-1146 Iteration 1 Code Review
type: sessions
tags: [review, echoecho, admin, react-native]
summary: Review of 5 commits across 6 files for bug fixes (ALP-1147-1150). Fixed eternal spinner bug and alert button order inconsistency.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

Reviewed iteration 1 of ALP-1146 (User found bugs). Five commits touching buildings.tsx, hazards.tsx, routes.tsx, route/[id].tsx, building/[id].tsx, and _layout.tsx. Overall solid work across all four sub-issues.

## Issues Found and Fixed

### 1. Eternal spinner on building fetch failure (building/[id].tsx)

The guard `if (isLoading || !building)` showed only a spinner. When the fetch completed with an error or 404, `isLoading` became false but `building` stayed null, trapping the user in a spinner with no back button and no error message.

**Fix:** Split the guard into two branches. Loading state shows spinner. Null building after loading shows error text with a back button. Added `loadError` state to surface the actual error message.

### 2. Alert button order on Android (building/[id].tsx)

`handleDelete` listed the Delete button before Cancel. On iOS this is cosmetic (cancel always renders at the bottom), but on Android buttons render in declaration order, putting the destructive action on the left. Every other Alert in the codebase (hazards.tsx) orders Cancel first.

**Fix:** Reordered to `[Cancel, Delete]`.

## Patterns Observed

- The `buildingPathOverlay` function and `MAX_STATIC_MAP_COORDS`/`MAX_BUILDING_COORDS` constants are duplicated between routes.tsx and route/[id].tsx. Worth extracting to a shared utility in a future pass.
- Hazards screen is well structured. The render-phase setState pattern for resetting edit state when hazard changes is correct and avoids the common setState-in-effect lint error.
- Consistent dark theme color palette (#0A0A0F, #111116, #1E1E26, etc.) across all screens.

## Open Items

None. Both fixes are mechanical and do not require design decisions.
