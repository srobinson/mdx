# Scout: motion timeline pan (custom drag-pan to dnd-kit transform pan)

Branch `docs/performance-audit` @ 7059f62. Scout beat only. All citations are `file:symbol`.

## Headline finding

The installed dnd-kit is the next generation kit: `@dnd-kit/react@0.5.0` plus `@dnd-kit/dom@0.5.0` (with `abstract`, `collision`, `geometry`, `state` at 0.5.0). The legacy packages `@dnd-kit/core` and `@dnd-kit/utilities` are absent from `package.json` and `pnpm-lock.yaml`. The user story's named APIs (`CSS.Transform.toString`, `collisionDetection`, legacy `onDragEnd` semantics) do not exist in this dependency tree. Searches run: `rg "CSS.Transform|@dnd-kit/core|@dnd-kit/utilities|useSortable|collisionDetection" src/` (0 hits), `rg "@dnd-kit" pnpm-lock.yaml`. The spec must be re-grounded on the 0.5.0 surface before any build brief.

Verified 0.5.0 API for a free-axis pan (read from the installed packages, `.pnpm` store included): `@dnd-kit/react` exports `DragDropProvider`, `useDraggable`, `useDroppable`, `DragOverlay`, `useDragOperation`, `useDragDropMonitor`, `PointerSensor`, `KeyboardSensor`; `@dnd-kit/dom/modifiers` exports `RestrictToElement`, `RestrictToWindow`; `@dnd-kit/abstract/modifiers` exports `RestrictToHorizontalAxis`, `RestrictToVerticalAxis`, `AxisModifier`, `SnapModifier`. Modifiers apply per hook via the `useDraggable` `modifiers` option (the pattern `PanelDragCapabilityRoot:DraggableBinding` already uses with `RestrictToWindow`), so an X-only pan is `RestrictToHorizontalAxis` on the pan binding plus `event.operation.transform` consumption in the provider's drag events. Position styling is handled by the kit; there is no `CSS.Transform.toString` and no momentum in any package.

## Reuse Map

### 1. Ownership: timeline scroll and pan state today

Scroll position lives on the DOM node (`.cc-strip` `scrollLeft`). No store slice, no context, no React state owns it. Writers, in the order they act:

| Writer | Symbol | When it writes |
|---|---|---|
| Drag pan | `src/panels/motion/useDragScroll.ts:useDragScroll` | `node.scrollLeft = startScrollLeft - deltaX` on pointermove past `useDragScroll:dragThresholdPx` (8 px), mouse pointers only, with pointer capture and a capture-phase click swallow |
| Follow active card | `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip` (activeIndex effect) | `scrollIntoView({ inline: "nearest" })` when the active State changes |
| Native scrolling | `.cc-strip { overflow-x: auto }` in `src/panels/motion/motion.css` | Wheel, touch pan, scrollbar. `useDragScroll` deliberately ignores touch pointers and defers to this |

Precedence today is implicit temporal last-write-wins with no arbitration symbol. The writers cannot collide in practice: the follow effect fires only on selection change, and the click swallow in `useDragScroll:onClick` prevents a pan from producing a selection. Keyboard selection mid-drag is the one theoretical overlap, and the next pointermove re-asserts the drag. So: no second-writer defect today, and also no recorded precedence rule. The future transform pan adds a writer in a different coordinate system (CSS translate vs `scrollLeft`), which makes the missing rule load-bearing. See Quality Map QM3.

Sole consumer of `useDragScroll` is `PieceStateStrip` (`stripRef`). Search run: `rg -l "useDragScroll" src/` (definition, `PieceStateStrip.tsx`, one CSS comment). Deleting the hook once replaced is a clean single-path removal.

### 2. Capability coupling: how dnd-kit is owned and consumed

dnd-kit imports are confined to `src/capabilities/panel-drag/`:

- `usePanelDrag.ts:usePanelDrag` builds `DragDropProvider` handlers; `onDragEnd` writes `CubicellStore.patchPanelPlacement` (float position or dock insertion) for every drag source.
- `PanelDragCapabilityRoot.tsx:PanelDragCapabilityRoot` mounts the single `DragDropProvider`; `PanelDragCapabilityRoot:DraggableBinding` calls `useDraggable({ element, handle, id, modifiers: [RestrictToWindow] })`.
- `EdgeDockZone.tsx:EdgeDockZone` renders dock drop targets.

The lazy pipeline that keeps dnd-kit off the initial delivery:

- Runtime: `src/studios/lazyCapability.ts:createLazyCapability` over `src/shared/generationalLoader.ts:createGenerationalLoader`.
- Slot: `src/studios/editor/usePanelDragCapability.ts:createPanelDragCapabilityModel`, load edge `import("../../capabilities/panel-drag/PanelDragCapability")`, prefetch via `src/studios/capabilityPrefetch.ts:prefetchCapabilityClosure("panel-drag")`.
- Decoupling seam: `src/app/panelDragPort.ts:createPanelDragPort` and `panelDragPort.ts:PanelDragRegistration` (`{element, handle, id: PanelId}`). Producers (`src/app/DockablePanel.tsx` via `setElement` / `setHandle`) register raw DOM nodes with zero dnd-kit knowledge; the capability's provider binds them after load.

