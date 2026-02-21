---
title: RecordScreen Crash Patterns — EchoEcho Admin App (ALP-1146)
type: research
tags: [react-native, mapbox, expo, crash, navigation, record-screen]
summary: Five crash/silent-failure patterns identified in the Map → Record screen navigation path, with specific code locations and diagnostics.
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

The crash path is: Map tab → tap "Record" FAB → `router.push('/record')` → `RecordScreen` mounts as `fullScreenModal`. Five distinct risk patterns were found across `record.tsx`, `useGpsRecording.ts`, and `gpsRecordingService.ts`.

---

## 1. Two Simultaneous MapboxGL.MapView Instances

**File**: `apps/admin/app/(tabs)/index.tsx` + `apps/admin/app/record.tsx`

The record screen is presented as `presentation: 'fullScreenModal'`. On iOS, `fullScreenModal` keeps the presenting view (Map tab) alive and rendering behind the modal. Both screens own a `MapboxGL.MapView` referencing the same `MAPBOX_STYLE_SATELLITE` style URL.

`@rnmapbox/maps` has documented instability when two `MapView` instances coexist — the Mapbox GL native renderer can race on style initialization and the shared tile cache. This is the most likely cause of a hard crash (signal abort from the native layer) rather than a JS error.

**Reference**: rnmapbox/maps GitHub issues #2107, #2483.

---

## 2. Camera With `centerCoordinate={undefined}` + Conflicting Props

**File**: `apps/admin/app/record.tsx`, lines 295–306

```tsx
const initialCenter = useMemo<[number, number] | null>(
  () => savedCenter ?? (activeCampus
    ? [activeCampus.center.longitude, activeCampus.center.latitude]
    : null),
  [activeCampus?.id],
);

<MapboxGL.Camera
  defaultSettings={{
    centerCoordinate: initialCenter ?? undefined,
    zoomLevel: initialZoom,
  }}
  followUserLocation={isRecording}
  followZoomLevel={initialZoom}
  centerCoordinate={initialCenter ?? undefined}  // ← duplicate of defaultSettings
  zoomLevel={initialZoom}
  animationMode="moveTo"
  animationDuration={0}
/>
```

Two issues:

**A. `null` → `undefined` coordinate**: When `savedCenter` is null AND `activeCampus` is null (no campus selected), `initialCenter` is null → `centerCoordinate={undefined}`. On some `@rnmapbox/maps` versions, an undefined `centerCoordinate` combined with `animationMode="moveTo"` causes the native camera to jump to a default origin (0,0 in the ocean, or Mapbox default). This is the "Dubai flash" symptom.

**B. `defaultSettings` + explicit props conflict**: Both `defaultSettings` and the explicit `centerCoordinate`/`zoomLevel` props are set simultaneously. In `@rnmapbox/maps`, `defaultSettings` is only honored when the explicit props are unset. Having both causes the Camera to attempt to honor conflicting constraints and can produce spurious animations or native assertion failures.

---

## 3. Unhandled Promise Rejection on Permission Request

**File**: `apps/admin/app/record.tsx`, lines 163–167

```tsx
useEffect(() => {
  if (permissionStatus === 'unknown') {
    requestPermissions();  // ← no void, no .catch()
  }
}, [permissionStatus, requestPermissions]);
```

`requestPermissions()` is async and ultimately calls `Location.requestBackgroundPermissionsAsync()`. On Android 10+ this can throw if the system denies the request in a way that produces an exception rather than a status code. The unhandled rejection propagates through React Native's global handler and becomes a red-screen crash in dev or an uncaught exception in production.

---

## 4. Background GPS Task — Silent Error Handling

**File**: `apps/admin/src/services/gpsRecordingService.ts`, line 156

```tsx
TaskManager.defineTask(GPS_TASK_ID, async ({ data, error }) => {
  if (error) {
    return;  // ← completely silent — no emit, no log, no UI feedback
  }
  // ...
});
```

Any background location task error (permission revoked mid-session, hardware failure, OS termination of the task) is completely swallowed. No `accuracy_degraded` event, no store state change, no user notification. The recording UI continues showing elapsed time while GPS has silently stopped.

---

## 5. `handleStop` Alert Callbacks Without Error Handling

**File**: `apps/admin/app/record.tsx`, lines 233–249

```tsx
onPress: async () => {
  await gpsStop();         // ← throws if task already stopped
  store.clearSession();
  router.back();           // ← never called if gpsStop throws
},
```

If `gpsStop()` throws (e.g., the OS already stopped the task), the callback rejects silently. `store.clearSession()` and `router.back()` are never called. The user is stuck on the record screen with no way to exit.

`gpsStop()` internally has a `try/catch` that eats the `stopLocationUpdatesAsync` error, so this is unlikely to surface — but the pattern is still a gap if the internal guard is ever changed.

---

## Error Handling Gaps Summary

| Location | Pattern | Risk |
|----------|---------|------|
| `record.tsx:163` | `requestPermissions()` with no catch | Unhandled rejection → crash |
| `gpsRecordingService.ts:156` | `if (error) return` in task | Silent GPS failure, no UI feedback |
| `record.tsx:236,243` | `await gpsStop()` no try/catch in Alert | User stuck on screen |
| `record.tsx` | No `ErrorBoundary` wrapping `RecordScreen` | Any render error crashes entire app |
| `gpsRecordingService.ts:121` | `flushBuffer` silently eats FileSystem errors | Data loss on kill (by design, noted) |

---

## Suggested Diagnostics

1. **Two-map-instance test**: Add `console.log('MapView mounted')` / `console.log('MapView unmounted')` lifecycle logs to both `index.tsx` and `record.tsx`. Confirm the map tab's view stays alive during modal. If so, this is the primary crash vector.

2. **Null campus test**: Open the record screen with no campus selected (`activeCampus = null`, `savedCenter = null`). Observe whether the camera throws or jumps.

3. **Permission rejection test** (Android): Revoke location permission while on the map screen, then navigate to record. Watch for an unhandled rejection crash.

4. **Add error boundary**: Wrap `RecordScreen` return in a component-level `ErrorBoundary` with crash logging to capture the JS stack trace on crash.

5. **Background task logging**: Add `console.error('[GPS Task]', error)` in the task error branch to surface background-context errors.

---

## Sources

- `apps/admin/app/record.tsx` (full file)
- `apps/admin/app/(tabs)/index.tsx` (full file)
- `apps/admin/app/_layout.tsx` (Stack config, `presentation: 'fullScreenModal'`)
- `apps/admin/src/hooks/useGpsRecording.ts` (full file)
- `apps/admin/src/services/gpsRecordingService.ts` (full file)
- `apps/admin/src/lib/locationPermissions.ts` (full file)

---

## Open Questions

- Which `@rnmapbox/maps` version is installed? Concurrent-view stability improved significantly after v10.1.
- Is the crash reproducible on iOS only, Android only, or both? Helps isolate native vs. JS cause.
- Does the crash produce a native stack trace in device logs / Metro? If so, is it in `mapbox-maps-ios`/`mapbox-android-sdk` or in JS?
