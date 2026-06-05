---
title: F2 layout engine OSS leverage — transitions, planner model, pan/zoom
type: research
tags: [transport-matters, session-canvas, frontend, animation, layout, oss]
summary: Keep Motion (already wired) for FLIP, keep hand-rolled efficientLayout, keep custom useCanvasViewport; no F1 rewrite.
status: active
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

# F2 Layout Engine: OSS Leverage Scout

Versions verified against npm/MDN June 2026. F1 already ships `motion` (^12.40.0) and `@use-gesture/react` (^10.3.1) on React 19.2.5 / Vite 8. `PaneFrame.tsx` is already a `motion.div` using `layoutId={paneId}` plus `animate={{x,y,opacity}}` — Motion is the installed, in-place transition engine.

## Q1 — Transitions (FLIP between planner geometries)

**Verdict: Keep Motion (formerly Framer Motion). It is already installed and already wired into `PaneFrame`.** Motion is the only option that animates DOM elements between geometries *we* compute, runs on the compositor (transform/opacity), and lets us drive `x/y` from our rects without owning the DOM tree. The native View Transitions API is the credible challenger but its React binding (`unstable_ViewTransition`) is Canary-only, not in stable React 19, and it snapshots/cross-fades the whole document per transition — wrong model for N independently moving panes at 60fps. Stay on Motion; revisit View Transitions when it ships stable and proves N-pane concurrency.

| Option | What it gives us | Coupling cost | License / health | Verdict |
| --- | --- | --- | --- | --- |
| **Motion `layout`/`layoutId`** | FLIP via `layoutId`, transform-only, `LayoutGroup` to sync sibling panes, `layoutDependency` to gate measures, reduced-motion built in | Low — already the seam; we keep owning rects and pass them to `animate` | MIT; v12.38.0 (2026-03-17), very active, React 19 | **Adopt (already in use)** |
| Native View Transitions API | GPU cross-fade morph; zero deps | High — whole-document snapshot model fights per-pane control; React binding `unstable_ViewTransition` is Canary, not stable R19 | Web standard; Chrome 111+/Safari 18+/Firefox 144+ | Skip (watch) |
| react-flip-toolkit | Configurable spring FLIP | Medium — second animation runtime alongside Motion | MIT; v7.2.4, last publish ~2yr ago (stale) | Skip |
| @formkit/auto-animate | One-line auto FLIP on child add/remove/reorder | Medium — it owns the heuristic; we cannot feed it our scored rects | MIT; v0.9.0 (~9mo), active | Skip |
| Hand-rolled WAAPI FLIP | Full control, zero deps | High — reimplements what Motion already does in-repo | n/a | Skip |

## Q2 — Planner / layout model behind our seam

**Verdict: Keep our hand-rolled `efficientLayout.ts`.** Every mature library evaluated *owns the DOM and content* (renders panels, tabs, drag chrome itself), which violates the `renderPane(paneId)` seam and the content-agnostic `PaneNode` contract. None ships a reusable, importable pure geometry planner we could adopt without dragging in their render tree. The closest borrowable *idea* is the n-ary split-tree model used by dockview/react-mosaic — but that is a pattern to mirror in our own reducers (already the F2 plan in fe-spec §7.2), not a dependency to adopt. The one optional, low-coupling add is `react-resizable-panels` for tiling *resize handle* mechanics only — but our `PaneFrame` already plumbs resize gestures via `@use-gesture/react`, so even that is a skip unless handle ergonomics prove painful.

| Option | Geometry model vs owns DOM | Coupling cost | License / health | Verdict |
| --- | --- | --- | --- | --- |
| react-mosaic | Owns DOM + content + drag chrome | Disqualifying for seam | MIT; R16–19, active | Skip (borrow split-tree idea only) |
| dockview | Owns DOM; tabs/groups/grids/float | Disqualifying | MIT; v-line active, ~99k wk dl | Skip (borrow split-tree idea only) |
| rc-dock | Owns DOM/docking | Disqualifying | MIT; lower adoption | Skip |
| @lumino/widgets | Owns DOM; imperative widget tree (JupyterLab) | Disqualifying; non-React imperative model | BSD-3 | Skip |
| golden-layout | Owns DOM; imperative | Disqualifying | MIT; maintenance uneven | Skip |
| react-resizable-panels | Resize handle mechanics (still renders panels) | Medium — overlaps our gesture plumbing | MIT; v4.11.2, active | Skip (optional handles only) |
| @xyflow/react (React Flow) | Owns node/edge canvas rendering | Disqualifying; graph canvas, not tiling | MIT; active | Skip |
| tldraw | Owns full infinite-canvas SDK | Disqualifying; also non-OSI license (not MIT/Apache) | tldraw license (watermark/commercial terms) | Skip (license + scope) |

License note: tldraw is **not** MIT/Apache — its license carries watermark/commercial terms, which alone disqualifies it for the littleorgans-reuse mandate.

## Q3 — Infinite canvas pan/zoom

**Verdict: Keep custom `useCanvasViewport`.** `react-zoom-pan-pinch` (v4.0.3, MIT, active) uses the same CSS-transform approach we already implement, and it wraps/owns its transform container — adopting it would add a dependency and a wrapper component to replicate behavior we already have, with no accuracy or perf gain. Our cursor-anchored zoom via inverse transform (fe-spec §5.1) is the standard technique; nothing materially better has appeared since early 2026.

| Option | What it gives us | Coupling cost | License / health | Verdict |
| --- | --- | --- | --- | --- |
| Custom `useCanvasViewport` | Cursor-anchored CSS-transform pan/zoom on one world layer | None | in-repo | **Keep** |
| react-zoom-pan-pinch | Same CSS-transform model, packaged | Medium — owns its transform wrapper | MIT; v4.0.3, active | Skip |

## Does this trigger an F1 engine rewrite? (must be NO)

**NO.** Every recommendation is "keep what F1 shipped": Motion is already the `PaneFrame` transition engine, `efficientLayout.ts` stays the planner (extended with the n-ary split tree in F2), and `useCanvasViewport` stays the pan/zoom layer. No new runtime dependency is required; the `PaneNode` / `renderPane(paneId)` seam is untouched.
