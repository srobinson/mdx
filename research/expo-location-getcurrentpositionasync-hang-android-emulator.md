---
title: expo-location getCurrentPositionAsync Hangs on Android Emulator with rnmapbox
type: research
tags: [expo-location, rnmapbox, android, emulator, location, react-native]
summary: getCurrentPositionAsync hangs indefinitely on Android emulator due to multiple overlapping causes: fused location provider conflicts, Google Location Accuracy interference, rnmapbox location listener registration conflicts, and API 36 preview instability.
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

# Summary

`getCurrentPositionAsync` hangs indefinitely on Android emulator (API 34-36) in the presence of `@rnmapbox/maps` due to a combination of: (1) rnmapbox registering a competing Android location listener that can starve expo-location, (2) the "Improve Google Location Accuracy" setting using Wi-Fi scanning that does not behave the same on emulator as on physical device, (3) `Accuracy.Balanced` requiring the fused location provider to have a valid network provider, which emulators often lack, and (4) API 36 (Android 16 "Baklava") being a developer preview with multiple known instability issues.

The hang is not a deadlock -- it is a silent failure where the fused location provider never calls back because no provider satisfies the requested accuracy tier.

# Details

## Root Cause Breakdown

### 1. Accuracy.Balanced requires network provider

`Accuracy.Balanced` maps to Android's `PRIORITY_BALANCED_POWER_ACCURACY` in the Fused Location Provider (FLP). This priority asks FLP to use cell towers and Wi-Fi, not GPS. On an emulator:
- Wi-Fi is virtual and not providing real scan data
- Cell tower data is absent
- FLP waits for a network provider fix that never arrives
- The promise never resolves or rejects -- there is no timeout by default

The mock location set via Android Studio Extended Controls is injected as a GPS fix, not a network fix. `Accuracy.Balanced` ignores GPS-only fixes when network providers are also registered but unavailable.

**Fix**: Use `Accuracy.Lowest` or `Accuracy.Low` on emulator. These map to `PRIORITY_LOW_POWER` and `PRIORITY_PASSIVE` which accept any fix including mock GPS.

```ts
const accuracy = __DEV__ && Platform.OS === 'android' && !Device.isDevice
  ? Location.Accuracy.Lowest
  : Location.Accuracy.Balanced;

const loc = await Location.getCurrentPositionAsync({ accuracy });
```

### 2. "Improve Google Location Accuracy" setting

Android emulators ship with this setting ON by default. This setting uses Wi-Fi scanning via Google Location services. On emulator it creates a background location scan loop that can interfere with FLP callbacks.

**Fix**: In the emulator, go to Settings > Location > Location Services > Google Location Accuracy and disable "Improve Location Accuracy". This forces GPS-only mode. The Expo docs explicitly note this as required for emulator testing.

### 3. rnmapbox/maps location listener conflict

