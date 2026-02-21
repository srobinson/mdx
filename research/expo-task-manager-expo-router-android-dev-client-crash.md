---
title: expo-task-manager + expo-router + Android dev client crash patterns
type: research
tags: [expo-task-manager, expo-router, android, dev-client, background-task, crash, background-location, foreground-service]
summary: On Android dev client, calling startLocationUpdatesAsync kills the process (signal 9) due to a convergence of three independent failure modes: missing foreground service type in the manifest, headless JS context initialization failing in the dev client's app loader, and Android 14+ foreground service permission enforcement. The service-file + _layout.tsx import pattern is architecturally correct but requires specific config plugin settings and a native rebuild to function.
status: active
source: deep-research
confidence: medium
created: 2026-03-10
updated: 2026-03-10
---

## Executive Summary

`Location.startLocationUpdatesAsync` on Android dev client can kill the process without a clean stacktrace due to at least three distinct, compounding failure modes. The most likely cause in an Expo dev client build is the foreground service type permission not being declared in the manifest — Android 14+ enforces this at the OS level and terminates the service process when it tries to start. Secondary causes include the dev client's headless app loader failing to find `ExpoHeadlessAppLoader` (a documented dev-client-specific issue), and fast-refresh invalidating the JS runtime while a background task is in flight. The pattern of defining `TaskManager.defineTask` at module level in a service file imported from `_layout.tsx` is architecturally correct per Expo's own documentation and maintainer guidance; the failure is in the runtime environment, not the registration pattern.

---

## Detailed Findings

### Theme 1: The Registration Pattern Is Correct

Expo's official docs and maintainer Brent Vatne both confirm the required pattern:

