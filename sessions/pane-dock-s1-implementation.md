---
title: Pane Dock S1 — canvas-resident dock + DRY lifecycle seam
type: sessions
tags: [frontend, transport-matters, canvas, react, zustand, dock, lifecycle-seam]
summary: Implemented Dock S1 (PR #76) — Option A minimized-pane dock, policy seam keeping capturedRunStore out of prod, CANVAS_LAYOUT_MARGIN unify (48→64), transparent lab bar.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-10
updated: 2026-06-10
---

## Summary

Built **Dock S1** for Transport Matters' canvas lab (`www/`), branch `feat/pane-dock-s1`, PR #76, off `main@5ff65a5`. Replaces the deleted director attach/detach surface with **Option A**: a canvas-resident dock of locally minimized panes (no `/api/runs`, no liveness polling). Spec was authoritative at `NOTES/captured-canvas/10-pane-dock-design.md`.

Gate: `pnpm lint && typecheck && test (94 files / 619 tests) && build` all green. `capturedRunStore` stays a separate lazy chunk (out of prod).

## Architecture Decisions

- **Policy seam (DRY).** `model/paneLifecycle.ts` = static `PaneLifecyclePolicy` table + `registerLifecycle`/`resolvePaneLifecycle`. The captured-run `onClose → stopRun` hook is registered **lab-side** via a side-effect import (`lab/labLifecycle.ts`, imported once by `CanvasLabRoute`). This is what keeps `capturedRunStore` out of `model/` and the prod bundle. Result: zero `kind === "captured-run"` branches in the store.
- **Generic lifecycle.** `canvasLabStore` gained `minimizePane`/`closePane`/`restorePane` + `docked[]`. The camera/node teardown (collapse-expand / leave-frame / undo-zoom) was extracted from `dismissPane` into `finalizePaneRemoval` and shared by both modes. Minimize keeps the captured run binding alive (restore re-attaches by run id); close runs the onClose hook (kills the run). In-flight spawn cancellation preserved.
- **Margin DRY.** New `CANVAS_LAYOUT_MARGIN` const in `engine/layout/types.ts` unifies the three literal `48`s (gridFit, singleRow, efficientLayout), bumped **48→64 prod-wide**, surfaced to CSS as `--canvas-layout-margin` set once at the lab shell from the const. Dock-band height reads the same var.
- **Overlay slot.** `LayoutCanvas` got a generic screen-space `overlay?` prop rendered inside `.canvas-viewport` after `.canvas-world` — pan/zoom-immune and outside the conditionally-rendered command bar, so the dock survives the TAB hide. `PaneDock` (shared `components/`) consumes it.
- **Deletions.** `DirectorPanel` (+ test), `attachCapturedRun`, `hidePane`, `CapturedRunAction`, `capturedRunStore.detachRun`/`adoptRun`. Grep-zero.

## Performance Notes

Dropping `backdrop-filter` on the transparent lab bar sheds one compositor layer (aligns with the canvas-render audit). No render-perf regression; build bundle unchanged in the prod path (`capturedRunStore` still code-split).

## Deviations from Spec

1. **DockedPane stores `{paneId, ref}`, not a `title` snapshot.** `PaneDock` derives the title via `titleForRef(ref)` at render. Rationale: importing the registry into the lab store would pull the eager viewer components (TranscriptChatPane, ResourcePane, …) into the store's import graph; `titleForRef` is pure, so deriving == snapshotting. Keeps the store decoupled from view concerns.
2. **Dock menu uses `<div role="menu">` + `<button role="menuitem">`** (not `<ul>/<li>`). Satisfies biome `noNoninteractiveElementToInteractiveRole` and is a valid ARIA menu.
3. **Kept a private `dismissPane(paneId, mode)` dispatcher** (param swapped from detach/stop → minimize/close). The spec said delete the `runAction` param + `CapturedRunAction` (done, grep-zero); the shared two-phase teardown function itself is a reasonable private helper.
4. **Transparent bar applied as-is, no label promotion.** Spec flagged the dim labels as a watch item needing a browser check. Computed contrast: `#949494` on the `#040404→#080808` gradient ≈ 6:1 (above AA), so no mitigation needed — applied the spec's exact CSS.

## Open Items

- **S2 (deferred):** reload-correct dock. The mount effect still re-opens persisted agent runs as *open* panes, so a minimized agent reopens after a browser reload. Needs a `minimized` flag in `capturedRunStore` (version bump + migrate). This is the only consumer of `onMinimize`.
- **Prod adoption (later slice):** dock for transcript/resource/exchange/picker panes; `canvasStore` grows its own `docked` + `minimizePane`; picker-close reopen. The seam + `PaneDock` + overlay are already store-agnostic for this.
