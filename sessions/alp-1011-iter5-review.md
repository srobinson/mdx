---
title: ALP-1011 Iteration 5 Review - SQL Migration Fixes
type: sessions
tags: [review, sql, postgis, rls, echoecho]
summary: Fixed 3 issues in iteration 5 SQL migrations - NULL geom semantics in views, missing campus check on building_entrances policy, no-op down migration
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed 5 SQL migrations (014-018) and their down scripts from iteration 5 of ALP-1011. Found and fixed 3 issues across 3 files. The remaining migrations (activity_log deny INSERT, routes FK ON DELETE SET NULL, match_route clamp) were clean.

## Issues Found and Fixed

### 1. NULL geom produces truthy empty objects instead of SQL NULL (migration 017)

**File:** `supabase/migrations/20260309080017_jsonb_coords_to_postgis.sql`

When `geom` is NULL, `jsonb_build_object('latitude', ST_Y(NULL), 'longitude', ST_X(NULL))` returns `{"latitude": null, "longitude": null}` rather than SQL NULL. This is a semantic change from the original views which returned `h.coordinate` (the raw JSONB column, which would be NULL).

Impact: (a) In v_buildings, the COALESCE for mainEntrance never falls through to the centroid when an entrance exists but has NULL geom. (b) Client code checking `if (hazard.coordinate)` sees a truthy object with null values.

**Fix:** Wrapped all `ST_X/ST_Y` calls in `CASE WHEN geom IS NOT NULL THEN ... ELSE NULL END` across v_buildings (2 locations), v_hazards (1), and v_routes hazards subquery (1).

### 2. building_entrances policy missing active-campus check (migration 014)

**File:** `supabase/migrations/20260309080014_scope_anon_read_policies.sql`

Every other table's anon read policy validates the referenced campus has `deleted_at IS NULL`. The building_entrances policy only checked that the parent building was not soft-deleted, missing the campus check entirely. Direct queries against building_entrances could return data from soft-deleted campuses.

**Fix:** Added `JOIN campuses c ON c.id = b.campus_id` with `c.deleted_at IS NULL` to the EXISTS subquery.

### 3. match_route down migration was a no-op (migration 018 down)

**File:** `supabase/migrations/down/20260309_018_match_route_clamp_limit_down.sql`

The down migration contained only comments explaining why it was intentionally left empty. This means rolling back migration 018 would leave the clamped function in place. A down migration that does nothing is not reversible.

**Fix:** Replaced the comment block with the full `CREATE OR REPLACE FUNCTION match_route(...)` body, identical to the UP migration but without the clamp lines.

## Patterns Observed

- The `jsonb_build_object` NULL propagation pattern is a recurring risk whenever views switch from reading a raw JSONB column to constructing JSONB from geometry functions. Any future migration that replaces `column_name` with `jsonb_build_object(... ST_X/ST_Y ...)` needs the same CASE guard.
- Down migrations that punt to "re-run the original migration" are not actually reversible. Every down migration should be self-contained.

## Open Items

None. All issues resolved.
