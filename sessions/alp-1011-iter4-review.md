---
title: ALP-1011 Iteration 4 Code Review
type: sessions
tags: [review, echoecho, ALP-1011, storage-keys, sync-engine]
summary: Reviewed 5 commits (ALP-1074, ALP-1048, ALP-1051, ALP-1062, ALP-1069). Fixed naming inconsistency in ResolvedMedia and dead test mock.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 4 of ALP-1011 (multi-perspective code review sweep). Five commits covering storage key alignment, URL-to-key migration for private buckets, retraction-by-absence sync logic, view query type cast cleanup, and anonymous sign-in config.

## Changes Reviewed

| Commit | Issue | Verdict |
|--------|-------|---------|
| c6009af | ALP-1074: Storage key format alignment | Clean |
| fd43118 | ALP-1048: Store keys instead of URLs | Fixed (naming) |
| cff1f95 | ALP-1051: Retraction by absence | Clean |
| fd188e5 | ALP-1062: Remove misleading type casts | Clean |
| ee881cb | ALP-1069: Enable anonymous sign-ins | Clean |

## Issues Found and Fixed

**1. ResolvedMedia field naming mismatch** (routeSaveService.ts)

ALP-1048 changed the semantics from storing public URLs to storage keys, and renamed local variables (`audioUrl` to `audioKey`, `photoUrl` to `photoKey`), but left the `ResolvedMedia` interface fields as `audioUrl`/`photoUrl`. This creates a maintenance trap where a future reader sees `audioUrl` and assumes it contains a URL.

Fix: Renamed `ResolvedMedia.audioUrl` to `audioKey` and `ResolvedMedia.photoUrl` to `photoKey`. Updated all 5 usage sites in the same file.

**2. Dead mockGetPublicUrl in test file** (routeSaveService.test.ts)

The `getPublicUrl` helper was removed from the service in ALP-1048, but `mockGetPublicUrl` was still declared, initialized, and wired into the storage mock in beforeEach. Dead test infrastructure obscures what the test actually exercises.

Fix: Removed `mockGetPublicUrl` declaration, initialization, and mock wiring.

## Patterns Observed

- The retraction-by-absence logic in syncEngine.ts is well designed: scoped to campusId, skips active navigation route, and correctly handles the "cached then retracted while offline" scenario.
- The signed URL approach in mediaCache.ts has proper error handling (fallback to null path on sign failure, legacy URL detection via `startsWith('http')`).
- The purge function's pending folder cleanup uses `created_at` with a sensible 24h threshold and defaults to 0 (epoch) for missing timestamps, ensuring files with no metadata get cleaned up.

## Open Items

None. All changes are internally consistent and the two issues found were fixed.
