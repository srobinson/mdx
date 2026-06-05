---
title: Ordered gridFit Plan Review for Transport Matters
type: research
tags: [transport-matters, captured-canvas, ordered-gridfit, plan-review, bus-review]
summary: Independent review found three initial conditional fixes; final gate-label cleanup was verified and the plan was signed off.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Executive Summary

Reviewed `NOTES/captured-canvas/17-ordered-gridfit-plan.md` against the approved `NOTES/captured-canvas/17-ordered-gridfit.md` spec, using `NOTES/captured-canvas/16-unified-drag-model.md` only for context. The plan covers the main spec surface, but needs three changes before implementation: a strategy-planned reorder guard, duplicate-safe order normalization, and gate wording that distinguishes repo recipes from inner-loop commands.

## Project Metadata

- Project: `transport-matters`
- Area: `www` React canvas frontend
- Baseline: `main` at `46982ad2d0a3`
- Indexed by fmm: yes, fmm returned 687 files and 104,318 LOC
- Relevant stack: React, zustand, `@use-gesture`, framer-motion, vitest
- Repo gates observed in justfiles:
  - Root `justfile`: `just check`, `just test`
  - `www/justfile`: `just check`, `just test`
  - `desktop/justfile`: `just check`, `just test`
  - `api/justfile`: `just check`, `just test`

## Architecture

The approved spec makes pane sequence an engine model concern. `EngineLayoutState` gains an `order: PaneId[]`, strategies continue to receive ordered pane ids, and live reflow uses a tentative order override so escape and terminal delivery can revert to committed order.

The plan maps implementation across:

- Engine state and mutations: `www/src/engine/types.ts`, `www/src/engine/reducers/layoutState.ts`
- Planning: `www/src/session-canvas/model/layoutPlanning.ts`
- Persistence: `www/src/session-canvas/persistence/canvasPersistOptions.ts`, `canvasPanePersistence.ts`
- Stores: `www/src/session-canvas/model/canvasStore.ts`, `www/src/session-canvas/lab/canvasLabStore.ts`
- Gesture and surface wiring: `www/src/engine/react/PaneFrame.tsx`, `LayoutCanvas.tsx`, `CanvasSurface.tsx`, `CanvasLabRoute.tsx`
- Shared drag feedback: `www/src/session-canvas/dnd/dropTargetStore.ts`, `CanvasDropTargetOverlay.tsx`, `paneReorder.ts`

## Key Patterns

- The design keeps live reflow tentative until release. This protects escape revert and terminal delivery revert.
- The plan reuses existing seams: `LayoutCanvas.paneMotion`, `PaneFrame` move drag, `canvasDrop` terminal delivery helpers, and shared `useCanvasDropTargets` wiring.
- The strongest DRY direction is Task 9's note to collapse duplicated terminal delivery logic into shared `locatorFor` and `terminalUnder` helpers instead of maintaining separate pane drop and reorder delivery paths.

## Detailed Findings

### Finding 1: Missing strategy-planned guard in Task 9

Severity: high.

The spec says floating mode is untouched and a move drag in floating mode stays a plain move: `NOTES/captured-canvas/17-ordered-gridfit.md:52-53`. It also scopes reorder lifting to a strategy-planned canvas: `NOTES/captured-canvas/17-ordered-gridfit.md:65-68`.

Task 9's controller test fixture uses `mode: "floating"` while expecting preview behavior: `NOTES/captured-canvas/17-ordered-gridfit-plan.md:794-829`. The implementation sketch computes insertion and calls `previewReorder` without a strategy guard: `NOTES/captured-canvas/17-ordered-gridfit-plan.md:922-942`. Surface wiring calls `reorder.onMove` for every pane move: `NOTES/captured-canvas/17-ordered-gridfit-plan.md:993-1000`.

Required change: add an explicit strategy-planned guard, either in `createPaneReorder` deps or at surface wiring, and test that floating moves never preview, commit, set reorder motion, or set the reorder overlay.

### Finding 2: `normalizeLayoutOrder` needs duplicate removal

Severity: medium.

The spec invariant is that `order` contains exactly the ids in `nodes`: `NOTES/captured-canvas/17-ordered-gridfit.md:36-44`. The plan's `normalizeLayoutOrder` drops unknown ids and appends missing ids, but preserves duplicate known ids because it filters the persisted array directly: `NOTES/captured-canvas/17-ordered-gridfit-plan.md:123-130`.

Required change: de-duplicate known ids while preserving first occurrence, then append missing node ids. Add a stale payload test such as `['b', 'b', 'ghost']` over `{a, b}` yielding `['b', 'a']`.

### Finding 3: Gate wording mixes repo recipes with inner-loop commands

Severity: medium.

