---
title: Expo Dev Build Setup for Android Physical Device on Apple Silicon Mac
type: research
tags: [expo, react-native, android, apple-silicon, m2, dev-build, rnmapbox, physical-device]
summary: Complete setup guide for building and running an Expo dev build (with custom native modules like @rnmapbox/maps) on an Android physical device from a Mac M2
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

To run an Expo dev build with custom native modules (like `@rnmapbox/maps`) on a physical Android device from a Mac M2, you need: Android Studio, JDK 17 (Zulu), Android SDK 35, `expo-dev-client` installed, and either a local build via `npx expo run:android` or a cloud build via EAS. The fastest path for a first build is EAS (no local toolchain required), then switch to local builds for iteration.

---

## Details

### 1. What to Install

| Tool | Version | How |
|------|---------|-----|
| Node.js | 22.11.0+ | `brew install node` or nvm |
| Watchman | latest | `brew install watchman` |
| JDK | 17 (Zulu) | `brew install --cask zulu@17` |
| Android Studio | latest stable | Download from developer.android.com/studio |
| Android SDK Platform | 35 (Android 15) | Via Android Studio SDK Manager |
| Android SDK Build-Tools | 36.0.0+ | Via Android Studio SDK Manager |
| Android SDK Command-line Tools | latest | Via Android Studio SDK Manager |
| EAS CLI (optional) | latest | `npm install -g eas-cli` |

**Why Zulu JDK 17?** The Azul Zulu distribution provides a native ARM64 build for Apple Silicon, resulting in faster Gradle builds compared to Intel-emulated JDKs. JDK 17 is the version the React Native / Expo toolchain targets.

### 2. Android Studio Configuration for Apple Silicon

When installing the Android SDK for **physical device only** (no emulator), you can skip emulator-related components. In SDK Manager:

- **SDK Platforms tab**: Install Android 15 (API 35) - check "Android SDK Platform 35" and "Sources for Android 35". Skip system images (those are for emulators).
- **SDK Tools tab**: Check:
  - Android SDK Build-Tools 36.0.0
  - Android SDK Command-line Tools (latest)
  - Android SDK Platform-Tools (adb)
  - (Skip Android Emulator if not needed)

No ARM-specific gotchas for the SDK itself. The SDK tools run fine under Rosetta or natively. The Zulu JDK is the main Apple Silicon optimization.

### 3. Environment Variables

Add to `~/.zshrc` or `~/.zprofile`:

```bash
export JAVA_HOME=/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/emulator
```

Then: `source ~/.zshrc`

Verify:
```bash
java -version          # should show OpenJDK 17 (Zulu)
echo $ANDROID_HOME     # should show path to sdk
adb devices            # should list connected devices
```

### 4. Connecting an Android Physical Device

#### USB Debugging (simplest, most reliable)

1. On phone: Settings > About Phone > tap "Build Number" 7 times to unlock Developer Options
2. Settings > Developer Options > enable "USB Debugging"
3. Connect USB cable to Mac
4. Accept the "Allow USB Debugging" prompt on phone
5. Verify: `adb devices` — device should appear as "device" (not "unauthorized")

#### Wireless Debugging (Android 11+)

1. Enable Developer Options (same as above)
2. Settings > Developer Options > enable "Wireless Debugging"
3. Tap "Pair device with pairing code" — note the IP:port and 6-digit code
4. On Mac: `adb pair <ip>:<pairing-port>` then enter the code
5. After pairing, tap "Wireless Debugging" to find the connection port
6. `adb connect <ip>:<connection-port>`
7. Verify: `adb devices`

**Note**: Corporate/guest Wi-Fi networks often block mDNS/p2p traffic. If wireless pairing fails, use USB.

### 5. Dev Build Workflow for Custom Native Modules

`@rnmapbox/maps` requires native code, so Expo Go will not work. You need a **development build** — a debug APK that includes `expo-dev-client` and your native modules.

#### Install expo-dev-client

```bash
npx expo install expo-dev-client
```

#### Configure @rnmapbox/maps plugin in app.json / app.config.js

```json
{
  "expo": {
    "plugins": [
      [
        "@rnmapbox/maps",
        {
          "RNMapboxMapsVersion": "11.18.2"
        }
      ]
    ]
  }
}
```

