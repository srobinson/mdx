---
title: ALP-1127 Iter 3 Review - Memory Explorer Components
type: sessions
tags: [review, am-chat, frontend, react, ALP-1127]
summary: Fixed 5 issues across memory explorer sidebar components (dedup, timer leak, cache key, type safety)
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Summary

Reviewed 5 commits implementing the Memory Explorer sidebar for the AM standalone chat interface: stats header (ALP-1141), feedback buttons (ALP-1145), episode list (ALP-1142), episode detail (ALP-1143), and memory search with two-phase retrieval (ALP-1144). 11 files changed, ~1,567 lines added.

Overall quality is solid. Component structure is clean, TanStack Query usage is consistent, user-facing terminology follows the ALP-1127 mapping, accessibility attributes are present throughout. Five issues found and fixed.

## Issues Found and Fixed

1. **Duplicate `getCategoryColor` in 3 files** - `memory-search.tsx`, `search-result.tsx`, `neighborhood-list.tsx` all had identical copies. Extracted to `chat/src/components/memory/shared.ts`.

2. **Duplicate `IndexEntry` type in `memory-search.tsx`** - Lines 197-205 defined a local interface identical to `QueryIndexEntry` from `@/lib/types.ts`. Replaced with the shared type import.

3. **`groupByCategory` silently dropped unknown categories** - Only iterated over `["Conscious", "Subconscious", "Novel"]`, filtering out any entry with an unexpected category value. Fixed to append unknown categories after the canonical three.

4. **Timer leak in `feedback-buttons.tsx`** - `setTimeout(() => setState("confirmed"), 2000)` was not cleaned up on unmount. Added `useRef` for the timer ID and cleanup in `useEffect` teardown.

5. **Cache key collision in `episode-detail.tsx`** - queryKey used `episode.name` which is not guaranteed unique. Changed to `episode.id`.

## Patterns Observed

- The worker agent consistently duplicates small utility functions across files rather than extracting shared code. Three identical `getCategoryColor` copies across components written in consecutive commits.
- Timer cleanup patterns (setTimeout in callbacks) are missed. Standard pattern should be: ref + useEffect cleanup.
- Query keys should always use stable unique identifiers (IDs), not display names.

## Open Items

None. All fixes are mechanical and verified by tsc + next build.
