---
title: EchoEcho Navigator — Mobile Engineering Code Review
type: sessions
tags: [mobile, react-native, expo, gps, haptics, audio, pdr, eas, build-config, accessibility]
summary: Full mobile engineering audit of both admin and student apps; 27 issues filed as children of ALP-1011
status: active
source: mobile-engineer
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Performed a comprehensive mobile engineering code review of the EchoEcho Navigator monorepo (React Native 0.76.9, Expo SDK 52, Expo Router v4). The codebase targets two audiences: sighted admin users who record accessible routes, and blind/low-vision (BLV) students who navigate them. All issues were filed as Linear children of ALP-1011, tagged `mobile-engineer`, assigned to team Alphabio, project echoecho.

**27 issues filed** across both apps. Severity breakdown:
- P1 Urgent: 1 (non-existent npm package blocks student build)
- P2 High: 11 (memory leaks, GPS safety, race conditions, OTA misconfiguration)
- P3 Normal: 12 (platform API gaps, logic bugs, architectural debt)
- P4 Low: 3 (cleanup, code duplication)

## Critical Finding

**ALP-1089 (P1)**: `react-native-haptic-patterns@^1.0.0` is listed in `apps/student/package.json` and imported at the top of `useHapticEngine.ts`. The package does not exist on the npm registry. The student app cannot be built until this is replaced. The likely intent is iOS Core Haptics via a native module; the correct approach is either a custom native module or expo-haptics with pattern timing implemented in JS.

## Platform-Specific Notes

### iOS
- `expo-battery` `isLowPowerModeEnabledAsync()` is iOS-only. The student app calls this without the `Platform.OS === 'ios'` guard present in admin. Filed as ALP-1091.
- `Audio.setAudioModeAsync({ playsInSilentModeIOS: true })` is correctly applied but `shouldDuckAndroid` is incorrectly set to `false` in `useAudioEngine.ts` — Android navigation audio will be overridden by music playback. Filed as ALP-1095.
- iOS VoiceOver conflicts with `TapGestureHandler numberOfTaps={3}` wrapping the entire Stack. RNGH intercepts accessibility swipe gestures on iOS 16+. Filed as ALP-1097.
- `NSLocationAlwaysUsageDescription` missing from student `app.json` while background location task exists. Filed as ALP-1085.

### Android
- Deprecated `READ_EXTERNAL_STORAGE` / `WRITE_EXTERNAL_STORAGE` permissions in admin `app.json` cause Play Store warnings on API 33+. Filed as ALP-1086.
- PDR axis normalization (`normalizeAccel`) correctly inverts X/Y on Android per expo-sensors issue #19229.
- Admin GPS background task: `useRecordingStore.getState()` in headless Android TaskManager context returns empty store. The buffer write is inside the store guard so it silently drops points. Filed as ALP-1090.
- `shouldDuckAndroid: false` in audio session means Android navigation announcements will not duck media. Filed as ALP-1095.

## Build Configuration

### EAS (eas.json)
- All build profiles (preview iOS/Android, production iOS/Android) are missing the `channel` field. OTA updates via `eas update` cannot be targeted to the correct build without channel assignment. Filed as ALP-1083.
- Preview Android profiles use `gradleCommand: ":app:assembleRelease"` producing an APK instead of an AAB. Internal testing tracks on Play Store require AAB. Removing `gradleCommand` lets EAS default to AAB. Filed as ALP-1084.

### app.json (student)
- Redundant `autolinking.exclude` block lists admin-only packages (e.g. `@rnmapbox/maps`). These packages are not in student `package.json` so the block is a no-op and misleading. Filed as ALP-1087.
- Conflicting location permission strings between `infoPlist` and the `expo-location` plugin config block. iOS uses whichever appears last; ordering is non-deterministic across prebuild runs. Filed as ALP-1085.

### Metro
- Both `metro.config.js` files correctly configure `watchFolders`, `nodeModulesPaths`, and `blockList` to isolate admin-only modules from the student bundle. No issues.

## GPS and Navigation Safety

For a BLV user, GPS bugs are safety-critical.

**ALP-1062 (P2)**: `useGpsNavigation.ts` `startTracking()` is `async`. It assigns `subscriptionRef.current` after `await Location.watchPositionAsync()`. If the component unmounts during the await, cleanup runs before the assignment, and the subscription is never removed. The location stream continues firing callbacks into a dead component indefinitely.

**Fix pattern**: Capture subscription in a local variable, check `isMounted` flag before assigning to ref, clean up if already unmounted.

**ALP-1063 (P2)**: `usePdrNavigation.ts` reanchor uses flat-earth distance (`Math.sqrt(dLat**2 + dLng**2) * 111_320`) instead of haversine. At TSBVI latitude (~30°N), the cosine correction for longitude introduces ~13% error. The 10m snap threshold becomes ~11.3m effective, causing premature snapping on some re-anchor events.