Confirmed in [rnmapbox/maps issue #2717](https://github.com/rnmapbox/maps/issues/2717): when rnmapbox's `UserLocation` component is mounted, it registers its own Android location listener. The conflict emerged between v10.0.0-beta.70 and v10.0.0-beta.71. Merely having another geolocation library installed (even without calling it) can cause rnmapbox's listener to stop updating -- and vice versa.

The mechanism: Android's FLP allows multiple clients but each client registers independently. When rnmapbox registers with its own request parameters, it can shift FLP's behavior and cause expo-location's pending request to stall waiting for a fix that matches its own priority parameters.

**Implication**: On emulator where providers are already marginal, this conflict is fatal. On physical device, the GPS/cell signal is strong enough that FLP satisfies both clients.

**Workaround**: If you need location data and have a map on screen, extract location from the map rather than calling `getCurrentPositionAsync`:

```ts
// Use rnmapbox's onUserTrackingModeChange or Camera ref instead
// Or subscribe via watchPositionAsync and cancel after first fix
const subscription = await Location.watchPositionAsync(
  { accuracy: Location.Accuracy.Lowest },
  (location) => {
    subscription.remove();
    resolve(location);
  }
);
```

### 4. API 36 (Android 16 "Baklava") instability

API 36 is the Android 16 developer preview. Google's own issue tracker documents emulator crashes at boot (guest kernel crash after quick boot on some hardware). Multiple framework-level regressions have been reported in Flutter and other ecosystems. This is not a stable target for testing location code.

Confirmed stable emulator targets for this stack: API 33 (Android 13) and API 34 (Android 14). API 35 (Android 15) is GA but has had some emulator quirks.

### 5. Permission re-request hang (secondary cause, issue #39851)

A separate but related issue: if `requestForegroundPermissionsAsync()` is called when permission is already granted, it hangs on Android after an OS security update (reported ~September 2025, SDK 53). For SDK 52 this is less likely to be the trigger, but the pattern to follow:

```ts
const { status } = await Location.getForegroundPermissionsAsync();
if (status !== 'granted') {
  const result = await Location.requestForegroundPermissionsAsync();
  if (result.status !== 'granted') return;
}
```

Never call `requestForegroundPermissionsAsync` unconditionally.

## Confirmed Workarounds (priority order)

1. **Use `Accuracy.Lowest` on emulator** -- most reliable single fix
2. **Disable "Improve Location Accuracy"** in emulator Settings
3. **Wrap with a manual timeout** since the API provides no built-in timeout:
   ```ts
   const locationPromise = Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Lowest });
   const timeoutPromise = new Promise<never>((_, reject) =>
     setTimeout(() => reject(new Error('Location timeout')), 10_000)
   );
   const loc = await Promise.race([locationPromise, timeoutPromise]);
   ```
4. **Use `getLastKnownPositionAsync` as a fast path** before calling `getCurrentPositionAsync`
5. **Use `watchPositionAsync` and cancel on first fix** -- this uses a different FLP codepath that is more tolerant
6. **Log into a Google account on the emulator** -- some reports confirm FLP requires a Google account session to function on emulator
7. **Downgrade emulator to API 33 or 34** -- avoids API 36 preview instability

## Accuracy Tier Mapping

| expo-location Accuracy | Android FLP Priority | Needs network provider? |
|---|---|---|
| Accuracy.Highest | PRIORITY_HIGH_ACCURACY | No (GPS ok) |
| Accuracy.High | PRIORITY_HIGH_ACCURACY | No |
| Accuracy.Balanced | PRIORITY_BALANCED_POWER_ACCURACY | Yes |
| Accuracy.Low | PRIORITY_LOW_POWER | No |
| Accuracy.Lowest | PRIORITY_PASSIVE | No |
| Accuracy.BestForNavigation | PRIORITY_HIGH_ACCURACY | No |

On emulator without Wi-Fi location, `Balanced` and below (in terms of GPS) will hang. Use `High`, `Highest`, or `BestForNavigation` for GPS, or `Lowest` for passive/mock acceptance.

## No Direct rnmapbox Fix Available

There is no confirmed fix in rnmapbox 10.1.33 for the listener conflict. The workaround is architectural: avoid calling `getCurrentPositionAsync` while `UserLocation` is mounted, or use rnmapbox's own location callbacks as the data source.

# Sources

- [expo/expo #39851: getCurrentPositionAsync hangs indefinitely (Minimal reproducible example)](https://github.com/expo/expo/issues/39851)
- [expo/expo #33981: Issue with expo-location on Certain Android Devices](https://github.com/expo/expo/issues/33981)
- [expo/expo #26825: getCurrentPositionAsync is never returning the location (Pixel 5 API 34)](https://github.com/expo/expo/issues/26825)
- [expo/expo #24856: getCurrentPositionAsync not working anymore on Android (FLP interface change)](https://github.com/expo/expo/issues/24856)
- [expo/expo #15478: getCurrentPositionAsync hangs indefinitely](https://github.com/expo/expo/issues/15478)
- [rnmapbox/maps #2717: UserLocation doesn't work with other GeoLocation Services (Android)](https://github.com/rnmapbox/maps/issues/2717)
- [Expo Location Documentation](https://docs.expo.dev/versions/latest/sdk/location/)

# Open Questions

- Does rnmapbox 10.1.33 still contain the listener registration regression from beta.71, or was it resolved in a later 10.x release? The PR #3089 was merged but user reports suggest it persists.
- Is there a way to configure rnmapbox to defer its location listener registration until the map is actually visible, reducing contention during app startup?
- API 36 specific: does the FLP in Android 16 preview have new permission requirements not yet handled by expo-location 17.x?
