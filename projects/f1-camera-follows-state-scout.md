# Camera-Follows-State Scout

Scope: what continuous camera-follows-state requires for Piece playback. Read-only scout of `f1-ink-tween` @ 46912bf (camera/pose layers identical to `f1-workspace-binding` and `main`). No fix or feature applied.

## Executive summary

Roughly 80 percent of the machinery already exists, is tested, and is dormant. The camera possession rail (authority, per-axis detach on user intent, frame writer integration) is fully built for authored camera tracks and has **zero producers in the app today**. Camera-follows-state is, mechanically, "build a producer that turns the piece's state timeline into camera samples and feed the existing rail." The real cost is not code; it is product feel decisions.

## What already exists (inventory)

### 1. The possession rail: complete, tested, unwired

- `CameraDriver` accepts `cameraTrack: CameraTrackFrame | null` (`{ animationAssetId, rearmEpoch, sample: CameraSample }`).
- `syncCameraTrackFrame` (`src/camera/cameraTrackFrame.ts`) drives `core.track.begin() / rearm() / release() / setPose()` per frame, deliberately "without treating ordinary clock ticks as intent."
- The authority (covered by `tests/cameraTrackAuthority.test.ts`) already handles: absolute authored pose, **hold on release** (no snap-back), **detach-on-view-intent per axis** (a user pose gesture detaches pose but not projection; a projection command detaches projection only), **explicit rearm**, and **full reset when the possessing target changes**.
- `ConnectedCubeScene` passes nothing; `cameraTrack` defaults to `null` everywhere. The rail idles.

### 2. Authored camera track model: domain and evaluator done

- `CameraTrack` / `CameraKeyframe` / `CameraSegment` (`src/domain/cameraTrack.ts`): pose snapshots, orbit or linear paths with shortest-arc derivation, eases, `cutAt`, projection blend.
- `sampleCameraTrack(track, timeMs) -> CameraSample` (`src/evaluation/cameraTrack.ts`): keyframe interpolation with easing, orbit arcs, projection weight. Production-ready, currently consumed by nothing.
- STUDIO.ANIMATION.md reserves **exactly one stage-owned camera lane**; the persisted keyframe fields are settled in CAMERA.md.

### 3. Framing math: per-scene targets already computable

- `createGridFrameTarget(scene, viewport)` -> `{ center, orientation, zoom }` frames any scene's occupied extent (projected envelope fill, cell cap, zoom bounds). Works per captured state scene as-is.
- `focusViewPose(pose, center, zoom, orientation, initial, bounds)` already converts a frame target into a `ViewPose`; `CameraPoseSnapshot` is `{ position, target, up, zoom }`. The adapter from frame target to camera keyframe is a thin composition of existing functions.

### 4. The state timeline signal

- `findStateTransitionTrack(asset.score)` + `resolveStateTransitionPosition(track, timeMs)` give exactly "which state is held / which transition is active at progress p" for any transport time. Boundary times and authored durations are all in the track.
- `TransportDriver` + `getPieceTransportDurationMs` already run the shared clock.

### 5. Interaction lock

- During piece staging `staged.interactive === false` and App gates `canvasInteractive`, shrinking the possession conflict surface during playback. (Verify in build: whether wheel zoom and orbit remain live during playback; if they do, the authority's detach-on-intent already defines the outcome: user wins, camera stays where the user put it until rearm.)

## What is missing (the actual work)

### A. A producer (the core task, ~1-2 days with tests)

A derivation that, given the attached piece and transport time, yields a `CameraTrackFrame`:

1. Per captured state, compute `createGridFrameTarget(stateScene, viewport)` and convert via `focusViewPose` math into a `CameraPoseSnapshot`.
2. Place those snapshots as **synthetic keyframes at the state boundary times** from the transition track, with segment eases mirroring each transition's settings.
3. Sample with the existing `sampleCameraTrack(syntheticTrack, transportTimeMs)` each frame and hand the result to the existing rail.

Nothing on the rail changes. The synthetic track is derived, never persisted (no wire-format or migration surface).

### B. Small decisions the producer forces

- **Possession key**: reuse `animationAssetId` slot with the structure asset id; bump `rearmEpoch` on each play press so replay re-takes the camera after a user detach.
- **Viewport resize mid-playback**: recompute the synthetic keyframes (framing is viewport-dependent). Cheap; the track is derived.
- **Projection**: piece playback swaps projection instantly; the synthetic keyframes should carry the current projection and avoid projection-follow entirely in v1 (the sample's `orthographicWeight` stays at the endpoint).
- **Zoom bounds**: clamp synthetic targets through `createGridZoomBounds` so follow never lands outside user-reachable zoom.
- **Feel constants**: landing fill and segment ease belong in config knobs, not hardcoded.

### C. Product decisions (the expensive part)

1. **Discrete vs truly continuous.** Recommended: discrete keyframes at state boundaries, eased across transitions (camera motion co-times with the morph). Truly continuous extent-following (frame the sampled scene's bounds every frame) is a feel hazard: staggered arrivals change the extent non-monotonically, producing zoom breathing.
2. **When armed**: playback only, or also scrub? A dock toggle, or always-on-while-playing? The F1 dock decision keeps that surface minimal.
3. **Relationship to the authored camera lane.** The synthetic follow-track is a poor man's camera track by construction. When the Animation camera lane lands, follow must yield to an authored track (simple precedence: authored track present -> follow off). Because both feed the same rail with the same sample type, this is a one-line arbitration, but it should be stated in ANIMATION.md when built.
4. **Default framing alternative**: frame-the-piece-union once at play start solves viewport overflow with zero camera motion, no toggle, and no per-state math. It can ship first and coexist; follow is the deluxe version on the same producer skeleton.

## Risks

- **Camera motion + morph motion compete** for attention; eases must be co-designed with transition eases or playback feels like two animations fighting.
- **Effect-loop hygiene**: the producer must be a pure per-frame derivation feeding `setPose`, never a React effect writing its own dependency (see the wheel-zoom lesson: convergence guards on self-retriggering effects).
- **Extent from renamed survivors**: cross-frame morphs (now allowed) mean a state's extent can move; union framing absorbs this, follow framing must use each state's own scene, which it does by construction.

## Suggested staging

1. `frame piece union at play start` (no UI, no possession, ~half day) — solves the observed pain.
2. Producer + rail wiring behind a knob: discrete follow keyframes (~1-2 days).
3. Fold into the authored camera lane arbitration when Animations land.
