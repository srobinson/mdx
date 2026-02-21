---
title: Android 14/15 Foreground Service Location Changes and Expo Impact
type: research
tags: [android-14, android-15, foreground-service, expo-location, react-native, permissions, background-location, SIGKILL]
summary: Android 14 made foreground service type declarations mandatory and introduced FOREGROUND_SERVICE_LOCATION as a required permission; expo-location has shipped partial fixes across SDK 50-53 but active regressions remain, and a signal 9 kill with no JS/Java stacktrace is a known symptom of a SecurityException thrown before the JS bridge initializes.
status: active
source: deep-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Executive Summary

Android 14 (API 34) introduced a hard enforcement of foreground service type declarations: every service must declare `android:foregroundServiceType` in the manifest, and every app must hold the matching type-specific permission before calling `startForeground()`. For location services the required permission is `FOREGROUND_SERVICE_LOCATION`. If either requirement is missing, the system throws a `SecurityException` inside the native service lifecycle, which in the context of an Expo dev client can kill the process (signal 9) before any JS-layer stacktrace is produced. Expo has shipped fixes across SDK 50-53 but several known regressions persist, including a bug where `shouldUseForegroundService` is always `true` even without explicit configuration (PR #35875, still open as of early 2026).

---

## Detailed Findings

### Theme 1: Android 14 Mandatory Foreground Service Type (the Root Law)

Android 14 (API level 34) made explicit service type declarations non-optional for all apps targeting API 34+. This applies regardless of whether the app previously worked without them.

**Manifest requirements (complete list for location):**

```xml
<manifest>
  <!-- Base foreground service permission -->
  <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />

  <!-- Type-specific permission: NEW and required in Android 14+ -->
  <uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />

  <!-- Runtime location permissions (at least one required) -->
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
  <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

  <!-- Required if starting service while app is backgrounded -->
  <uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />

  <application>
    <service
      android:name=".services.LocationTaskService"
      android:foregroundServiceType="location"
      android:exported="false" />
  </application>
</manifest>
```

**Code-level requirement:** The `startForeground()` call itself must pass the service type:

```kotlin
ServiceCompat.startForeground(
    serviceId,
    notification,
    FOREGROUND_SERVICE_TYPE_LOCATION  // required on API 29+; enforced on API 34+
)
```

**Failure modes (two distinct paths):**

1. `SecurityException` — missing `FOREGROUND_SERVICE_LOCATION` permission OR location runtime permission not granted before `startForeground()` is called. Thrown synchronously inside the native service binding lifecycle.
2. `MissingForegroundServiceTypeException` — service starts without `android:foregroundServiceType` declared in the manifest at all.

Both exceptions are thrown at the native layer. In React Native, if this happens during module initialization before the JS bridge is up, the process is terminated by the system and the only observable symptom is signal 9 / SIGKILL with no Java or JS stacktrace surviving.

Source: [Android developer docs — fgs-types-required](https://developer.android.com/about/versions/14/changes/fgs-types-required), [fgs/service-types](https://developer.android.com/develop/background-work/services/fgs/service-types), [fgs/troubleshooting](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)

**Critical sequencing rule:** Runtime permissions must be requested and granted BEFORE `startForeground()` is called. Apps that previously requested permissions lazily (after starting the service) will crash on Android 14+.

Source: [developer.android.com fgs-types-required](https://developer.android.com/about/versions/14/changes/fgs-types-required)

---

### Theme 2: Android 15 Additional Restrictions

Android 15 did not add new restrictions specifically targeting location foreground services. The Android 15 foreground service changes page focuses on:

- A new `mediaProcessing` service type with a 6-hour time limit per 24 hours.
- Additional services blocked from starting via `BOOT_COMPLETED` receivers (camera, data sync, media playback, media projection, phone call).
- While-in-use permission restriction tightened: apps in the background cannot start foreground services that require while-in-use permissions (camera, microphone, location) even if they hold background exemptions.

The while-in-use tightening is the Android 15 change most likely to affect background location recording. An app that calls `Location.startLocationUpdatesAsync()` during a background state transition (e.g., during a background task callback or after the user presses Home) will get a `ForegroundServiceStartNotAllowedException` on Android 12+ and this is now more strictly enforced on Android 15.

Source: [Android 15 foreground service types](https://developer.android.com/about/versions/15/changes/foreground-service-types), [Android 15 behavior changes](https://developer.android.com/about/versions/15/behavior-changes-15)

---

### Theme 3: Expo's Response — What Was Fixed and When

**expo-location's bundled AndroidManifest (version 14.3.0 / Expo SDK ~49):**

```xml
<manifest>
  <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
  <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
  <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
  <application>
    <service android:name=".services.LocationTaskService"
             android:exported="false"
             android:foregroundServiceType="location" />
  </application>
</manifest>
```

**Notable absence:** `FOREGROUND_SERVICE_LOCATION` was NOT in the bundled manifest at version 14.3.0. This is the critical gap that caused crashes when SDK 50 began targeting API 34.

**SDK 50 fix (February–March 2024, expo-location ~16.x):** Expo acknowledged the issue in GitHub issue #27336. The fix (PR #27355) added handling for the `SecurityException` when the foreground service is unavailable on API 34. Running `npx expo install --fix` after SDK 50 upgrade was the recommended remediation.

The current Expo docs note that `FOREGROUND_SERVICE_LOCATION` is automatically added by the plugin — meaning it was added to the plugin-injected manifest logic at some point during the SDK 50 cycle — but the bundled module manifest still varied by version.

**SDK 51 (expo-location 17.x) regression:** `startLocationUpdatesAsync` started failing with "foreground service permissions were not found in the manifest." Foreground location service support was removed from Expo Go for Android in SDK 51. Development builds are required.

**SDK 52 regression (expo-location 18.0.1):** A separate crash caused by a deprecated Support Library class (`android.support.v4.app.ActivityCompat`). Fixed in expo-location 18.0.2 via a pre-jetified `.aar`. Not specific to Android 14 foreground service types, but a parallel breakage.

**SDK 52/53 regression (PR #35875, open):** `shouldUseForegroundService` is always `true` because the code checks for the existence of a map key that is always present. This causes an unexpected foreground service notification even when the developer did not configure one, and can cause the service to be started without proper foreground service options configured, potentially triggering a crash when the resulting notification has no title or body. This is an active, unfixed regression as of early 2026.

**SDK 53 regression (issue #39851, 2025):** `Location.getCurrentPositionAsync()` hangs indefinitely on subsequent app launches when foreground service is enabled. First launch works; subsequent launches hang. This suggests a stale service state problem.

**Config-plugins gap (PR #33166, merged):** The `ManifestServiceAttributes` TypeScript type was missing `android:foregroundServiceType` as a declared property. This prevented TypeScript-correct custom config plugins from injecting the attribute, causing silent failures in managed workflow apps with custom native modifications.

Sources: [expo/expo #27336](https://github.com/expo/expo/issues/27336), [expo/expo #26846](https://github.com/expo/expo/issues/26846), [expo/expo #28767](https://github.com/expo/expo/issues/28767), [expo/expo #32545](https://github.com/expo/expo/issues/32545), [expo/expo #33041](https://github.com/expo/expo/issues/33041), [expo/expo PR #33166](https://github.com/expo/expo/pull/33166), [expo/expo PR #35875](https://github.com/expo/expo/pull/35875), [expo/expo #39851](https://github.com/expo/expo/issues/39851)

---

### Theme 4: The Signal 9 / No-Stacktrace Pattern

A signal 9 (SIGKILL) kill with no surviving JS or Java stacktrace is consistent with a `SecurityException` thrown at the native Android service layer before the React Native bridge initializes. This is distinct from normal Java crashes, which produce stacktraces in logcat.

Mechanism:
1. The Expo dev client loads and begins initializing native modules.
2. `expo-location` or `expo-task-manager` attempts to bind or start the `LocationTaskService` during module initialization.
3. Android 14/15 validation fails (missing permission or service type) and throws `SecurityException` inside `startForeground()`.
4. The uncaught native exception propagates outside the JVM's normal exception handling, causing the process to be killed by the system runtime.
5. No logcat entry with a clean stacktrace survives because the exception is thrown in a context that bypasses normal Java exception reporting (native binder thread).

This pattern is documented in Google's Issue Tracker (issue #362123232) where developers report crashes "only in production via Crashlytics" that are unreproducible on test devices — consistent with a permission grant state difference between environments.

Source: [issuetracker.google.com/362123232](https://issuetracker.google.com/issues/362123232), [expo/expo #27336](https://github.com/expo/expo/issues/27336)

---

### Theme 5: Emulator vs Physical Device Differences

No authoritative Android documentation addresses behavioral differences between emulators and physical devices for foreground service SecurityException behavior. Community reports suggest:

- The crash IS reproducible on Android 14/15 emulators (virtual Pixel 8 Pro confirmed in community reports).
- Emulators may behave differently from physical devices for background start restrictions because emulators often lack the same battery optimization and power management triggers that activate stricter enforcement on physical devices.
- The `Improve Location Accuracy` setting on the emulator (which uses Wi-Fi scanning) may interact with foreground service behavior; turning it off and using GPS-only sometimes resolves emulator-specific location hangs.
- On Samsung Galaxy S25 (Android 15), a distinct regression was reported where foreground services crash with `SecurityException` for reasons not seen on other Android 15 hardware — suggesting OEM-level variation in enforcement.

Source: [Samsung Developer Forums](https://forum.developer.samsung.com/t/crash-on-foregroundservices-only-on-samsung-s25-android-15-devices/41642), [Expo location docs](https://docs.expo.dev/versions/latest/sdk/location/)

---

### Theme 6: Background Start Restriction (ForegroundServiceStartNotAllowedException)

A separate but frequently conflated failure mode: Android 12+ restricts starting foreground services from the background. Apps that call `startLocationUpdatesAsync()` after transitioning to the background receive `ForegroundServiceStartNotAllowedException`.

Community workaround: Call `startLocationUpdatesAsync()` immediately after app launch while the app is in the foreground state, rather than on-demand. This ensures the foreground service starts while the app is in the foreground and can then continue while backgrounded.

This is distinct from the Android 14 type-declaration failure, but both can manifest as process kills in Expo with no stacktrace if the exception propagates before the bridge is up.

Source: [expo/expo #32545](https://github.com/expo/expo/issues/32545) (unresolved as of February 2025)

---

## Sources Consulted

### Android Official Documentation
- [Foreground service types are required (Android 14)](https://developer.android.com/about/versions/14/changes/fgs-types-required)
- [Changes to foreground service types (Android 15)](https://developer.android.com/about/versions/15/changes/foreground-service-types)
- [Foreground service types reference](https://developer.android.com/develop/background-work/services/fgs/service-types)
- [Foreground service troubleshooting](https://developer.android.com/develop/background-work/services/fgs/troubleshooting)
- [Restrictions on starting foreground services from background](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start)
- [Behavior changes: Android 14](https://developer.android.com/about/versions/14/behavior-changes-14)
- [Behavior changes: Android 15](https://developer.android.com/about/versions/15/behavior-changes-15)

### Expo GitHub Issues
- [#27336 — Android 14 foreground service permission crash (SDK 50)](https://github.com/expo/expo/issues/27336)
- [#26846 — SDK 50 Android 14 foreground service docs gap](https://github.com/expo/expo/issues/26846)
- [#28767 — startLocationUpdatesAsync fails, foreground permissions not found in manifest](https://github.com/expo/expo/issues/28767)
- [#32545 — ForegroundServiceStartNotAllowedException, cannot start from background (SDK 51)](https://github.com/expo/expo/issues/32545)
- [#33041 — SDK 52 expo-location android dev build crash](https://github.com/expo/expo/issues/33041)
- [#28959 — startLocationUpdatesAsync task callback never fires (SDK 51)](https://github.com/expo/expo/issues/28959)
- [#39851 — getCurrentPositionAsync hangs indefinitely (SDK 53)](https://github.com/expo/expo/issues/39851)
- [PR #33166 — ManifestServiceAttributes missing foregroundServiceType](https://github.com/expo/expo/pull/33166)
- [PR #35875 — shouldUseForegroundService always true](https://github.com/expo/expo/pull/35875)

### Expo Documentation
- [Location SDK reference (current)](https://docs.expo.dev/versions/latest/sdk/location/)

### Google Issue Tracker
- [#362123232 — Android 14 foreground location crash despite permissions](https://issuetracker.google.com/issues/362123232)
- [#297509048 — Foreground service SIGKILL after hours](https://issuetracker.google.com/issues/297509048)

### Module Source
- [expo-location AndroidManifest.xml v14.3.0 (UNPKG)](https://app.unpkg.com/expo-location@14.3.0/files/android/src/main/AndroidManifest.xml)

---

## Source Quality Assessment

**Confidence: High** for the Android platform requirements (official Google documentation, cross-referenced across multiple doc pages). The manifest requirements and exception types are unambiguous.

**Confidence: High** for the Expo SDK 50 crash being FOREGROUND_SERVICE_LOCATION related — multiple independent reporters with identical error strings.

**Confidence: Medium** for the signal 9 / no-stacktrace explanation — the mechanism is inferred from the exception type and React Native initialization order; there is no Google documentation that explicitly maps this SecurityException to SIGKILL in the emulator context.

**Confidence: Medium** for the active state of PR #35875 (`shouldUseForegroundService` regression) — the PR existed as of late 2025 but the exact merge status as of March 2026 was not confirmed.

**Gaps:** No Reddit discussions found for this specific combination of symptoms. Community discussion is primarily in GitHub issues. Emulator vs physical device behavioral differences are poorly documented and rely on anecdotal reports.

---

## Open Questions

1. Does the current production version of expo-location (as of March 2026) include `FOREGROUND_SERVICE_LOCATION` in the bundled `AndroidManifest.xml`, or is it injected only by the config plugin? The v14.3.0 manifest did not include it; later versions should, but this needs verification against the installed version in the affected app.

2. Is PR #35875 (`shouldUseForegroundService` always true) merged in the version the affected app is using? If not, an unintentional foreground service with no notification config may be the immediate cause of the crash.

3. Does the affected app call `startLocationUpdatesAsync()` from a foreground state or during a background transition? This determines whether the crash is Android 14 type enforcement or Android 12+ background start restriction.

4. What is the exact Expo SDK version and expo-location version installed in the affected app? The failure mode differs substantially across SDK 50, 51, 52, and 53.

5. Is the emulator running with a Google Play image (which enforces Play Protect security policies and may have stricter foreground service enforcement than AOSP emulator images)?

---

## Actionable Takeaways

### Immediate diagnostic steps

1. **Check the compiled AndroidManifest.xml in the build output.** In a development build, run:
   ```bash
   # In the android/ directory of the prebuild
   cat app/build/intermediates/merged_manifests/debug/AndroidManifest.xml | grep -A5 "FOREGROUND_SERVICE"
   ```
   Verify that BOTH `android.permission.FOREGROUND_SERVICE` AND `android.permission.FOREGROUND_SERVICE_LOCATION` are present. Verify that `LocationTaskService` has `android:foregroundServiceType="location"`.

2. **Check logcat before the kill signal.** Run:
   ```bash
   adb logcat -c && adb logcat *:E | grep -E "SecurityException|ForegroundService|LocationTask"
   ```
   Filter for the moment just before the signal 9. A `SecurityException` line will appear before the process is killed if this is the root cause.

3. **Verify the expo-location version** installed: `cat node_modules/expo-location/package.json | grep '"version"'`. If below 16.x (SDK 50 era), the FOREGROUND_SERVICE_LOCATION permission may not be present in the bundled manifest.

### Configuration fixes

4. **Ensure the app.json plugin config is correct:**
   ```json
   {
     "expo": {
       "plugins": [
         [
           "expo-location",
           {
             "isAndroidBackgroundLocationEnabled": true,
             "isAndroidForegroundServiceEnabled": true
           }
         ]
       ]
     }
   }
   ```
   Then rebuild the development client — plugin changes require a new native build.

5. **If the config plugin is not injecting FOREGROUND_SERVICE_LOCATION**, add it explicitly via a custom config plugin or via `app.json`'s `android.permissions` array. This is a known workaround documented in issue #26846.

6. **Ensure `startLocationUpdatesAsync()` is called from a foreground state** — do not call it inside a background task callback, `useEffect` that runs after navigation, or any code path that could execute during a background-to-foreground transition. Call it synchronously in response to a user action while the app is active.

7. **Run `npx expo install --fix`** to ensure all expo packages are on compatible versions for your SDK.

### Longer-term

8. For the `shouldUseForegroundService` always-true regression (PR #35875), monitor the expo-location changelog. If affected, explicitly pass `foregroundService: { notificationTitle: "...", notificationBody: "..." }` to `startLocationUpdatesAsync()` as a workaround to ensure the notification is valid when the service starts.

9. Test on both an **AOSP emulator image** and a **Google Play emulator image** — enforcement behavior can differ. Physical device testing on Android 14+ is recommended before considering emulator results authoritative.