Motion's own lazy slot: `src/studios/editor/useMotionCapability.ts:createMotionCapabilityModel`, load edge `import("../../capabilities/motion/MotionCapability")`. `src/panels/motion/*` sits inside that closure (`MotionCapability.tsx` reaches it through `panels/BottomDock.tsx:BottomDock` and `useMotionInspector`).

**Edge added if the timeline imports dnd-kit directly:** `src/panels/motion/PieceStateStrip.tsx -> @dnd-kit/react`. Motion already loads lazily on dock open, so dnd-kit would stay off initial delivery either way, but the edge pulls the dnd-kit chunk into motion's capability increment closure (budget consequence below). It also requires a second `DragDropProvider` inside motion: the strip renders under `MotionCapabilityActive.renderDock` inside `BottomDock`, outside `PanelDragCapabilityRoot`'s provider, and `useDraggable` needs a provider ancestor.

**Reuse-correct consumption:** extend the existing port seam. `panelDragPort.ts:PanelDragRegistration` grows a registration kind for a free-axis pan surface; `PieceStateStrip` registers its strip element through the port exactly as `DockablePanel` does; `PanelDragCapabilityRoot` binds it inside the one existing provider. dnd-kit imports stay confined to `src/capabilities/panel-drag/`, no new module graph edge from motion to dnd-kit, and the pan activates through the already-shipped `usePanelDragCapability` slot. The cost is a precedence rule in `usePanelDrag:onDragEnd`, which today assumes every source is a panel and writes `patchPanelPlacement`; a pan source must be excluded there explicitly (Quality Map QM4).

### 3. Budget

Increment semantics (`scripts/delivery-capabilities.mjs:checkDeliveryIncrements`): each capability increment is the gzip sum of chunks in `closure(root)` minus `closure(baselineRoots)`. Increments are computed independently, so a chunk shared by motion and panel-drag but absent from the baseline is charged to both buckets.

Ceilings in `budgets/initial-delivery.json` (`generatedFrom` 27813ba), which are measured values at zero headroom by ratchet policy:

| Bucket | Ceiling (gzip) | Note |
|---|---|---|
| `capabilityIncrements.motion` | 8,718 B | owns `src/panels/motion/` and `src/capabilities/motion/` by source rule |
| `capabilityIncrements.panel-drag` | 32,977 B | closure includes all `@dnd-kit/*` today; source rule assigns `/node_modules/@dnd-kit/` to panel-drag |

dnd-kit size signal: the visualizer raw data (`artifacts/bundle/raw-data.json`) sums 51,676 B gzip across 11 `@dnd-kit` module parts. Per-module gzip overestimates chunk-level gzip; the chunk-level truth is bounded by the whole panel-drag increment at 32,977 B including its own source. Call it roughly 25 to 30 KB gzip at chunk level.

Consequences, facts only:

- A static `panels/motion -> @dnd-kit` edge adds the dnd-kit chunk to motion's increment: roughly 3 to 4 times its entire 8,718 B ceiling. Deterministic `CAPABILITY_INCREMENT_RATCHET` red. Cannot land without a re-baseline of that scale.
- The port-extension path adds only pan wiring bytes to motion (registration call) and binding bytes to panel-drag. Both ceilings sit at zero headroom, so any byte growth is red and a re-baseline of the touched buckets is required by policy either way; this path re-baselines by tens of bytes to low hundreds instead of tens of kilobytes.
- Classification vs accounting divergence: with a direct motion edge, `capabilitySourceRules` still labels `@dnd-kit` as panel-drag-owned while the increment accounting charges motion. The two views of ownership would disagree.
- `checkCapabilityPreloads` requires the emitted preload map to match each capability's non-entry closure exactly; any closure change moves that surface too (build-derived, but it is a gate error surface to re-verify).
- `vite.config.ts` `codeSplitting.groups` has no dnd-kit group; chunk assignment for a newly shared dnd-kit would fall to rolldown's default splitting.

### 4. Interaction surface on the timeline

Everything that consumes input on or beside the strip:

- `PieceStateStrip`: option tile `onClick` (select), `PieceStateStrip:onOptionKeyDown` (ArrowLeft/ArrowRight roving focus, Enter/Space select), Update button `onClick` with `stopPropagation`, Build-in / transition / Snapshot buttons `onClick`, roving `tabIndex`, and the `scrollIntoView` follow effect.
- `useDragScroll`: pointerdown/move/up/cancel plus a capture-phase click listener that swallows the pan's trailing click. The 8 px threshold is what keeps card clicks alive; the dnd-kit equivalent is a pointer sensor activation distance constraint, which must be carried over or clicks die.
- `TransportPlayhead`: `input[type=range]` scrub with `onChange` and `onPointerDown/Up/Cancel` render pulses (`scene/renderProducers:requestRenderPulse` / `finishRenderPulse`). It is a sibling row above the strip (`PieceMotionPanel` renders `TransportRow` then `PieceStateStrip`), so it collides only if a draggable listener lands on a shared ancestor.
- Native: wheel and touch panning via `.cc-strip { overflow-x: auto }`. No JS wheel handler exists anywhere in `src/panels/motion/` (search run: `rg "onWheel|wheel|pointerdown|onPointerDown|onPointerMove" src/panels/motion src/capabilities/motion src/panels/BottomDock.tsx`).
- CSS feel: `.cc-strip` cursor grab/grabbing, `user-select: none`, `.cc-strip--dragging` class toggled by `useDragScroll`.

