---
title: watchPositionAsync as Foreground GPS Recording Fallback in Expo Android
type: research
tags: [expo-location, watchPositionAsync, android, gps, route-recording, foreground, startLocationUpdatesAsync, taskmanager]
summary: watchPositionAsync is a sound foreground-only fallback for GPS route recording in Expo Android apps, but requires expo-keep-awake to prevent screen-lock interruption, carries an open subscription-cleanup bug in SDK 52, and must use distanceInterval (not timeInterval alone) as the throttle mechanism.
status: active
source: deep-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Executive Summary

`Location.watchPositionAsync` is the correct Expo API for foreground-only GPS route recording and is widely used in production React Native apps for this purpose. It requires only `ACCESS_FINE_LOCATION` (no background permission, no TaskManager, no foreground service), making it the lowest-friction path for a POC. The hard constraint is that it stops when the screen locks or the app is backgrounded -- this is by design, not a bug. For volunteer-testing where the screen stays on, this is acceptable; pair it with `expo-keep-awake` to enforce that. Two active bugs demand defensive coding: a subscription cleanup regression in SDK 52 (`.remove()` may not fully stop updates on Android), and a long-standing issue where `timeInterval` alone does not throttle updates reliably -- use `distanceInterval` instead.

---

## Detailed Findings

### 1. API Design: Foreground-Only is a Feature, Not a Limitation

The Expo documentation is unambiguous: "Updates will only occur while the application is in the foreground." This is intentional API design. `watchPositionAsync` maps directly to the underlying OS foreground location provider and does not spin up a foreground service, does not require TaskManager, and does not trigger Android's background execution restrictions.

For the specific use case -- a POC admin app used by volunteers who keep the screen active during recording -- this constraint is entirely acceptable. The primary competing API (`startLocationUpdatesAsync`) has a documented crash pattern on Android: if the call is made while the app is transitioning to the background or has already entered it, Android throws `ForegroundServiceStartNotAllowedException` (confirmed production impact: one team reported 63,000 crashes over 90 days from this exception). The `watchPositionAsync` path sidesteps this class of failure entirely.

**Source triangulation:** Expo official docs, GitHub issue #24760 (ForegroundServiceStartNotAllowedException), GitHub issue #32545 (foreground service start rejection).

### 2. Screen Lock Behavior: The Real Constraint

`watchPositionAsync` stops delivering updates when:
- The user presses the Home button (app backgrounded)
- The screen locks (display off)
- The user switches to another app

This is confirmed by the Expo docs and corroborated across multiple GitHub issues. The condition is that the application must remain "in the foreground" -- which Android defines as having an active, visible window.

**Mitigation:** `expo-keep-awake` (`useKeepAwake()` hook or `activateKeepAwakeAsync()`) prevents the screen from sleeping, satisfying the foreground requirement. For a volunteer recording session where the device is in-hand and the screen is expected to stay on, this is the appropriate solution. Note: `expo-keep-awake` itself has had issues in development builds (resolved in recent SDK versions), but is reliable in production builds.

**Source:** Expo keep-awake docs, GitHub issue #15607 (background location stops when phone sleeps), community discussion patterns across multiple threads.

### 3. Permission Requirements: Minimal Footprint

For foreground-only use, `watchPositionAsync` requires only:
- `ACCESS_FINE_LOCATION` (or `ACCESS_COARSE_LOCATION` for lower accuracy)
- Calling `Location.requestForegroundPermissionsAsync()` at runtime

It does **not** require:
- `ACCESS_BACKGROUND_LOCATION`
- `FOREGROUND_SERVICE` or `FOREGROUND_SERVICE_LOCATION`
- Any entry in `app.json`'s `expo.android.permissions` for background use

**Important historical caveat:** Expo managed workflow (SDK 39 and earlier) used to inject `ACCESS_BACKGROUND_LOCATION` into the manifest automatically, causing Google Play Store rejections even for apps using only `watchPositionAsync`. This was fixed in SDK 40+. With current SDK (51/52), explicitly blocking the permission with `"blockedPermissions": ["android.permission.ACCESS_BACKGROUND_LOCATION"]` in `app.json` is a belt-and-suspenders measure if publishing to the Play Store matters for this use case.

**Source:** GitHub issue #11918 (Play Store rejection), GitHub issue #18915 (background permission injected without request), Expo permissions guide.

