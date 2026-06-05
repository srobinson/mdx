# F1 Zoom Loop Scout: perspective wheel-zoom "Maximum update depth exceeded"

Scope: root cause only, no fix applied. Source read as-is in worktree `cubicell-f1`; runtime evidence produced by running vitest against the worktree's actual source from a scratchpad test (zero source edits). Camera and pose files are identical between `main` and `f1-workspace-binding` (`git diff main...HEAD -- src/camera src/pose` is empty), so the crash reproduces on main as well; it is not F1-specific.

## Symptom

In perspective projection, after a few scroll-wheel zooms, React throws "Maximum update depth exceeded". Stack: `applyPerspectiveProjection` (`src/camera/cameraProjectionSwap.ts:167`) ← `applyProjectionCameraSwap` (`:123`) ← the `useProjectionCameraSwap` effect (`:57`) ← `<CameraDriver>` (`src/scene/CubeScene.tsx:394`).

## The setState cycle

The store field in the cycle is the **R3F root store's `camera`**:

1. `useProjectionCameraSwap`'s effect lists `camera` (from `useThree()`) as a dependency (`cameraProjectionSwap.ts:67-77`).
2. Its perspective branch has a convergence guard: if `hasMatchedPerspectiveFraming(camera.fov, camera.zoom)` fails, it calls `set({ camera: buildProjectionCamera('perspective', createViewPoseFromSnapshot(core.getState().pose), size) })` (`:163-174`).
3. `set` writes a **new PerspectiveCamera instance** into the R3F store → `useThree` re-renders `CameraDriver` → the effect re-runs with the new `camera` dep.
4. The freshly built camera is constructed by `createMatchedPerspectiveCamera` (`cameraDriverMath.ts:131-143`), which calls `applyViewPoseToCamera` on the **same pose**, deterministically reproducing the same `zoom` value. If that value fails the guard once, it fails on every rebuild: the fixed-point iteration cannot converge, and the effect loops `set → render → effect → set` past React's nested-update limit.

## Root cause

Two facts collide, both introduced or exposed by commit `b4a4487` "fix(camera): preserve center orbit during perspective dolly":

**1. The guard is an exact float equality on a now-derived value.**
`hasMatchedPerspectiveFraming` (`src/pose/projectionMatch.ts:103-108`) is `fovDegrees === 50 && zoom === 1`, no epsilon. Before b4a4487, `applyViewPoseToCamera` pinned `camera.zoom = 1` for perspective cameras (removed line visible in the diff), so the guard was tautologically true and the rebuild branch at `:167` was unreachable. After b4a4487, perspective `camera.zoom` is a **derived magnification**: `getPerspectiveMagnificationForOrthoZoom(zoom, distance, viewportHeightPx, fov)` = `poseZoom * 2 * distance * tan(fov/2) / viewportHeightPx` (`viewPose.ts:141-146`).

**2. Wheel zoom accumulates float error in exactly the product the magnification measures.**
The wheel handler dispatches a zoom command (`cameraWheelZoom.ts:33-40`) into `zoomViewPose` (`viewPose.ts:236-249`), which b4a4487 changed into a dolly: `newZoom = clamp(zoom * factor)` and `newDistance = distance * (zoom / newZoom)`. In exact arithmetic the product `zoom * distance` is invariant and the magnification stays 1. In IEEE 754 each tick adds rounding error, so the magnification drifts off exact 1 by ulps.

## Runtime evidence

Vitest run against the worktree source (`src/pose/projectionMatch.ts`, `src/pose/viewPose.ts`, `src/camera/cameraWheelZoom.ts` imported directly; matched starting pose, default wheel sensitivity 0.002, deltaY 53 per tick, viewport height 918):

```
tick 0: magnification = 1                       guard pass
tick 1: magnification = 1                       guard pass
tick 2: magnification = 0.9999999999999998      guard FAIL   (-2.22e-16)
tick 3: magnification = 0.9999999999999998      guard FAIL
tick 4: magnification = 0.9999999999999996      guard FAIL   (-4.44e-16)
tick 5: magnification = 0.9999999999999997      guard FAIL
```

Also verified: recomputing the magnification from the same pose twice yields the identical non-1 value (`rebuildA === rebuildB`, `rebuildA !== 1`), proving each rebuilt camera reproduces the failure and the loop cannot converge. This matches the repro's "multiple scroll-wheel zooms": tick 1 happened to round exactly to 1; from tick 2 the guard fails persistently.

## Why the crash fires when it does

The loop needs one seed: any re-run of the swap effect while the live pose is drifted. Dep wiggles that seed it include the morph-completion `set({camera})` in the frame writer (`cameraFrameWriter.ts:114-118`), a canvas resize (`size` dep changes on any panel or dock layout change), a `morphDurationMs` preference edit, or a projection re-toggle. Before b4a4487 those re-runs were harmless no-ops because the guard always passed. Note also that the guard can fail by a wide margin (not just ulps) for any pose whose `zoom * distance` product does not equal `viewportHeight / (2 * tan(25 degrees))`, for example an unmatched persisted pose; the fix should account for both cases.

## Proposed fix direction (not implemented)

The guard's intent is "this camera is already a resting perspective camera; do not rebuild". Zoom stopped being a reliable identity signal when b4a4487 made it pose-derived, so:

1. **Primary: stop treating derived magnification as an identity mismatch.** Rebuild only on a genuine identity mismatch (camera type, or `fov !== perspectiveFovDegrees`). The per-frame writer (`composeCameraWrite`) already re-applies the pose, including magnification, every frame, so a zoom delta never requires a rebuild.
2. **If a zoom check is kept, make it a tolerance, not exact equality** (a named epsilon constant beside `hasMatchedPerspectiveFraming` in `projectionMatch.ts`). Exact `=== 1` on a value computed via `tan`, multiply, and divide can never be trusted.
3. **Defense in depth:** `applyPerspectiveProjection`'s rebuild is a deterministic function of the pose, so any remaining guard must be provably satisfied by the camera the rebuild produces, or the loop returns. A regression test should assert guard-pass on a freshly built camera after N wheel ticks (the scout test in the session scratchpad, `zoomLoopScout.test.ts`, is directly adaptable).

Severity: Blocker (hard crash of the canvas during basic navigation). Owners: `src/pose/projectionMatch.ts::hasMatchedPerspectiveFraming`, `src/camera/cameraProjectionSwap.ts::applyPerspectiveProjection`, regression origin `b4a4487` (`src/pose/viewPose.ts::applyViewPoseToCamera` / `zoomViewPose`).
