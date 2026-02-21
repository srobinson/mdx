---
title: ALP-1011 Iteration 6 Review - Security Fixes & Performance
type: sessions
tags: [review, security, rls, hmac, performance, sql]
summary: Reviewed 5 commits covering RLS security fixes, HMAC webhook auth, CTE view rewrite, and seed determinism. All clean.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 6 of ALP-1011 (multi-perspective code review sweep). Five commits covering security hardening, query performance, and test infrastructure reliability. All changes are correct and well structured.

## Commits Reviewed

1. **ALP-1085** (seed determinism): Replaced non-deterministic `SELECT id FROM auth.users LIMIT 1` with fixed UUID `00000000-0000-0000-0000-000000000099`. Added prerequisite check via `DO $$ ... RAISE EXCEPTION` that aborts if the test user is missing. Eliminates silent NULL failures.

2. **ALP-1076** (v_routes CTE rewrite): Replaced correlated subqueries with pre-aggregated CTEs for waypoints and hazards. Verified output shape matches migration 017 definition exactly (diff confirmed). Down migration also verified identical to 017. The NULL guard on `h.geom` for hazard coordinates is correctly preserved. Waypoints do not need a guard because `waypoints.geom` is `NOT NULL` in the schema.

3. **ALP-1017** (HMAC webhook): Replaced static Bearer token comparison with HMAC-SHA256 signature verification via `crypto.subtle.verify` (constant-time). Body read as raw text before verification, then parsed. All error paths fail closed. The `hexToBytes` helper does not validate hex format, but malformed input produces wrong bytes that `verify` will reject, so no security gap exists.

4. **ALP-1020** (profiles_insert RLS): Removed `OR id = auth.uid()` self-insert clause that allowed arbitrary role escalation. Only admin can now INSERT profiles via RLS. The `handle_new_user()` SECURITY DEFINER trigger and invite-user edge function (service role key) are unaffected.

5. **ALP-1021** (waypoints_insert RLS): Added `r.recorded_by = auth.uid()` ownership check for volunteers. Admin and om_specialist retain unrestricted insert. Policy correctly uses `EXISTS` subquery referencing the NEW row's `route_id`.

## Issues Found and Fixed

None. All changes are correct.

## Quality Checks

- `just check`: Pre-existing failures in `@echoecho/ui` (HazardPickerSheet.tsx missing type declarations). Unrelated to this iteration.
- `just lint`: Pre-existing eslint plugin resolution failure. Unrelated.
- `just test`: Pre-existing react-native-reanimated resolution error. Unrelated.

## Verdict

Clean.
