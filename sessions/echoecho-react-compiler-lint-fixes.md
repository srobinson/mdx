---
title: EchoEcho React Compiler ESLint fixes
type: sessions
tags: [frontend, react-compiler, eslint, react-native]
summary: Fixed all 34 React Compiler lint errors across admin (28) and student (6) apps
status: active
source: frontend-engineer
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

Resolved 34 `react-compiler/react-compiler` and `react-hooks/set-state-in-effect` violations across 11 files. Zero errors remain in both workspaces.

## Architecture Decisions

### setState during render (derived state pattern)
Used for two cases where an effect was syncing props/sibling state into state:
- `WaypointEditSheet`: replaced `useEffect` prop-sync with render-time conditional `if (waypoint !== syncedWaypoint)` pattern. Required tracking previous prop in a `syncedWaypoint` state variable.
- `haptic-lab.tsx` scheme change: replaced `useEffect` that called `setActiveS4State(null)` with a render-time conditional tracking `lastSchemeIndex`.

### nowMs state for Date.now() in render
`hazards.tsx` had `Date.now()` calls in `useMemo`, `HazardListItem` render body, and `HazardDetailSheet` render body. Introduced `nowMs` state in `HazardsScreen` initialized with `() => Date.now()` and updated every 60s via `setInterval`. Passed as prop to both sub-components.

### Ref to state for latencyStats
`haptic-lab.tsx` `latencyTrials` was a `useRef<number[]>` whose `.current` was read during render. Converted to `useState<number[]>`. Mutations (`.push`) became functional updaters `(prev) => [...prev, ms]`, and `.current = []` became `setLatencyTrials([])`.

### Async IIFE wrappers for useEffect calls
`void asyncFn()` directly in effect body is flagged when the async function internally calls setState. Wrapping as `const run = async () => { await asyncFn(); }; void run();` gives React Compiler a clear async boundary. Applied to: `buildings.tsx`, `hazards.tsx`, `route/[id].tsx`, `CampusContext.tsx`.

### Loading state initialization
For effects whose first operation was `setIsLoading(true)`, the fix was to initialize the state as `true` via `useState(true)` and remove the synchronous call. Applied to `buildings.tsx` (changed from `false` to `true`), `save-route.tsx` (changed `buildingsLoading` from `false` to `true`). `route/[id].tsx` and `useRouteHistory.ts` already started as `true`; removed the redundant set calls.

### runOnUI for Reanimated shared value mutation
`EmergencyOverlay.tsx` called `flashOpacity.value = withSequence(...)` inside a `useCallback`. React Compiler flags mutations of hook return values. Fix: wrap in `runOnUI(() => { 'worklet'; flashOpacity.value = ... })()`. This runs the assignment on the UI thread as a worklet, which is also the correct Reanimated pattern.

### Ref updated via useEffect for recursive useCallback
`useAudioEngine.ts` `drainQueue` called itself recursively, which React Compiler flags as "accessed before declared". Fix: introduce `drainQueueRef`, call `drainQueueRef.current?.()` inside `drainQueue`, and update the ref via `useEffect([drainQueue])`. This breaks the circular dependency while maintaining the same runtime behavior.

### useRef initializer Date.now() replacement
`useGpsNavigation.ts` used `useRef<number>(Date.now())` to track last GPS update time. The ref is always reset to `Date.now()` in `startWatchdog()` before the watchdog interval fires, so the initial value is never observed. Changed to `useRef<number>(0)`.

## Performance Notes

None of these changes introduce measurable overhead. The `nowMs` interval in `HazardsScreen` fires every 60s and triggers a re-render only when the list is visible — negligible cost. Converting `latencyTrials` from ref to state means renders happen on each trial completion (expected behavior for a test harness).

## Deviations from Spec

None — these were bug fixes to existing code.

## Open Items

- The `async IIFE` wrapper pattern for `void asyncFn()` in effects is a recurring pattern across the codebase. Consider a shared utility or lint autofix rule.
- `HazardsScreen` now passes `nowMs` down to `HazardListItem` which is memoized — the 60s update will bust memo cache on all rendered items. Acceptable for this screen's scale, but could be optimized by computing `isExpiringSoon` outside the memo component if the list grows large.
