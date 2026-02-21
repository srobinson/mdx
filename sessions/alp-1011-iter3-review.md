---
title: ALP-1011 Iteration 3 Code Review
type: sessions
tags: [review, echoecho, favorites, sectionlist, react-native]
summary: Fixed duplicate SectionList key bug in favorites.tsx; other 4 commits clean
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed 5 commits from iteration 3 of ALP-1011 (multi-perspective code review sweep). Four commits were clean. One had a latent bug introduced during the FlatList to SectionList migration.

**Commits reviewed:**
- ALP-1082: Keyboard fallback search handler on home screen
- ALP-1107: Dead routeStore deletion
- ALP-1078: WaypointDot/HazardDot memoization
- ALP-1088: INACTIVE_STT_SESSION static constant for navigate screen
- ALP-1084: FlatList to SectionList migration on favorites screen

## Issues Found and Fixed

### 1. Duplicate SectionList keys (favorites.tsx)

**File:** `apps/student/app/favorites.tsx`
**Severity:** Medium (causes React reconciliation warnings and potential UI glitches)

The SectionList migration changed `keyExtractor` from `${item.type}-${item.routeId}` (which included a section prefix) to bare `item.routeId`. A route can exist in both `favorites` and `history` arrays locally between the optimistic favorite toggle and the next Supabase sync. The Supabase query uses `is_favorite` as a mutually exclusive flag, but the local state does not enforce this.

**Fix:** Filter `history` to exclude routes already present in `favorites` within the `useMemo` that builds `sections`. This matches the Supabase semantic where a route is either a favorite or a history entry, never both.

## Patterns Observed

- The SectionList migration correctly removed Fragment-as-root and index-based section detection, but lost the key uniqueness guarantee that the old `type` prefix provided. When migrating list structures, key strategies need to be reevaluated alongside the data model.
- `BUNDLED_BUILDINGS` is an empty array (ALP-1061 tracks this separately). The keyboard search fallback will return "No destination found" on first launch before sync. Not a regression from this iteration.

## Open Items

None. All issues resolved.
