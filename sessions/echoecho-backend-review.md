---
title: EchoEcho Navigator Backend Security and Quality Review
type: sessions
tags: [backend, security, rls, supabase, postgres, react-native, audit]
summary: Comprehensive backend review of EchoEcho Navigator — 20 Linear issues filed covering security holes, data integrity bugs, auth race conditions, and performance problems
status: active
source: backend-engineer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Full backend review of the EchoEcho Navigator codebase (ALP-935 worktree at `/Users/alphab/Dev/LLM/DEV/helioy/client-projects/echoecho-worktrees/nancy-ALP-935`). All backend surface reviewed: 10 Postgres migrations, 5 Edge Functions, 2 Supabase client configs, and all app-side Supabase usage.

20 Linear issues filed as children of ALP-1011, covering the full priority spectrum.

## Issues Filed

### Priority 1 — Security Holes

| Issue | Summary |
|-------|---------|
| ALP-1015 | CORS wildcard on all 3 admin Edge Functions |
| ALP-1017 | Auth webhook uses static Bearer secret, not HMAC-SHA256 |
| ALP-1020 | profiles_insert RLS allows any auth user to self-insert with admin role |
| ALP-1021 | Volunteer can insert waypoints onto any other user's route |

### Priority 2 — Data Integrity / Auth Bugs

| Issue | Summary |
|-------|---------|
| ALP-1024 | content_hash NULL when waypoints deleted — sync engine re-fetches forever |
| ALP-1026 | save_route does not validate campus existence or building-campus membership |
| ALP-1028 | deactivate-user TOCTOU race — auth ban and profile update not atomic |
| ALP-1029 | ensureAnonymousSession() returns void, silently swallows failure |
| ALP-1032 | waypoints_content_hash trigger is FOR EACH ROW — O(N²) on route save |
| ALP-1035 | signIn bypasses setSession — initialized flag race condition |
| ALP-1039 | Migration 010 re-adds columns from 004 with wrong types (integer vs float) |
| ALP-1041 | Down migrations missing for 007, 008, 009, 010 |
| ALP-1045 | Anonymous read policies (008) remove campus scoping — any anon reads any campus |
| ALP-1048 | routeSaveService calls getPublicUrl on private buckets — all audio URLs 403 |
| ALP-1051 | syncEngine includes retracted routes in fetch — retracted route detection broken |

### Priority 3 — Quality / Performance

| Issue | Summary |
|-------|---------|
| ALP-1053 | routes.start/end_building_id FKs have no ON DELETE action |
| ALP-1055 | hazards, pois, building_entrances store coordinates as JSONB not PostGIS geometry |
| ALP-1056 | Missing composite index on routes(campus_id, status) |
| ALP-1058 | purge-orphaned-storage has no authentication check |
| ALP-1060 | purge-orphaned-storage has no pagination — orphans beyond FOLDER_LIMIT never purged |
| ALP-1062 | useAdminMapData uses `as 'tableName'` type casts — filter may silently do nothing |
| ALP-1064 | CampusContext uses .single() instead of .maybeSingle() — crashes on empty DB |
| ALP-1067 | profiles missing partial index on is_active — RLS helper functions slow |
| ALP-1069 | enable_anonymous_sign_ins = false in config.toml — student app broken locally |
| ALP-1074 | Audio uploads to pending/{localId} path — never cleaned up by purge function |
| ALP-1076 | v_routes view uses correlated subqueries — N+1 on admin map load |

### Priority 4 — Nitpicks

| Issue | Summary |
|-------|---------|
| ALP-1079 | activity_log has no explicit INSERT RLS policy — relies on implicit default-deny |
| ALP-1081 | preloadRoute does not filter by status=published — could cache draft/retracted routes |
| ALP-1085 | seed_staging.sql uses LIMIT 1 without ORDER BY for recorded_by — non-deterministic |
| ALP-1086 | match_route p_limit has no upper bound — unbounded result set possible |

## Critical Findings Worth Highlighting

### ALP-1048: getPublicUrl on private buckets
This is a functional blocker. The buckets are private but the code calls `getPublicUrl`. Every audio annotation stored in the DB will have a 403 URL. Student audio guidance is entirely non-functional in production. Fix: store storage keys, generate signed URLs at access time.

### ALP-1020: Role escalation via profiles INSERT
Any anonymous student can become an admin with a single `supabase.from('profiles').insert()` call. The `handle_new_user` trigger uses `ON CONFLICT DO NOTHING`, so it does not overwrite a pre-inserted row. Fix: remove the `OR id = auth.uid()` clause from the INSERT policy.

### ALP-1074 + ALP-1048 (compound): Storage path scheme mismatch
The `routeSaveService` uploads to `pending/{localId}/audio.m4a` but the purge function expects `{route_id}/{waypoint_id}.ext`. Combined with the public URL bug, the entire audio pipeline is broken in two independent ways.

## Architecture Observations

- The content hash scheme (SHA-256 over ordered waypoints) is sound for offline change detection — but the per-row trigger creating O(N²) work undermines it.
- The SECURITY DEFINER pattern for helper functions is correct but needs the search_path fix (migration 009 correctly addresses handle_new_user; current_user_role and current_user_campus should get the same treatment).
- The dual RLS policy sets (profiled users in migration 002, anonymous in migration 008) create policy conflicts that need careful ordering analysis. Postgres evaluates permissive policies with OR logic, so both sets are active simultaneously — this is intentional but the lack of campus scoping in migration 008 is a design regression.
