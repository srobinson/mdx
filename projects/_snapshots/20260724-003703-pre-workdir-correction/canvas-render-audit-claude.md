---
title: Canvas rendering audit, Claude frontend
created: 2026-06-08
source: frontend-engineer-claude
branch: feat/canvas-pane-motion-interaction
status: filed
role: MoE peer (Claude FE 2.1) vs Codex FE 2.2; orchestrator general 3.1
---

# Canvas rendering audit — Claude FE

## Scope read (live)

Branch `feat/canvas-pane-motion-interaction`. Reviewed committed + uncommitted.

- `git log -5`: f801bd0 unframe re-frames underlying pane; 9a034b9 defer reflow to drag-end; 4e4ea1e framing stack; 533b038 pane motion + shift-gated viewport; 15328c1 grid-fit.
- Uncommitted (`git diff`): `LayoutCanvas.tsx` (instant gate `zooming||framing||zoomed`), `canvas.css` (removed per-pane `will-change`, added comment), `canvasLabStore.ts` + `.test.ts` (stack → single-slot framing + `UNFRAME_FLY_PANE_LIMIT`).
- Shared production surface: `LayoutCanvas`, `PaneFrame`, `canvas.css` are used by BOTH `/canvas-lab` (`CanvasLabRoute`) and production `/canvas` (`CanvasSurface`). `CanvasSurface` wires `LayoutCanvas` WITHOUT `framing` (good camera-fly isolation), but inherits all shared CSS + the `zoomed` motion heuristic.

## Live browser measurement (real Chrome via CDP, tab B1CCA25D)

DOM probe of `localhost:5174/canvas-lab` at audit time (`document.visibilityState: "hidden"`, i.e. backgrounded):

```
scale (world)         0.5452898  (fit-to-content, <1 — the headline condition)
.canvas-world         will-change: transform; transform: matrix(0.545,0,0,0.545,0,0)
paneCount             50
[data-pane-frame]     contain: computed "content" (= layout paint style); will-change: auto
pane transform        matrix(1,0,0,1,48,48)  (Framer translate, 2D)
pane opacity          1        <-- COMPUTED OPACITY IS 1, NOT 0
.canvas-pane-window   backdrop-filter: blur(18px)
windows w/ backdrop   50 / 50  <-- EVERY pane window is a backdrop-filter element
```

Two facts settled empirically:
1. **Framer "opacity:0 stuck" hypothesis is refuted.** Computed pane opacity is `1` and per-pane `will-change` is already `auto`. A stuck inline `opacity:0` would also not be cured by a scroll (the brief says scroll/zoom *restores* the panes), so the symptom is a stale *raster*, not a wrong *style*.
2. **Every one of the 50 pane windows carries `backdrop-filter: blur(18px)`.** `backdrop-filter` unconditionally promotes its element to its own compositor layer → ~50–72 per-pane GPU layers nested inside the single scaled `will-change:transform` world layer.

Observation limit (honest): CDP `Page.captureScreenshot` forces a fresh raster, which *masks* a GPU tile-discard bug, so I could not screenshot the blank directly. The user's OS screenshot is the ground-truth symptom; my measurements establish the mechanism. The same limit blocked Codex.

## Headline root cause

**Per-pane `backdrop-filter: blur(18px)` (`canvas.css:121`) promotes each of the ~50–72 panes to its own GPU compositor layer. Under fit-to-content (world scale 0.545) these layers live inside the scaled `will-change:transform` `.canvas-world` layer (`canvas.css:40-47,46`). When the tab is hidden, Chromium releases the backgrounded tab's per-layer GPU tile backing. On restore it fails to re-raster most of these per-pane layers (backdrop-filter under a scaled ancestor transform is a known Chromium fragility: the backdrop snapshot is not re-resolved on visibility change), so most panes present blank. Any transform mutation (scroll/zoom changes the world matrix) invalidates the layers and forces a correct re-raster, restoring them.**

This is the same per-pane-GPU-layer eviction the team described in the new `canvas.css:50-54` comment and tried to kill by removing per-pane `will-change`. The removal was incomplete: `backdrop-filter` is an independent, stronger layer-promotion trigger that re-creates the exact condition.

### Why backdrop-filter, not paint-containment (the peer's thesis)

Codex's headline is `contain: paint` on each pane. I read it as a real perf cost but **not** the blank's root cause:

- **`contain: paint` creates no compositor layer.** It clips paint to the box and establishes a stacking context. The *unit Chromium evicts and fails to restore is a layer's tile backing* — there is no per-pane layer from `contain` alone, so `contain:paint` cannot be the per-pane eviction unit. The per-pane blank granularity (whole panes blank/painted, scattered) requires per-pane layers, which only `backdrop-filter` supplies here.
- **`contain: paint`'s only paint optimization is skipping *off-screen* contents.** The blanked panes are *on-screen* (visible in the fit viewport) and scattered, not viewport-edge-correlated. For paint-containment to blank an on-screen pane, Chromium would have to misclassify a visible pane as off-screen — a different, unestablished mechanism.
- Codex's own data shows removing paint-containment **did not** help (its controlled run), while removing **backdrop-filter** did. Codex filed backdrop-filter removal as Finding 2 (perf); I argue it is also the headline fix. We already agree backdrop-filter must go in dense/scaled mode — we disagree only on whether removing *paint-containment* is necessary or sufficient.

### Minimal fix (root cause)

1. **Gate/remove per-pane `backdrop-filter`.** Most direct + also the largest perf win. Options, in order of preference:
   - Drop `backdrop-filter` from `.canvas-pane-window` and raise the surface background opacity (`rgb(var(--shadow-rgb)/0.74)` → ~`0.92`) so panes stay legible. At scale 0.545 an 18px blur renders ~10px over only the dark gradient backdrop — near-invisible, ~zero visual loss, minus 50–72 layers.
   - Or gate it: apply `backdrop-filter` only to the focused pane and/or only when `scale ≥ 1` && pane count is low.
