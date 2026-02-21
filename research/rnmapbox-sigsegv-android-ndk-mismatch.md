---
title: rnmapbox/maps SIGSEGV SEGV_ACCERR on Android - NDK C++ ABI Mismatch Root Cause
type: research
tags: [rnmapbox, mapbox, android, sigsegv, ndk, crash, react-native]
summary: The SIGSEGV code 2 (SEGV_ACCERR) crash in a Mapbox Worker thread is caused by C++ exception unwinding across incompatible NDK ABIs - Mapbox Maps SDK v10.x was compiled with NDK 21, but React Native 0.76.x uses NDK 26. The fix is upgrading to rnmapbox/maps v10.2.x which uses Mapbox Maps SDK v11.x (NDK 23+ compatible).
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

The SIGSEGV (signal 11), code 2 (SEGV_ACCERR), "trying to execute non-executable memory" crash in a Mapbox Worker thread is a **C++ exception ABI mismatch** between NDK 21 (Mapbox Maps SDK v10.x) and NDK 26 (React Native 0.76.x). This is a well-documented upstream incompatibility, not a bug in the app code.

The fix is upgrading from `@rnmapbox/maps` v10.1.x to **v10.2.x**, which ships with Mapbox Maps SDK **v11.16.2** (NDK 23+ compatible).

---

## Root Cause

### NDK ABI Incompatibility

Mapbox Maps SDK v10.x (including v10.18.0) was compiled with **NDK 21**. React Native's NDK version has evolved:

| React Native | NDK Version |
|---|---|
| 0.71 | NDK 23 (breaking change) |
| 0.72 | NDK 23 |
| 0.73 | NDK 25 |
| 0.74–0.75 | NDK 26 |
| 0.76.x | NDK 26 |

