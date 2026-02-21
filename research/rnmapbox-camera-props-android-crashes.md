---
title: "@rnmapbox/maps Camera Props Android Crash Analysis"
type: research
tags: [rnmapbox, mapbox, android, camera, expo-location, crash]
summary: "defaultSettings is safe and non-conflicting; animationMode='moveTo' is valid; animationDuration=0 has a known double-fire bug; startLocationUpdatesAsync has real Android crash vectors."
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

All four Camera prop questions are answered from direct source inspection of @rnmapbox/maps v10.1.33. The `startLocationUpdatesAsync` question has confirmed crash vectors in expo/expo GitHub issues.

---

## Details

### 1. `defaultSettings` prop on Camera — Android issues?

**No known crash bug. Design is intentional, but has a subtle behavior.**

Source: `RNMBXCamera.kt`, method `setInitialCamera`:

```kotlin
private fun setInitialCamera(mapView: RNMBXMapView) {
    mDefaultStop?.let {
        val map = mapView.getMapboxMap()
        it.setDuration(0)
        it.setMode(CameraMode.NONE)  // instant, no animation
        val item = it.toCameraUpdate(mapView)
        item.run()
    }
}
```

`defaultSettings` is applied **once, synchronously, at mount time** (`addToMap`). Its animation mode and duration are **overridden to NONE/0** before execution, regardless of what was passed. There is no crash associated with this prop. No open GitHub issues.

### 2. `animationMode="moveTo"` — is it a valid value in v10.1.33?

**Yes, fully supported.**

From `Camera.tsx`:

```ts
export type CameraAnimationMode =
  | 'flyTo'
  | 'easeTo'
  | 'linearTo'
  | 'moveTo'
  | 'none';
```

The JS→native mapping (`nativeAnimationMode`):

```ts
case 'moveTo':
  return NativeCameraModes.Move;  // → 4
```

The Android `CameraMode.java` constants:

```java
public static final int MOVE = 4;
```

And in `CameraUpdateItem.kt`, `MOVE` is treated identically to `NONE` and `duration=0` — it calls `flyToV11` with `duration(0)`. This is an instant snap, not an animation. No crash risk.

### 3. `animationDuration={0}` — does it cause native issues?

**No crash, but there is a double-execution bug.**

In `CameraUpdateItem.kt`, the `run()` method has a logic flaw:

```kotlin
// Block 1: fires for duration==0, MOVE, or NONE
if (duration == 0 || mCameraMode == CameraMode.MOVE || mCameraMode == CameraMode.NONE) {
    map.flyToV11(mCameraUpdate, animationOptions.apply { duration(0) }, callback)
}

// Block 2: only fires for duration > 0
if (duration > 0) {
    animationOptions.apply { duration(duration.toLong()) }
}

// Block 3: fires based on mode, regardless of Block 1
if (mCameraMode == CameraMode.FLIGHT) {
    map.flyToV11(...)
} else if (mCameraMode == CameraMode.LINEAR) {
    map.easeToV11(...)
} else if (mCameraMode == CameraMode.EASE) {
    map.easeToV11(...)
}
```

When `duration=0` with `animationMode="easeTo"` (the default), Block 1 fires `flyToV11(duration=0)` AND Block 3 fires `easeToV11`. **Two camera transitions execute.** With `animationMode="moveTo"` or `animationMode="none"`, Block 3 is skipped (no matching branch), so only Block 1 fires. This is actually the safest combination for instant positioning.

**Conclusion**: `animationDuration={0}` with `animationMode="moveTo"` is the correct pattern for an instant no-animation snap. No crash, and the double-fire problem is avoided because `MOVE` has no matching branch in Block 3.

### 4. Can `defaultSettings` conflict with `centerCoordinate` when both are set?

**No crash conflict. They execute sequentially by design.**

In `addToMap`:

```kotlin
mapView.callIfAttachedToWindow {
    withMapView { mapView ->
        setInitialCamera(mapView)      // defaultSettings applied first, duration=0, mode=NONE
        updateMaxBounds(mapView)
        mCameraStop?.let { updateCamera(it, mapView) }  // then centerCoordinate stop
    }
}
```

`defaultSettings` runs first as an instant position seed. Then `mCameraStop` (built from `centerCoordinate` + `animationMode` + `animationDuration` props) is enqueued and executed immediately after. `CameraUpdateQueue.execute` is synchronous — it drains the queue recursively without waiting for animations. So the `centerCoordinate` stop will always overwrite whatever `defaultSettings` placed. No conflict, no crash.

