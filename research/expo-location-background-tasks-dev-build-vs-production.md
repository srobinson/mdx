---
title: expo-location Background Tasks - Dev Build vs Production, iOS Simulator vs Device
type: research
tags: [expo, expo-location, background-tasks, ios, development-build, simulator, prebuild, eas-build]
summary: startLocationUpdatesAsync requires a native development build (not Expo Go), specific app.json config with isIosBackgroundLocationEnabled, a prebuild/rebuild after config changes, and a physical iOS device (not simulator).
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

`Location.startLocationUpdatesAsync` requires all four of the following to function correctly on iOS:

1. A **development build** (or production build) — not Expo Go
2. `isIosBackgroundLocationEnabled: true` in the expo-location plugin config in **app.json**
3. A **native rebuild** (prebuild + new binary) after any config plugin change
4. A **physical iOS device** — the iOS Simulator does not support background location

Miss any one of these and the feature either silently stops delivering updates, or crashes.

---

## Details

### 1. Expo Go vs Development Build

Background location is **not supported in Expo Go on iOS**. The official docs state explicitly:

> "iOS users require a development build (not supported in Expo Go)."

Expo Go ships with a fixed set of native libraries and a fixed Info.plist — it cannot carry the `UIBackgroundModes: location` entitlement for your specific app. The TaskManager docs note that "you can test TaskManager in Expo Go" but then defer to each library's docs. The expo-location docs override that: background location is an Expo Go hard no on iOS.

On Android, background foreground services are also unavailable in Expo Go. A development build is required there too.

**Development build** = a custom native binary built via EAS Build (or locally with `npx expo run:ios`) that includes your app's specific native modules and entitlements.

### 2. app.json Config: isIosBackgroundLocationEnabled

The expo-location config plugin does **not** enable background location by default. You must set:

```json
{
  "expo": {
    "plugins": [
      [
        "expo-location",
        {
          "isIosBackgroundLocationEnabled": true,
          "isAndroidBackgroundLocationEnabled": true
        }
      ]
    ]
  }
}
```

The plugin's `withLocation.ts` adds `'location'` to `UIBackgroundModes` in Info.plist only when `isIosBackgroundLocationEnabled` is `true`. Without this, iOS will not deliver background location events to the app (it terminates them silently — not a crash, just no callbacks).

On Android, `isAndroidBackgroundLocationEnabled: true` adds the `ACCESS_BACKGROUND_LOCATION` permission, which is required for Android 10+ background access and triggers Google Play review.

### 3. Prebuild and Rebuild Required After Config Changes

Config plugins modify native files (`Info.plist`, `AndroidManifest.xml`, entitlements) **only at prebuild time**, not at runtime. The sequence is:

```
app.json plugin config change
  → npx expo prebuild   (generates/updates ios/ and android/ native dirs)
  → rebuild native binary (EAS Build, or npx expo run:ios)
  → install new binary on device
```

If you add `expo-location` to app.json (or change its plugin options) but skip `npx expo prebuild` and rebuilding the app:

- The native binary does **not** have `UIBackgroundModes: location` in its Info.plist
- `startLocationUpdatesAsync` will register the task but iOS will never fire it in background
- On some SDK versions this can throw an error; on others it silently drops background events
- It does **not** necessarily produce a JavaScript-visible crash — it may appear to work in foreground but background updates simply never arrive

The only way to get config plugin changes into a running app is to build a new binary.

### 4. iOS Simulator Limitations

The iOS Simulator does **not** support background location. This is an Apple platform limitation, not an Expo limitation. Specifically:

- Background app execution is heavily restricted in the Simulator
- `startLocationUpdatesAsync` may appear to register without error in the Simulator
- Location updates will not arrive in the background on Simulator
- Testing background location requires a **physical iOS device** with the development build installed

The Simulator does support simulated foreground location (via the Debug menu in Simulator.app), so foreground `watchPositionAsync` works fine there. Background tasks do not.

### 5. What Happens if app.json Has expo-location But No Prebuild Was Run

