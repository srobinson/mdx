---
title: rnmapbox/maps Camera Component Crash Patterns and followUserLocation Behavior
type: research
tags: [rnmapbox, mapbox, react-native, camera, followUserLocation, crash, ios, android]
summary: Conditional Camera rendering is unsafe; toggling followUserLocation on a single instance is the correct pattern, but has its own known bugs fixed in v10.1.37+; the Viewport API is the recommended modern alternative.
status: active
source: quick-research
confidence: high
created: 2026-03-10
updated: 2026-03-10
---

## Summary

**Do not conditionally render different Camera instances.** Use a single `<Camera>` instance and toggle `followUserLocation` between `true` and `false`. However, toggling has its own documented bugs in versions prior to approximately 10.1.37, and there is a well-known style-load race condition that affects both Android and iOS.

The most robust modern approach is to use the `<Viewport>` component with `transitionTo()` instead of Camera for follow/static switching, or to gate Camera rendering behind `onDidFinishLoadingStyle`.

---

## Details

### 1. Conditionally Rendering Different Camera Components

**This is unsafe.** There are two mechanisms that make conditional rendering or ternary-swapped Camera components problematic:

- When the Camera native view is unmounted and remounted, the native Mapbox SDK instantiates a new camera controller against the same `MapView` instance. On iOS (v10+, Fabric), this involves calling `map.viewport.transition(to:)` on a view that may already have a viewport state observer attached. The SDK does not always clean up the previous observer before the new one registers, which can trigger assertion failures or null-pointer dereferences in native code.
- On iOS specifically (issue [#2240](https://github.com/rnmapbox/maps/issues/2240)), unmounting the Camera (or the entire MapView) before the map finishes loading causes a fatal `Unexpectedly found nil while unwrapping an Optional value` crash at `RNMBXMapViewManager.swift:32`. The Camera component holds map references that become dangling during rapid mount/unmount cycles.
- Spreading different prop sets onto a single Camera instance via a ternary (e.g., `{...(isFollow ? followProps : staticProps)}`) does not cause a remount by itself since the component instance is stable, but it does trigger all the `didSet` observers on the native Swift/Kotlin object simultaneously, which can produce interleaved prop update calls.

**The official example (`SetUserTrackingModes.js`) uses a single Camera instance** and drives both modes through boolean state:

```tsx
<Mapbox.Camera
  defaultSettings={{ centerCoordinate: [...], zoomLevel: 0 }}
  followUserLocation={userSelectedUserTrackingMode !== 'none'}
  followUserMode={...}
  onUserTrackingModeChange={onUserTrackingModeChange}
/>
```

### 2. Toggling `followUserLocation` false → true on a Single Instance

The native handlers on both platforms call `_updateCameraFromTrackingMode()` (iOS) or `_updateViewportState()` (Android) on every prop change. The key behavior difference between the two modes is:

**iOS (`RNMBXCamera.swift`):**
```swift
@objc public var followUserLocation : Bool = false {
  didSet {
    _updateCameraFromTrackingMode()
  }
}

func _updateCameraFromTrackingMode() {
  withMapView { map in
    guard self.followUserLocation && userTrackingMode != .none else {
      self._disableUserTracking(map)  // calls map.viewport.idle()
      return
    }
    // transitions to FollowPuckViewportState
    let followState = map.viewport.makeFollowPuckViewportState(options: followOptions)
    map.viewport.transition(to: followState)
    map.viewport.addStatusObserver(self)
    map.mapboxMap.setCamera(to: _camera)
  }
}
```

Setting `followUserLocation = false` calls `map.viewport.idle()`. Setting it back to `true` calls `map.viewport.transition(to: followState)`. This is straightforward but `withMapView` enqueues the callback if the map is not yet attached, so there is no null-pointer risk from the toggle itself.

**Known bug (iOS, v10.1.37):** Issue [#3794](https://github.com/rnmapbox/maps/issues/3794) and [#3793](https://github.com/rnmapbox/maps/issues/3793) confirm that setting `followUserLocation = false` after it was `true` does **not** stop following on iOS in v10.1.37. The viewport state observer does not respond to `viewport.idle()` under certain conditions (particularly when the location update is very precise or comes in quickly). The issues are marked closed, suggesting a fix landed, but no specific PR is referenced in those threads.

**Known bug (iOS, v10.1.37):** Issue [#3969](https://github.com/rnmapbox/maps/issues/3969) shows that on iOS with `followUserLocation={false}` explicitly set, the Camera still jumps to user location on app start if UserLocation is rendered and a location fix arrives quickly. Android is unaffected. Root cause: the `withMapView` callback queue may fire before React has fully resolved props, causing the initial state to be `followUserLocation = true` (the Swift default) before the JS bridge delivers `false`.

**Android (`RNMBXCamera.kt`):**
```kotlin
fun setFollowUserLocation(value: Boolean?) {
    mFollowUserLocation = value ?: defaultFollowUserLocation
    _updateViewportState()
}
```

`_updateViewportState()` checks `mFollowUserLocation`:
- If `false`: calls `viewport.idle()` and `setFollowLocation(false)`.
- If `true`: builds a `FollowPuckViewportStateOptions` and transitions.

This is stable for toggling as long as `addToMap` has already been called (i.e., the MapView is attached). The `defaultFollowUserLocation` constant is `false`, so `null` from JS correctly disables following.

### 3. Style-Load Race Condition (Both Platforms, All v10 Versions)

Issue [#344](https://github.com/rnmapbox/maps/issues/344) documents the original race condition. While that issue predates v10, the underlying mechanism still applies:

If `followUserLocation` becomes `true` before the map style has finished loading, the viewport transition may attempt to activate location tracking against an uninitialized style/map. On Android (v8-era), this threw a hard `NullPointerException` on `LocationComponentActivationOptions`. In v10, the Viewport API is more defensive, but the race is still observable.

**Canonical workaround:**
```tsx
const [styleLoaded, setStyleLoaded] = useState(false);

<MapView onDidFinishLoadingStyle={() => setStyleLoaded(true)}>
  {styleLoaded && (
    <Camera
      followUserLocation={isFollowing}
      followUserMode="normal"
    />
  )}
</MapView>
```

This is the pattern explicitly suggested in issue #344's workaround comment, and it remains valid for v10.

### 4. Recommended Pattern for Switching Between Static and Follow Mode

**Option A: Single Camera instance with boolean toggle (official pattern)**

```tsx
const [isFollowing, setIsFollowing] = useState(false);
const [styleLoaded, setStyleLoaded] = useState(false);

<MapView onDidFinishLoadingStyle={() => setStyleLoaded(true)}>
  <UserLocation visible />
  {styleLoaded && (
    <Camera
      defaultSettings={{ centerCoordinate: staticCoord, zoomLevel: 14 }}
      centerCoordinate={isFollowing ? undefined : staticCoord}
      zoomLevel={isFollowing ? undefined : 14}
      followUserLocation={isFollowing}
      followUserMode="normal"
      animationMode="easeTo"
      animationDuration={500}
    />
  )}
</MapView>
```

Key points:
- Gate behind `onDidFinishLoadingStyle` to avoid the race condition.
- Do not pass `centerCoordinate` when `followUserLocation` is `true` (the JS Camera ignores it via `_updateCameraFromJavascript` guard, but passing it anyway may confuse the prop diffing).
- `defaultSettings` provides a safe fallback position for the initial render before location is known.

**Option B: `<Viewport>` API (recommended workaround for the followUserLocation=false bug)**

The workaround posted in issue [#3794](https://github.com/rnmapbox/maps/issues/3794) uses the `Viewport` component directly:

```tsx
const viewport = useRef<Viewport>(null);

useEffect(() => {
  if (isFollowing) {
    viewport.current?.transitionTo(
      { kind: 'followPuck', options: { pitch: 0, bearing: 0, zoom: 'keep' } },
      { kind: 'default', maxDurationMs: 5000 },
    );
  } else {
    // Transition to a fixed state or call idle()
    viewport.current?.transitionTo(
      { kind: 'overview', geometry: staticGeometry, options: {} },
      { kind: 'default', maxDurationMs: 1000 },
    );
  }
}, [isFollowing]);

<MapView>
  <Viewport ref={viewport} />
  <UserLocation visible />
</MapView>
```

This bypasses the Camera component entirely for mode switching and avoids the known `followUserLocation=false` not-stopping-follow bug. The Viewport API maps directly to `MapboxMap.viewport` on the native side and is the recommended v10 idiom in official Mapbox Maps SDK docs.

**Option C: `camera.current?.setCamera()` for static moves after exiting follow**

When transitioning from `followUserLocation=true` to static, the viewport transitions to idle, and then you can imperatively move:

```tsx
const onExitFollow = () => {
  setIsFollowing(false);
  // Slight delay may be needed for the viewport.idle() to complete
  setTimeout(() => {
    camera.current?.setCamera({
      centerCoordinate: targetCoord,
      zoomLevel: 14,
      animationDuration: 300,
    });
  }, 50);
};
```

Issue [#4090](https://github.com/rnmapbox/maps/issues/4090) documents that `setCamera` calls made immediately after a viewport state change may be ignored due to a race condition. A `setTimeout(fn, 0)` or a short delay resolves this.

---

## Sources

- rnmapbox/maps issue [#344](https://github.com/rnmapbox/maps/issues/344): followUserMode race condition crash before style load
- rnmapbox/maps issue [#2240](https://github.com/rnmapbox/maps/issues/2240): iOS v10 crash on unmount before map fully loaded
- rnmapbox/maps issue [#3793](https://github.com/rnmapbox/maps/issues/3793), [#3794](https://github.com/rnmapbox/maps/issues/3794): followUserLocation cannot be turned off (iOS, v10.1.37)
- rnmapbox/maps issue [#3969](https://github.com/rnmapbox/maps/issues/3969): iOS ignores centerCoordinate, jumps to user location despite followUserLocation=false
- rnmapbox/maps issue [#4013](https://github.com/rnmapbox/maps/issues/4013): MapView children removed on MapView prop change (related: style URL update re-initializes map)
- rnmapbox/maps issue [#4090](https://github.com/rnmapbox/maps/issues/4090): Camera.setCamera ignored after navigation, race condition
- Source: `ios/RNMBX/RNMBXCamera.swift` (main branch)
- Source: `android/src/main/java/com/rnmapbox/rnmbx/components/camera/RNMBXCamera.kt` (main branch)
- Source: `example/src/examples/Camera/SetUserTrackingModes.js` (official example)

---

## Open Questions

- Whether the followUserLocation=false bug in [#3793/#3794](https://github.com/rnmapbox/maps/issues/3794) was fully resolved and in which exact version. The issues are closed but no fix PR is referenced.
- Whether the iOS `centerCoordinate` jump bug ([#3969](https://github.com/rnmapbox/maps/issues/3969)) is resolved in versions after 10.1.37, or still present.
- Behavior of the `<Viewport>` API when transitioning from `followPuck` back to a static `overview` state when no geometry is available.