2. **Defense-in-depth (cheap, low-risk):** also relax `[data-pane-frame]` containment `layout paint style` → `layout style` (drops `paint`). Addresses the peer's thesis at near-zero cost; pane bodies already `overflow:auto`, so paint clipping is largely redundant.
3. **Secondary:** remove the always-on `will-change: transform` from `.canvas-world` (`canvas.css:46`); let the `.canvas-world--framing` class / Framer add it transiently. It contradicts the team's own `canvas.css:50-54` philosophy and is inherited by prod.
4. **Verification the orchestrator should run (decisive A/B, real Chrome, 71 panes, fit):** background the tab and restore. Test removing `backdrop-filter` ONLY vs removing `paint`-containment ONLY. Whichever stops the blank is root cause. Prediction: backdrop-filter removal fixes it; paint-containment removal alone does not.

## Ranked findings

1. **CRITICAL — headline.** `canvas.css:121` `.canvas-pane-window { backdrop-filter: blur(18px) }` × N panes ⇒ N GPU layers ⇒ tab-hide eviction ⇒ blank on restore (root cause above). Shared with prod. → remove/gate backdrop-filter (+ optional `paint` containment drop). Live-measured 50/50 panes affected.

2. **HIGH — dead code + lying comments.** `PaneFrame.tsx:31` `TELEPORT_DISTANCE_FACTOR = 0` makes `teleport = moved > Math.max(w,h)*0 = moved > 0` (`PaneFrame.tsx:68`), so EVERY position change uses `SNAP_TRANSITION` (instant). The position-spring path and the "neighbours shuffle / rows slide" prose (`:28-31,60-62,78,140-141`) are unreachable. → restore a real factor (e.g. `1.5`) if springy moves are wanted, or delete the dead spring branch + comments. (Verified by reading; peer did not flag.)

3. **HIGH — perf, confirms backdrop cost.** `canvas.css:68-72,112-121` 50–72 translucent `backdrop-filter` + shadow surfaces dominate pan/raster budget independent of viewer content. Folds into #1. (Peer Finding 2; concur.)

4. **HIGH — a11y.** `CanvasLabRoute.tsx:34-44` global `window` keydown intercepts plain `Tab` (preventDefault → toggles command bar), breaking keyboard traversal of all controls + panes. → use a non-essential chord, scope to viewport, ignore when focus is in controls. (Peer Finding 3; concur.)

5. **MEDIUM — prod regression vector.** `LayoutCanvas.tsx:36,71` `instant = zooming||framing||zoomed`; `zoomed = scale≠1` is shared with prod via `CanvasSurface`, so any prod canvas left at non-1 zoom permanently snaps all pane size motion. → gate on density / explicit `disablePaneSizeMotion` prop, not raw scale. (Peer Finding 7; concur.)

6. **MEDIUM — re-render storm.** `LayoutCanvas.tsx:31` `Object.values(nodes).filter(...)` + `CanvasLabRoute.tsx:116-132` inline `renderPane` closure with per-pane regex (`paneIndexOf`, `titleIdForPane`) run on every viewport pan/zoom tick; prod shares the closure shape. → `useMemo` node list; `useCallback` renderer + memoize pane frames by id/focus/rect/lifecycle. (Peer Finding 4; concur.)

7. **MEDIUM — O(N²) allocation.** `canvasLabStore.ts` `planLayout` → `updateNodeRect` (`layoutState.ts:62-73`) spreads the whole `nodes` map per pane; one Organize/Add at 71 panes copies the map N times. → add a bulk `updateNodeRects(state, rects)` single-copy reducer. (Peer Finding 5; concur.)

8. **MEDIUM — uncommitted default.** `CanvasLabRoute.tsx:11` `SEED_PANES = 50` with a "seed a few panes" comment boots the lab straight into the worst-case scene. → restore small default; expose 50 as a named stress preset/query param. (Peer Finding 6; concur — applies to uncommitted tree.)

9. **LOW — a11y.** `PaneChrome.tsx:77-81` resize handle is an `aria-hidden` pointer-only div, no keyboard path. → focusable labelled control + keyboard resize, or document as lab-only. (Peer Finding 8; concur.)

10. **LOW — typing.** `PaneChrome` `state: string` accepts any string into `data-state`/aria. → union `"default"|"loading"|"empty"|"error"|"framed"`. (Subagent.)

11. **LOW — DRY.** Lab viewers `LabCardPane` vs `LabRulerPane` are near-identical (only the `<strong>` label differs). → collapse to one component with a `label` prop.

12. **LOW — reduced motion.** `PaneFrame.tsx:73-82` close still holds the node mounted `CLOSE_DELAY_MS` under `prefers-reduced-motion`. → shorten/skip the timer when reduced motion.

## Positive findings (concur with peer)

- `PaneFrame` resize defers store commit to `liveRect` + drag-end — correct for 60fps pointer work.
- Single-level framing (`canvasLabStore.ts`) is simpler than the nested stack; good KISS move.
- Per-pane `will-change` removal was the right direction (just incomplete vs backdrop-filter).
- `CanvasSurface` not passing `framing` cleanly isolates the camera-fly transition from prod.

## Shared-boundary verdict

Prod `/canvas` inherits from shared `canvas.css`/`PaneFrame`: per-pane `backdrop-filter` (#1), always-on `will-change` (#fix-3), `contain` (#1 defense), and the `zoomed`-snaps-motion heuristic (#5). Camera-fly + framing are lab-only. The real lab→prod regression vectors are #1 and #5 as pane density grows.
