---
title: expo-location startLocationUpdatesAsync Android Process Death
type: research
tags: [expo, expo-location, android, crash, background-location, task-manager, foreground-service, signal-9]
summary: Android process death (signal 9 / SIGKILL) on startLocationUpdatesAsync call is caused by one of three native-layer failures: SecurityException from missing FOREGROUND_SERVICE_LOCATION permission (Android 14+), ForegroundServiceStartNotAllowedException from the app being backgrounded during task restore, or missing foreground service notification options triggering an uncaught IllegalStateException - none of which produce JS logs before the process dies.
status: active
source: deep-research
confidence: medium
created: 2026-03-10
updated: 2026-03-10
---

## Executive Summary

The pattern of "process killed by signal 9, no JS stacktrace, no AndroidRuntime exception in logcat, only happens on Start Recording (which calls `startLocationUpdatesAsync`), not on screen open" is a documented class of failure in expo-location on Android. The kill happens before or during native foreground service startup, which means the JS runtime never gets a chance to log anything. The three most likely root causes are: (1) a `SecurityException` thrown synchronously when the foreground service is started without `FOREGROUND_SERVICE_LOCATION` permission declared in the manifest (required on Android 14+ / API 34+), (2) a `ForegroundServiceStartNotAllowedException` thrown when `LocationTaskConsumer.maybeStartForegroundService()` is invoked while the process is considered "background" by Android 12/13/14, or (3) a `shouldUseForegroundService` logic bug (PR #35875) that forces a foreground service start even when no notification options were passed, resulting in an empty-notification foreground service that the OS kills immediately. A fourth, rarer cause is ProGuard stripping the TaskService class tree in release builds. This is a long-standing issue across SDK 38 through 52 with different surface manifestations per Android version.

---

## Detailed Findings

### Theme 1: SecurityException from Missing FOREGROUND_SERVICE_LOCATION (Android 14+, SDK 50+)

Android 14 (API 34) introduced a hard requirement that any foreground service of type `location` must have `android.permission.FOREGROUND_SERVICE_LOCATION` declared in the manifest. The OS enforces this synchronously at `startForegroundService()` time.

**Crash signature** (from GitHub issue #27336, SDK 50, Android 14):
```
Fatal Exception: java.lang.SecurityException
Starting FGS with type location callerApp=ProcessRecord{...} targetSDK=34
requires permissions: all of the permissions allOf=true
[android.permission.FOREGROUND_SERVICE_LOCATION]
any of the permissions allOf=false
[android.permission.ACCESS_COARSE_LOCATION, android.permission.ACCESS_FINE_LOCATION]
and the app must be in the eligible state/exemptions
```

This exception is thrown inside the native binder call to `ActivityManagerService`, which is below the React Native layer. The JS runtime has no opportunity to catch it. The process is killed by the OS immediately. This matches the signal 9 / "killed by OS" pattern with no JS logs.

**Why this affects dev builds specifically**: If the development build was created before `isAndroidForegroundServiceEnabled: true` was added to app.json, or if the prebuild step was skipped, the `FOREGROUND_SERVICE_LOCATION` permission is absent from `AndroidManifest.xml`. Expo Go cannot run background tasks at all on Android, so this crash only appears in dev builds that are missing the manifest entry.

**Fix path**: Ensure app.json has both `isAndroidForegroundServiceEnabled: true` and `isAndroidBackgroundLocationEnabled: true` in the expo-location plugin config, then run `npx expo prebuild` and rebuild the native binary. Check the generated `android/app/src/main/AndroidManifest.xml` to confirm `FOREGROUND_SERVICE` and `FOREGROUND_SERVICE_LOCATION` are both present.

Sources: GitHub #27336, GitHub #26846, GitHub #28767, Expo Location docs.

---

### Theme 2: ForegroundServiceStartNotAllowedException During Task Restore (Android 12/13/14)

When the app is killed while a location task is registered, Android fires a `TaskBroadcastReceiver` on relaunch to restore registered tasks. `LocationTaskConsumer.didRegister()` calls `maybeStartForegroundService()` inside this broadcast receiver handler. Because broadcast receivers execute in the background state, Android 12+ raises `ForegroundServiceStartNotAllowedException` when the service start is attempted.

**Crash signature** (from GitHub issue #24760, SDK 49, Android 12/13):
```
Exception java.lang.RuntimeException:
  at android.app.ActivityThread.handleReceiver (ActivityThread.java:4315)
  ...
Caused by android.app.ForegroundServiceStartNotAllowedException:
  at android.app.ContextImpl.startForegroundService (ContextImpl.java:1870)
  at expo.modules.location.taskConsumers.LocationTaskConsumer.maybeStartForegroundService (LocationTaskConsumer.java:241)
  at expo.modules.location.taskConsumers.LocationTaskConsumer.didRegister (LocationTaskConsumer.java:74)
  at expo.modules.taskManager.TaskService.internalRegisterTask (TaskService.java:469)
  at expo.modules.taskManager.TaskService.restoreTasks (TaskService.java:565)
  at expo.modules.taskManager.TaskService.<init> (TaskService.java:78)
  at expo.modules.taskManager.TaskBroadcastReceiver.onReceive (TaskBroadcastReceiver.java:13)
```

This crash affects production apps with 63,000+ occurrences reported in 90 days in one filing (GitHub #24760). It was causing 70% of production crashes for another reporter. The JS runtime is not involved; the exception surfaces in the Android system's broadcast receiver dispatch and kills the process.

**Fix**: Expo merged PR #24737 (`[location][android] Migrate to new modules API`) which added a foreground state check before calling `maybeStartForegroundService()`. This fix was included in the SDK 50 cycle. Apps still on SDK 49 or below are unpatched. Confirm the fix is present by checking `expo-location` version: should be `>=16.x` for SDK 50 or `>=17.0.1` for SDK 51.

**Critically relevant to the described crash scenario**: If `startLocationUpdatesAsync` is called from a button press while the app is visible (foreground), this specific path should not trigger. However, if the OS has classified the app process as background (which can happen briefly on Android even when the activity is visible, particularly during certain window focus transitions or on some OEM builds), `maybeStartForegroundService` inside the registration path can still throw.

Sources: GitHub #24760, GitHub #9570, GitHub #15081, PR #24737.

---

### Theme 3: shouldUseForegroundService Bug Forces Empty Notification Service (All SDK Versions Prior to PR #35875 Fix)

`LocationTaskConsumer.shouldUseForegroundService()` historically checked for the existence of the `foregroundService` key in the options map, not for a non-null value. The result: if the app called `startLocationUpdatesAsync` without passing a `foregroundService: { notificationTitle, notificationBody }` object, the service was still started (because the key existed as null), producing a foreground service notification with an empty title and body.

On modern Android (12+), a foreground service that fails to post a valid notification within a short window is killed by the OS. A foreground service started with a null-titled notification can fail this check, resulting in the process being signaled.

**PR #35875** (`[expo-location][android] fix: shouldUseForegroundService is always true`) fixed this by only adding the key to the options map when the value is non-null. This was merged in 2025.

**Actionable implication**: If `startLocationUpdatesAsync` is called without a `foregroundService` object in the options, on any expo-location build prior to the PR #35875 fix, Android will attempt to start a foreground service with no notification content. The OS may kill the service (and the process) within milliseconds. This is a plausible signal-9 cause on dev builds where the `foregroundService` option is absent or where `isAndroidForegroundServiceEnabled` is true in the manifest but the call-site options do not include the notification fields.

Sources: PR #35875, GitHub #22445, GitHub #9200.

---

### Theme 4: ProGuard Stripping TaskService in Release Builds

One confirmed workaround in GitHub #28959 comments: setting `"enableProguardInReleaseBuilds": false` resolved a case where the background task registered successfully but the callback never ran and the process eventually died. ProGuard was stripping expo-task-manager's `TaskService` class or related reflection paths.

This is not a signal-9 cause in dev builds (ProGuard is off in debug builds), but confirms that production builds can fail in this way.

Source: GitHub #28959 comment by `aeminkyr`.

---

### Theme 5: AsyncFunctionQueue "callback cannot be called more than once" Native Crash (SDK 47+)

A separate crash mode reported in GitHub #20663 (SDK 47, background location running overnight):
```
FATAL EXCEPTION: expo.modules.AsyncFunctionQueue
java.lang.RuntimeException: callback 2 arg cannot be called more than once
  at expo.modules.kotlin.jni.JavaCallback.invoke(Native Method)
  at expo.modules.location.LocationHelpers$1.onLocationChanged(LocationHelpers.java:157)
  at expo.modules.location.LocationModule$1.onLocationResult(LocationModule.java:557)
  at com.google.android.gms.internal.location.zzau.notifyListener
```

This crash happens when the Google Play Services location client fires two rapid location results and the internal promise callback is invoked twice. This is a crash in the `AsyncFunctionQueue` thread, not signal 9 — but it can appear similar in adb output (fatal exception kills the process). The crash only manifests after the service has been running for some time (typically overnight), not immediately on `startLocationUpdatesAsync` call.

Source: GitHub #20663.

---

### Theme 6: Dev Client Instability When Background Tasks Are Active

From GitHub #9415 and #9570: using `startLocationUpdatesAsync` in Expo Go or an early development client causes `ClassNotFoundException: host.exp.exponent.taskManager.ExpoHeadlessAppLoader`. The headless app loader class is only included in standalone builds and properly configured dev clients. This is SDK 38/39 vintage, fixed by SDK 39 patch release.

The symptom matches: pressing a button triggers `startLocationUpdatesAsync`, the app crashes and falls back to the launcher. The fix was rebuilding the dev client with the correct task manager module included. Relevant for teams still running old dev client binaries.

Source: GitHub #9415, GitHub #9570.

---

### Theme 7: Version-Specific Regressions by SDK

| SDK | Known Android Issue | Status |
|-----|--------------------|----|
| 38–39 | ClassNotFoundException ExpoHeadlessAppLoader on foreground task | Fixed SDK 39 patch |
| 42–43 | Crash on relaunch after kill with background task active (NullPointerException in TaskService.executeTask) | Partially fixed |
| 44 | startLocationUpdatesAsync broken in killed state + ReactInstanceManager crash on relaunch | Open/Stale |
| 47 | AsyncFunctionQueue double-callback crash on overnight background location | Not fixed as of #20663 |
| 49 | ForegroundServiceStartNotAllowedException on Android 12/13 broadcast receiver | Fixed in PR #24737 (SDK 50) |
| 50 | SecurityException for FOREGROUND_SERVICE_LOCATION on Android 14 | Manifest config fix required |
| 51 | Location task callback never fires on Android (fixed in expo-task-manager 11.8.2) | Fixed |
| 52 | NoClassDefFoundError for ActivityCompat (Jetifier regression) | Fixed in patched expo-location |

---

### Theme 8: Android 14 and 15 Foreground Service Policy Changes

Android 14 (API 34) introduced `FOREGROUND_SERVICE_LOCATION` as a distinct permission type. Apps targeting API 34 without it declared crash immediately when starting a location foreground service. This became a forced issue at SDK 50 because SDK 50 bumped the Android target SDK to 34.

Android 15 introduced additional foreground service restrictions (background launch restrictions tightened, health/safety/location service type splits). No specific expo-location issues for Android 15 were found in this research, but the trajectory is toward stricter enforcement of foreground service types.

Sources: GitHub #27336, GitHub #26846, Google Play policy docs.

---

## Sources Consulted

### GitHub Issues (expo/expo)
- [#9570](https://github.com/expo/expo/issues/9570) — Expo keeps stopping when app killed with background location active (SDK 38); root cause known, 40 comments
- [#9415](https://github.com/expo/expo/issues/9415) — Android Dev Client unstable with background tasks; ClassNotFoundException ExpoHeadlessAppLoader
- [#14784](https://github.com/expo/expo/issues/14784) — SDK 43 startLocationUpdatesAsync crashes standalone app on Android (first launch after kill)
- [#15081](https://github.com/expo/expo/issues/15081) — SDK 43 foreground service disappears and app crashes
- [#15515](https://github.com/expo/expo/issues/15515) — SDK 44 startLocationUpdatesAsync broken in killed state + ReactInstanceManager crash
- [#20663](https://github.com/expo/expo/issues/20663) — expo-location crash on Android background (SDK 47); AsyncFunctionQueue double-callback
- [#22445](https://github.com/expo/expo/issues/22445) — Background location and foreground service notification not working on Android
- [#24760](https://github.com/expo/expo/issues/24760) — ForegroundServiceStartNotAllowedException on Android 12/13 (SDK 49)
- [#26846](https://github.com/expo/expo/issues/26846) — SDK 50 Android 14 foreground service permission requirements (docs)
- [#27336](https://github.com/expo/expo/issues/27336) — Android 14 FOREGROUND_SERVICE_LOCATION SecurityException crash (SDK 50)
- [#28767](https://github.com/expo/expo/issues/28767) — startLocationUpdatesAsync fails; foreground permissions not found in manifest (SDK 51)
- [#28959](https://github.com/expo/expo/issues/28959) — Location task callback never fires on Android SDK 51; ProGuard workaround
- [#32545](https://github.com/expo/expo/issues/32545) — Foreground service cannot start when app is in background (SDK 51)

### GitHub Pull Requests (expo/expo)
- [PR #24737](https://github.com/expo/expo/pull/24737) — Migrate location to new modules API; fix ForegroundServiceStartNotAllowedException by checking app state before starting service
- [PR #35875](https://github.com/expo/expo/pull/35875) — Fix shouldUseForegroundService always true; prevents empty-notification foreground service crash

### Google Issue Tracker
- [issuetracker.google.com/297509048](https://issuetracker.google.com/issues/297509048) — Foreground service killed by SIGKILL after hours; no root cause identified even with battery optimization disabled

### Expo Documentation
- [expo.dev/versions/latest/sdk/location/](https://docs.expo.dev/versions/latest/sdk/location/) — Confirms FOREGROUND_SERVICE_LOCATION required for Android 14+; dev build required for Android background tasks

### Reddit
No signal-relevant Reddit threads found for this specific crash pattern. Reddit discussions on expo-location focus on update frequency and permission UX, not process death.

---

## Source Quality Assessment

**High confidence findings** (multiple independent sources, maintainer-confirmed):
- ForegroundServiceStartNotAllowedException on Android 12/13 during task restore (PR #24737 confirmed fix)
- SecurityException from missing FOREGROUND_SERVICE_LOCATION on Android 14+ (issue #27336, Expo docs)
- shouldUseForegroundService always-true bug (PR #35875 merged)
- ProGuard stripping TaskService classes in release builds (#28959 comment)

**Medium confidence findings** (reported by users, not isolated by Expo team):
- Signal-9 with no JS log as the observable crash form; this matches the native-layer throw pattern but the exact mechanism was not isolated in a reproducible issue
- The AsyncFunctionQueue double-callback crash (#20663) as a distinct failure mode

**Low confidence / gaps**:
- No Reddit or HackerNews threads specifically on signal-9 from startLocationUpdatesAsync were found
- No issues specifically filed for SDK 53 (current) on this pattern
- The exact kill pathway for "no AndroidRuntime stacktrace in logcat" was not documented in any single issue; the hypothesis is that the SecurityException or ForegroundServiceStartNotAllowedException kills the process before logcat output is flushed

---

## Open Questions

1. **Does the dev build's AndroidManifest.xml include `FOREGROUND_SERVICE_LOCATION`?** This is the most likely single cause on Android 14+ (Pixel, Samsung with Android 14). Check with `adb shell dumpsys package <package-name> | grep FOREGROUND_SERVICE`.

2. **Is `foregroundService: { notificationTitle, notificationBody }` being passed in the `startLocationUpdatesAsync` call options?** If absent, the PR #35875 bug (shouldUseForegroundService always true) forces a foreground service with no notification content, which the OS may kill immediately.

3. **What expo-location and expo-task-manager versions are in the dev build?** Versions prior to the PR #24737 merge (late 2023) will have the broadcast receiver foreground service crash.

4. **Is the crash reproducible on Android < 12?** If it only crashes on Android 12+, the ForegroundServiceStartNotAllowedException path is most likely. If it also crashes on Android 10/11, the issue is different.

5. **Does `adb logcat -s ActivityManager` show "ANR" or "Killing" lines just before the crash?** The OS kill would appear in the ActivityManager log even if the AndroidRuntime exception is not flushed.

---

## Actionable Takeaways

### Immediate diagnostic steps

1. Run `adb shell dumpsys package <your.package.name> | grep -E "FOREGROUND_SERVICE"` on the crashing device. Confirm both `android.permission.FOREGROUND_SERVICE` and `android.permission.FOREGROUND_SERVICE_LOCATION` appear. If `FOREGROUND_SERVICE_LOCATION` is absent, that is the crash cause on Android 14.

2. Check the `startLocationUpdatesAsync` call site. Ensure the options include:
   ```typescript
   foregroundService: {
     notificationTitle: 'Recording',
     notificationBody: 'Location tracking active',
   }
   ```
   This is required for Android 8+ to legally keep the service alive. Without it, on expo-location versions before PR #35875, the service starts with blank content and may be killed.

3. Capture `adb logcat -d | grep -E "ActivityManager|SIGKILL|killed|ExpoLocation|TaskService" > crash.log` immediately after triggering the crash. Look for `Starting FGS with type location ... requires permissions` (SecurityException path) or `ForegroundServiceStartNotAllowedException` lines.

### Config fixes (require native rebuild)

4. In `app.json`, set:
   ```json
   ["expo-location", {
     "isAndroidBackgroundLocationEnabled": true,
     "isAndroidForegroundServiceEnabled": true
   }]
   ```
   Then run `npx expo prebuild --clean` and rebuild the dev client binary.

5. Add `FOREGROUND_SERVICE_LOCATION` explicitly if targeting Android 14:
   ```json
   "android": {
     "permissions": [
       "ACCESS_FINE_LOCATION",
       "ACCESS_COARSE_LOCATION",
       "ACCESS_BACKGROUND_LOCATION",
       "FOREGROUND_SERVICE",
       "FOREGROUND_SERVICE_LOCATION"
     ]
   }
   ```

### Version pinning

6. Use `expo-location` >= 17.0.1 (SDK 51) or >= 16.5.x (SDK 50). Older versions lack the PR #24737 foreground state check that guards against the broadcast-receiver crash.

7. Use `expo-task-manager` >= 11.8.2 for SDK 51 fixes.

### Alternative architecture (if expo-location remains unstable)

8. The community has migrated to [`react-native-background-geolocation`](https://github.com/transistorsoft/react-native-background-geolocation) (paid, $129/app) or `@mauron85/react-native-background-geolocation` (free, older) for production-grade background location. These libraries manage foreground service lifecycle directly in native code and have better documentation for each Android version's restrictions. Multiple Expo issue commenters report switching to these as the only reliable path for high-reliability background tracking.

9. If the app only needs foreground location (user is looking at the screen while recording), replace `startLocationUpdatesAsync` with `watchPositionAsync` inside a React component and manage cleanup in the unmount effect. This avoids the foreground service machinery entirely and is not subject to any of these crash modes. The tradeoff is no background delivery.

---

## Related Research Files

- `/Users/alphab/.mdx/research/expo-location-startLocationUpdatesAsync-crash-patterns.md` — Broader crash pattern catalog (iOS, Android, double-registration, defineTask timing)
- `/Users/alphab/.mdx/research/expo-location-background-tasks-dev-build-vs-production.md` — Dev build vs Expo Go, config plugin requirements, prebuild sequence
