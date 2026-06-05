---
title: dnd-kit Sortable Grid Implementation (Transport Matters canvas)
type: sessions
tags: [frontend, dnd-kit, canvas, transport-matters, world-space, e2e]
summary: Replaced the hand-rolled pane reorder layer with dnd-kit sortable running entirely in world space; fixed the zoomed-drag e2e failure; all gates green.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

# Summary

Implemented NOTES/captured-canvas/19-dndkit-sortable-design.md on
feat/ordered-gridfit (e7dead7 -> 30ffb44, four commits). Canvas pane
reordering now runs through @dnd-kit/core 6.3.1 + @dnd-kit/sortable 10
in Stuart's DndContext -> SortableContext shape, with every dnd-kit
coordinate in world space: one planner-rect measure feeds BOTH measuring
halves (the draggable half keeps layout-shift compensation inert under
scale), collision converts the pointer screen -> world, strategy deltas
apply 1:1 in the scaled container, and only the active pane divides its
pointer delta by the camera scale at the single `sortableTransformToWorld`
seam.

# Architecture Decisions

- Engine stays dnd-kit-free: LayoutCanvas gained a `paneDndAdapter`
  component seam; session-canvas `SortablePane` calls useSortable and hands
  PaneFrame a plain world-space handle. Adapter is module-stable so the
  memoized PaneLayer keeps bailing on viewport renders; scale is read
  non-reactively (only consumed mid-drag, zoom locked via a new
  `zoomLocked` viewport option).
- Activation gating lives in a PointerSensor subclass reusing the engine's
  `dragModeForTarget` policy (Shift stays with pan, resize with
  use-gesture, bodyDrag opt-in honoured, controls clickable).
- Behavioral contracts moved from the deleted paneReorder controller into
  `createPaneDndCallbacks`: terminal delivery precedence by store
  hit-test (never `over`), over-index commit with same-order no-op,
  change-guarded terminal highlight, settle verdicts feeding the existing
  useReorderSettle/paneMotion machinery (sibling shift animates with the
  product's 320ms motion; cancel springs the lifted pane home because the
  store never mutates mid-drag, killing cancelReorder on both stores).
- Free move kept in PaneFrame for the floating stress route per doc 19;
  the reorder-specific Escape wiring deleted (dnd-kit cancels natively).

# Performance Notes

No regression paths: the adapter avoids per-pane scale subscriptions (zoom
ticks still bail through the PaneLayer memo) and per-tick drop-target
writes are change-guarded.

# Deviations from Spec

None beyond doc 19's signed amendment (sibling-shift gap replaces the slot
indicator; slot variant and insertionIndexAtWorldPoint deleted).

# E2E Findings

Run 27395174909's failure was a stale free-move assertion: it measured the
header AFTER release, but ordered gridFit settles releases into slots, so
a same-order release springs home (-0.2px observed). Rewrote to assert
cursor-lock MID-drag at sub-1.0 zoom (the seam invariant; doubled
conversion reads delta/scale, skipped reads delta*scale), slot settle,
order-swap commit, Escape cancel, click inert. Flake lessons: baselines
must be measured at true rest (await the camera-fly class removal plus a
two-sample calm streak; a stalled renderer fakes stillness mid-glide);
measure the pane frame, not the header (focus styling shifts the header
box); tolerate ~3px FLIP re-measure drift under scale (the guarded
regressions move a full slot).

# Post-Implementation Fixes (same day, head 9bc596f)

- Review blocker (c8027e0): the hero was invisible to collision (both
  useSortable halves disabled), so releases over it fell through to the
  nearest side pane and committed a wrong reorder. Fixed with lift-only
  disable plus an `over !== expandedPaneId` commit guard; failing-before
  unit tests and an expanded-mode e2e (pre-fix displacement: a full slot).
- Roadtest fix (9bc596f): ghost trails from per-tick subpixel translates
  (planner base + delta/scale) inside the scaled container. `dndPanePosition`
  quantizes the composed drag position to whole world pixels while a
  transform is live; rest keeps exact planner values. Stuart confirmed the
  branch works perfectly after this.

# Open Items

- Keyboard a11y for sortable (no KeyboardSensor; out of scope per doc 17
  non-goals).
- Dock drag-out (doc 16 slice 2) now unblocked: a dock drop resolves to an
  insertion index.
- ~~If rendering artifacts ever appear AT REST, round in the planner.~~
  Done same day (94e92f1): `roundWorldRect`/`roundWorldPoint` in
  engine/layout/geometry.ts quantize every geometry producer — planLayout
  chokepoint (all strategies + expand planner), moveRect/resizeRect per-tick
  gestures, dndPanePosition. Cameras stay fractional (a static transform
  cannot trail). Store tests expect the quantized contract via the shared
  primitive.
