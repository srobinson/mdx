---
title: EchoEcho ALP-935 Iteration 12 Review
type: sessions
tags: [review, echoecho, alp-935, react-native, expo, favorites, emergency-mode, admin-map]
summary: Reviewed admin map 4-layer panel (ALP-965/966/967/968) and student emergency/favorites work (ALP-962/964). Fixed favorite-clobber bug in appendHistory, useMemo for annotationWaypoints, and O(n²) renderItem allocation in favorites.tsx.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Iteration 12 covered:
- **ALP-965/966/967/968**: Admin map 4-layer panel (BuildingLayer, RouteLayer, PoiLayer, MapDetailPanel), BuildingEditPanel with metadata edit sheet, WaypointDetailContent, RouteDetailContent
- **ALP-962**: Emergency mode rebuilt — synchronous offline Haversine routing via useEmergencyRouting, CampusProvider with AsyncStorage-first offline cache, EmergencyOverlay triple-tap at root layout, emergency.tsx screen with focus management
- **ALP-964**: useRouteHistory hook with optimistic favorite toggle + Supabase sync, favorites.tsx screen with two-section FlatList, home screen updated with top-5 favorites

Both typechecks passed clean before and after fixes.

## Issues Found and Fixed

### 1. `appendHistory` silently de-favorites routes on re-navigation

**File:** `apps/student/src/hooks/useRouteHistory.ts`

**Bug:** `appendHistory` upserted with `is_favorite: false` hardcoded. On conflict (user_id, route_id), Supabase's `DO UPDATE SET` overwrites the existing `is_favorite` column. A user who had favorited a route and then navigated it again would have their favorite cleared in Supabase on the next app load.

**Fix:** Removed `is_favorite` from the `appendHistory` upsert payload. On INSERT the schema default (`false`) applies. On UPDATE the existing column is not touched, preserving any prior `true` value.

### 2. `annotationWaypoints` recomputed on every render

**File:** `apps/admin/src/hooks/useAdminMapData.ts`

**Bug:** The `.flatMap().filter()` expression ran on every call to the hook without memoization. For a campus with many routes and waypoints this is unnecessary work on every render cycle.

**Fix:** Wrapped in `useMemo([routes])`. Also renamed the internal `fetch` callback to `fetchMapData` to avoid shadowing the global `fetch` API.

### 3. FlatList data and section header logic in `favorites.tsx`

**File:** `apps/student/app/favorites.tsx`

**Bug 1:** `data={[...favorites.map(...), ...history.map(...)]}` was inlined directly in JSX — a new array allocated on every render, causing FlatList to think data changed even when it hadn't.

**Bug 2:** `renderItem` computed `[...favorites, ...history][index - 1]` on every item render to find the previous item for section header detection. O(n) allocation per item = O(n²) total. The type guard (`!('type' in prevItem)`) could never be true given the data structure.

**Fix:** Lifted merged list into `useMemo([favorites, history])` as `listData`. Replaced the prevItem check with `item.type === 'history' && index === favorites.length`, which is equivalent (the first history item is always at index === favorites.length in the merged array) and O(1).

## Patterns Observed

- The optimistic-write pattern in `useRouteHistory` is well-structured: local update → AsyncStorage write → announcement → Supabase write → revert on error.
- `CampusProvider` correctly separates static campus config from ephemeral navigation state in the Zustand store.
- `MapDetailPanel` slot-based architecture (`detailContent` prop) cleanly decouples the sheet chrome from per-feature content — good extension point design.

## Open Items

None requiring human decision. All issues were fixable and fixed.