The only edge case: if `centerCoordinate` is `undefined` (all the position props are undefined), `nativeStop` returns `null` and nothing is sent as `mCameraStop`. In that case `defaultSettings` is the sole initial position. This is exactly the documented intent.

---

### 5. `Location.startLocationUpdatesAsync` on Android — crash risks on quick start

**Yes, confirmed crash vectors. Not related to the 500ms timing window specifically, but to native lifecycle state.**

#### Crash #1: `NullPointerException` in `LocationTaskService.prepareChannel` (Android 9–11)

Source: expo/expo issue [#24834](https://github.com/expo/expo/issues/24834)

```
expo.modules.location.services.LocationTaskService.prepareChannel
expo.modules.location.services.LocationTaskService.buildServiceNotification
expo.modules.location.services.LocationTaskService.startForeground
expo.modules.location.taskConsumers.LocationTaskConsumer$3.onServiceConnected
```

The NPE originates in `NotificationManager.createNotificationChannel` when the notification system is not yet ready. This is an Android 9–11 system bug that surfaces when the foreground service starts before the system notification channel infrastructure is fully initialized. Reported as causing ~10% of production crashes for affected apps.

#### Crash #2: `RuntimeException: Unable to start receiver TaskBroadcastReceiver` (NullPointerException on List.sort)

Source: expo/expo issues [#39467](https://github.com/expo/expo/issues/39467) and [#41663](https://github.com/expo/expo/issues/41663)

```
java.lang.RuntimeException: Unable to start receiver expo.modules.taskManager.TaskBroadcastReceiver
Caused by: java.lang.NullPointerException: Attempt to invoke interface method
  'void java.util.List.sort(java.util.Comparator)' on a null object reference
```

This crash happens when the app is killed and restarted by the Android job scheduler to deliver location updates. The TaskService attempts to reconstruct task state before JS is loaded, and an internal list in TaskService is null. Occurs after the app has been in background for extended periods (~1 hour+). Not timing-related on initial mount.

#### Crash #3: `IllegalStateException` — foreground service started from background

Source: expo/expo issue [#32545](https://github.com/expo/expo/issues/32545)

```
Couldn't start the foreground service. Foreground service cannot be started
when the application is in the background.
```

This is a hard Android 12+ restriction (not a bug). Calling `startLocationUpdatesAsync` while the app transitions to background — including immediately on mount if the component renders while the Activity is not in the foreground — throws this. An Expo maintainer confirmed this is a known limitation and that background task handling is actively being improved.

**On the 500ms question specifically**: There is no documented crash specifically from calling `startLocationUpdatesAsync` within 500ms of screen mount when the Activity IS in the foreground. The crashes above are from:
- Android system service not ready (older OS versions, notification channel)
- App being in background state (Android 12+ foreground service restriction)
- Background job restoration after the app has been dormant

The safest call pattern is: call `startLocationUpdatesAsync` only after confirming `AppState.currentState === 'active'` and after verifying permissions. Do not call it during the initial render cycle — defer to a `useEffect` with a check.

---

## Sources

- `rnmapbox/maps` `src/components/Camera.tsx` — [GitHub](https://github.com/rnmapbox/maps/blob/main/src/components/Camera.tsx)
- `rnmapbox/maps` `android/.../RNMBXCamera.kt` — direct API fetch
- `rnmapbox/maps` `android/.../CameraStop.kt` — direct API fetch
- `rnmapbox/maps` `android/.../CameraUpdateItem.kt` — direct API fetch
- `rnmapbox/maps` `android/.../CameraMode.java` — direct API fetch
- expo/expo issue [#24834](https://github.com/expo/expo/issues/24834) — LocationTaskService NPE Android 9–11
- expo/expo issue [#39467](https://github.com/expo/expo/issues/39467) — TaskBroadcastReceiver NPE
- expo/expo issue [#41663](https://github.com/expo/expo/issues/41663) — TaskService.executeTask NPE (Expo 53)
- expo/expo issue [#32545](https://github.com/expo/expo/issues/32545) — foreground service from background

---

## Open Questions

- The double-fire bug in `CameraUpdateItem.run()` for `duration=0` + `easeTo` mode has no open issue. It may be worth filing.
- Whether the `LocationTaskService.prepareChannel` NPE is fixed in current expo-location versions (issue was filed against SDK 49, may be resolved by now).
- The `withMapView { }` wrapper in `addToMap` — need to confirm whether it guarantees execution on the main thread before the Activity is fully resumed, which could interact with the foreground service restriction.