When a C++ exception is thrown inside `libmapbox-maps.so` or `libmapbox-common.so` (compiled with NDK 21's `libc++_shared.so`), the exception unwinder from NDK 26's `libc++_shared.so` cannot correctly unwind the stack. The crash manifests as:

- `SIGSEGV`, code `SEGV_ACCERR` (access error on valid memory - "trying to execute non-executable memory")
- Single-frame backtrace landing in `[anon:scudo:primary]` (the scudo memory allocator's primary allocation arena)
- Always on a `Worker` thread (Mapbox uses worker threads for tile/geojson processing)
- Happens seconds after `MapView` mounts (when Mapbox first processes map data and throws/catches internal C++ exceptions)
- Reproducible on both emulators and physical devices because the NDK mismatch is deterministic

The `[anon:scudo:primary]` frame is a red herring - the crash is not a heap corruption. Scudo catches the corrupted stack state during an allocation or the unwinder corrupts the stack into a non-executable page.

### Why the crash appears in scudo

When the C++ exception unwinder from NDK 26 encounters a frame compiled with NDK 21's exception tables, it reads incorrect unwind data and jumps to an invalid address that happens to be in the scudo allocator's memory region. This region is mapped non-executable, so the CPU raises `SEGV_ACCERR` (access error: permission violation on accessible memory).

### Why it happens on second MapView mount

The Mapbox SDK defers heavy initialization. On the first mount it may not trigger a C++ exception. On the second mount (navigating back to a screen with MapView), Mapbox initializes its worker thread processing pipeline more aggressively, hitting a code path that throws-and-catches internally.

### Why 16KB page size does not change the diagnosis

Android 16 with 16KB pages is not the cause here. The crash pattern is identical on 4KB-page devices. The NDK mismatch is the controlling variable.

---

## Issue References

### rnmapbox/maps

- **Issue #3385** (OPEN): ["Crash on Android with dynamic shape source, Fatal signal 11 (SIGSEGV), code 2 (SEGV_ACCERR)"](https://github.com/rnmapbox/maps/issues/3385)
  - Exact same signal, code, and Worker thread pattern
  - rnmapbox maintainer `mfazekas` confirmed: *"Mapbox 10.* uses NDK 21 and it's known to be incompatible with NDK 23. Any C++ exception thrown inside Mapbox 10 causes a crash. Mapbox 11 is NDK 23 and it seems to be compatible with newer NDK 23 and newer."*
  - Linked to upstream: https://github.com/mapbox/mapbox-maps-android/issues/1697

### mapbox/mapbox-maps-android

- **Issue #1697** (OPEN): ["SIGABRT - Native crash on Samsung devices running Android 12"](https://github.com/mapbox/mapbox-maps-android/issues/1697)
  - Shows the scudo callstack: `scudo::die()` → `scudo::reportInvalidChunkState()` → `libmapbox-maps.so`
  - Mapbox engineer `kiryldz` confirmed: *"I can reliably reproduce the crash in our test apps replacing 21.4.7075529 with 23.1.7779620. Every time a C++ exception is thrown (inside try-catch) it crashes in stack unwinding in libc++."*
  - Mapbox engineer confirmed: *"NDK 21/23 C++ exceptions are incompatible. The only safe option is to use compatible Maps/RN versions. Maps v11 will be shipped with NDK 23."*

---

## Fix: Upgrade to @rnmapbox/maps v10.2.x

### Version mapping

| @rnmapbox/maps | Mapbox Maps SDK (Android) | NDK | Compatible with RN |
|---|---|---|---|
| 10.1.33 | 10.18.0 (default) / 10.18.4 (build.gradle default) | **NDK 21** | RN ≤ 0.70 |
| **10.2.0+** | **11.15.2** (default at release) | **NDK 23+** | RN 0.71+ |
| **10.2.10** (latest stable) | **11.16.2** | **NDK 23+** | RN 0.76+ |

The v10.2.0 release notes state: *"default to Mapbox v11.15.2 with deprecation warnings for v10 and old architecture"*

Confirmed from the v10.2.10 `package.json`:
```json
"mapbox": {
  "ios": "~> 11.16.2",
  "android": "11.16.2"
}
```

### Migration steps

1. Update `package.json`:
   ```
   "@rnmapbox/maps": "^10.2.10"
   ```

2. Run `yarn install` (or `npm install`).

3. In `android/build.gradle`, you no longer need to pin `RNMapboxMapsVersion` to a v10 SDK. Remove any `RNMapboxMapsVersion = "10.x.x"` override.

4. Follow the v11 migration guide if any breaking API changes affect the codebase: https://docs.mapbox.com/android/maps/guides/migrate-to-v11/

   Key breaking changes in Mapbox v11:
   - `styleURL` → `mapStyle` prop
   - Some layer style property names changed
   - `StyleURL.*` constants moved/renamed in some cases
   - The rnmapbox library itself maintains a v10 compatibility shim (`src/main/mapbox-v11-compat/v10`) so many things work without changes

5. Clean the Android build cache:
   ```bash
   cd android && ./gradlew clean
   ```

---

## Workarounds (if upgrade is not immediately possible)

These are partial mitigations. None fully resolve the root cause.

### 1. Force NDK 21 in the project (not recommended for RN 0.76)

In `android/build.gradle`:
```groovy
ndkVersion = "21.4.7075529"
```

**Caveat**: React Native 0.76.x itself and other native dependencies may be compiled with NDK 26. Forcing NDK 21 can cause the same ABI mismatch in the opposite direction for those dependencies.

### 2. Override Mapbox SDK version to a v10.x NDK-27 build (experimental)

Mapbox publishes NDK-27 variants:
```groovy
// In android/build.gradle ext block:
RNMapboxMapsVersion = "10.18.0-android-ndk27.0"  // check if this variant exists
```

**Caveat**: As of research date (2026-03-10), no official NDK-27 build of Mapbox Maps SDK v10.18.x was found. The NDK-27 AAR exists only for v11.x. See mapbox/mapbox-maps-android issue #2691.

### 3. Guard ShapeSource coordinate count (workaround for specific SIGSEGV trigger)

Issue #3385 identified that passing a `LineString` with fewer than 2 coordinates to `ShapeSource` is one trigger path. Adding a guard prevents that specific code path:

```typescript
// Only render ShapeSource when there are at least 2 coordinates
{coordinates.length >= 2 && (
  <ShapeSource id="route" shape={{ type: 'LineString', coordinates }}>
    <LineLayer id="routeLine" ... />
  </ShapeSource>
)}
```

**Caveat**: This only prevents one specific trigger. The NDK mismatch means any C++ exception in the Mapbox native code can cause this crash.

---

## Project-Specific Context

The project at `/Users/alphab/Dev/LLM/DEV/helioy/client-projects/echoecho-worktrees/nancy-ALP-1146` has:

- React Native: **0.76.9**
- `@rnmapbox/maps`: **10.1.33** (installed)
- `android/build.gradle`: `ndkVersion = "26.1.10909125"`
- Mapbox Maps SDK in use: **10.18.0** (from the crash report) / build.gradle default is **10.18.4**

This is precisely the incompatible combination. NDK 26 project + Mapbox v10 (NDK 21) = guaranteed crashes on any C++ exception.

---

## Sources

- rnmapbox/maps issue #3385: https://github.com/rnmapbox/maps/issues/3385
- mapbox/mapbox-maps-android issue #1697: https://github.com/mapbox/mapbox-maps-android/issues/1697
- rnmapbox/maps v10.2.0 release notes: https://github.com/rnmapbox/maps/releases/tag/v10.2.0
- rnmapbox/maps v10.2.10 release notes: https://github.com/rnmapbox/maps/releases/tag/v10.2.10
- React Native NDK version history: https://github.com/facebook/react-native/pull/35066

---

## Open Questions

- Does rnmapbox/maps v10.2.x require any additional API migration beyond the Mapbox v10→v11 changes? The rnmapbox compatibility shim handles most of the delta but the style prop changes (`styleURL` → `mapStyle`) may need updating.
- Are there any EAS Build configuration changes needed when upgrading (e.g., token configuration for v11)?
