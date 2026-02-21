---
title: ALP-935 Iteration 27 Review — camelCase views migration
type: sessions
tags: [review, echoecho, sql, views, hazards]
summary: Fixed missing resolved_at column on hazards table and added resolved hazard filtering to views
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 27 which introduced a SQL migration creating 6 camelCase views (`v_campuses`, `v_buildings`, `v_waypoints`, `v_hazards`, `v_routes`, `v_building_entrances`) and updated all admin frontend queries to use them. The migration correctly solves the DB snake_case vs TS camelCase mismatch and eliminates `as unknown as T[]` casts in most places.

## Issues Found and Fixed

### 1. Missing `resolved_at` / `resolved_by` columns on hazards table (fixed)

**File:** `supabase/migrations/20260309080010_camelcase_views.sql`

The admin UI has a "Resolve Hazard" feature (`hazards.tsx` line 171-174) that writes `resolved_at` to the hazards table, but the column never existed in any migration. The update was silently succeeding with zero effect. Added `resolved_at timestamptz` and `resolved_by uuid` columns to the same migration.

### 2. v_hazards view missing resolved_at filter (fixed)

**File:** `supabase/migrations/20260309080010_camelcase_views.sql`

The original hazards query filtered `.is('resolved_at', null)` to exclude resolved hazards. The view had no such filter, meaning resolved hazards would appear in the list after the column was added. Added `WHERE h.resolved_at IS NULL` to the view.

### 3. v_routes embedded hazards included resolved hazards (fixed)

**File:** `supabase/migrations/20260309080010_camelcase_views.sql`

The correlated subquery embedding hazards into v_routes had no resolved_at filter. Added `AND h.resolved_at IS NULL` to the WHERE clause.

## Patterns Observed

- The `as 'table_name'` cast pattern (`from('v_campuses' as 'campuses')`) is used throughout to satisfy PostgREST's type inference while querying views. This is a reasonable workaround for Supabase's generated types not knowing about views.
- `_layout.tsx` calls `setLoading(false)` but never `setLoading(true)`. The `isLoading` state is consumed nowhere. Dead code but harmless.
- Realtime subscription in hazards.tsx (line 126) subscribes to the raw `hazards` table, not the view. This is correct since Postgres realtime operates on tables, not views.

## Open Items

None. All issues within scope were resolved.