> "It must be called at the top level of your app, outside of any function execution. Tasks must register themselves even if the React app is not rendered."
> — Brent Vatne, [Issue #20210](https://github.com/expo/expo/issues/20210)

The rationale is that when Android launches the app headlessly for a background task, no React views are mounted. The task handler must be reachable by simply evaluating the module graph. A service file that exports `TaskManager.defineTask(...)` at module scope, imported from the root `_layout.tsx`, satisfies this requirement.

**Confirmed incorrect patterns** (documented across multiple issues):
- Calling `defineTask` inside a React component function
- Calling it inside a custom hook
- Calling it inside `componentDidMount` or `useEffect`
- Registering (`startLocationUpdatesAsync`) before the task is defined

**The `_layout.tsx` import approach** is explicitly recommended in Expo's own example repos. The `BackgroundLocationMapScreen.tsx` in native-component-list places the `defineTask` call at module scope, at the top of the file.

---

### Theme 2: Missing Manifest Entries — The Most Likely Process Kill Cause

The most probable root cause for a silent process kill (signal 9, no stacktrace) on Android dev client is missing foreground service declarations in the manifest.

**Android 14+ (API 34+) enforcement:**

Android 14 requires an explicit `foregroundServiceType="location"` attribute on the foreground service declaration. Without it, the OS terminates the service process when it attempts to start. This produces no clean application-level stacktrace because the kill happens at the OS process scheduler level before the JVM exception handler can fire.

Documented in:
- [Issue #27336](https://github.com/expo/expo/issues/27336): "Starting FGS with type location requires permissions: android.permission.FOREGROUND_SERVICE_LOCATION" — the app crashed in standalone builds
- [Issue #26846](https://github.com/expo/expo/issues/26846): SDK 50 changelog documenting new Android 14 foreground service type requirements
- [Issue #28767](https://github.com/expo/expo/issues/28767): SDK 51 regression — "foreground service permissions were not found in the manifest", confirmed to affect dev client builds too

**What the config plugin must emit:**

The following `app.json` (or `app.config.js`) configuration is required. Without a native rebuild after setting these, the manifest will not contain the correct entries:

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

The `isAndroidForegroundServiceEnabled: true` flag is what triggers the config plugin to inject `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_LOCATION`, and the `android:foregroundServiceType="location"` attribute into the manifest. This requires a native rebuild — OTA updates do not affect the manifest.

**The "foreground service cannot be started when app is in background" error** ([Issue #32545](https://github.com/expo/expo/issues/32545)) is a related but distinct failure: calling `startLocationUpdatesAsync` while the app is in background state (rather than during active foreground) triggers Android's "foreground service start while backgrounded" restriction (added in Android 12). The confirmed workaround is to call `startLocationUpdatesAsync` during app initialization (while the app is visibly in the foreground), not in response to a background/suspend lifecycle event.

---

### Theme 3: Dev Client-Specific Headless App Loader Failures

The Android dev client has a documented, long-standing instability with background tasks that does not occur in production standalone builds.

**`ClassNotFoundException: host.exp.exponent.taskManager.ExpoHeadlessAppLoader`**
([Issue #9415](https://github.com/expo/expo/issues/9415))

When a background task fires and Android needs to spin up a headless JS environment, the dev client's custom app loader mechanism attempts to instantiate `ExpoHeadlessAppLoader`. In the dev client build, this class is sometimes not present on the DEX path — causing the headless environment to fail to initialize before the task runs. The task system then reports "Cannot execute background task because application loader can't be found" ([Issue #6017](https://github.com/expo/expo/issues/6017)).

Key characteristics:
- **Dev client only.** Standalone production builds do not exhibit this failure
- **Intermittent.** Apps sometimes start successfully after multiple attempts
- **Original SDK 39 fix** addressed the specific `ClassNotFoundException` but related loader failures have resurfaced in later SDKs
- The underlying mechanism is that the dev client uses a different app initialization path than production builds, which does not guarantee `ExpoHeadlessAppLoader` is available when Android spawns a headless process for task execution

**`Cannot get ReactInstanceManager from kernel`** ([Issue #15515](https://github.com/expo/expo/issues/15515))

A related SDK 44 regression: when `startLocationUpdatesAsync` triggers a headless execution context after the app is killed, `ExpoTurboPackage.getDefaultUIManager` attempts to retrieve the `ReactInstanceManager` from the kernel. In headless mode, `kernel.reactInstanceManager` returns null, causing a `RuntimeException`. Fixed by PR #15575 — the fix skips UIManager registration in the headless `getReactModuleInfoProvider`, allowing fallback to RN's default UIManager.

---

### Theme 4: Fast Refresh / Hot Reload Invalidation

Fast refresh (pressing 'r' in Metro, or saving a file) during an active background task session creates a dangerous state in the Android dev client.

**Duplicate task registration is not the primary issue.** The native Android `TaskService` is idempotent — re-registering an already-registered task updates its options rather than creating a duplicate. This was confirmed by examining the native `TaskService.java` implementation.

**What is dangerous is the stale runtime:**

When fast refresh fires, the old JS runtime is torn down and a new one is created. If a background location update arrives between the teardown and re-initialization, the native location service tries to invoke the task callback on the now-invalidated JS runtime. On Android this can cause:

- `IllegalArgumentException: You attempted to access the app context before the module was created` ([Issue #35439](https://github.com/expo/expo/issues/35439)) — triggered in `expo-modules-core` JSI context initialization, resulting in a SIGABRT (signal 6)
- `RuntimeException: callback 2 arg cannot be called more than once` ([Issue #20663](https://github.com/expo/expo/issues/20663)) — the promise callback for a location event is invoked twice across the reload boundary

Both of these produce abrupt process termination with no clean application stacktrace from the JavaScript side, because the crash occurs in JNI/native code before JS error boundaries can catch it.

**Rapid reload crash ([Issue #35439](https://github.com/expo/expo/issues/35439)):** Pressing 'r' 5-10 times quickly in Metro reliably crashes the Android dev client with a fatal SIGABRT in `expo::JSIContext::prepareRuntime()`. This is purely a dev-client issue. It confirms the JS runtime teardown/reinit cycle is not hardened against concurrent native callbacks.

---

### Theme 5: SDK-Specific Regressions

Several SDK upgrades introduced regressions in Android background location that are directly relevant:

**SDK 51 regression** ([Issue #28959](https://github.com/expo/expo/issues/28959)):
- Task callbacks registered with `startLocationUpdatesAsync` stopped firing on Android
- Task appeared registered (confirmed via `TaskManager.getRegisteredTasksAsync`)
- No callbacks were delivered; logcat showed the app running out of memory after minutes
- Fixed by PR #29024
- The issue confirmed SDK 50 → SDK 51 was a breaking regression for Android background location

**SDK 51 manifest regression** ([Issue #28767](https://github.com/expo/expo/issues/28767)):
- Foreground service permission annotations missing from manifest after SDK 51 config plugin changes
- Affected both Expo Go (expected) and dev client builds (unexpected — this was a regression)
- Persisted even with correct `app.json` settings; required a clean rebuild

**SDK 50, Android 14 foreground service crash** ([Issue #27336](https://github.com/expo/expo/issues/27336)):
- Fixed by PR #27355 within hours of report
- `npx expo install --fix` updates the package to the patched version

**Duplicate `expo-task-manager` installation** ([Issue #26717](https://github.com/expo/expo/issues/26717)):
- When `expo-background-fetch` (or other packages) bundle their own `expo-task-manager` version, the two instances maintain separate task registries
- `defineTask` in one registry is not visible to `startLocationUpdatesAsync` in the other
- Produces the error: "Task 'X' is not defined. You must define a task using TaskManager.defineTask before registering"
- Fix: add a `resolutions` entry in `package.json` (Yarn) or `overrides` (npm) to force a single version

---

### Theme 6: Android Background Service Lifecycle and Dev Client Differences

Android's foreground service rules interact with Expo's TaskManager in ways that behave differently in dev client vs production:

**The foreground service start restriction (Android 12+):** Apps cannot start a foreground service while running in the background. In production, this typically means location tracking must be initiated while the app is in the foreground, then kept alive via the notification. In dev client, the Metro bundler connection and dev menu activity can alter what Android considers "foreground", leading to timing differences in when this restriction fires.

**`killServiceOnDestroy` flag:** The `LocationTaskServiceOptions` supports a `killServiceOnDestroy` boolean. When `true`, stopping the app also stops the background service. When `false` (default), the service survives app closure. In dev client, the app "closes" more frequently (bundle reload, Metro reconnect) than in production, and if the service survives these reloads, it can be in a state where it holds a reference to a now-invalid JS runtime.

**The force-stop crash** ([Issue #28728](https://github.com/expo/expo/issues/28728)):
When the app is force-stopped while a background location task is active, and the app is reopened, a crash occurs with:
`"The module wasn't created! You can't access the app context"` during JSI interop installation.
This only appeared with additional Expo dependencies installed (expo-font, expo-notifications, expo-updates alongside expo-location), suggesting a module initialization ordering problem during the headless restart sequence.

---

## Sources Consulted

### GitHub Issues (expo/expo)

- [#6017](https://github.com/expo/expo/issues/6017) — startLocationUpdatesAsync + defineTask crash and unregistering (2020, standalone Android)
- [#9288](https://github.com/expo/expo/issues/9288) — Umbrella issue: task manager + background location on Android
- [#9415](https://github.com/expo/expo/issues/9415) — Android dev client: ClassNotFoundException ExpoHeadlessAppLoader (dev-client-specific)
- [#14784](https://github.com/expo/expo/issues/14784) — SDK 43 startLocationUpdatesAsync crashes standalone Android
- [#15515](https://github.com/expo/expo/issues/15515) — SDK 44 startLocationUpdatesAsync doesn't work when app killed, crashes
- [#19681](https://github.com/expo/expo/issues/19681) — Cannot register background task (TaskManager interface null)
- [#20210](https://github.com/expo/expo/issues/20210) — defineTask documentation unclear, maintainer clarification on global scope requirement
- [#20663](https://github.com/expo/expo/issues/20663) — expo-location crash in background, SDK 47+ (callback invoked twice)
- [#22183](https://github.com/expo/expo/issues/22183) — Task manager doesn't work in background
- [#23559](https://github.com/expo/expo/issues/23559) — Task executor stops firing after app reopen (foreground service misconfiguration, SDK 48)
- [#26717](https://github.com/expo/expo/issues/26717) — Expo 50: task not defined due to duplicate expo-task-manager installations
- [#26846](https://github.com/expo/expo/issues/26846) — SDK 50 docs: Android 14 foreground service permission requirements
- [#27336](https://github.com/expo/expo/issues/27336) — Android 14 foreground service permission crash in SDK 50, fixed by PR #27355
- [#28728](https://github.com/expo/expo/issues/28728) — Force stop crash with background location active (SDK 50, standalone)
- [#28767](https://github.com/expo/expo/issues/28767) — SDK 51: startLocationUpdatesAsync fails, foreground permissions not in manifest
- [#28959](https://github.com/expo/expo/issues/28959) — SDK 51 regression: task callback never fires on Android, OOM after minutes
- [#32545](https://github.com/expo/expo/issues/32545) — Foreground service cannot be started when app is in background (SDK 51+)
- [#35385](https://github.com/expo/expo/issues/35385) — "App react context shouldn't be created before" crash in DevLauncherAppLoader (SDK 52)
- [#35439](https://github.com/expo/expo/issues/35439) — App crashes on quick reload in Android, SIGABRT in JSIContext::prepareRuntime (SDK 52)
- [#36492](https://github.com/expo/expo/issues/36492) — Background task registered but never executes (SDK 52)

### Official Documentation

- [TaskManager docs](https://docs.expo.dev/versions/latest/sdk/task-manager/) — global scope requirement for defineTask
- [Location docs](https://docs.expo.dev/versions/latest/sdk/location/) — config plugin fields, foreground service requirements
- [BackgroundTask docs](https://docs.expo.dev/versions/latest/sdk/background-task/) — top-level scope requirement

### Engineering Blog

- [Goodbye background-fetch, hello expo-background-task](https://expo.dev/blog/goodbye-background-fetch-hello-expo-background-task) — migration context, WorkManager vs JobScheduler

---

## Source Quality Assessment

**Confidence: medium**

The GitHub issues are primary sources and cross-corroborate each other well. The failure modes for missing manifest entries and headless app loader are documented by multiple independent reporters and confirmed by Expo maintainers. However:

- No single issue precisely describes the combination of "dev client + expo-router + service file import + process kill on startLocationUpdatesAsync call" — the findings are synthesized from adjacent issues
- The exact signal 9 kill (as opposed to SIGABRT or a Java exception) is not well-documented with clean attribution; signal 9 is an OOM kill or a direct `kill -9` from the OS, distinct from the SIGABRT crashes in #35439
- The most recent SDK versions (52/53) have fewer issues filed, possibly because the ecosystem has moved toward `expo-background-task` (WorkManager) for periodic tasks, with `startLocationUpdatesAsync` reserved for GPS tracking use cases
- Fast refresh / hot reload duplicate registration being safe (idempotent native layer) is inferred from architecture, not directly tested in a controlled experiment

---

## Open Questions

1. **Is signal 9 from OOM or from OS foreground service enforcement?** Signal 9 specifically means either OOM killer or a `kill -9` system call. The foreground service type violation on Android 14+ terminates the process via `ActivityManager.killBackgroundProcesses` which can appear as signal 9. This needs confirmation via `adb logcat -s ActivityManager` at the moment of the kill.

2. **Does the dev client's Metro connection activity prevent Android 14 from classifying the process as "truly backgrounded"?** This could explain why the timing of the kill is correlated with calling `startLocationUpdatesAsync` specifically rather than at app launch.

3. **Does the expo-router lazy evaluation of route modules affect when `_layout.tsx` imports execute?** expo-router uses Metro bundler's lazy loading for routes. If the service file import is tree-shaken or lazily evaluated, `defineTask` could execute after the bundle has been fully loaded but before the native task system checks for the registration. This needs testing with `console.log` before and after the `defineTask` call.

4. **Is there a version of expo-task-manager (or expo-location) where the headless app loader is correctly bundled in dev client builds?** The #9415 fix targeted SDK 39. There is no clear confirmation it holds for SDK 51+.

5. **Does `killServiceOnDestroy: false` cause the zombie service to hold a stale JS context across bundle reloads?** The service surviving a Metro bundle reload while holding references to the prior JS runtime is a plausible mechanism for the JSI context crash seen in #35439.

---

## Actionable Takeaways

### Immediate Diagnostics

1. **Run `adb logcat -s ActivityManager` during the crash.** This will confirm whether the process kill is an OOM event or a foreground service type violation. Look for lines like `Killing ... (adj ...)` or `Starting FGS with type location ... requires permissions`.

2. **Verify the manifest has `FOREGROUND_SERVICE_LOCATION` and `android:foregroundServiceType="location"`:**
   ```bash
   cd android && grep -r "foregroundServiceType" app/src/main/AndroidManifest.xml
   grep -r "FOREGROUND_SERVICE_LOCATION" app/src/main/AndroidManifest.xml
   ```
   If these are absent, the config plugin has not run or the native build is stale.

3. **Confirm `app.json` (or `app.config.js`) has both flags:**
   ```json
   ["expo-location", {
     "isAndroidBackgroundLocationEnabled": true,
     "isAndroidForegroundServiceEnabled": true
   }]
   ```
   Then run `npx expo prebuild --clean` and rebuild the dev client binary.

4. **Check for duplicate expo-task-manager installations:**
   ```bash
   find node_modules -name "package.json" -path "*/expo-task-manager/package.json" | xargs grep '"version"'
   ```
   If more than one version appears, add a `resolutions` (Yarn) or `overrides` (npm/pnpm) entry.

### Code-Level Fixes

5. **Call `startLocationUpdatesAsync` only while the app is visibly in the foreground.** Do not trigger it from an app state change listener reacting to `background`. Call it during the initial mount of the recording screen or on a user gesture.

6. **Guard `startLocationUpdatesAsync` with a check for task definition:**
   ```typescript
   const isDefined = await TaskManager.isTaskDefined(GPS_TASK_ID);
   if (!isDefined) {
     console.error('Task not defined — service file may not have been evaluated');
     return;
   }
   await Location.startLocationUpdatesAsync(GPS_TASK_ID, options);
   ```
   This surfaces the "task not defined" failure as a clean error rather than a crash.

7. **In dev client, add a `try/catch` around `startLocationUpdatesAsync` and log the full error:**
   ```typescript
   try {
     await Location.startLocationUpdatesAsync(GPS_TASK_ID, options);
   } catch (e) {
     console.error('startLocationUpdatesAsync failed:', JSON.stringify(e), e?.message);
   }
   ```
   A process kill (signal 9) will not be catchable, but any Java-level rejection (foreground service permission, headless loader failure) will surface as a rejected promise.

8. **Avoid fast-refresh during active location tasks in dev client.** Metro's fast refresh is not safe to trigger while `startLocationUpdatesAsync` is active on Android. Stop location updates before saving files if you must iterate quickly.

### Build Strategy

9. **Test background location features in a production-profile EAS build** (`eas build --profile production --platform android`) rather than a dev client build, to distinguish dev-client-specific crashes from genuine application bugs.

10. **If the dev client binary is old, rebuild it.** Dev client binaries do not receive config plugin changes via OTA. Any manifest change — including adding foreground service type — requires a new native build pushed via EAS or locally via `npx expo run:android`.
