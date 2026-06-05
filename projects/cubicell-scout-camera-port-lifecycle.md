# Scout: Camera Motion Port Lifecycle (Slice 4 Strict Mode regression)

Branch `perf/initial-delivery-slice4`, HEAD b2c8e69, PR #132. Read-only scout. Citations use path + symbol, never line numbers.

## 1. Causal chain: CONFIRMED

The orchestrator's chain is correct end to end. Evidence:

- `src/main.tsx` renders `<AppBootstrap>` inside `<StrictMode>`. Strict Mode simulates mount → unmount → remount, so every effect runs setup, cleanup, setup once at initial mount.
- `src/app/useEditorCommands.ts` → `useEditorCommands` holds `core` in `useState` (stable identity for the component's life) and registers `useEffect(() => () => core.dispose(), [core])`. This is **dispose-only**: empty setup, cleanup calls `core.dispose()`. Strict Mode's mount→cleanup→remount therefore disposes `core` once, and the re-run setup does nothing to revive it. `core` is never recreated (it is `useState`-pinned), so it stays disposed for the whole session.
- `src/interaction/interactionCore.ts` → `createInteractionCore` returns `dispose: authority.dispose` (direct passthrough). So `core.dispose()` **is** `authority.dispose()`.
- `src/renderer/SharedRendererModule.ts` → `createCameraAuthority` builds the authority as `createCameraAuthorityRuntime(initialCamera, feelConfig, createCameraMotionPort({ wake }))`. The **lazy** port (not the ready one) is wired into the real authority.
- `src/camera/cameraAuthorityRuntime.ts` → `disposeCameraAuthority` calls `state.motionPort.dispose()`.
- `src/camera/cameraMotionPort.ts` → `createCameraMotionPort` closure: `dispose()` sets `disposed = true` and calls `cancel()`. `request()` opens with `if (disposed) return;`.

Result: after Strict Mode's first-mount cleanup, `disposed` is latched true forever. `src/camera/cameraAuthorityRuntime.ts` → `requestCameraMotion` (the eased path) calls `state.motionPort.request(...)`, which early-returns, so no motion plan is ever built and no pending activation is ever queued. Eased camera / numpad / keyboard commands are dead in `pnpm dev`. `pnpm preview` has no Strict Mode, so the cleanup never fires and the port stays live. **CONFIRMED.**

Scope note: instant paths in `cameraAuthorityRuntime.ts` (`applyInstantZoomCommand`, `applyInstantViewResult`) do not touch `motionPort.request`, so a strictly-instant command would still mutate pose; the dead surface is specifically the eased/motion-routed commands, which is the entire numpad/keyboard feel.

## Reuse Map (owners the fix should reuse, path + symbol)

- **Reversible disposed→live lifecycle pattern** — `src/studios/lazyCapability.ts` → `LazyCapabilityRuntime.resume`. It flips `disposed = false`, republishes `absent`, and re-registers the owner **without calling `load()` or touching the module**. This is the exact semantic template: revive the latch, do not warm the chunk. `resume` is already on the `LazyCapability` type surface.
- **Mount-effect shape** — `src/studios/editor/usePanelDragCapability.ts` → `usePanelDragCapability` uses `useEffect(() => { model.capability.resume(); return () => { …dispose… }; }, [model])`. Same shape in `src/studios/editor/useMotionCapability.ts` → `useMotionCapability` and `src/studios/editor/useThumbnailCapability.ts` → `useThumbnailCapability` (`resume()` in setup, `dispose` as cleanup). The fix for `useEditorCommands` is this shape: `resume()` in setup, `dispose()` in cleanup.
- **Dispose plumbing to extend** — chain that must gain a `resume()` passthrough:
  - `src/camera/cameraMotionPort.ts` → `CameraMotionPort` type + `createCameraMotionPort` (add `resume()` that sets `disposed = false` only).
  - `src/camera/cameraMotionPort.ts` → `createReadyCameraMotionPort` (the ready/no-op double; must implement the new `resume()` as a no-op to satisfy the type).
  - `src/camera/cameraAuthorityRuntime.ts` → `CameraAuthority` contract (`src/interaction/authority.ts` → `CameraAuthority` / `authority.ts`), `createCameraAuthorityRuntime`, and a `resumeCameraAuthority` sibling to `disposeCameraAuthority` that forwards to `state.motionPort.resume()`.
  - `src/interaction/interactionCore.ts` → `createInteractionCore` (add `resume: authority.resume` passthrough next to `dispose: authority.dispose`).
  - `src/app/useEditorCommands.ts` → `useEditorCommands` effect (switch to `resume()`+`dispose()` shape).
- **Test / ready port** — `src/camera/cameraMotionPort.ts` → `createReadyCameraMotionPort` is the only other `CameraMotionPort` implementer in the tree. Searches run: `rg "CameraMotionPort|createReadyCameraMotionPort|motionPort"` across `src`, and `rg` for `*.test.ts(x)` referencing those symbols — **no colocated `*.test.ts` doubles found** beyond the ready port; adding `resume()` to the type forces `createReadyCameraMotionPort` to implement it (no-op).
- **Pending-activation queue/replay** — `src/camera/cameraMotionPort.ts` → `pending` / `generation` / `promise` closure vars, consumed in `request` and `cancel`. See Risk Notes for why replay is a non-issue for the Strict Mode fix.
- **Existing camera-side `resume`** — **none found.** `rg "resume"` across `src/camera`, `src/interaction`, `src/renderer` returns only an unrelated comment in `cameraProjectionSwap.ts`. The resume lifecycle must be authored, modeled on `LazyCapabilityRuntime.resume`, not reused from an existing camera symbol.

## Quality Map / Blast Sweep

Swept every effect whose cleanup tears down a resource with no reviving setup (`rg "=> () =>"`, `rg -U "return () => …dispose/cancel/release/disconnect…"`, plus the two multiline `() => () => {…}` effects). **Exactly one live defect. Twelve other dispose-only effects are same-shape but anchored.**

**The defect:**
- `src/app/useEditorCommands.ts` → `useEditorCommands` — `core.dispose()` dispose-only effect. Strict Mode mount→cleanup→remount: **dead** (permanent `disposed` latch, no reviving setup). Real prod unmount→remount: the whole `useEditorCommands` host would remount and re-run `useState`, giving a fresh `core`, so prod is only at risk if `core` outlives a dispose without remount — not the case today. The Strict Mode dev path is the live break.

**Same-shape, anchored (not defects):**

LazyCapability slots — all already carry `resume()` in their mount effect, so a Strict Mode cleanup that disposes is revived by the re-run setup:
- `src/studios/editor/usePanelDragCapability.ts` → `usePanelDragCapability` — SAFE (`resume()` in setup).
- `src/studios/editor/useMotionCapability.ts` → `useMotionCapability` — SAFE (`resume()`).
- `src/studios/editor/useThumbnailCapability.ts` → `useThumbnailCapability` — SAFE (`resume()`).
- `src/studios/editor/useRecordingCapability.ts` → `useRecordingCapability` — SAFE (`resume()`).

Render-producer releases — `src/scene/renderScheduler.ts` → `release` is `queuedProducers.delete(producer)`, a pure reversible set op that any later `request`/`report` re-arms:
- `src/camera/CameraDriver.tsx` → `CameraDriver` `renderLiveness.release()` (via `src/camera/cameraRenderLiveness.ts` → `createCameraRenderLiveness.release`) — SAFE; re-armed by the per-frame `report`/`wake` after remount.
- `src/scene/RenderSchedulerDriver.tsx` → `RenderSchedulerDriver` `scheduler.release(recording)` — SAFE; re-armed by `useFrame` → `reportRenderProducerFrame`.
- `src/capabilities/panel-drag/usePanelDrag.ts` → `usePanelDrag` `renderScheduler.release(panelDrag)` — SAFE; re-armed on next `onDragStart`.

Three mesh disposers — dispose GPU-side resources but are anchored by a **companion `useLayoutEffect` setup** (same `[mesh]` dep) that re-grows and re-syncs the mesh on remount; the `<primitive>` stays mounted and Three re-uploads. This is the "Three anchored-by-design" note in the b2c8e69 commit. The distinction from `cameraMotionPort`: the mesh has a sibling setup that revives it; the port has none.
- `src/scene/InstancedPartMesh.tsx` → `InstancedPartMesh` `disposeInstancedPartMesh(mesh)` — SAFE.
- `src/scene/EdgeCoverageLayer.tsx` → `EdgeCoverageLayer` `disposeEdgeCoverageMesh(mesh)` — SAFE.
- `src/scene/SelectionChromeLayer.tsx` → `SelectionChromeBatchMesh` `disposeInstancedPartMesh(mesh)` — SAFE.

State/pointer resets — no external resource:
- `src/panels/useRetainedSelectionBuilder.ts` → dispose-only `setDraft(null)` — SAFE (React state reset, re-derivable).
- `src/scene/CubeScene.tsx` → dispose-only `selectionPressCleanupRef.current?.()` — SAFE (ref is null at mount; releases an in-flight pointer press only).

Balanced (not dispose-only, listed for completeness):
- `src/transport/TransportFrameDriver.tsx` → `TransportFrameDriver` — `request` in setup, `release` in cleanup. Balanced and reversible.

## Risk Notes on the proposed fix

- **resume() must revive only, never warm the chunk.** Model it on `LazyCapabilityRuntime.resume`: for `createCameraMotionPort`, `resume()` sets `disposed = false` and returns. It must not call `load()`, read `module`, or import `../motion/cameraMotion`. Cold-boot laziness survives because `module` stays `null` and the dynamic import fires only on the first real eased command via the existing `promise ??= load()` in `request`.
- **Real unmount must still dispose.** Using the `usePanelDragCapability` effect shape (`resume` in setup, `dispose` in cleanup) preserves this: a genuine unmount runs cleanup and does not remount, so `disposed` stays true. Keep `resume()` in the mount-effect setup only; never call it on every render or after a real dispose.
- **Replay is a non-issue for this fix.** `cameraMotionPort.dispose()` calls `cancel()`, which nulls `pending` and bumps `generation`. In the Strict Mode case the dispose happens at initial mount before any command, so there is nothing queued to replay — `resume()` clearing the latch is sufficient. The authority re-issues motion on the next command through `requestCameraMotion` → `state.pendingMotion` (also null at mount), so no port-level replay is needed. Deliberately do **not** try to preserve `pending` across dispose: a real remount should start from a clean pose, and a stale in-flight `load().then` callback already guards itself with `disposed || current?.generation !== generation` (with `pending` nulled, `current` is null → early return), so no ghost activation fires after resume.
- **Type ripple.** Adding `resume()` to the `CameraMotionPort` type forces `createReadyCameraMotionPort` to implement it (no-op) and adds a `resume` to the `CameraAuthority` contract and `InteractionCore`. Small, mechanical, single path — no duplication if the passthroughs mirror the existing `dispose` chain exactly.

## Plan (fix shape, for the builder)

1. `src/camera/cameraMotionPort.ts`: add `resume()` to `CameraMotionPort`; in `createCameraMotionPort` implement `resume() { disposed = false; }`; in `createReadyCameraMotionPort` implement `resume() {}`.
2. `src/camera/cameraAuthorityRuntime.ts`: add a `resumeCameraAuthority(state)` that calls `state.motionPort.resume()`; expose `resume` on the returned `CameraAuthority`.
3. `src/interaction/authority.ts` + `src/interaction/interactionCore.ts`: add `resume` to the `CameraAuthority`/`InteractionCore` types and pass it through (`resume: authority.resume`).
4. `src/app/useEditorCommands.ts`: change the effect to `useEffect(() => { core.resume(); return () => core.dispose(); }, [core])`, matching `usePanelDragCapability`.
5. Verify: live gate in `pnpm dev` (Strict Mode) — eased numpad/keyboard camera works; `pnpm preview` unchanged; cold boot does not import `motion/cameraMotion` until first eased command (Network tab / dynamic-import assertion).
