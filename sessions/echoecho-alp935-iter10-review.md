---
title: EchoEcho ALP-935 Iteration 10 Code Review
type: sessions
tags: [review, echoecho, alp-935, sql, react-native]
summary: Reviewed route save flow (ALP-953), SQL RPCs, waypoint dead code removal. Fixed empty-waypoints silent DB corruption.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed commits from iteration 10, covering:

- `save_route` / `publish_route` / `retract_route` SQL RPCs
- `routeSaveService.ts` media upload and save sequencing
- `save-route.tsx` metadata form and building stub creation
- `waypointDetectionService.ts` dead code removal

The prior review commit (1e52c68) fixed: end-building GPS location, disabled button style, silent publish/retract RPC failures, and the unreachable `suppressDistanceCandidate` block. All were correct fixes.

## Issues Found and Fixed

### Empty waypoints → silent DB corruption (commit a29c179)

**File:** `supabase/migrations/20260309_004_route_save_rpcs.sql`

If `p_waypoints` is an empty JSONB array, `jsonb_array_elements` produces 0 rows. The waypoint INSERT is a no-op. `ST_MakeLine` on 0 rows returns NULL. The route is committed as `draft` with `path = NULL` and `total_distance_m = NULL` — structurally corrupt. Added `IF jsonb_array_length(p_waypoints) = 0 THEN RAISE EXCEPTION 'no_waypoints'; END IF;` before the route INSERT, so no corrupt state is ever written.

**File:** `apps/admin/app/save-route.tsx`

`validate()` had no guard on `session.trackPoints.length`. A session with no GPS data would pass validation, proceed through the media upload stages, then fail at the DB with `no_waypoints`. Added `trackPoints.length === 0` check in `validate()` so the error surfaces in the UI before any upload work begins.

## Patterns Observed

- SQL SECURITY DEFINER functions in this project use `current_user_role()` helper for authorization — consistent pattern across all 4 RPCs in this migration.
- TypeScript service discriminated unions (`{ ok: true; ... } | { ok: false; error: string }`) are used consistently. No throws escape the service boundary.
- The `buildWaypointList` function in `routeSaveService.ts` is not exported and cannot be unit-tested directly. Its behavior is covered implicitly by the integration-style saveRoute tests.

## Open Items

- `ST_MakeLine` is computed twice in `save_route` step (c) — once for `path`, once for `total_distance_m`. A CTE would eliminate the duplicate aggregation. Not a correctness issue; acceptable for MVP.
- Storage objects are not renamed from `pending/{localId}/...` to `{routeId}/{waypointId}/...` after save. Noted in the original commit as a known open item requiring copy+delete.
- PendingHazards not persisted (no hazards table yet).