The structural collision: a transform pan translates items while `scrollLeft` remains the coordinate the follow effect and native wheel write. Layout is also load-bearing here: cards interleave via flex `order` and the listbox uses `display: contents`, and the strip clips through its own overflow box. A transform that moves items without moving `scrollLeft` leaves wheel, `scrollIntoView`, and scrollbar all writing a coordinate the eye no longer sees. One writer model must be chosen (Plan, decision c).

## Quality Map

| # | Finding | Disposition |
|---|---|---|
| QM1 | Spec/library mismatch: the user story cites legacy `@dnd-kit/core` APIs; installed kit is `@dnd-kit/react` 0.5.0 with a different surface. Building against the brief as written is impossible without either rewriting the spec against 0.5.0 or installing the legacy kit alongside (two dnd-kits in one tree). | Refactor first: re-adjudicate the spec before any build brief. Human decision. |
| QM2 | Momentum exists nowhere: dnd-kit (either generation) ships no inertia, and no momentum/glide helper exists in the repo for this surface. Searches: `rg -i "momentum|inertia|velocity" src/panels src/capabilities` (no pan-related hits). The user story's "momentum" is net-new custom code. | Surface to human: momentum is scope, unowned by any existing symbol. |
| QM3 | Missing precedence rule among scroll writers (drag, follow effect, native wheel), currently benign, becomes a defect the moment a transform writer joins. | During design: record one writer model before the build brief. |
| QM4 | `usePanelDrag:onDragEnd` writes `patchPanelPlacement` for every drag source. If the pan reuses the shared provider, an unguarded pan-source drop would write panel placement state: a second writer to owned state with no precedence rule, the exact builder blind spot named in `.warroomagents/gpt-sol.md`. | During build: source-kind guard is part of the slice's acceptance, with a test. |
| QM5 | `useDragScroll:dragThresholdPx` (8 px) is a hardcoded feel constant; project convention places feel constants in config knobs. If `useDragScroll` is deleted, the value must migrate into the sensor activation constraint, honoring the same convention. | During. |
| QM6 | `scrollIntoView` follow pattern duplicated between `PieceStateStrip` and `panels/StructureSection.tsx:StructureSection`. Two call sites, three lines each. | Defer: consolidation is worth less than the churn while this surface is in motion. |
| QM7 | Dead code: none found relevant to the pan surface. `useDragScroll` has exactly one consumer; no orphan pan/scroll helpers. Searches: `rg "scrollLeft|scrollIntoView|scrollTo" src/`, `rg -l "useDragScroll" src/`. | None. |
| QM8 | Sizing: all touched files are well under limits (`useDragScroll.ts` 87, `PieceStateStrip.tsx` 205, `usePanelDrag.ts` 120, `EditorStudio.tsx` 362). No refactor-first sizing trigger. | None. |
| QM9 | Reorder non-goal alignment: the strip's `role="listbox"` with flex-`order` interleaving and `display: contents` would fight any future sortable. Gating reorder behind pan is consistent with the code as it stands. | Defer, by design. |

## Plan (dispositions the orchestrator must collect before a build brief)

a. **QM1, spec grounding.** Rewrite the pan story against `@dnd-kit/react` 0.5.0 (`DragDropProvider`, `useDraggable`, `@dnd-kit/dom` modifiers, sensor activation distance) or decide to install the legacy kit. Everything downstream depends on this.

b. **Integration path.** Reuse: extend `panelDragPort.ts:PanelDragRegistration` with a pan surface kind, bind in `PanelDragCapabilityRoot`, keep dnd-kit confined to `src/capabilities/panel-drag/`, budget movement measured in bytes. Deviate: motion-local `DragDropProvider` with a direct `panels/motion -> @dnd-kit` edge, second provider instance, motion increment re-baselined roughly 4x. If deviate is chosen it needs its one-line reason recorded.

c. **Writer model (QM3).** Either the pan keeps writing `scrollLeft` through dnd-kit's drag events (transform consumed as a delta source, `overflow-x` remains the single coordinate, follow effect and wheel keep working), or transform replaces scrolling entirely and the follow effect, wheel, and scrollbar are re-implemented against the transform. The first preserves three existing writers; the second rewrites them.

d. **Budget expectation.** Any landing re-baselines the touched buckets at zero headroom per ratchet policy; the delta scale is decided by (b). Controlled-red proof required if any ceiling moves, per `WARROOM.md` budget gate discipline.

e. **Feel gate.** Canvas-input and drag surfaces carry the live UX gate before merge (`live-ux-gate-before-merge`); the click-preserving threshold and grab cursor behavior are part of that pass, on dev and preview both.
