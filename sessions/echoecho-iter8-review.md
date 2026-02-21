---
title: EchoEcho Navigator MVP — Iteration 8 Review
type: sessions
tags: [review, echoecho, react-native, ALP-949, ALP-952]
summary: Reviewed recording UI, hazard marking, and new @echoecho/ui package. Fixed stale elapsed timer and missing CI workspace.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Reviewed iteration 8 of EchoEcho Navigator MVP, which delivered:
- Full recording UI rewrite (`apps/admin/app/record.tsx`) integrating `useGpsRecording`, live map markers for waypoints and hazards, `RecordingBottomBar`, `VoiceAnnotationSheet` wiring, and 30-second accessibility announcements (ALP-949)
- Hazard marking flow: `HazardButton`, `HazardPickerSheet` in new `@echoecho/ui` workspace, `expiresAt` field on `PendingHazard` (ALP-952)
- Route placeholder at `apps/admin/app/route/[id].tsx`

All 10 unit tests passed. Typechecks passed. Two bugs found and fixed.

## Issues Found and Fixed

### 1. Frozen elapsed timer under infrequent GPS updates

**File:** `apps/admin/app/record.tsx`
**Lines:** 81, 101-111

The `elapsedMs` `useMemo` was memoized on `[session, isPaused]`. The 1Hz tick used `const [, setTick] = useState(0)` — the tick value was discarded. When the interval fired, it triggered a re-render, but `elapsedMs`'s deps hadn't changed, so the cached value was returned. The elapsed time display was effectively driven by GPS data arrivals, not the clock.

On battery-saver mode (Balanced accuracy, triggered at <20% battery), GPS updates arrive at low frequency. In this mode, the timer would freeze between fixes — potentially for seconds at a time. Also problematic during the window after recording starts before the first GPS fix arrives.

**Fix:** Changed `const [, setTick]` to `const [tick, setTick]` and added `tick` to the memo deps array with an explanatory comment.

### 2. @echoecho/ui missing from CI typecheck target

**File:** `justfile`

The `check` target listed `@echoecho/shared`, `@echoecho/admin`, and `@echoecho/student` but not the newly introduced `@echoecho/ui` workspace. Type errors in `HazardPickerSheet.tsx` would only surface through admin's imports, leaving type-only errors in the UI package invisible to `just check`.

**Fix:** Added `yarn workspace @echoecho/ui run typecheck` to the `check` target, positioned before admin (shared → ui → admin → student respects the dependency order).

## Patterns Observed

- The `useMemo` + separate tick-state pattern for timers is a recurring trap in React. Any memoized computation involving `Date.now()` needs the tick in its deps if updates are required at a rate independent of the primary data source.
- New workspace packages (packages/ui, packages/shared) need to be manually added to the justfile check/lint/test targets — the root `workspaces` glob does not automatically extend those targets.

## Open Items

- `formatElapsed` is duplicated between `record.tsx` and `RecordingBottomBar.tsx`. Both have identical implementations. This is a minor issue (no bug), but it could be extracted to `@echoecho/shared` when convenient.
- VoiceAnnotationSheet mounts with BottomSheet `index` defaulting to 0 (open immediately). The redundant `voiceSheetRef.current?.snapToIndex(0)` call in `handleWaypoint` is a no-op since the ref is still null at that point (component hasn't mounted yet from the state update). Both behaviors are harmless but worth noting if the sheet open animation ever behaves unexpectedly.
- `expiresAt` on `PendingHazard` is optional (`?`). ALP-953 should either make it required or ensure the route save flow handles the absent case explicitly.