Scenario: developer adds `expo-location` (or its background config) to app.json but is still running the old Expo Go build or an old development build binary.

| Situation | Behavior |
|-----------|----------|
| Expo Go, any config | Background location not available; calling `startLocationUpdatesAsync` may throw or silently fail |
| Old dev build, new app.json config added | Old binary doesn't have `UIBackgroundModes: location`; background callbacks never fire |
| Old dev build, `expo-location` was already in native build | May work if native entitlements were already present from a prior build |
| Fresh dev build from EAS with correct app.json | Works correctly on physical device |

A crash specifically from `startLocationUpdatesAsync` (as opposed to silent failure) typically comes from:
- Calling `startLocationUpdatesAsync` before defining the task with `TaskManager.defineTask` at module top-level scope
- Missing required permissions at runtime (calling without having requested "Always" permissions)
- Android TaskManager NullPointerException (known intermittent bug, GitHub issue #41663)

### 6. EAS Build vs Local Development

For background location support, both EAS Build and local development (`npx expo run:ios`) are viable. The distinction is:

**EAS Build (cloud):**
- Runs `expo prebuild` as part of its process — app.json config plugins are always applied
- Produces a `.ipa` or `.apk` installable on device
- Development builds from EAS include the `expo-dev-client` for hot reloading JS while keeping native binary stable
- If you change `isIosBackgroundLocationEnabled` in app.json, you must trigger a new EAS build — JS bundle updates via EAS Update do **not** apply native changes

**Local development (`npx expo run:ios`):**
- Also runs prebuild implicitly if `ios/` doesn't exist
- You must re-run `npx expo run:ios` (or `npx expo prebuild` + Xcode build) after any config plugin change
- Works on physical device via Xcode or `--device` flag
- Does not work on Simulator for background location testing

**Critical distinction**: EAS Update (OTA JS updates) cannot change Info.plist or native entitlements. Any change to `UIBackgroundModes` requires a full native rebuild via EAS Build or local Xcode.

### 7. defineTask Placement Requirement

Independent of the build environment, `TaskManager.defineTask` must be called at **module top level**, not inside a React component or lifecycle method:

```typescript
// CORRECT - top level of a module loaded at app startup
TaskManager.defineTask(LOCATION_TASK_NAME, ({ data, error }) => {
  // handle location data
});

// WRONG - inside component
useEffect(() => {
  TaskManager.defineTask(...); // will not work for background execution
}, []);
```

iOS launches the JS runtime without mounting UI when executing background tasks. If the task definition was never registered in global scope, the background handler has nothing to call.

---

## Sources

- Expo Location docs: https://docs.expo.dev/versions/latest/sdk/location/
- Expo TaskManager docs: https://docs.expo.dev/versions/latest/sdk/task-manager/
- Expo Development Builds intro: https://docs.expo.dev/develop/development-builds/introduction/
- Config Plugins intro: https://docs.expo.dev/config-plugins/introduction/
- CNG / Prebuild docs: https://docs.expo.dev/workflow/continuous-native-generation/
- expo-location plugin source (`withLocation.ts`): github.com/expo/expo/packages/expo-location/plugin/src/withLocation.ts
- GitHub issue #41663 (Android NullPointerException in startLocationUpdatesAsync)
- GitHub issue #35362 (task not executing until restart — permissions misconfiguration)
- Apple UIBackgroundModes location key: developer.apple.com InfoPlist reference

---

## Open Questions

- Does calling `startLocationUpdatesAsync` without `UIBackgroundModes: location` in Info.plist throw a catchable JS error, or silently fail? The Apple docs say the system terminates background updates — it likely surfaces as the task simply never firing rather than a thrown exception. Needs a direct reproduction test to confirm.
- Android behavior when `ACCESS_BACKGROUND_LOCATION` permission is absent but `startLocationUpdatesAsync` is called — does it throw or silently drop events?
- SDK 52+ permission handling changes (GitHub issue #33911 was closed): confirm whether `requestBackgroundPermissionsAsync` is the correct sole API or whether foreground permissions must be requested separately first.