### 4. Known Bug: Subscription Cleanup Regression (SDK 52, April 2025)

A high-priority open issue (GitHub #35926, filed April 7, 2025) documents that calling `.remove()` on the subscription returned by `watchPositionAsync` does **not** reliably stop location updates on Android. Updates continue emitting after removal. The issue is assigned and accepted by the Expo team; iOS received a partial fix in 18.0.7 but Android "might still be an issue."

**Practical impact for route recording:** If the component unmounts (e.g., user navigates away from the record screen) while recording is active, the subscription may keep firing and accumulating GPS data in whatever callback state is still referenced. This can cause ghost data appended to a route, or in extreme cases a memory-adjacent crash if the callback holds a stale React state setter.

**Defensive patterns:**

```typescript
// Pattern 1: useEffect cleanup with null guard
useEffect(() => {
  let subscription: LocationSubscription | null = null;
  let cancelled = false;

  (async () => {
    const sub = await Location.watchPositionAsync(options, (loc) => {
      if (!cancelled) {
        // update route state
      }
    });
    if (cancelled) {
      sub.remove(); // already navigated away before promise resolved
    } else {
      subscription = sub;
    }
  })();

  return () => {
    cancelled = true;
    subscription?.remove();
  };
}, []);

// Pattern 2: useFocusEffect for expo-router screens (starts on focus, stops on blur)
useFocusEffect(
  useCallback(() => {
    let subscription: LocationSubscription | null = null;
    let cancelled = false;

    (async () => {
      const sub = await Location.watchPositionAsync(options, (loc) => {
        if (!cancelled) { /* update */ }
      });
      if (cancelled) sub.remove();
      else subscription = sub;
    })();

    return () => {
      cancelled = true;
      subscription?.remove();
    };
  }, [])
);
```

The `cancelled` flag guards against the async gap between when `watchPositionAsync` is called and when it resolves, which is a distinct race condition from the cleanup bug itself.

**Source:** GitHub issues #35926 and #35925 (dual reports, Android and iOS), useFocusEffect React Navigation docs.

### 5. Known Bug: timeInterval Option Unreliable on Android

The `timeInterval` option in `watchPositionAsync` has been broken for years and was marked "completed" in April 2025 (GitHub issue #10196), but it is unclear which SDK version carries the fix. Historically, setting only `timeInterval` causes the callback to fire once and stop, or to be ignored entirely. Setting `distanceInterval` alone works reliably.

**Recommendation for route recording:** Use `distanceInterval` as the primary throttle mechanism. A value of 5-10 meters is typical for walking-speed route recording. Do not rely on `timeInterval` as the sole update trigger until the fix is confirmed in your target SDK.

```typescript
await Location.watchPositionAsync(
  {
    accuracy: Location.Accuracy.High,
    distanceInterval: 5,  // meters -- reliable
    // timeInterval: 3000  -- historically unreliable; omit or verify your SDK version
  },
  (location) => { /* append to route */ }
);
```

**Source:** GitHub issue #10196 (timeInterval ignored, 4+ year history, closed April 2025).

### 6. Accuracy: HIGH is the Right Setting for Route Recording

Expo exposes six accuracy tiers:

| Level | Approx. radius | Use case |
|---|---|---|
| `Lowest` | ~3000m | City-level |
| `Low` | ~1000m | Neighborhood |
| `Balanced` | ~100m | General awareness |
| `High` | ~10m | Route recording |
| `Highest` | <5m | Precision |
| `BestForNavigation` | <5m + accelerometer | Turn-by-turn nav |

For foreground-only route recording with volunteers on foot or in vehicles, `Accuracy.High` is the correct choice. `BestForNavigation` activates the accelerometer in addition to GPS, increases battery drain significantly, and provides marginal benefit outside of navigation apps. `Accuracy.Highest` is acceptable but slightly more battery-intensive than `High`.

There is a historical report (GitHub issue #6226) that `Accuracy.Highest` did not produce meaningfully different results from `High` on some Android devices, suggesting the hardware ceiling is often the binding constraint rather than the API setting.

**Source:** Expo location docs, coffey.codes implementation guide, community accuracy discussions.

### 7. Battery Behavior in Foreground

`watchPositionAsync` with `Accuracy.High` and a `distanceInterval` of 5-10m is battery-intensive but bounded. Because the screen must stay on (a precondition of foreground operation), the GPS radio is not the dominant battery consumer -- the display is. For volunteer-testing sessions of finite duration (a single route recording, not continuous multi-hour tracking), this is not a material concern.

Community guidance: "Battery usage drops ~70% with Balanced accuracy, 10+ second intervals, and deferred batching." For a POC where accuracy matters, accept the battery cost.

**Source:** coffey.codes article, Expo location docs.

### 8. expo-router Integration

`watchPositionAsync` integrates cleanly with expo-router. The recommended pattern is `useFocusEffect` (from `@react-navigation/native`, re-exported through expo-router) rather than plain `useEffect`. This is because expo-router uses a stack navigator where screens remain mounted in memory -- `useEffect` with an empty dependency array only fires on first mount, not on re-focus after navigation. `useFocusEffect` starts the subscription when the screen comes into view and tears it down when it leaves focus.

Note: `useFocusEffect` has a separate open bug (#38204) where it fires twice on back navigation in some stack configurations with SDK 52/53. The `cancelled` guard in the cleanup pattern above also handles this race condition.

**Source:** React Navigation useFocusEffect docs, GitHub issue #38204 (useFocusEffect double-fire).

### 9. Production Usage Evidence

Multiple production-quality tutorials and implementations from 2024-2025 use `watchPositionAsync` as the standard foreground route recording API:

- Atomic Object's Expo map guide (2025): uses `watchPositionAsync` with foreground permissions only
- DEV Community real-time tracking post: uses `watchPositionAsync` with `Accuracy.Highest`, `timeInterval: 3000`, `distanceInterval: 5`
- LogRocket, PubNub, Djamware guides: all use `watchPositionAsync` for active foreground tracking

The community consensus is that `watchPositionAsync` is the correct API for use cases where the screen stays on. `startLocationUpdatesAsync` is recommended only when background/screen-off operation is required.

### 10. What watchPositionAsync Does NOT Replace

`watchPositionAsync` cannot substitute for `startLocationUpdatesAsync` in these scenarios:
- The device screen locks during recording
- The user switches apps mid-route
- The app is killed by the OS

For a production shipping app where any of these would cause data loss, `startLocationUpdatesAsync` with a foreground service notification is required -- with the caveat that this API has its own set of Android reliability issues (doze mode batching, ForegroundServiceStartNotAllowedException, foreground service stopping after 5-10 minutes on some devices). For a POC with volunteer testers who understand the screen must stay active, `watchPositionAsync` plus `expo-keep-awake` is a legitimate, lower-complexity alternative.

---

## Sources Consulted

### Official Documentation
- [Expo Location API docs](https://docs.expo.dev/versions/latest/sdk/location/)
- [Expo KeepAwake docs](https://docs.expo.dev/versions/latest/sdk/keep-awake/)
- [Expo Permissions guide](https://docs.expo.dev/guides/permissions/)

### GitHub Issues (expo/expo)
- [#35926 - watchPositionAsync subscription not removed on Android (SDK 52, April 2025)](https://github.com/expo/expo/issues/35926)
- [#35925 - Same bug, iOS report](https://github.com/expo/expo/issues/35925)
- [#10196 - timeInterval option ignored/broken (Android + iOS)](https://github.com/expo/expo/issues/10196)
- [#24760 - ForegroundServiceStartNotAllowedException on Android 12/13](https://github.com/expo/expo/issues/24760)
- [#32545 - startLocationUpdatesAsync rejected when app is backgrounded](https://github.com/expo/expo/issues/32545)
- [#22445 - Background location + foreground service not working (closed: works in production build)](https://github.com/expo/expo/issues/22445)
- [#14076 - TaskManager stops after 5-10 min in doze mode (closed stale 2022)](https://github.com/expo/expo/issues/14076)
- [#18915 - expo-location injects ACCESS_BACKGROUND_LOCATION without request](https://github.com/expo/expo/issues/18915)
- [#11918 - Play Store rejection due to background location in manifest](https://github.com/expo/expo/issues/11918)
- [#15607 - Background location stops when phone sleeps](https://github.com/expo/expo/issues/15607)
- [#38204 - useFocusEffect fires twice on back navigation](https://github.com/expo/expo/issues/38204)

### Engineering Blogs and Guides
- [Anthony Coffey - Building Location-Based Features Using Expo Location](https://coffey.codes/articles/building-location-based-features-using-expo-location)
- [Atomic Object - Current Location Map with Expo and React Native](https://spin.atomicobject.com/current-location-expo-react-native/)
- [DEV Community - Real-Time Location Tracking & Live Route Updates](https://dev.to/dainyjose/real-time-location-tracking-live-route-updates-in-react-native-4g15)
- [React Navigation - useFocusEffect](https://reactnavigation.org/docs/use-focus-effect/)

### Feature Tracking
- [Expo Canny - Background Location Tracking (879 votes, complete)](https://expo.canny.io/feature-requests/p/background-location-tracking)

---

## Source Quality Assessment

**Confidence: High**

The core behavioral characteristics of `watchPositionAsync` (foreground-only, screen-lock stops updates, no background permissions required) are confirmed by the official Expo docs and corroborated across multiple independent GitHub issues. The two active bugs (subscription cleanup, timeInterval) are confirmed by accepted issues with reproduction steps from multiple reporters. The screen-lock behavior is implied by docs and confirmed indirectly by issue #15607 and the general community understanding of "foreground" on Android.

**Gaps:**
- No direct Android hardware telemetry comparing GPS accuracy between `watchPositionAsync` and `startLocationUpdatesAsync` in foreground mode. The expectation is they are equivalent since both call the same underlying Android location provider, but this is not independently verified.
- The subscription cleanup bug (#35926) was filed in April 2025 and assigned; it is unknown whether it was resolved in SDK 53 or later. Teams on SDK 53+ should verify before shipping.
- Battery consumption data is community-estimated (the "70% reduction" figure) rather than measured.

---

## Open Questions

1. **Is the subscription cleanup bug fixed in SDK 53+?** The issue was assigned in April 2025 but the research did not find a confirmed merged fix or which SDK version ships it.

2. **Does `expo-keep-awake` reliably prevent screen lock in production builds on all Android OEMs?** Samsung and Xiaomi are known for aggressive background process killing. No device-specific data was found.

3. **Is `timeInterval` reliable in SDK 52+?** Issue #10196 was closed as "completed" in April 2025, but the specific SDK version that ships the fix was not documented.

4. **What is the GPS accuracy difference (if any) between `watchPositionAsync` and `startLocationUpdatesAsync` when both run in the foreground?** Both ultimately call the Android Fused Location Provider, suggesting parity, but no benchmark data was found.

5. **Does `useFocusEffect`'s double-fire bug (#38204) affect subscription creation in a way that causes duplicate routes?** The `cancelled` guard pattern mitigates this but needs verification in the specific expo-router version in use.

---

## Actionable Takeaways

1. **Replace `startLocationUpdatesAsync` with `watchPositionAsync` for the POC.** This is a sound engineering decision for foreground-only volunteer recording. It eliminates the entire class of TaskManager and foreground service failures.

2. **Add `expo-keep-awake`.** Call `activateKeepAwakeAsync()` when recording starts and `deactivateKeepAwake()` when it stops. This is the mechanism that keeps the screen on and therefore keeps `watchPositionAsync` receiving updates.

3. **Use `distanceInterval`, not `timeInterval`, as your update throttle.** Set `distanceInterval: 5` (meters) for walking routes. The `timeInterval` option has a multi-year bug history and was only marked fixed in April 2025 -- do not rely on it.

4. **Use `Accuracy.High` for route recording.** Do not use `BestForNavigation` unless turn-by-turn is needed; it activates the accelerometer and drains battery with negligible accuracy benefit for route tracing.

5. **Implement the `cancelled` flag pattern in your cleanup.** The subscription cleanup bug means `.remove()` alone may not stop updates on Android SDK 52. The flag prevents stale callbacks from writing to unmounted component state.

6. **Use `useFocusEffect` (not `useEffect`) for expo-router screens.** This ensures the subscription starts and stops on screen focus/blur, not just mount/unmount.

7. **Block `ACCESS_BACKGROUND_LOCATION` in `app.json` if this app goes to the Play Store.** Add `"blockedPermissions": ["android.permission.ACCESS_BACKGROUND_LOCATION"]` under `expo.android` to prevent the old Expo behavior of injecting it automatically.

8. **Document the screen-must-stay-on constraint for volunteer testers.** This is a UX requirement, not a technical workaround. The recording session ends if the screen goes dark. Consider a visible on-screen indicator that warns when the screen timeout is near.
