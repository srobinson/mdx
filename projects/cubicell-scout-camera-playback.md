# Scout: camera track playback

Read at d5c842e (feat/mount-camera-track). Question: what does it take for three captured keyframes plus Play to walk the camera.

## Reuse map

The renderer half is fully built, wired, and tested. Only two pieces are missing: a pure sampler and a production frame producer.

Exists end to end:
- Canvas seam: `src/renderer/contract.ts:34` `SharedRendererCanvasProps.cameraTrack?: CameraTrackFrame | null`. `src/camera/CameraDriver.tsx:21,107,118` consumes it in `useSingleCameraWriterFrame` (retained-buffer writer) and `useProjectionCameraSwap` (`cameraTrackActive`).
- Frame sync: `src/camera/cameraTrackFrame.ts:syncCameraTrackFrame` handles begin/release on asset change, rearm via `rearmEpoch`, null frame releases possession; `resolveCameraProjectionSample` and `getCameraTrackProjectionSwap` arbitrate projection weight vs live morph.
- Possession state machine: `src/camera/cameraTrackAuthority.ts` (`beginCameraTrackPossession`, `setCameraTrackPose`, `detachCameraTrackPose`, `detachCameraTrackProjection`, `rearmCameraTrackFollow`, `releaseCameraTrackPossession`), exercised by `tests/cameraTrackAuthority.test.ts`. Exposed as `core.track.*` on the interaction core.
- Sample contract: `src/domain/cameraTrack.ts:51` `CameraSample = {pose, orthographicWeight, endpointProjection}` — already the type `CameraTrackFrame.sample` carries.
- Math ingredients: orbit arc resolve/rotate (`src/domain/cameraTrack.ts:resolveCameraOrbitArc`, `rotateAroundAxis`), pose paths and `cutAt` authored on `CameraSegment`; easing registry `src/evaluation/scoreAt.ts:99:easingFor(EasingId)`; command-motion interpolators in `src/motion/cameraMotion.ts` (different contract: gesture plans, not authored segments — do not force-share).
- Timing: `src/evaluation/scoreAt.ts:86` already counts the camera track in `getScoreDurationMs`; `src/transport/TransportFrameDriver.tsx` + `advanceScheduledTransportFrame` tick `editor.transport.timeMs` per frame; `EditorRendererBinding` already re-renders per tick via the staged `moment` prop, so a per-tick `cameraTrack` prop adds no new render cadence (guarded by `tests/appPlaybackBoundary.test.tsx`).

None found (searches: `rg "sampleCameraTrack|CameraTrackSample|trackSample" src tests`, `rg cameraTrack src/evaluation src/studios`):
- No evaluator turns track + timeMs into a `CameraSample`. `sceneMorph` interpolates cells only.
- No production caller passes `cameraTrack` to the Canvas (`EditorRendererBinding` omits it; the prop defaults null).
- Recording samples nothing per frame today; deterministic export is recorded future work (ANIMATION.md), untouched by this.

## Possession answers (Q2)

Owner: the interaction core's `core.track` API over `cameraTrackAuthority` state. Mid-play user input: a user view intent calls `detachCameraTrackPose` — pose follows the user, possession stays active, projection following stays armed; a live projection command calls `detachCameraTrackProjection`. Replay rearms via `rearmEpoch` → `rearmCameraTrackFollow`; stop passes a null frame → `releaseCameraTrackPossession`. INTERACTIVE.md matches the code.

## Invariants (Q3)

Safe write path is the built one: Canvas prop → `syncCameraTrackFrame` → `core.track.setPose` → the same single-writer retained pose buffer gestures use (`src/camera/cameraFrameWriter.ts`). No per-frame commands on the bus, no direct buffer writes. Staged-scene framing and fitted-distance reset live on the command/framing path and are not touched by frames; the live gate should confirm reset-after-playback still carries the fitted distance since the camera parks wherever release left it.

## Plan

1. **Sampler (pure).** `cameraTrackSampleAt(track, timeMs): CameraSample` in `src/evaluation` beside `scoreAt` (reuses `easingFor`; domain stays easing-free). Clamp before first/after last keyframe; pose path cut honors `cutAt`, linear lerps, orbit rotates by eased sweep fraction around the resolved arc; projection weight blends eased or cuts. Gate: unit tests over every path/easing/clamp edge; tsc. No user story yet.
2. **Producer + session (feel-critical).** During Play, when the session's open camera Animation has keyframes, EditorApp-side wiring derives `CameraTrackFrame` per tick (rearmEpoch bumped at play start) and `EditorRendererBinding` passes it; null when stopped or trackless. User story: three captures + Play walks the camera; a drag mid-play takes the pose without killing playback; stop releases. Gates: integrator jsdom test asserting the produced frame prop across ticks (production tree, CubeScene mocked); one Chromium assertion that pose at t moved (counts/values, no timings); Stuart drives live before merge.
3. **Truth + budget.** Flip CAMERA.md/ANIMATION.md/INTERACTIVE.md possession-idle claims; re-baseline budgets (sampler should ride a lazy or deferred chunk — the `camera-motion` deferred increment at `src/motion/cameraMotion.ts` is the precedent; keep it out of the cold closure, gate already enforces).

## Sizes

1. M — the honest driver is orbit + cutAt + eased projection correctness with real test coverage, not plumbing.
2. M — driver is session semantics (which Animation, when possession begins/ends) plus the browser proof and the live feel gate.
3. S — mechanical, same shape as the mount PR.

Total: L (2 to 4 days across three PRs); nothing renderer-side needs building.

## Risk

The clock mismatch: the transport plays the attached piece's score, but the camera track lives on a separate Animation asset whose duration can exceed or undercut the piece's (`getScoreDurationMs` vs `getCameraTrackDurationMs`). Which duration governs Play, and what the camera does past its last keyframe while the piece continues, is the one decision most likely to thrash — settle it with Stuart before slice 2.
