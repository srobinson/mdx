---
title: expo-location startLocationUpdatesAsync crash patterns and known issues
type: research
tags: [expo, expo-location, expo-task-manager, expo-battery, ios, android, background-location, sdk50, sdk51, sdk52]
summary: Comprehensive crash patterns, native throw conditions, simulator behavior, double-registration behavior, SDK 50/51/52 regressions, and defineTask timing issues for expo-location startLocationUpdatesAsync
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

`startLocationUpdatesAsync` does not produce native crashes from double-calling the same task — the native layer on both iOS (EXTaskService.m) and Android (TaskService.java) simply updates options when the task already exists. The real crash vectors are: missing `UIBackgroundModes`, `RCTCallableJSModules` nil on hot-reload (iOS simulator), ClassNotFound on SDK 52 Android, and the JS-side "task not defined" warning that auto-unregisters the task. Expo Go cannot run background tasks. Physical iOS devices with dev builds are the correct test target.

---

## Details

### 1. Native crash causes (not JS exceptions)

**iOS: NSInternalInconsistencyException on hot reload (simulator)**
- Issue [#17081](https://github.com/expo/expo/issues/17081): Crash triggered when a location update fires *after* the app is reloaded via the RN debug "Reload" button.
- Exception: `NSInternalInconsistencyException: "Error when sending event: Expo.locationChanged ... RCTCallableJSModules is not set."`
- Root cause: After a JS reload, the old native `EXReactNativeEventEmitter` tries to fire events into a stale/nil JS runtime. This is a simulator-only (or dev-client fast-refresh) issue.
- Classification: **EXC_CRASH (SIGABRT)** — true native crash.

**iOS: `startLocationUpdatesAsync` throws as JS-rejected promise (not a crash) when:**
- `UIBackgroundModes` does not include `"location"` → throws `LocationUpdatesUnavailable` ("Background location has not been configured...")
- `CLLocationManager.significantLocationChangeMonitoringAvailable()` returns false (uncommon edge case)
- Foreground location permissions not granted → throws `DeniedForegroundLocationPermission`
- Source: `LocationModule.swift` and `LocationExceptions.swift`

**Android SDK 52: Hard crash at startup / on first location update**
- Issue [#33041](https://github.com/expo/expo/issues/33041), [#33573](https://github.com/expo/expo/issues/33573): `expo-location` 18.0.1 depends on `io.nlopez.smartlocation:library:3.3.3` which references `android.support.v4.app.ActivityCompat` (legacy support library, not AndroidX). This class does not exist in modern builds → `NoClassDefFoundError` → **hard native crash**.
- SDK 51 was fine because Jetifier rewrote the reference to `androidx.core.app.ActivityCompat`. SDK 52 broke this.
- Fix: upgrade to a patched expo-location version or add Jetifier configuration.

**Android: JSI interop crash on force-stop with background task active**
- Issue [#28728](https://github.com/expo/expo/issues/28728): When the app is force-stopped while a background location task is running, the task service is respawned but the JSI module context is gone → `IllegalArgumentException: The module wasn't created! You can't access the app context.`
- Only manifests in standalone/production builds, not dev builds.
- Correlated with having additional Expo modules installed (expo-notifications, expo-updates, etc. — the more modules, the more likely).

### 2. iOS simulator vs. physical device vs. Expo Go

| Environment | startLocationUpdatesAsync works? | Notes |
|---|---|---|
| iOS Simulator | **Yes, but limited** | Background mode fires are unreliable. Hot-reload causes the RCTCallableJSModules crash (#17081). Simulated location works for foreground. |
| Physical iOS device, dev build | **Yes** | First-launch issue (#26373) on SDK 49: task doesn't execute on very first install until app is force-quit and relaunched once. Fixed or not reproducible in SDK 52. |
| Expo Go (iOS) | **No** | TaskManager does not support background execution in Expo Go on iOS. `isAvailableAsync()` returns false. |
| Expo Go (Android) | **No** | TaskManager is completely unavailable. |
| Physical Android, dev build | Generally works but see SDK 51/52 regressions below. |

**Expo Go limitation** (from docs): "You must use a development build to use background location since it is not supported in the Expo Go app."

### 3. Double-calling startLocationUpdatesAsync (task already registered)

**Does not crash.** Both native implementations explicitly handle this case as an update:

iOS (`EXTaskService.m`):
```objc
if (task && [task.consumer isMemberOfClass:unversionedConsumerClass]) {
  // Task already exists. Let's just update its options.
  [task setOptions:options];
  if ([task.consumer respondsToSelector:@selector(setOptions:)]) {
    [task.consumer setOptions:options];
  }
}
```

Android (`TaskService.java`):
```java
if (task != null && unversionedConsumerClass != null
    && unversionedConsumerClass.isInstance(task.getConsumer())) {
  // Task already exists. Let's just update its options.
  task.setOptions(options);
  task.getConsumer().setOptions(options);
}
```

Calling `startLocationUpdatesAsync` twice with the same task name is therefore **idempotent** — it updates options and does not double-register or crash. Use `hasStartedLocationUpdatesAsync(taskName)` to guard if you need to avoid the options-update side effect.

### 4. SDK 50/51/52 known regressions

**SDK 51 (Android):**
- Issues [#29557](https://github.com/expo/expo/issues/29557), [#29558](https://github.com/expo/expo/issues/29558): `expo-task-manager` foreground and background tasks stopped working after SDK 50→51 upgrade on Android. Both issues were filed against managed workflow / Expo Go. Confirmed not an issue in development builds with correct permissions. Root cause appears to be a permission manifest change.
- Issue [#28959](https://github.com/expo/expo/issues/28959): Location task callback receives no updates on Android (SDK 51) even though the task is registered.

**SDK 52 (Android):**
- Issue [#33041](https://github.com/expo/expo/issues/33041): Hard crash due to `android.support.v4.app.ActivityCompat` missing (see above).
- Issue [#33573](https://github.com/expo/expo/issues/33573): Same root cause, `ActivityCompat` ClassNotFound.

**SDK 49 (iOS):**
- Issue [#26373](https://github.com/expo/expo/issues/26373) — OPEN as of research date: First-launch silent failure on physical iOS device. Task is registered, native layer logs `EXTaskService: Executing task '...'` but the JS executor never fires. Second launch after force-quit works correctly. Assigned to `behenate` (Expo engineer), no resolution noted.

**SDK 52 (iOS, dev build):**
- Issue [#35362](https://github.com/expo/expo/issues/35362): Same first-launch silent failure pattern persists in SDK 52 (`expo-location` 18.0.7, `expo-task-manager` 12.0.5). Native logs show task executing but JS callback never invoked on fresh install. Works after one force-quit cycle.

### 5. TaskManager.defineTask timing and module load order

**The invariant:** `defineTask` must be called at module evaluation time (top-level of the entry file), not inside React lifecycle methods or lazy-loaded modules.

**Why this matters:**
When the app is woken in the background for a location event, React Native spins up a minimal JS environment — no views, no component lifecycle. Only top-level module evaluation runs. If `defineTask` was inside a component, the Map of defined tasks is empty when the native task fires.

**What happens on mismatch** (from `TaskManager.ts` source):
```typescript
console.warn(
  `TaskManager: Execution of "${taskName}" was requested but looks like it is not defined.
   Available tasks: [${[...tasks.keys()].join(', ')}].
   Make sure that "TaskManager.defineTask" is called during initialization phase.`
);
// Auto-unregisters the task
await ExpoTaskManager.notifyTaskFinishedAsync(taskName, { eventId, result });
await ExpoTaskManager.unregisterTaskAsync(taskName);
```

This is **not a crash** — it is a `console.warn` + silent auto-unregistration. After this, the task is gone from the registry and future location events will not fire it.

**Dev client / hot reload gotcha:**
- Issue [#6619](https://github.com/expo/expo/issues/6619): After saving changes in a dev client, the JS bundle reloads but the native task service remains registered. On next location event, the JS side may briefly lack the task definition (the warn fires) and the task self-unregisters. This is why the task appears to "stop working after a hot reload."
- Pattern: `defineTask` at module top level in a dedicated `tasks.ts` file (not `App.tsx`) imported before any component that calls `startLocationUpdatesAsync`.

**Production vs. dev client:**
- In production, the bundle is fully evaluated before any UI is shown, so load order issues are rare.
- In dev client, Fast Refresh replaces only modified modules. If the tasks file is not modified, its top-level code does not re-run, but the native task registration persists. The task definition Map in JS is re-populated from the still-loaded module. Generally safe if tasks are in a separate module.

### 6. expo-battery getBatteryLevelAsync on iOS simulator

**Does not crash.** Returns `-1` gracefully.

From `Battery.ts` source:
```typescript
export async function getBatteryLevelAsync(): Promise<number> {
  if (!ExpoBattery.getBatteryLevelAsync) {
    return -1;
  }
  return await ExpoBattery.getBatteryLevelAsync();
}
```

`isAvailableAsync()` checks `ExpoBattery.isSupported` which is `false` on iOS simulators. But `getBatteryLevelAsync` itself guards with a null check and returns `-1` rather than throwing. Event listeners (`addBatteryLevelListener`) will simply never fire on simulator.

**Correct guard pattern:**
```typescript
const available = await Battery.isAvailableAsync();
if (available) {
  const level = await Battery.getBatteryLevelAsync();
}
```

---

## Sources

- [expo/expo #6017](https://github.com/expo/expo/issues/6017) — defineTask + startLocationUpdatesAsync task crash and unregistering (Android, SDK 35)
- [expo/expo #6619](https://github.com/expo/expo/issues/6619) — defineTask not in global scope error after saving changes
- [expo/expo #7975](https://github.com/expo/expo/issues/7975) — "Task has been executed but looks like it is not defined" (iOS)
- [expo/expo #17081](https://github.com/expo/expo/issues/17081) — NSInternalInconsistencyException crash on iOS simulator after hot reload
- [expo/expo #26373](https://github.com/expo/expo/issues/26373) — OPEN: startLocationUpdatesAsync not initiating on first launch (iOS, SDK 49)
- [expo/expo #28728](https://github.com/expo/expo/issues/28728) — Android crash on force-stop with background task active
- [expo/expo #29557](https://github.com/expo/expo/issues/29557) / [#29558](https://github.com/expo/expo/issues/29558) — expo-task-manager broken after SDK 50→51 upgrade (Android)
- [expo/expo #33041](https://github.com/expo/expo/issues/33041) — SDK 52 Android crash: ActivityCompat ClassNotFound
- [expo/expo #33573](https://github.com/expo/expo/issues/33573) — SDK 52 Android crash: same root cause
- [expo/expo #35362](https://github.com/expo/expo/issues/35362) — SDK 52 iOS: task not executed until restart (fresh install)
- [expo-location LocationModule.swift](https://github.com/expo/expo/blob/main/packages/expo-location/ios/LocationModule.swift) — iOS startLocationUpdatesAsync implementation
- [expo-location LocationExceptions.swift](https://github.com/expo/expo/blob/main/packages/expo-location/ios/LocationExceptions.swift) — iOS exception types
- [expo-location LocationModule.kt](https://github.com/expo/expo/blob/main/packages/expo-location/android/src/main/java/expo/modules/location/LocationModule.kt) — Android startLocationUpdatesAsync implementation
- [expo-task-manager TaskManager.ts](https://github.com/expo/expo/blob/main/packages/expo-task-manager/src/TaskManager.ts) — JS task registry and auto-unregister logic
- [expo-task-manager EXTaskService.m](https://github.com/expo/expo/blob/main/packages/expo-task-manager/ios/EXTaskManager/EXTaskService.m) — iOS double-registration behavior
- [expo-task-manager TaskService.java](https://github.com/expo/expo/blob/main/packages/expo-task-manager/android/src/main/java/expo/modules/taskManager/TaskService.java) — Android double-registration behavior
- [expo-battery Battery.ts](https://github.com/expo/expo/blob/main/packages/expo-battery/src/Battery.ts) — getBatteryLevelAsync implementation
- [Expo Location docs](https://docs.expo.dev/versions/latest/sdk/location/)
- [Expo Battery docs](https://docs.expo.dev/versions/latest/sdk/battery/)

## Open Questions

- Issue #26373 (iOS first-launch silent failure) remains open — is it fixed in SDK 52 or does #35362 confirm it persists?
- The SDK 52 Android ActivityCompat crash: which patch version of expo-location resolved this?
- Is there a hot-reload-safe pattern for tasks that does not require a full app restart after a JS bundle change?
