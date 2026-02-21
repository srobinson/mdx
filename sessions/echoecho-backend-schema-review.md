---
title: EchoEcho Navigator — Backend Issue Review and Schema Specification
type: sessions
tags: [backend, supabase, postgis, rls, offline-sync, accessibility]
summary: Reviewed and updated 7 Linear issues for EchoEcho campus navigation app; added full DDL, RLS policies, PostGIS query patterns, sync strategy, and API contracts
status: active
source: backend-engineer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed ALP-942, ALP-945, ALP-946, ALP-953, ALP-955, ALP-963, ALP-971 for the EchoEcho Navigator project (accessibility-first campus nav for VI students, Supabase + PostGIS + React Native). All 7 issues were updated in Linear with full implementation specs.

Key decisions made:

- Role system uses `profiles` table queried at RLS evaluation time (not JWT custom claims) to enable immediate deactivation without waiting for token expiry.
- `waypoints.geom` is `GEOMETRY(Point, 4326)`, not lat/lng floats. `routes.path` is a materialized `GEOMETRY(LineString, 4326)`.
- `content_hash` on `routes` drives incremental offline sync — clients compare hashes before fetching waypoints.
- Storage uploads (audio, photos) must precede Postgres writes. Orphaned objects are purged by a nightly Edge Function.
- Navigation loop is purely deterministic (bearing math against local SQLite waypoints). Zero LLM calls mid-navigation.
- `expo-sqlite` selected over AsyncStorage for local route storage. `upsertRoute` is a shared function between the sync engine (ALP-963) and route pre-load (ALP-955).

## API Contract

### match_route RPC (ALP-955)

```ts
// POST /functions/v1/match_route
interface MatchRouteRequest {
  lat: number; lng: number;
  destination_text: string;
  campus_id: string;
  limit?: number;  // default 3
}
interface MatchRouteResponse {
  matches: RouteMatch[];
  nearest_building_id: string | null;
  nearest_building_name: string | null;
  unmatched_destination: boolean;
}
```

Ranking weights: destination similarity 0.5, inverse distance 0.3, difficulty 0.2.

### invite_user / deactivate_user / update_user_role (ALP-971)

All implemented as Edge Functions (service role key never on client). Deactivation sets both `auth.users.banned = true` AND `profiles.is_active = false` for immediate effect.

## Database Changes

### New tables
- `campuses` — with GiST indexes on `location` (Point) and `bounds` (Polygon)
- `buildings` — GiST on `outline`, `entrances`; GIN trigram on `name`
- `routes` — GiST on `path` (LineString); indexes on `campus_id`, `status`, `start_building_id`, `end_building_id`; `content_hash`, `soft-delete`
- `waypoints` — GiST on `geom`; float `position` with unique constraint; `recorded_at` as tiebreaker
- `profiles` — extends `auth.users`; `role`, `campus_id`, `is_active`
- `activity_log` — indexes on `actor_id`, `target_id`, `created_at DESC`

### Extensions required
- `postgis`
- `pg_trgm`

### Storage buckets
- `route-audio` (private, per-object RLS)
- `route-photos` (private, per-object RLS)

## Security Considerations

- RLS helper functions `current_user_role()` and `current_user_campus()` are `SECURITY DEFINER STABLE`.
- Every table has RLS enabled with campus_id isolation for students.
- Volunteers restricted to `status = 'pending_save'` on INSERT via RLS CHECK constraint.
- Storage bucket policies mirror route publication status.
- Activity log captures: user.invite, user.deactivate, user.role_change, auth.login (via Auth webhook), route.publish, route.retract.

## Performance Notes

- `match_route` target: p95 < 200ms (test at 500 routes, 50 buildings).
- GiST indexes on all geometry columns are mandatory before any spatial query benchmarking.
- Incremental sync via `content_hash` comparison avoids re-fetching unchanged routes.
- Navigation loop reads from local SQLite at ~1Hz; no network I/O in hot path.

## Open Items

- Student auth flow not specced. Must be designed before student RLS policies can be fully tested.
- Multi-campus user assignment: current schema is single `campus_id` per profile. If om_specialists span campuses, a `profile_campus_assignments` junction table is required — coordinate in ALP-942 before any other issue starts implementation.
- Ranking weights (0.5/0.3/0.2) in `match_route` are unvalidated assumptions. Revisit after first VI user testing session.
- Storage quota: 100 routes × 20 audio clips × 500KB ≈ 1GB per campus. Implement LRU eviction for routes not navigated in 30+ days.
- Bootstrap mechanism for first admin account: recommend Supabase dashboard direct creation; document this in ALP-971 runbook.
- Background sync on iOS is unreliable (Expo Background Fetch ~15min cap, can be killed). Foreground sync on app resume is the only reliable path for safety-critical route updates.

## Dependency Graph

```
ALP-942 (schema)
  ├── ALP-945 (auth)
  │     └── ALP-971 (user mgmt)
  ├── ALP-946 (CI)
  ├── ALP-953 (route save)
  ├── ALP-963 (offline sync)  ←── ALP-955 (route matching)
  └── ALP-955 (route matching)
```