The Mapbox access token can be supplied at runtime (not baked into the binary) if fetched from a backend. If you must embed it, use EAS Secrets rather than `EXPO_PUBLIC_` (which exposes it in the binary).

#### Path A: Local Build (requires Android Studio setup above)

```bash
npx expo run:android
```

This runs `expo prebuild` (generates the `android/` directory), then invokes Gradle to build and install the APK directly onto the connected device. Subsequent JS-only changes use `npx expo start` without rebuilding.

When to rebuild: whenever you add/modify native modules or plugins.

#### Path B: EAS Cloud Build (no local toolchain needed)

```bash
eas build:configure          # creates eas.json
eas build --platform android --profile development
```

In `eas.json`, confirm the development profile has `developmentClient: true`:

```json
{
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    }
  }
}
```

After the cloud build completes, install the APK on device via:
- QR code from the EAS dashboard "Install" button (downloads APK to phone, tap to install)
- Expo Orbit app (menu bar app that pushes builds directly to connected devices)

Then start the local JS bundler:
```bash
npx expo start
```

Press `a` to open on the connected Android device.

### 6. Fastest Path to First Run

For a first-time setup, EAS cloud builds eliminate local toolchain debugging:

1. `npm install -g eas-cli && eas login`
2. `npx expo install expo-dev-client`
3. Configure `@rnmapbox/maps` plugin in `app.json`
4. `eas build:configure`
5. `eas build --platform android --profile development`
6. Install APK on phone via QR code from dashboard
7. `npx expo start` — the dev client on the phone connects to your local Metro bundler

Switch to `npx expo run:android` (local builds) once toolchain is verified, for faster iteration without cloud build queue times.

### 7. Common Pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `adb: command not found` | PATH missing platform-tools | Add `$ANDROID_HOME/platform-tools` to PATH |
| `ANDROID_HOME not set` | Missing env var | Add to `~/.zshrc` and reload shell |
| Gradle fails: wrong JDK | System JDK not 17 | Set `JAVA_HOME` to Zulu 17 path |
| Device shows "unauthorized" | USB debugging prompt not accepted | Re-plug USB, accept prompt on phone |
| Build fails: SDK not found | SDK Platform 35 not installed | Install via Android Studio SDK Manager |
| `@rnmapbox/maps` not found at runtime | Token not provided | Pass `accessToken` prop to `<MapboxGL.MapView>` |
| Mapbox SDK download fails during build | Missing Mapbox Maven credentials | Set `MAPBOX_DOWNLOADS_TOKEN` env var (secret downloads token, not public token) |
| Metro can't connect to device wirelessly | mDNS blocked on network | Use USB, or run `adb reverse tcp:8081 tcp:8081` |
| `npx expo prebuild` conflicts | Existing `android/` directory with manual changes | Either commit and use bare workflow, or delete and regenerate |

**Mapbox credentials gotcha**: `@rnmapbox/maps` requires a Mapbox secret token (starting with `sk.`) during the build phase to download the SDK from Mapbox's Maven registry. This is separate from the public access token used at runtime. Set it as `MAPBOX_DOWNLOADS_TOKEN` in EAS Secrets or in `~/.gradle/gradle.properties` for local builds.

---

## Sources

- https://docs.expo.dev/get-started/set-up-your-environment/ (Android + physical device + dev build + local)
- https://reactnative.dev/docs/set-up-your-environment (Mac M2 Android setup)
- https://docs.expo.dev/guides/local-app-development/
- https://docs.expo.dev/develop/development-builds/create-a-build/
- https://docs.expo.dev/tutorial/eas/android-development-build/
- https://docs.expo.dev/build/setup/
- https://developer.android.com/tools/adb (wireless ADB)
- https://github.com/rnmapbox/maps (plugin/install.md)

---

## Open Questions

- Whether `@rnmapbox/maps` v11 has specific minimum Android SDK requirements (minSdkVersion) beyond what Expo sets — check `android/install.md` in the rnmapbox repo.
- EAS Build free tier limits (build minutes per month) may matter if iterating frequently on native changes.
- Whether this project already has an `android/` directory (bare workflow) or is managed (no `android/` dir). If bare workflow, `npx expo run:android` skips prebuild.
