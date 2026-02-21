---
title: ALP-1146 Record Screen Fix Review
type: sessions
tags: [review, react-native, mapbox, echoecho, crash]
summary: Reviewed 5 commits fixing record screen crashes; found and fixed a critical Camera prop regression in the final commit.
status: active
source: clinical-reviewer
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

Reviewed all 5 commits on branch `nancy/ALP-1146` addressing record screen crashes in the EchoEcho admin app. The crash path is: Map tab → tap Record → record screen → crash.

The commits form a coherent escalation of fixes, each building on the previous. The final commit (88fc48e) introduced a critical regression that would cause a crash the moment recording starts on any device that has visited the main map.

**One fix applied**: `apps/admin/app/record.tsx` — Camera prop regression in 88fc48e.

---

## Commit-by-Commit Analysis

### 0164383 — Switch static map overlays to GeoJSON format
**Scope**: `routes.tsx`, `route/[id].tsx` (list and detail screens)
**Not in the crash path.** Converts static map overlays from some format to GeoJSON. Unrelated to the record screen.
**Residual risk**: None for this crash path.

### 6d063fd — Fix record screen map jump and crash on open
**Root cause**: `TSBVI_CENTER` was hardcoded to Austin, TX coordinates. The Camera had both `followUserLocation` and `centerCoordinate` set simultaneously — a known rnmapbox native conflict that causes a crash.
**Fix**: Conditional Camera rendering — when recording: `followUserLocation` only. When idle: empty `<MapboxGL.Camera />`.
**Residual risk from this commit**: Empty Camera when idle meant the viewport was unpredictable (user could see ocean/wrong location). Addressed in next commit.

### c930a7e — Fix record screen world-jump and Start Recording crash
**Root cause 1**: Empty Camera left the idle viewport uncontrolled. User would see a "world jump" to an arbitrary location.
**Fix**: Added `campusCenter` from `useCampusStore` as idle camera target with `animationMode="none"`.

**Root cause 2**: No guard for `foreground_only` permission status. `startLocationUpdatesAsync` throws if the OS task has foreground-only grants.
**Fix**: Explicit `foreground_only` check before calling `gpsStart`, with an alert directing the user to Settings.

**Root cause 3**: `gpsStart()` could throw with no catch, propagating unhandled to the UI.
**Fix**: Wrapped in try/catch with user-facing alert.

**Residual risk**: `campusCenter` memo dependency is `[activeCampus?.id]` but does not include `savedCenter` (added in next commit). Intentional snapshot behavior.

### 4941f37 — Preserve map viewport when navigating to record screen
**Root cause**: Users navigating from the main map to the record screen would see the campus center instead of where they were looking — disorienting and potentially causing map jump.
**Fix**: Introduced `mapViewportStore` (Zustand). Main map (`index.tsx`) saves `center`/`zoom` on `onMapIdle`. Record screen reads `savedCenter`/`savedZoom` and falls back to campus center.
**Architecture note**: `onMapIdle` fires once after camera settles, not per frame during gestures — correct choice to avoid store thrash.
**Residual risk**: `initialCenter` memo keyed on `[activeCampus?.id]`, not `savedCenter`. If store updates post-mount, `initialCenter` won't update. This is intentional (one-time snapshot). Not a bug.

### 88fc48e — Fix record screen crash, Dubai flash, and auto-start
**Root cause (Dubai flash)**: Conditional Camera rendering caused the Camera component to unmount/remount when `isRecording` changed, triggering an animation that flashed to a distant location.
**Fix attempt**: Collapsed to a single `<MapboxGL.Camera>` instance with `defaultSettings` to prevent remount.

**CRITICAL REGRESSION INTRODUCED**: The collapsed Camera passes both `followUserLocation={isRecording}` AND `centerCoordinate={initialCenter ?? undefined}` with no gating. After commit 4941f37, `initialCenter` is guaranteed non-null any time the user has visited the main map. The moment `isRecording` becomes `true`, the Camera has both props active — the exact native conflict that 6d063fd documented as causing a crash.

**Other changes (correct)**:
- `isIosBackgroundLocationEnabled: true` added to `app.json`. Missing iOS config; background location would silently fail on iOS without this.
- `autoStartFired` ref prevents double-fire of auto-start effect.
- `startInFlight` ref at UI level + `_starting` flag in service = two-layer guard against concurrent starts.
- `clearPersistedBuffer()` before each fresh start. Recovery flow removed (design decision).
- Removed `hasPersistedBuffer` recovery prompt (simplification, not a bug).

---

## Fix Applied

**File**: `apps/admin/app/record.tsx`
**Location**: Camera JSX block (~line 295)

Replaced:
```jsx
<MapboxGL.Camera
  defaultSettings={{ centerCoordinate: initialCenter ?? undefined, zoomLevel: initialZoom }}
  followUserLocation={isRecording}
  followZoomLevel={initialZoom}
  centerCoordinate={initialCenter ?? undefined}
  zoomLevel={initialZoom}
  animationMode="moveTo"
  animationDuration={0}
/>
```

With:
```jsx
{/* Single Camera instance avoids remount flash when recording starts.
    NEVER pass centerCoordinate alongside followUserLocation — rnmapbox
    native conflict causes a crash. Gate the two prop sets on isRecording. */}
<MapboxGL.Camera
  defaultSettings={{ centerCoordinate: initialCenter ?? undefined, zoomLevel: initialZoom }}
  followUserLocation={isRecording}
  followZoomLevel={isRecording ? 18 : undefined}
  centerCoordinate={isRecording ? undefined : (initialCenter ?? undefined)}
  zoomLevel={isRecording ? undefined : initialZoom}
  animationMode={isRecording ? 'easeTo' : 'moveTo'}
  animationDuration={isRecording ? 500 : 0}
/>
```

**Why this works**: Single Camera instance preserved (no remount, no flash). When `isRecording=true`, `centerCoordinate` and `zoomLevel` are undefined — `followUserLocation` + `followZoomLevel` take over exclusively. When `isRecording=false`, `followUserLocation` is false and `centerCoordinate`/`zoomLevel` position the viewport at the inherited position. The two prop sets never coexist.

Typecheck + lint: clean.

---

## Architectural Pattern

These 5 commits expose a single recurring trap: **rnmapbox Camera prop interference**.

The library has at least two undocumented constraints:
1. `followUserLocation` and `centerCoordinate` must never be set simultaneously. The native bridge crashes.
2. Conditional rendering of the Camera component (mount/unmount on prop changes) triggers animations that cause visible flashes.

These constraints pull in opposite directions. The correct resolution is a single Camera instance with explicit prop gating on recording state — which is what the fix in this review implements.

**Recommendation for future work**: Document these constraints in a comment on the Camera component or in a codebase ARCHITECTURE.md. The same mistake was made twice across 5 commits in a single session.

---

## Residual Risks (Not Fixed — Design Decisions)

1. **Recovery flow removed**: `clearPersistedBuffer()` discards any previously interrupted recording session silently. Users who backgrounded the app during a recording and return will lose that data. This is a deliberate simplification but should be tracked as a known limitation.

2. **`mapViewportStore` is memory-only (no persistence)**: On app cold start, `center`/`zoom` are null, falling back to campus center. On warm navigation, store is populated. This is correct but means the first navigation to record screen after a cold start will always show campus center rather than any previously viewed position.

3. **`initialCenter` memo dependency**: Only updates when `activeCampus?.id` changes, not when the viewport store updates. This is intentional snapshot semantics. If `activeCampus` changes while on the record screen (unlikely), the camera won't update. Acceptable.

---

## Open Items

None requiring a design decision. One fix applied and verified.
