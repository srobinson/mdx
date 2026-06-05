---
title: Ordered gridFit Implementation
type: sessions
tags: [frontend, transport-matters, canvas, drag-and-drop, frozen-drag]
summary: Implemented ordered gridFit and refactored PR #95 to frozen reorder drag with slot overlay and one settle replan.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Summary

Implemented the ordered gridFit slice on branch `feat/ordered-gridfit` and PR #95. The original live reflow build landed at `775b846`, review and roadtest fixes were folded through `d365024`, and the amended frozen drag model is now pushed at `e7dead7`. The current branch follows the amended `NOTES/captured-canvas/17-ordered-gridfit.md`: lifting a pane freezes the committed layout, the overlay shows a slot indicator or terminal target, release commits one reorder replan, and same order release does nothing.

## Architecture Decisions

- Added `EngineLayoutState.order` as the durable source of truth for user pane order.
- Added shared order helpers for append, splice, move, and normalization so persistence and stores do not duplicate ordering logic.
- Removed the live reflow seam: `previewReorder` no longer exists in either store, and `planLayout` no longer accepts a tentative pane id override.
- Kept drag orchestration surface side. `createPaneReorder` is store agnostic, computes insertion indexes from frozen candidate rects, writes only `dropTargetStore` feedback during drag, gives terminal delivery precedence, and calls `commitReorder` only when the spliced order differs from the committed order.
- Added `dropTargetStore` kind `{ kind: "slot", rect }` and `CanvasDropTargetOverlay` slot rendering through the existing screen space overlay layer.
- Changed `PaneFrame` move drags to use a local live rect, matching resize behavior. This lets the lifted pane track the pointer while the store layout remains frozen until release.
- Added `useReorderSettle` so release and escape keep `paneMotion` active for the existing `LayoutCanvas -> PaneFrame layoutMotion` seam long enough for the committed replan to visibly settle.
- Exported `LAYOUT_MOTION_MS` from `PaneFrame` so the settle handoff uses the same timing as the pane layout transition.
- Review cleanup `e7dead7`: removed vestigial `PaneReorderEnd.handled`, unreachable plain move fallbacks in `CanvasSurface` and `CanvasLabRoute`, and stale dependencies.
- Preserved the 4 world px activation threshold, escape cancel, terminal highlight and delivery precedence, and membership change refresh for frozen insertion geometry.
- Detect file hover intent during `dragover` through `dataTransfer.types.includes("Files")`, because `dataTransfer.files` can be empty in browser protected mode. Keep drop classification on `dataTransfer.files`.

## Performance Notes

- The active drag no longer runs per tick layout planning, which removes the feedback loop that caused preview oscillation and expanded pane flicker.
- The lifted pane moves through local React state, so store subscribers and other panes do not re-render just to follow the pointer.
- The only release animation is the existing pane motion transition, scoped to reorder settle and escape settle.
- No bundle or Lighthouse measurements were required for this slice. Functional gates and type checks passed.

## Verification

- Focused inner loop: `cd www && npx vitest run src/session-canvas src/engine` passed with 59 files and 363 tests.
- Type check: `cd www && npx tsc -b --noEmit` passed.
- Combined type and focused loop after formatting: `cd www && npx tsc -b --noEmit && npx vitest run src/session-canvas src/engine` passed.
- Repo gate: `just check` passed, including desktop typecheck plus 7 files and 29 tests, www format, lint, typecheck, and api ruff plus mypy.
- Cleanup proof: `git diff --check && cd www && pnpm exec biome check --write src/session-canvas/dnd/paneReorder.ts src/session-canvas/components/CanvasSurface.tsx src/session-canvas/lab/CanvasLabRoute.tsx && npx tsc -b --noEmit && npx vitest run src/session-canvas` passed with 50 files and 314 tests.
- Branch pushed: `feat/ordered-gridfit` force updated from `d365024` to `d272597`, then review cleanup amended it to `e7dead7`.
- Bus replies sent to `transport-matters:general:1:4.1`: `done: d272597`, then `done: e7dead7` for the vestigial handled cleanup.

## Deviations from Spec

- None against the amended frozen drag spec.
- The previous live reflow implementation, preview store actions, tentative planning override, pending index, and hysteresis machinery were intentionally removed because the amended spec made them obsolete.
- Manual desktop `/canvas-lab` roadtest remains owned by the orchestrator unless requested separately.

## Open Items

- Await Stuart or orchestrator roadtest feedback on the slot indicator feel and settle animation.