The spec asks for gates verbatim: repo `just check`, api `just test`, www vitest under `just check`, desktop `pnpm test`: `NOTES/captured-canvas/17-ordered-gridfit.md:148-149`. Root and package justfiles expose `just check` and `just test`; `www/package.json` maps `test` to `vitest run`, but `npx vitest run` and `npx tsc -b --noEmit` are not the repo recipes.

The plan front matter says gates are repo `just check`, www `npx vitest run`: `NOTES/captured-canvas/17-ordered-gridfit-plan.md:9`. Multiple task steps use `npx vitest run` and `npx tsc -b --noEmit` as gates, for example `NOTES/captured-canvas/17-ordered-gridfit-plan.md:136`, `628`, and `1028`.

Required change: label targeted `npx` commands as inner-loop checks only. Use `just check` and `just test` for gates, with package scoped `pnpm test` acceptable where the spec names desktop `pnpm test`.

### Clean Citation Checks

Verified against `main` and fmm outlines:

- `www/src/session-canvas/components/CanvasSurface.tsx` exports `CanvasSurface` and currently wires `useCanvasDropTargets` into `LayoutCanvas`.
- `www/src/session-canvas/lab/CanvasLabRoute.tsx` exports `CanvasLabRoute` and currently wires `useCanvasDropTargets` into `LayoutCanvas`.
- `www/src/session-canvas/dnd/useCanvasDropTargets.ts` exports `useCanvasDropTargets` and has `onMovePaneEnd` delegating to `deliverPaneDropToTerminal`.
- `www/src/session-canvas/dnd/canvasDrop.ts` exports `deliverPaneDropToTerminal`, `paneIdAtPoint`, and `paneIdAtWorldPoint`.
- `www/src/session-canvas/viewers/terminal/pasteRegistry.ts` exports `registerPasteHandle`, `resolvePasteHandle`, and `escapeDropLocator`.
- `www/src/engine/react/LayoutCanvas.tsx` has the `paneMotion` prop and forwards it into `PaneFrame.layoutMotion`.

## Dependencies

Critical dependencies in the reviewed plan:

- `zustand`: canvas stores and the proposed drop-target store.
- `@use-gesture/react`: pane move and resize gesture handling in `PaneFrame`.
- `framer-motion`: pane transitions and the existing `layoutMotion` seam used for live reflow.
- `vitest`: frontend test runner, normally through package scripts or `just` recipes.

## Relevance to Helioy

This plan touches the shared captured canvas interaction model. The strategy guard matters because future Helioy canvas work relies on preserving the distinction between strategy-planned pane sequence and true freeform positioning.

## Correction Round Delta Review

On the correction round, `NOTES/captured-canvas/17-ordered-gridfit-plan.md` was re-read from disk and only the named deltas were verified. Most corrections landed:

- Tech Stack now declares the repo gate as `just check && just test` and globally labels `npx vitest run` / `npx tsc -b --noEmit` as inner-loop checks.
- Task 1 adds duplicate-safe `normalizeLayoutOrder`, duplicate persisted-id test coverage, and shared `splicePaneOrder`.
- Task 3 removes `tentativeOrderFor`, points stores and controller at `splicePaneOrder`, and adds an `openPaneIds` non-open lifecycle test.
- Task 4 names `rebuildPersistedCanvasState`, `RebuiltCanvasState`, `model/canvasStore.persistence.ts`, and `lab/canvasLabStore.persistence.ts` for order threading.
- Task 6 corrects `LayoutCanvas -> PaneLayer -> single PaneFrame` prop threading and calls out stable props for the memoized pane layer.
- Task 8 adds `CanvasDropTargetOverlay.test.tsx` with viewport mapping assertions.
- Task 9 adds floating-mode reconciliation, `sameOrder` and `previewed` guards, zero-move and drag-back-home tests, delete-old-path instructions for `useCanvasDropTargets.onMovePaneEnd` and `deliverPaneDropToTerminal`, stable module-level `paneBodyDrag`, and dragover/hint/dragleave tests.

Residual issue sent to the orchestrator: Tasks 4, 6, 7, and 9 still used headings such as `Run gates` or `Run all gates` for npx-only steps, despite the top-level gate delta declaring those commands inner-loop only. Signoff was escalated pending that label cleanup.

## Final Gate-Label Cleanup Verification

A follow-up correction retitled the affected headings. Disk verification found:

- Task 1 Step 5: `Full www inner-loop sweep plus `just check`, commit`.
- Task 4 Step 4, Task 6 Step 4, and Task 7 Step 2: `Run inner-loop checks, commit`.
- Task 9 Step 6: `Run inner-loop checks plus `just check``.
- The only remaining step titled `Gates` is Task 10 Step 1, whose command is `just check && just test`.

Final bus reply: `signoff: I sign off on 17-ordered-gridfit-plan.md as currently filed`.

## Open Questions

None for this review round.
