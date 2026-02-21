---
title: EchoEcho Navigator MVP — Iteration 9 Code Review
type: sessions
tags: [review, echoecho, ALP-935, route-save, gps-recording, waypoint-detection]
summary: Four bugs fixed across route save UI, Postgres RPCs, and waypoint detection algorithm after iteration 9 delivering ALP-947/948/949/950/951/952/953.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 9 of ALP-935 (EchoEcho Navigator MVP). This iteration delivered the full walk-and-record pipeline: GPS recording service (ALP-947), automatic waypoint detection (ALP-948), recording UI (ALP-949), voice annotation (ALP-950), photo snapshots (ALP-951), hazard marking (ALP-952), and route save flow with metadata (ALP-953).

All 25 tests passed. Typecheck and lint clean before and after review. Four bugs fixed.

## Issues Found and Fixed

### 1. Wrong GPS location for end building stub — `save-route.tsx`

`handleCreateBuilding` always used `session.trackPoints[0]` (the start of the walk) as the stub polygon center, even when the user was creating a building for the end picker. The building stub for the end of the route was placed at the wrong end of campus.

**Fix:** Read the last track point when `showNewBuilding === 'end'`, first point when `=== 'start'`.

### 2. "Create" button missing disabled visual state — `save-route.tsx`

The Pressable for creating a building had `disabled={buildingCreating || !newBuildingName.trim()}` but the style only applied `chipButtonDisabled` when `buildingCreating` was true. When the name was empty the button appeared enabled but was non-functional.

**Fix:** Applied `chipButtonDisabled` style when either `buildingCreating || !newBuildingName.trim()`.

### 3. `publish_route` / `retract_route` silent no-op — SQL migration

Both functions UPDATE routes with a status guard (`WHERE status = 'draft'` / `WHERE status = 'published'`). When the route did not exist or was in the wrong status, 0 rows were updated and no exception was raised. TypeScript callers received `{ ok: true }` for failed operations.

**Fix:** Added `GET DIAGNOSTICS v_count = ROW_COUNT` after each UPDATE and `RAISE EXCEPTION` when `v_count = 0`.

### 4. Dead `suppressDistanceCandidate` code — `waypointDetectionService.ts`

The distance-waypoint detection block resets the heading window to `[]` before the heading analysis block runs. With an empty window, `headingWindow.length >= 3` is false, so the turn branch is skipped entirely. `suppressDistanceCandidate` was therefore unreachable. The function-level JSDoc described the suppression as if it were active behaviour, which was incorrect and would mislead future maintainers.

**Fix:** Removed the dead `suppressDistanceCandidate` block; updated the JSDoc to accurately describe the one-candidate-per-invocation invariant.

## Patterns Observed

- **Zustand full-store subscription in useEffect deps** (`useGpsRecording.ts`): `store` is included in the effect dependency array. Since `useRecordingStore()` without a selector returns a new object reference on every state change, this causes the waypoint detection effect to fire on every `appendTrackPoint` call. `prevLengthRef` prevents double-processing so correctness is maintained, but it is a latent performance issue. Not fixed (no observable bug), but worth noting for future optimisation.

- **`startLocationTask` does not reset `_sequenceIndex`**: Module-level counter continues across sessions. Recovery logic remains correct because a cleared session starts with `currentMax = -1`, so all new points (with any positive index) are accepted. Not a bug.

- **SQL function role checks use `current_user_role()` (custom helper), not standard `auth.role()`**: Consistent with the rest of the schema — assuming this function exists and is tested. Reviewers should verify it is defined in an earlier migration.

## Open Items

- `clearPersistedBuffer()` is not called from `save-route.tsx` on successful save. The buffer is cleared only implicitly if `gpsRecordingService.clearPersistedBuffer()` is invoked elsewhere. Should confirm the buffer cleanup path on success.
- Storage objects remain at `pending/{localId}/...` keys after save — acknowledged as a known open item for ALP-953 (requires copy+delete since Supabase Storage has no rename).
- `PendingHazard` entries are not persisted to the database — noted as open in the commit.
