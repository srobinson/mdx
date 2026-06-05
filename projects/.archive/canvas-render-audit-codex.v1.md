---
title: Canvas rendering audit, Codex frontend
created: 2026-06-08
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

Browser note: the in app browser was unavailable (`Browser is not available: iab`). Standalone Playwright could exercise `localhost:5174/canvas-lab`, add panes, capture screenshots, and measure frame pacing, but its tab switching path did not put the page into `document.hidden`. I used the supplied Chrome screenshot as the real tab return evidence and verified the live DOM, CSS, and performance shape against the current tree.

## Executive summary

Findings: 8 total.

- Critical: 1
- High: 2
- Medium: 4
- Low: 1

Headline assessment: the blank pane failure is best explained by per pane paint containment under one scaled compositor world. Permanent per pane `will-change` was already removed, and Framer opacity does not match the symptom or source shape. The minimal fix is to remove `paint` from `[data-pane-frame]` containment, then keep the visual load cuts from Finding 2 so the repaint cost remains acceptable.

## Findings

### 1. Critical: tab return blanks most panes because every pane is a paint contained island inside one scaled world

Location:

- `www/src/session-canvas/canvas.css:40-47`
- `www/src/session-canvas/canvas.css:49-55`
- `www/src/engine/react/LayoutCanvas.tsx:56-62`
- `www/src/engine/react/PaneFrame.tsx:125-157`

Evidence:

- The current CSS leaves `[data-pane-frame="true"]` with `contain: layout paint style`; Chromium reports that as `contain: content` in computed style.
- The panes are all absolute children under `.canvas-world`, whose transform is a single `translate3d(...) scale(...)` compositor transform.
- The supplied real Chrome screenshot shows the exact failure after returning to the tab: route says `71 panes`, the viewport is at fit scale below 1, and only scattered pane islands paint while most expected pane regions are black. A repaint by scroll or zoom restores them.
- Removing the static per pane `will-change` did not fix the failure, and the current live CSS no longer has that property at `canvas.css:49-55`.
- Framer opacity is a poor fit: open panes animate to `opacity: 1` and `scale: 1` in `PaneFrame.tsx:151-157`; there is no per pane state branch that would keep most panes invisible after tab return while a viewport repaint restores them.

Impact:

- Core `/canvas-lab` interaction becomes visually unusable after a normal Chrome tab switch at high pane count.
- The same CSS and `PaneFrame` surface are shared with production `/canvas`, so the failure mode can cross into real session panes as density grows.

Recommended fix:

1. Change pane frame containment to remove paint containment:
   - from `contain: layout paint style`
   - to `contain: layout style`
2. Keep layout containment for internal pane layout isolation.
3. Pair the fix with Finding 2 so the larger paint invalidation does not reintroduce jank.
4. Add a browser regression that opens a high density scaled canvas, backgrounds the page in real Chrome if the harness supports it, restores it, and asserts the screenshot contains all expected pane chrome. If the harness cannot force hidden tabs, make the test a manual smoke with saved before and after screenshots.

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
- Removing paint containment alone did not improve pan cost in the controlled run: p95 `66.6 ms`, still `26` frames over `33 ms`

Impact:

- Pan misses 60 fps by a wide margin before any real transcript viewer content is present.
- The lab currently measures the cost of 72 translucent blur surfaces, not just layout interaction.

Recommended fix:

1. At high density or any fit scale below 1, disable `backdrop-filter` and the heavy pane shadow stack.
2. Prefer a flat tokenized surface fill plus a single border in dense mode.
3. Keep blur for low pane counts where it adds polish without blowing the compositor budget.
4. Consider locking pane body overflow in the stress cards, or give real viewers one virtualized scroll surface rather than every pane body creating a scrollable region.

### 3. High: global Tab interception breaks keyboard navigation

Location:

- `www/src/session-canvas/lab/CanvasLabRoute.tsx:34-44`

Evidence:

The route installs a `window` keydown handler. For any plain Tab key it calls `event.preventDefault()` and toggles command bar visibility.

Impact:

- Keyboard users cannot tab through Add pane, Organize, Fit to content, layout select, layout controls, pane Frame, pane Close, or pane regions.
- This blocks WCAG keyboard operability for the lab route.
- It also makes screen reader navigation unpredictable because the command bar can disappear during expected focus traversal.

Recommended fix:

1. Do not bind plain Tab globally.
2. Use a non essential chord such as `?`, `Ctrl+K`, or a visible command bar toggle button.
3. If a shortcut remains, scope it to the canvas viewport only and ignore events when focus is inside controls.