**ALP-1064 (P2)**: PDR `reanchor()` smooth interpolation creates a `setInterval` stored in a local `timer` variable (not a ref). `deactivate()` cannot cancel this timer. After GPS loss and recovery while walking, the interpolation continues running even after deactivation — injecting phantom position updates into the GPS service.

**ALP-1065 (P2)**: PDR `activate()` sets `activeRef.current = true` before subscriptions are registered. A concurrent call to `deactivate()` between the flag set and the subscription setup would clear the flag without removing non-existent subscriptions, then a second `activate()` would create duplicate subscriptions.

## Memory Leaks (Post-Navigation)

**ALP-1066 (P2)**: `useOffRouteDetection` creates three timers (`correctiveTimerRef` setInterval every 5s, `hysteresisTimerRef`, `stationaryTimerRef`) but has no cleanup `useEffect` with a return function. When the navigation screen unmounts, all three continue running. The corrective interval calls `AccessibilityInfo.announceForAccessibility()` into the void every 5 seconds, consuming battery and degrading VoiceOver on the home screen.

**ALP-1096 (P2)**: `useAudioEngine` loads `Audio.Sound` objects (`soundRef.current`) but has no cleanup `useEffect`. Loaded sounds are never unloaded on unmount — audio buffer memory leaks accumulate across navigation sessions.

## Race Conditions and UI Logic

**ALP-1092 (P3)**: `useSttDestination.ts` `rejectDestination()` sets `setSttState('listening')` then calls `void startListening()`. If `startListening` fails (microphone permission denied), the state remains "listening" while no listener is active. The student sees "Listening..." with no recovery path.

**ALP-1093 (P3)**: `navigate/[routeId].tsx` `ProgressCard` renders "Waypoint N+1 of N" after the last waypoint is reached — one-indexed display miscalculation.

**ALP-1094 (P2)**: `navigate/[routeId].tsx` suppresses `react-hooks/exhaustive-deps` on the `startNavigation` useEffect and `handleNavEvent` callback. The stale closure risk is non-trivial: if route data changes (e.g. live route update via OTA sync), the navigation loop continues with stale waypoint data.

**ALP-1095 (P3)**: `useAudioEngine.ts` `at_waypoint` case enqueues `text` (e.g. "Turn left.") at both `waypoint_annotation` priority and `turn` priority. Student hears the same turn instruction announced twice in succession when no pre-recorded clip is available.

## Data and Offline

**ALP-1061 (P2)**: `buildingIndex.ts` exports `BUNDLED_BUILDINGS: BuildingEntry[] = []` — an empty array. No build-time script populates it. STT destination voice search fails entirely on first launch before the sync engine has run. For a BLV student who cannot read the screen to debug, this is a silent total failure of the primary input method.

**ALP-1088 (P3)**: `syncEngine.ts` exports `syncCampus()` intended to be called on app foreground resume. No `AppState` listener exists anywhere in the student app to trigger it. Campus data only syncs on cold launch.

## Architecture Debt

**ALP-1098 (P4)**: `navigationLoop.ts` duplicates `haversineDistanceM` and `bearingTo` already present in `useGpsNavigation.ts` and `packages/shared/src/utils/geo.ts`. Three independent implementations of the same formulas — divergence risk as the product matures.

**ALP-1099 (P3)**: Admin `voiceAnnotationService.ts` stores STT subscriptions by monkey-patching them onto `Audio.Recording` via `(recording as unknown as { _sttSubs })._sttSubs`. This relies on Expo's internal recording object shape, which is not part of the public API and will break on any expo-av minor bump.

**ALP-1100 (P2)**: Admin `voiceAnnotationService.ts` audio upload reads the entire recorded file to base64 in the JS heap then converts to `Uint8Array`. A 60-second clip at typical quality is 2-4 MB base64-encoded. On low-RAM Android devices (1.5 GB), this OOM risk is real and will cause hard crashes mid-route-recording.

**ALP-1082 (P3)**: Admin `hapticPatternPlayer.ts` uses module-level mutable singletons (`activeCancel`, `loopIntervalId`, `sttActive`, `cueQueue`). Concurrent invocations from different React components are not safe.

## Performance Impact

- The empty `BUNDLED_BUILDINGS` issue (ALP-1061) is the highest user-impact finding: it silently disables the primary navigation input for BLV users on first launch.
- The GPS subscription leak (ALP-1062) will drain battery on every navigation session, compounding with the timer leaks in ALP-1066.
- The audio file OOM (ALP-1100) will cause unpredictable crashes on Android mid-recording.

## Open Items

- `react-native-haptic-patterns` replacement strategy needs a product decision: custom native module for Core Haptics patterns, or JS-level pattern simulation using expo-haptics with `setTimeout` sequencing. The latter has ~50ms scheduling jitter on the JS thread under load.
- The `BUNDLED_BUILDINGS` population pipeline needs a design decision: static asset bundled at build time vs. mandatory first-launch sync with a loading gate.
- PDR accuracy beyond 80m without GPS correction is documented as the known limitation. ARCore/ARKit SLAM upgrade path is noted in comments but not scoped.
