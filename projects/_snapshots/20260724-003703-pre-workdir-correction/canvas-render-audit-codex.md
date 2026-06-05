---
title: Canvas rendering audit, Codex frontend
created: 2026-06-08
updated: 2026-06-08
source: frontend-engineer-codex
branch: feat/canvas-pane-motion-interaction
status: filed
---

# Canvas rendering audit, Codex frontend

## Scope read

Live branch: `feat/canvas-pane-motion-interaction`.

Live tree at audit time:

- HEAD: `ea99ca0 feat(www): KISS single-level framing + unframe fly pane limit`
- Uncommitted: `www/src/session-canvas/lab/CanvasLabRoute.tsx`, `SEED_PANES = 50`
- Shared production surface: `LayoutCanvas`, `PaneFrame`, `canvas.css`, and `PaneChrome` are used by `/canvas-lab`; `LayoutCanvas`, `PaneFrame`, and `canvas.css` are also used by production `/canvas` through `CanvasSurface`.

Verification run:

- `pnpm --dir www lint`: exit 0, `Checked 224 files in 90ms. No fixes applied.`
- `pnpm --dir www typecheck`: exit 0
- `pnpm --dir www test -- src/engine/layout/gridFit.test.ts src/session-canvas/lab/canvasLabStore.test.ts src/engine/reducers/framing.test.ts src/engine/perf/frameMeter.test.ts`: exit 0, `67 passed`, `445 passed`

Browser note: the in app browser was unavailable (`Browser is not available: iab`). Standalone Playwright exercised `localhost:5174/canvas-lab`, added panes, captured screenshots, and measured frame pacing, but its tab switching path did not put the page into `document.hidden`. The supplied Chrome screenshot remains the ground truth for the tab return blanking symptom.

## Converged headline assessment

After the MoE peer challenge, I converge on per pane `backdrop-filter` as the primary headline root cause. My original paint containment thesis remains useful defense in depth, not the primary fix.

Root cause chain:

1. `.canvas-world` is one scaled transform layer with `will-change: transform` at `www/src/session-canvas/canvas.css:40-47`.
2. Every pane window carries `backdrop-filter: blur(18px)` at `www/src/session-canvas/canvas.css:112-121`, and the command bar carries `backdrop-filter: blur(16px)` at `www/src/session-canvas/canvas.css:58-72`.
3. At 50 to 71 panes under fit to content, that means 50 to 71 pane backdrop surfaces inside the scaled world.
4. After a real Chrome tab restore, most per pane GPU tile backing can remain stale or missing. A scroll or zoom mutates the world transform and forces re raster, restoring the panes.
5. Framer opacity is refuted by source and peer CDP measurement: open panes animate to `opacity: 1` in `www/src/engine/react/PaneFrame.tsx:151-157`.

Decisive real browser A/B still recommended: at 71 panes and fit scale below 1, test removing per pane `backdrop-filter` only versus removing paint containment only, then switch away from the tab and back. Prediction after peer debate: removing backdrop filter fixes the blanking; paint containment relaxation alone is insufficient.

## Executive summary

Findings: 9 total.

- Critical: 1
- High: 3
- Medium: 4
- Low: 1

Minimal headline fix: gate or remove per pane `backdrop-filter` at high density or any scale below 1. As cheap insurance, relax `[data-pane-frame]` containment from `layout paint style` to `layout style`.

## Findings

### 1. Critical: tab return blanks panes because per pane backdrop filters create too many scaled compositor surfaces

Location:

- `www/src/session-canvas/canvas.css:40-47`
- `www/src/session-canvas/canvas.css:58-72`
- `www/src/session-canvas/canvas.css:112-121`
- `www/src/engine/react/LayoutCanvas.tsx:56-62`
- `www/src/engine/react/PaneFrame.tsx:151-157`

Evidence:

- The supplied real Chrome screenshot shows the exact failure after returning to the tab: route says `71 panes`, fit scale is below 1, and only scattered pane islands paint while most expected pane regions are black. A repaint by scroll or zoom restores them.
- Current CSS still has `backdrop-filter` on every `.canvas-pane-window` at `canvas.css:121` and on the command bar at `canvas.css:72`.
- Peer CDP measurement on the live tab found 50 of 50 pane windows were backdrop filtered, with world scale `0.545` and pane computed opacity `1`.
- My controlled run at `2048 x 1152`, 71 panes, fit scale `0.5274725274725275` measured `72` backdrop filtered elements and showed pan cost dominated by those surfaces.
- Removing paint containment alone did not improve the controlled pan path, while removing pane and command bar backdrop filters plus heavy shadows dropped pan p95 from `50.0 ms` to `16.8 ms`.

Impact:

- `/canvas-lab` becomes visually unusable after a normal Chrome tab switch at high pane count.
- The same CSS and `PaneFrame` surface are shared with production `/canvas`, so the failure mode can cross into real session panes as density grows.

Recommended fix:

1. Gate or remove `.canvas-pane-window { backdrop-filter: blur(18px) }` at high density or when `layout.viewport.scale < 1`.
2. Prefer a flat tokenized surface fill plus a single border in dense mode.
3. Also relax `[data-pane-frame]` from `contain: layout paint style` to `contain: layout style` as defense in depth.
4. Consider removing always on `.canvas-world { will-change: transform }` outside active framing, panning, or zooming.
5. Add a real Chrome regression or manual smoke script that records before and after tab restore screenshots at 71 panes.

### 2. High: backdrop filters and pane shadows dominate pan cost at 71 panes

Location:

- `www/src/session-canvas/canvas.css:68-72`
- `www/src/session-canvas/canvas.css:112-121`
- `www/src/session-canvas/canvas.css:197-200`

Evidence:

Standalone Playwright at `2048 x 1152`, current dirty tree, 71 panes, fit scale `0.5274725274725275`:

- DOM: `1202` elements
- Backdrop filtered elements: `72`
- Baseline shift drag pan: p95 frame delta `50.0 ms`, max `82.7 ms`, `24` frames over `33 ms`
- CSS injection removing `.canvas-pane-window` and `.canvas-command-bar` `backdrop-filter` plus shadows, and making pane bodies non scrollable for the stress case: p95 `16.8 ms`, max `50.3 ms`, `3` frames over `33 ms`
- Removing paint containment alone: p95 `66.6 ms`, `26` frames over `33 ms`

Impact:

- Pan misses 60 fps before any real transcript viewer content is present.
- The lab currently measures the cost of translucent blur surfaces, not just layout interaction.

Recommended fix:

Use the same dense mode as Finding 1. Disable blur and heavy shadows at high pane counts or fit scale below 1.

### 3. High: teleport threshold is zero, so position spring code is unreachable

Location:

- `www/src/engine/react/PaneFrame.tsx:28-31`
- `www/src/engine/react/PaneFrame.tsx:60-68`
- `www/src/engine/react/PaneFrame.tsx:76-78`
- `www/src/engine/react/PaneFrame.tsx:140-147`

Evidence:

`TELEPORT_DISTANCE_FACTOR = 0` at line 31. `teleport` is computed as `moved > Math.max(node.rect.width, node.rect.height) * TELEPORT_DISTANCE_FACTOR` at line 68. With factor 0, any nonzero movement teleports, so `positionTransition` becomes `SNAP_TRANSITION` for every position change.

Impact:

- The comments about neighbour shuffle and row slide springs are inaccurate.
- The normal position spring branch exists in code but is practically dead for position changes.
- The intended motion feel cannot be audited because the threshold disables it.

Recommended fix:

Choose one direction explicitly:

1. Restore a real factor if small moves should spring.
2. Delete the dead position spring branch and update comments if all layout position changes should snap.

### 4. High: global Tab interception breaks keyboard navigation

Location:

- `www/src/session-canvas/lab/CanvasLabRoute.tsx:34-44`

Evidence:

The route installs a `window` keydown handler. For any plain Tab key it calls `event.preventDefault()` and toggles command bar visibility.

Impact:

- Keyboard users cannot tab through Add pane, Organize, Fit to content, layout select, layout controls, pane Frame, pane Close, or pane regions.
- This blocks WCAG keyboard operability for the lab route.
- Screen reader navigation becomes unpredictable because the command bar can disappear during expected focus traversal.

Recommended fix:

Do not bind plain Tab globally. Use a visible toggle or a non essential shortcut that ignores events from form controls.

### 5. Medium: viewport changes re render every pane and rebuild every pane chrome closure

Location:

- `www/src/engine/react/LayoutCanvas.tsx:29-31`
- `www/src/engine/react/LayoutCanvas.tsx:64-80`
- `www/src/session-canvas/lab/CanvasLabRoute.tsx:116-132`
- `www/src/session-canvas/lab/viewers/PaneSizeReadout.tsx:5-12`

Evidence:

- `LayoutCanvas` receives one monolithic `layout` object. Any viewport pan or zoom changes `layout.viewport`, so the component maps every open node again.
- The lab passes an inline `renderPane` closure that captures `layout.focusedPaneId`, `framedPane`, and action closures, so every viewport render recreates pane chrome for every pane.
- Each pane body includes `PaneSizeReadout`, which subscribes to `state.layout.nodes[paneId]?.rect`.

Impact:

- The browser does React work for all panes even when a pan should only update the world transform.
- Real production viewers will be heavier than the lab cards.

Recommended fix:

Split viewport transform updates from pane child rendering. Memoize pane frames and pane chrome by pane id, focus state, frame state, lifecycle, and rect. Pass stable action callbacks.

### 6. Medium: bulk layout planning is O(N squared) in object spreads

Location:

- `www/src/session-canvas/lab/canvasLabStore.ts:145-165`
- `www/src/engine/reducers/layoutState.ts:62-73`

Evidence:

`planLayout` loops every planned rect and calls `updateNodeRect`. `updateNodeRect` spreads the full `state.nodes` map on every call. At 71 panes, one organize or add plan copies the nodes map once per pane.

Measured on the current dirty tree while adding from 50 to 71 panes:

- Add pane duration p95: `49 ms`
- Max add duration: `52 ms`
- `5` of `21` add actions exceeded `33 ms`

Impact:

Add and Organize scale poorly with pane count.

Recommended fix:

Add a bulk reducer, for example `updateNodeRects(state, rects)`, that copies `state.nodes` once and updates all changed rects in a single pass. Keep the single node helper for direct drag moves.

### 7. Medium: current dirty tree turns the lab default into a 50 pane stress route

Location:

- `www/src/session-canvas/lab/CanvasLabRoute.tsx:11`
- `www/src/session-canvas/lab/CanvasLabRoute.tsx:46-50`

Evidence:

The uncommitted route sets `SEED_PANES = 50`, while the nearby comment still says "Seed a few panes". A fresh visit now boots directly into a high density, scaled, 1200 element scene.

Impact:

- The default route is no longer a small experimental lab. It immediately exercises the worst case paint path.
- It hides whether regressions come from normal lab usage or stress usage.

Recommended fix:

Restore the small seed count for default lab entry. If the 50 pane state is needed for repro, expose it as a named stress preset, query param, or button.

### 8. Medium: shared `LayoutCanvas` now snaps all pane size motion whenever zoomed

Location:

- `www/src/engine/react/LayoutCanvas.tsx:36`
- `www/src/engine/react/LayoutCanvas.tsx:64-72`
- `www/src/session-canvas/components/CanvasSurface.tsx:38-75`

Evidence:

`instant={zooming || framing || zoomed}` applies to every pane whenever `layout.viewport.scale` differs from 1. `CanvasSurface` uses the same `LayoutCanvas` for production `/canvas`, so production inherits this behavior even though only the lab passes a `framing` prop.

Impact:

This is a valid jank guard for high density fit views, but it is a broad shared behavior change. A production user who zooms a small canvas loses smooth pane size transitions even at low pane count.

Recommended fix:

Gate the instant path on density or explicit layout mode, not only scale. Examples: `nodes.length > denseThreshold`, `layoutMotion="instant"`, or a parent supplied `disablePaneSizeMotion` flag.

### 9. Low: resize handle is pointer only and hidden from accessibility APIs

Location:

- `www/src/session-canvas/components/PaneChrome.tsx:77-81`
- `www/src/session-canvas/canvas.css:202-209`

Evidence:

The resize affordance is an `aria-hidden="true"` div with a resize cursor and drag data attribute. It is not focusable and has no keyboard path.

Impact:

Keyboard only users cannot resize panes. Screen reader users do not know the resize affordance exists.

Recommended fix:

Use a focusable control with an accessible label and keyboard resizing, or expose a pane actions menu with size presets. If freeform keyboard resize is too much for the lab slice, document it as a known limitation and keep it out of production claims.

## Positive findings

- `PaneFrame` defers content reflow during resize by using `liveRect` locally and committing the store rect only on drag release. That is the right direction for 60 fps pointer work.
- Single level framing is simpler than nested frame history and avoids a confusing stack model.
- Static per pane `will-change` removal was correct. It reduced layer pressure, though it did not remove the independent `backdrop-filter` layer source.
- Typecheck, lint, and targeted tests are green on the live tree.

## Minimal fix order

1. Fix the headline paint bug: gate or remove per pane `backdrop-filter` in dense or scaled mode.
2. Relax pane containment from `layout paint style` to `layout style` as defense in depth.
3. Restore `SEED_PANES` to a small default or move 50 panes into an explicit stress preset.
4. Remove plain Tab interception.
5. Decide the teleport threshold contract and either restore position springs or delete dead code.
6. Add a bulk rect reducer.
7. Split viewport transform updates from pane child rendering.
8. Revisit shared `LayoutCanvas` motion gating for production.
9. Make resize keyboard accessible or mark it as lab only.

## Open verification gap

I could not make the available browser harness create a real hidden tab state. The next reviewer should run the decisive real Chrome A/B after applying only the backdrop filter change, then only the containment change. Passing criterion: with 71 panes at fit scale, switching away from the tab and back paints all pane chrome and content without requiring a scroll or zoom repaint.