### 4. Medium: viewport changes re render every pane and rebuild every pane chrome closure

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
- This compounds the paint cost from Finding 2.
- Real production viewers will be heavier than the lab cards.

Recommended fix:

1. Split viewport transform updates from pane child rendering.
2. Memoize pane frames and pane chrome by pane id, focus state, frame state, lifecycle, and rect.
3. Pass stable action callbacks and move lab viewer selection into a memoized pane component.
4. Keep `PaneSizeReadout` lab only, or pass dimensions as props from the pane rect already being rendered.

### 5. Medium: bulk layout planning is O(N squared) in object spreads

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

- Add and Organize scale poorly with pane count.
- The code produces unnecessary allocation churn before React and paint costs even start.

Recommended fix:

Add a bulk reducer, for example `updateNodeRects(state, rects)`, that copies `state.nodes` once and updates all changed rects in a single pass. Keep the single node helper for direct drag moves.

### 6. Medium: current dirty tree turns the lab default into a 50 pane stress route

Location:

- `www/src/session-canvas/lab/CanvasLabRoute.tsx:11`
- `www/src/session-canvas/lab/CanvasLabRoute.tsx:46-50`

Evidence:

The uncommitted route sets `SEED_PANES = 50`, while the nearby comment still says "Seed a few panes". A fresh visit now boots directly into a high density, scaled, 1200 element scene.

Impact:

- The default route is no longer a small experimental lab. It immediately exercises the worst case paint path.
- It hides whether regressions come from normal lab usage or stress usage.
- It makes the headline bug easier to hit, but it should not ship as the default without explicit intent.

Recommended fix:

Restore the small seed count for default lab entry. If the 50 pane state is needed for repro, expose it as a named stress preset, query param, or button.

### 7. Medium: shared `LayoutCanvas` now snaps all pane size motion whenever zoomed

Location:

- `www/src/engine/react/LayoutCanvas.tsx:36`
- `www/src/engine/react/LayoutCanvas.tsx:64-72`
- `www/src/session-canvas/components/CanvasSurface.tsx:38-75`

Evidence:

`instant={zooming || framing || zoomed}` applies to every pane whenever `layout.viewport.scale` differs from 1. `CanvasSurface` uses the same `LayoutCanvas` for production `/canvas`, so production inherits this behavior even though only the lab passes a `framing` prop.

Impact:

- This is a valid jank guard for high density fit views, but it is a broad shared behavior change.
- A production user who zooms a small canvas loses smooth pane size transitions even at low pane count.

Recommended fix:

Gate the instant path on density or explicit layout mode, not only scale. Examples: `nodes.length > denseThreshold`, `layoutMotion="instant"`, or a parent supplied `disablePaneSizeMotion` flag. Keep production default behavior intentional and tested.

### 8. Low: resize handle is pointer only and hidden from accessibility APIs

Location:

- `www/src/session-canvas/components/PaneChrome.tsx:77-81`
- `www/src/session-canvas/canvas.css:202-209`

Evidence:

The resize affordance is an `aria-hidden="true"` div with a resize cursor and drag data attribute. It is not focusable and has no keyboard path.

Impact:

- Keyboard only users cannot resize panes.
- Screen reader users do not know the resize affordance exists.

Recommended fix:

Use a focusable control with an accessible label and keyboard resizing, or expose a pane actions menu with size presets. If freeform keyboard resize is too much for the lab slice, document it as a known limitation and keep it out of production claims.

## Positive findings

- `PaneFrame` defers content reflow during resize by using `liveRect` locally and committing the store rect only on drag release. That is the right direction for 60 fps pointer work.
- Single level framing is simpler than nested frame history and avoids a confusing stack model.
- The static per pane `will-change` removal was correct. It reduced layer pressure even though it did not resolve the headline paint bug.
- Typecheck, lint, and targeted tests are green on the live tree.

## Minimal fix order

1. Fix the headline paint bug: remove `paint` containment from pane frames.
2. Add dense mode paint cuts: remove blur and heavy shadow for high pane counts or scaled fit views.
3. Restore `SEED_PANES` to a small default or move 50 panes into an explicit stress preset.
4. Remove plain Tab interception.
5. Add a bulk rect reducer.
6. Split viewport transform updates from pane child rendering.
7. Revisit shared `LayoutCanvas` motion gating for production.
8. Make resize keyboard accessible or mark it as lab only.

## Open verification gap

I could not make the available browser harness create a real hidden tab state. The next reviewer should try one real Chrome reproduction after applying only the containment change. Passing criterion: with 71 panes at fit scale, switching away from the tab and back paints all pane chrome and content without requiring a scroll or zoom repaint.
