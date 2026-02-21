---
title: EchoEcho Navigator MVP — Iteration 5 Review
type: sessions
tags: [review, echoecho, ALP-935, ALP-945, ALP-942, auth, supabase, edge-function]
summary: Reviewed iter5 auth bootstrap flash fix and purge edge function refactor; fixed 3 bugs — splash hang on getSession failure, unhandled AppState rejection, and purge N+1 queries
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed two commit-pairs from iteration 5 of EchoEcho Navigator MVP (ALP-935):
- `e89f284` — Auth bootstrap flash fix (ALP-945) and purge function folder-listing fix (ALP-942)
- `3b28718` — Haptic UX research artifacts (docs only, no code to review)

The auth and purge fixes were correct in their core intent but had three production-grade issues that were fixed.

## Issues Found and Fixed

### 1. `useAuth.ts` — Bootstrap `getSession()` missing `.catch()`

**File:** `apps/admin/src/hooks/useAuth.ts`

**Problem:** The bootstrap `getSession()` call had no error handler. If AsyncStorage is unavailable, the Supabase client throws, the promise rejects, `setSession` is never called, and `initialized` stays `false` forever. The app hangs on the splash screen.

**Fix:** Added `.catch(() => setSession(null))` so `initialized` is always set to `true` regardless of whether the bootstrap succeeds or fails.

### 2. `useAuth.ts` — Foreground AppState handler unhandled rejection

**File:** `apps/admin/src/hooks/useAuth.ts`

**Problem:** The `AppState.addEventListener('change', async ...)` handler called `await supabase.auth.getSession()` with no try/catch. On network failure when resuming from background, the rejection is unhandled and silent on most React Native versions.

**Fix:** Wrapped the foreground handler body in `try/catch`. On network failure, auth state is left as-is (correct — we have no new information).

### 3. `purge-orphaned-storage` — N+1 DB queries and missing UUID validation

**File:** `supabase/functions/purge-orphaned-storage/index.ts`

**Problem 1:** The original fix (correct two-level folder listing) still queried the DB once per object using `.count('exact')`. With FOLDER_LIMIT=200 and OBJECT_LIMIT=500 this is up to 100,000 round trips per invocation on a large dataset.

**Problem 2:** `obj.name.replace(/\.[^.]+$/, '')` is used as a waypoint UUID without validation. Files named `.placeholder` or with non-UUID names would have count=0 and get deleted.

**Fix:** Added `UUID_RE` constant; filter candidates to UUID-named files only; batch the DB existence check to one `.in('id', waypointIds)` query per folder instead of one per file.

## Patterns Observed

- The EchoEcho codebase consistently handles the "happy path" but misses error paths on async init sequences. Both bugs in `useAuth.ts` follow the same pattern: async call with no error handler in a lifecycle context where an unhandled rejection is invisible.
- Supabase storage `list('')` returning virtual folder entries (not files) is a non-obvious API behavior. The iter5 worker correctly identified and fixed this, but didn't notice the N+1 that followed.

## Open Items

None. All issues were resolved with concrete fixes.
