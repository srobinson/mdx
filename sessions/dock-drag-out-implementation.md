---
title: Dock drag-out implementation (doc 18)
type: sessions
tags: [frontend, transport-matters, captured-canvas, dock, html5-dnd]
summary: Dock rows are HTML5 drag sources; drops restore at the slot under the pointer or paste locators into terminals (PR#96)
status: active
source: frontend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

# Dock Drag-Out Implementation

## Summary

Implemented `NOTES/captured-canvas/18-dock-drag-out.md` (signed against main cf51be2) on
`feat/dock-drag-out`, PR#96, squash title "feat(canvas): drag dock entries onto the canvas and
terminals". Three commits: restore-at-index store substrate, dock drop resolution seams, drag-out
feature surface. TDD throughout (every slice red-green), gates `just check && just test` green,
www e2e 42/42 across chromium/firefox/webkit including the new dock drag-out scenario.

## Architecture Decisions

- `restorePaneAtIndex(paneId, index)` on both stores composes the existing restore with a
  `movePaneOrder` splice inside one `set`: the seed-then-plan helpers (`planSpawnedPaneLayout`,
  lab `spawnPaneLayout`) gained an optional `orderIndex` threaded between seed and plan, so the
  pane never flashes at the tail. `restorePane` delegates with the tail index (no-op splice),
  keeping one path per store.
- `locatorForPaneRef` (the promoted shared predicate) lives in `dnd/canvasDrop.ts` beside its
  inverse `refForLocator`, not in `paneDndCallbacks.ts` where the private mapping sat: a
  paneDndCallbacks home would create an import cycle with `handleDockDrop`. Consumers:
  `deliveryTargetAt`, the dragover resolver, `handleDockDrop`.
- `closestPaneAtWorldPoint` extracted from `createWorldSpaceCollision` over canonical
  `{x,y,width,height}` world rects; the collision converts dnd-kit ClientRects at the boundary,
  the dock drop feeds `layout.nodes` directly. One targeting geometry for reorder and dock drops.
- `dnd/dockDragSource.ts` owns the mime constant, the module-scoped in-flight holder
  (protected-mode dragover cannot read the payload), and `parseDockDragPayload` (guarded parse,
  hostile/cross-window payloads resolve to null).
- Paste branch bumps the entry via `dockPane(refForLocator(locator))`, converging on the same
  substrate as external-drop paste and keeping `paneIdForRef` de-dupe consistent.

## Deviations from Spec

- `effectAllowed` is `copyMove`, not the spec's `copy`: the spec's own per-target dropEffect
  alignment (`move` over surface) would otherwise have the browser veto surface drops entirely.
- `dragleave` clears only the overlay, not the holder. The spec's clear-down sentence reads as
  both, but dragleave fires on every internal boundary crossing and on leave/re-enter; clearing
  the holder there would kill terminal targeting (decision 3) for the rest of the drag. `drop`
  and `dragend` clear both; dragend always fires on a same-window source.
- Kill-button opt-out adds a dragstart target guard and pointerdown `preventDefault` beyond the
  spec's `draggable={false}` + stopPropagation, which alone do not prevent a parent-row drag in
  native engines.

Both deviations noted in the PR body.

## Open Items

- Doc 15 (dock previews): whichever ships second rebases; the new preview `img` must be authored
  `draggable={false}` (decision 5 / interlock section).
- Terminal-paste e2e not covered (needs a live PTY backend in the e2e harness); covered by unit
  tests at the `handleDockDrop` and resolver layers.
