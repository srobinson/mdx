---
title: F2 Layout Manager design — n-ary split tree, scored planner, Motion FLIP
type: sessions
tags: [transport-matters, session-canvas, f2, frontend, layout, design]
summary: Design for the F2 layout manager — tiling split tree + scored efficient planner + mode transitions, extending the real F1 engine with no new deps.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

# F2 Layout Manager Design

Phase 1 design. No implementation. This extends the **real F1 engine** shipped in
`www/src/engine/**` (PR #39). It honors the locked baseline in `fe-spec.md`
(§3.3 contracts, §5.1 transform, §6 panes, §7 layout manager, §8 registry, §12 F2)
and the locked OSS decisions in `f2-oss-research.md`: keep **Motion** (`framer-motion`
^12.40.0) for FLIP, keep the hand-rolled `efficientLayout.ts` planner, keep custom
`useCanvasViewport`, borrow only the **n-ary split-tree data model**. No new runtime
dependency. The `PaneNode` / `renderPane(paneId)` content-agnostic seam is inviolable.

## 0. Grounding: what F1 actually shipped (and the real gaps)

Read before designing, because the spec describes the target and the code describes the
floor. They differ, and the difference *is* F2's scope.

Real F1 engine surface (`www/src/engine/`):

| File | Reality today |
| --- | --- |
| `types.ts` | `PaneNode {paneId, lifecycle, rect:WorldRect, z, pinned}`, `EngineLayoutState {mode, viewport, nodes:Record<PaneId,PaneNode>, focusedPaneId}`. **No split tree. No `layoutVersion`.** `LayoutMode = "floating"\|"tiling"\|"focus"` exists as a type but only `floating` is exercised. |
| `planners/efficientLayout.ts` | `planEfficientLayout(input)` returns `{rects, reason}`. Implements **only** `planFloatingGrid` (ceil(√n) balanced grid) and `planFocus` (focused pane + right-edge rails). **The §7.2 five-candidate set, the `score` formula, and the tie-breakers do not exist.** Constants: `WORLD_MARGIN=48`, `PANE_GAP=24`, `MIN_PANE_WIDTH=320`, `MIN_PANE_HEIGHT=240`, `FOCUS_RAIL_WIDTH=180`. |
| `reducers/layoutState.ts` | Pure reducers over the flat `nodes` map: `upsertNode`, `focusNode` (raises `z` via `nextPaneZ`), `updateNodeRect`, `markNodeClosing` (reassigns focus to `nearestPaneId` by rect center), `removeNode`, `setViewport` (`clampScale` 0.45–1.8), `panViewport`, `zoomViewportAt` (cursor-anchored). |
| `reducers/paneLifecycle.ts` | `createPaneNode`, `moveRect`, `resizeRect`. |
| `react/PaneFrame.tsx` | `motion.div` with `layoutId={paneId}`, `animate={{x,y,opacity}}`, `style={{width,height,zIndex}}`, spring `NORMAL_TRANSITION={type:"spring",stiffness:360,damping:38}` / `REDUCED_TRANSITION={duration:0}` via `useReducedMotion`. Drag via `@use-gesture/react`; drag mode resolved from `data-pane-resize-handle` / `data-pane-drag-handle`; world scale read from `[data-canvas-world]` dataset. **Position is driven by `animate` transform; size is set by `style` and snaps (never animates).** No `layout` prop, no `LayoutGroup`, no `layoutDependency`. |
| `react/LayoutCanvas.tsx` | Viewport `section` + `canvas-world` transform layer; maps open nodes to `PaneFrame` and calls the `renderPane(paneId)` render-prop. The seam. |
| `react/useCanvasViewport.ts` | Wheel/keyboard pan+zoom, drag-to-pan (skips events inside `[data-pane-frame]`). |
| `perf/frameMeter.ts` | `FrameMeter` rAF sampler → `{frames, p95DeltaMs, maxDeltaMs}`. |

Real F1 feature wiring (`www/src/session-canvas/`):

- `model/canvasStore.ts` (zustand) is the single state hub. **It never calls
  `planEfficientLayout`.** `spawnPane`/`insertPane` place panes with hard-coded staggered
  rects from `model/spawn.ts` `rectForRef` (`PICKER_RECT 440×640`, `TRANSCRIPT_RECT 720×640`
  offset by 28px per index). `closePane` → `markNodeClosing` → `setTimeout(140ms)` →
  `removeNode`. **No auto-realign on spawn or close. No `setMode`. No tiling.**
- `components/CanvasSurface.tsx` owns the `renderPane` closure: joins `PaneNode` →
  `PaneRecord` via `panes[paneId]`, resolves the viewer (`resolveViewer`), wraps content in
  `PaneWindow`. This join lives **outside** the engine, exactly as the seam requires.
- `components/CanvasCommandBar.tsx` is a `role="toolbar"` with two buttons (Focus picker,
  Reset view) and a focus-status line. No mode controls, no keyboard leader.
- `components/PaneWindow.tsx` owns session-canvas chrome (header, title, close, drag/resize
  handles). No tiling separators yet.
- `perf/SessionCanvasStressRoute.tsx` drives the F1 floating stress harness.

**F2 net work, therefore:**

1. Implement the §7.2 scored multi-candidate floating planner (today it is one heuristic).
2. Add the n-ary split tree + `planTilingLayout` + tiling reducers.
3. Add `setMode` + mode-switch transitions + real `focus` mode wiring.
4. **Wire auto-realign into the store** on spawn/close (the missing call to the planner).
5. Upgrade `PaneFrame` to FLIP **size** for tiling/mode-switch (Motion `layout` +
   `layoutDependency` gating), keeping position+size transform-only.
6. Tiling resize separators with APG `separator` semantics.
7. Command bar mode controls + keyboard leader shortcuts.
8. Extend the stress harness to mode switches, presets, and tiling resize.

Nothing here rewrites the F1 engine. Every change is additive or a localized swap behind the
same `PaneNode` + `renderPane` seam, which is the F1-no-rewrite constraint from
`f2-oss-research.md`.

---

## 1. Layout data model

### 1.1 The spine stays; the tree is additive

`EngineLayoutState` remains the single engine state object. Two additions:

```ts
// www/src/engine/types.ts (extended)

export type SplitAxis = "row" | "column";
// "row":    children laid out left → right, separated by vertical dividers (tmux split -h)
// "column": children laid out top → bottom, separated by horizontal dividers (tmux split -v)

export type LayoutTree = LayoutLeaf | LayoutSplit;

export interface LayoutLeaf {
  kind: "leaf";
  paneId: PaneId;
}

export interface LayoutSplit {
  kind: "split";
  axis: SplitAxis;
  children: LayoutTree[];   // length >= 2 (singletons are collapsed)
  sizes: number[];          // length === children.length; each in (0,1); Σ === 1
}

export interface EngineLayoutState {
  mode: LayoutMode;
  viewport: CanvasViewport;
  nodes: Record<PaneId, PaneNode>;   // unchanged: the committed RENDER projection
  focusedPaneId: PaneId | null;
  // --- F2 additions ---
  tree: LayoutTree | null;           // non-null when mode === "tiling" OR a suspended tiling layout is held (see suspended)
  layoutVersion: number;             // bumped only on discrete re-plans; gates FLIP
  floatingRects: Record<PaneId, WorldRect> | null; // snapshot to restore floating on round-trip
  suspended: SuspendedLayout | null; // prior mode held while a transient mode (focus zoom) is active
}

// Explicit suspended-layout contract so focus-zoom can be entered from tiling without
// violating the tree invariant (resolves the §1.1↔§3.1 contradiction codex flagged).
export interface SuspendedLayout {
  preFocusMode: LayoutMode;          // the mode focus-zoom was entered FROM
  preFocusTree: LayoutTree | null;   // the tiling tree to restore on un-zoom (null if entered from floating)
  preFocusRects: Record<PaneId, WorldRect> | null; // floating rects to restore (null if entered from tiling)
}
```

Tree invariants (asserted by a dev-only `assertTreeInvariant(tree, openPaneIds)`,
stripped in prod):

- **Presence:** `tree !== null` iff `mode === "tiling"` **or** `suspended?.preFocusTree !== null`
  (focus-zoom suspended from tiling holds the tree in `suspended.preFocusTree`, not in the
  live `tree`, which is null while focus is the active mode). Exactly one of `tree` /
  `suspended.preFocusTree` is non-null at a time.
- Every open pane id appears exactly once as a leaf; no leaf references a closed pane.
- `split.children.length === split.sizes.length >= 2`.
- `sizes` are positive and sum to `1 ± 1e-6`.
- No split has a single child (pruning collapses it; see §4).
- Recursive min feasibility: `subtreeMinExtent(tree, axis) <= viewport extent` is *desired*
  but not guaranteed; when violated the planner overflows uniformly rather than clamping
  (see §2.5), so the invariant never assumes the tree fits.

### 1.2 One source of truth per concern, never two

`nodes[].rect` is **always** the render source — `LayoutCanvas` already renders
`node.rect`, and that does not change. Planners are **commit-time pure functions** that
produce a new rect set folded back into `nodes`. The discriminant is `mode`:

| Mode | Structural truth | How `nodes[].rect` is produced |
| --- | --- | --- |
| `floating` | `nodes[].rect` + `pinned` flags | Manual drag/resize writes directly; spawn/close run `planFloatingLayout` over **unpinned** panes and commit |
| `focus` | `focusedPaneId` + open set | `planFocusLayout(focusedPaneId, set)` derives one main + rails |
| `tiling` | `tree` | `planTilingLayout(tree, viewport)` derives all rects; `pinned`/`floatingRects` ignored while tiling |

Floating positions and the tree never coexist *live*: a canvas is in exactly one mode.
They coexist only across a transition — entering tiling snapshots `floatingRects`; leaving
restores it. `focusedPaneId` is **mode-independent** and consumed by all three planners
(focus → big pane; tiling → active leaf for split/resize/zoom; floating → z-raise +
spawn-after ordering). This is why mode switches preserve pane identity and stream
subscriptions (fe-spec §12 F2 acceptance): we only swap rects and the tree, never the
`paneId`-keyed `nodes`/`panes`, so viewers and `EventSource` streams never remount.

### 1.3 Why a tree at all (vs. the flat rect map F1 uses)

Floating needs only rects. Tiling needs **structure**: a divider between two tiles is a
relationship, not a coordinate. The n-ary split tree (the one borrowable idea from
dockview/react-mosaic per `f2-oss-research.md`) encodes "these panes share a row, resizing
the boundary trades their widths" in a form that resize, split, and prune mutate cheaply and
that `planTilingLayout` walks in O(panes). Storing tiling as raw rects would force us to
re-derive adjacency on every resize — fragile and non-deterministic.

---

## 2. Planner / auto-arrange

### 2.1 Extended planner contract

```ts
// www/src/engine/planners/efficientLayout.ts (extended)

export interface EfficientLayoutInput {
  paneIds: readonly PaneId[];                       // creation order (caller guarantees)
  currentRects: Readonly<Record<PaneId, WorldRect>>;
  viewport: ViewportBounds;
  mode: LayoutMode;
  focusedPaneId: PaneId | null;
  pinnedPaneIds?: readonly PaneId[];
  tree?: LayoutTree | null;                         // NEW: required when mode === "tiling"
}

export interface EfficientLayoutPlan {
  rects: Record<PaneId, WorldRect>;
  reason: string;                                   // winning candidate name (kept for tests/telemetry)
  score?: number;                                   // NEW: winning score (floating only)
}

export function planEfficientLayout(input: EfficientLayoutInput): EfficientLayoutPlan {
  if (input.mode === "tiling" && input.tree) return planTilingLayout(input);
  if (input.mode === "focus" && input.focusedPaneId) return planFocusLayout(input);
  return planFloatingLayout(input); // §2.2 scored candidates (replaces the single grid)
}
```

`planFocusLayout` is the existing `planFocus`, renamed; its behavior is unchanged and it is
also reused as candidate #5 below.

### 2.2 Floating: the scored candidate set (fe-spec §7.2)

Five pure candidate generators, each `(ctx) => Record<PaneId, WorldRect>` over the unpinned
set within world bounds (`viewport` minus `WORLD_MARGIN`, `PANE_GAP` between cells):

1. `balancedGrid` — existing `ceil(√n)` columns. (Already shipped.)
2. `singleRow` — `n` columns × 1 row.
3. `singleColumn` — 1 column × `n` rows.
4. `mainPlusSideStack` — focused pane takes a `MAIN_FRACTION` (≈0.62) main column; the rest
   stack in a right column. Falls back to `balancedGrid` if no focused pane.
5. `focusWithDockRails` — reuse `planFocusLayout` (focused fills work area; others become
   `FOCUS_RAIL_WIDTH` rails).

Candidates are selected in **two stages** so hard constraints are a *feasibility filter*, not
magic weights, and only soft terms are summed. (This rewrite fixes the dimensional bugs codex
proved with the score probe: negative empty area at N=5, N-growing aspect/movement sums, and
non-derivable worked examples.)

**Stage 1 — feasibility filter (hard constraints).** A candidate is *feasible* iff it neither
overflows the world bounds nor overlaps any pair of panes. If at least one feasible candidate
exists, all infeasible candidates are discarded. If none is feasible (world smaller than the
min-size layout), every candidate passes through and the soft `overflowPenalty` ranks the
least-bad. This removes the indefensible `W_OVERFLOW=1000` / `W_OVERLAP=1000` magic weights:
hard constraints **gate**, they do not **weigh**.

**Stage 2 — weighted sum of normalized soft terms** (lower wins). Every term is clamped
**non-negative** and every per-pane sum is divided by `n`, so terms are dimensionally
comparable across pane counts:

```ts
soft = W_EMPTY        * emptyAreaPenalty
     + W_ASPECT       * aspectPenalty
     + W_MOVE         * movementPenalty
     + W_FOCUS        * focusPenalty
     + W_OVERFLOW_SOFT * overflowPenalty;   // only ranks the all-infeasible fallback
```

| Term | Definition (corrected) | Weight |
| --- | --- | --- |
| `emptyAreaPenalty` | `max(0, (usableArea − unionArea) / usableArea)` — **union** area, **clamped ≥ 0**. Fixes the N=5 `singleRow` empty=−0.1905 bug: union (not Σ paneArea) cannot exceed usable, so overflow can't drive it negative or double-count overlap. | `W_EMPTY = 3` |
| `aspectPenalty` | `(1/n) · Σ |log((w/h) / TARGET_ASPECT)|`, `TARGET_ASPECT = 4/3` — **per-pane mean** | `W_ASPECT = 2` |
| `movementPenalty` | `(1/n) · Σ dist(curCenter, nextCenter) / worldDiagonal` (0 for a brand-new pane) — **per-pane mean** | `W_MOVE = 4` |
| `focusPenalty` | `max(0, FOCUS_TARGET_AREA − focusedArea) / FOCUS_TARGET_AREA` (single pane, already normalized) | `W_FOCUS = 5` |
| `overflowPenalty` | `(1/n) · Σ max(0, extentBeyondWorld) / worldDiagonal` — ranks only the infeasible fallback | `W_OVERFLOW_SOFT = 6` |

The four soft weights encode an **ordering**, not tuned constants: focus (5) > movement (4) >
empty (3) > aspect (2) = "keep the focused pane comfortable, then keep panes still, then fill
the canvas, then avoid slivers." They are exported constants, tuned against the stress harness
+ visual review; the tie-break chain is the deterministic backstop.

Tie-breaks (scores within `SCORE_EPSILON = 1e-3`), **reordered** so the worked examples are
derivable (codex showed the old #2-before-#3/#4 order made them non-derivable):

1. Smaller `|Δ focusedArea|` (preserve focused pane size — fe-spec §7.2 #1).
2. **Shape-by-count (fe-spec §7.2 #3/#4): `n ≤ 3` prefer fewer rows; `n ≥ 4` prefer
   `balancedGrid`.** Moved ahead of generic stability so the "fewer rows for 2–3 panes" intent
   wins ties.
3. Stable candidate order (final deterministic backstop — fe-spec §7.2 #2).

**`efficientLayout.test.ts` is canonical.** It holds the exact expected winner + rects per
`(N, focusedPaneId, viewport)` row; the §2.6 prose examples are *derived from that table*, not
asserted independently. Determinism holds: fixed candidate order, panes in caller creation
order, no `Date.now`/`Math.random`. Same input → same plan.

### 2.3 Spawn algorithm (wire the missing call)

Today `canvasStore.spawnPane` skips the planner. F2 wires it:

```
spawn(ref):
  paneId = paneIdForRef(ref)              // existing
  if exists: focus(paneId); return         // existing dedupe (fe-spec §6.1)
  insert node (lifecycle "open")           // existing upsertNode
  orderedUnpinned = panesAfterFocused(focusedPaneId) ∪ {paneId}   // "after focused, else after picker"
  if mode == floating: commit planFloatingLayout(orderedUnpinned); bumpVersion()
  if mode == tiling:   tree = insertIntoTree(tree, focusedPaneId, paneId, focusedLeafRect)
                       commit planTilingLayout(tree); bumpVersion()
  if mode == focus:    commit planFocusLayout(); bumpVersion()
  onLayoutAnimationComplete → focus(paneId)   // "focus the new pane after transition"
```

Pinned panes keep manual rects; only unpinned are scored (fe-spec §7.2 spawn rules).

### 2.4 Close algorithm

```
close(paneId):
  markNodeClosing(paneId)                  // existing: exit opacity + focus → nearestPaneId
  after CLOSE_DELAY_MS (140, existing):
    removeNode(paneId)                       // existing
    if mode == floating: commit planFloatingLayout(remainingUnpinned); bumpVersion()  // compact
    if mode == tiling:   tree = pruneFromTree(tree, paneId); commit planTilingLayout(tree); bumpVersion()
    if mode == focus:    commit planFocusLayout(); bumpVersion()
```

Closing panes are excluded from scoring once `lifecycle !== "open"` (fe-spec §7.2 close
rules). Focus falls to nearest pane by center, else the picker (existing `nearestPaneId` /
`firstOpenPaneId`).

### 2.5 Tiling planner

Pure recursive walk. The leaf-clamp in the first draft was wrong (codex point 4): clamping a
leaf to `MIN_PANE_*` *after* the parent already advanced its cursor by the unclamped extent
makes a clamped leaf overlap its sibling and breaks the sizes-sum contract when a subtree's
mins exceed its allocation. The fix is **recursive minimum extents** enforced at every split,
with uniform overflow when the world is too small — never a leaf-level clamp:

```
// Recursive minimum extent of a subtree ALONG one axis.
subtreeMinExtent(node, axis):
  if node.kind == "leaf":
    return axis == "row" ? MIN_PANE_WIDTH : MIN_PANE_HEIGHT
  if node.axis == axis:                          // children end-to-end along this axis
    return Σ subtreeMinExtent(child, axis) + gap * (children.length - 1)
  else:                                          // children stacked across this axis
    return max over children of subtreeMinExtent(child, axis)

planTilingLayout(tree, world, gap=PANE_GAP, margin=WORLD_MARGIN) -> Record<PaneId, WorldRect>:
  rects = {}
  walk(node, rect):
    if node.kind == "leaf": rects[node.paneId] = rect; return     // NO leaf clamp
    axisLen   = node.axis == "row" ? rect.width : rect.height
    available = axisLen - gap * (children.length - 1)
    mins      = children.map(c => subtreeMinExtent(c, node.axis))
    totalMin  = Σ mins
    extents   = available >= totalMin
              ? children.map((c,i) => mins[i] + (available - totalMin) * sizes[i]) // slack by fraction
              : mins   // below total min → allocate mins; the world overflows UNIFORMLY (pan/zoom reaches it)
    cursor    = node.axis == "row" ? rect.x : rect.y
    for (child, i):
      childRect = node.axis == "row"
        ? { x: cursor, y: rect.y, width: extents[i], height: rect.height }
        : { x: rect.x, y: cursor, width: rect.width, height: extents[i] }
      walk(child, childRect)
      cursor += extents[i] + gap
  walk(tree, insetByMargin(world, margin))
  return rects
```

Guarantees: every leaf is ≥ its min on both axes (mins enforced recursively at each split);
siblings never overlap (cursor advances by the *actual* allocated extent); `sizes` distribute
only the **slack** above the mins, so the sum invariant is untouched; when the world is too
small the layout overflows uniformly (panes at min, reachable by pan/zoom — §7 dense-layout
hint) rather than clamping-and-overlapping. Root: `tree=leaf(A)` → A fills the inset world;
`tree=null` → empty canvas, `{}`. O(panes), deterministic, no measurement. Unit-tested by
`layoutState.test.ts` (fe-spec §13).

### 2.6 Worked examples

World ≈ 1440×900 world units, `WORLD_MARGIN=48`, `PANE_GAP=24`. Tiling tree shapes are exact
(deterministic from the algorithm); floating winners are stated as *expected* and are pinned
authoritatively by the `efficientLayout.test.ts` table (§2.2), not by prose.

**N=1** — floating: all candidates collapse to the single pane filling the work area (identical
rects). tiling: `tree = leaf(A)`, A fills the inset world.

**N=2** — floating: `balancedGrid` (2×1) and `singleRow` produce **identical** rects (codex
confirmed), so they tie; tie-break #2 (`n ≤ 3` fewer rows) keeps both at 1 row → tie-break #3
picks the first in candidate order. Geometrically indistinguishable either way. tiling:
`split(row,[A,B],[.5,.5])` → vertical divider, two columns.

**N=3** — floating: with a focused pane, `mainPlusSideStack` is expected to win on the
corrected score (lower aspect: focus 62% main + 2 stacked beats a 3-wide row of slivers —
codex probe: mainPlusSide aspect 0.342 ≪ singleRow 2.73); without a focused pane the shape-by-
count tie-break favors fewer rows. tiling (spawn A, split B, split C into B's leaf along the
wider axis): `split(row,[A, split(column,[B,C],[.5,.5])],[.5,.5])` → A left half; B/C stacked
right.

**N=5** — floating: `balancedGrid` expected (shape-by-count #4 for `n ≥ 4`): 3 cols × 2 rows
(`ceil(√5)=3`), last row holds 2; clamped union `emptyAreaPenalty` accepts the one gap. tiling:
balanced BSP, e.g. `split(row,[ split(column,[A,B]), split(column,[C,D]), leaf(E) ])`.

**N=12** — floating: `balancedGrid` 4×3. If min-size cells exceed the world, the feasibility
filter discards the worse single-row/col candidates; if none is feasible, soft
`overflowPenalty` still ranks the grid best, and the world overflows (pan reaches it). tiling:
balanced BSP to 12 leaves; recursive-min rect math stays exact and non-overlapping. Part of the
§6 stress sweep `[1,2,4,8,16,30]`.

---

## 3. Mode semantics + transitions

### 3.1 Triggers and what re-plans

| Transition | Trigger | What happens |
| --- | --- | --- |
| `floating → tiling` | command bar / leader | `tree = treeFromPanes(orderedOpenPanes, viewportAspect)` (balanced BSP); snapshot `floatingRects`; commit `planTilingLayout`; `bumpVersion()` → FLIP |
| `tiling → floating` | command bar / leader | restore `floatingRects` if present, else seed from current tiling rects (panes stay where their tiles were, now draggable); `tree = null`; `bumpVersion()` |
| `* → focus` | double-click header / leader-`z` | `planFocusLayout(focusedPaneId)`; from tiling this is a tmux-style **zoom** that retains `tree` (hidden) and restores it on exit |
| `focus → *` | leader-`z` again / mode cycle | restore prior mode's structural truth; `bumpVersion()` |

`treeFromPanes` recursively halves the ordered pane list, alternating axis by the running
rect's aspect (wider → `row` split, taller → `column`), so the initial tiling looks like a
sensible grid rather than a 1-deep row. Deterministic.

### 3.2 Motion choreography (named APIs)

All from `framer-motion` ^12.40.0 (already the `PaneFrame` engine):

- **`<LayoutGroup>`** wraps the pane list in `LayoutCanvas` so all sibling `PaneFrame`s
  measure and animate in one synchronized FLIP batch (no per-pane jitter).
- **`motion.div` with `layout` + `layoutId={paneId}` + `layoutDependency={layoutVersion}`** on
  `PaneFrame`. The committed rect is written to the **layout box** (`style={{left, top,
  width, height}}`); Motion measures before/after and animates the delta with **transform
  only** (translate + scale), GPU-composited. `layoutId` preserves identity for any future
  shared-element move (e.g. focus overlay portal); `layout` does the in-place FLIP.
- **`layoutDependency={layoutVersion}`** is the gate: Motion only re-measures/animates when
  `layoutVersion` changes. Stream appends, content re-renders, pan/zoom, and **active drags
  never bump it** → those commit instantly with no FLIP. This is the single most important
  perf lever (§6) and the mechanism the brief calls "layoutDependency gating."
- **Spring config:** reuse `NORMAL_TRANSITION = {type:"spring", stiffness:360, damping:38}`
  for spawn/close/realign; add `MODE_TRANSITION = {type:"spring", stiffness:300, damping:34}`
  for floating↔tiling↔focus switches (a touch softer so a big reflow *settles*).
- **Stagger:** spawn uses `AnimatePresence` with `initial={{opacity:0, scale:0.96}}` /
  `exit={{opacity:0}}`. Preset and mode switches add a subtle per-pane delay
  `transition={{...spring, delay: index * 0.012}}` capped so total ≤ ~150ms — premium, not
  sluggish.
- **`onLayoutAnimationComplete`** clears `will-change` and runs size-dependent work
  (e.g. transcript virtualization remeasure) — fe-spec §7.3 "size dependent work runs after
  onLayoutAnimationComplete."
- **Reduced motion:** `useReducedMotion()` (already wired) → `transition={{duration:0}}`;
  optionally a single top-level `<MotionConfig reducedMotion="user">` so the whole canvas
  honors it without per-component branches. Result: instant rect commit + short opacity, per
  fe-spec §5.2 / §7.3.

### 3.3 The load-bearing change: PaneFrame size FLIP

F1 `PaneFrame` animates **position only** (`animate={{x,y}}`) and **snaps size**
(`style={{width,height}}`). That is fine for floating where panes mostly translate, but
tiling and mode switches change size constantly — snapping size while sliding position reads
as broken. F2 moves `PaneFrame` to Motion `layout` FLIP so **both** position and size animate
transform-only:

```tsx
// PaneFrame.tsx (F2 shape — sketch, not final)
<motion.div
  layout
  layoutId={node.paneId}
  layoutDependency={layoutVersion}
  className="absolute outline-none"
  style={{ left: node.rect.x, top: node.rect.y, width: node.rect.width, height: node.rect.height, zIndex: node.z }}
  transition={prefersReducedMotion ? REDUCED_TRANSITION : transitionForReason}
  onLayoutAnimationComplete={clearWillChange}
  /* drag/resize unchanged: @use-gesture writes rects directly; version frozen → no FLIP */
>
```

**Distortion reality (corrected — codex point 1).** Motion does **not** automatically
counter-scale arbitrary DOM. When a parent animates `layout`, it animates a `transform: scale`;
only descendant **`motion` components that themselves declare `layout`** receive the
inverse-scale correction (the motion-dom scale-correction path). Plain viewer markup inside a
scaling parent **visibly distorts** (text squashes/stretches) for the animation's duration. So
full `layout` on `PaneFrame` is right for premium position+size morphing, but the content seam
needs an explicit correction layer.

**Concrete mitigation (required, not optional):**

1. `PaneWindow` wraps the `renderPane` output in a single `motion.div` that declares `layout`
   (an engine/chrome-owned counter-scaling layer — content stays opaque, the seam holds).
   Motion then applies the inverse-scale to that layer so content is position-corrected and does
   not squash; what remains is a brief, bounded wrapper scale that settles on the spring.
2. Heavy / measure-dependent work (transcript virtualization remeasure) defers to
   `onLayoutAnimationComplete` (fe-spec §7.3).
3. Per-viewer escape hatch: any viewer that still cannot tolerate the residual transform sets
   `layout="position"` (snap size, translate-only, zero scale) on its frame.
4. **Acceptance gate:** the stress harness adds a *visual* proof — a text-dense pane resized and
   mode-switched **at non-1 zoom** (`scale` 0.45 and 1.8, the `clampScale` bounds) — and the
   slice does not pass until that proof shows no residual text distortion at rest and bounded
   distortion in flight. This is the piece codex required for Open Q#1.

Recommendation: **adopt full `layout` with the mitigation above** (Open Q#1, resolved with
codex).

---

## 4. Reducer / state machine

All pure `EngineLayoutState -> EngineLayoutState`; rects derived by the pure planners. This
keeps `state -> rects` unit-testable (fe-spec §13: `efficientLayout.test.ts`,
`layoutState.test.ts`).

| Action | Mutation | Version bump? |
| --- | --- | --- |
| `addPane(paneId, rect)` | `upsertNode`; floating→plan; tiling→`insertIntoTree`; focus→plan | yes |
| `removePane(paneId)` | `markNodeClosing` → `removeNode`; re-plan / `pruneFromTree` | yes |
| `focusPane(paneId)` | `focusNode` (raises z, existing) | no (focus alone never reflows in floating; in focus-mode it re-plans → yes) |
| `movePane(paneId, rect)` | `updateNodeRect` (existing), floating only | **no** (instant pointer track) |
| `resizePane(paneId, rect)` | `updateNodeRect` (existing), floating only | **no** |
| `setMode(target)` | build/drop `tree`, snapshot/restore `floatingRects`, derive rects | yes |
| `splitFocused(axis)` | `insertIntoTree` at focused leaf with explicit axis | yes |
| `resizeSplit(path, i, Δ)` | adjust `sizes[i]/sizes[i+1]`, derive | **no** (instant) |
| `applyPreset(presetId)` | `treeFromPreset`, derive | yes |

Tree mutation helpers (pure, in `reducers/layoutTree.ts`, a new sibling of
`layoutState.ts`):

```ts
treeFromPanes(paneIds: readonly PaneId[], viewportAspect: number): LayoutTree
insertIntoTree(tree, focusedPaneId, newPaneId, focusedLeafRect): LayoutTree
  // fe-spec §7.2 tiling: split focused leaf along the axis with more available space;
  // if parent split shares that axis, insert a sibling + re-normalize; else wrap the leaf
  // in a new split [focusedLeaf, newLeaf] sizes [.5,.5].
pruneFromTree(tree, paneId): LayoutTree | null
  // remove the leaf; collapse any now-single-child split into its child (bubble up);
  // re-normalize sibling sizes proportionally. null if the tree empties.
resizeSplit(tree, path, boundaryIndex, deltaFraction): LayoutTree
  // trade sizes[i] ↔ sizes[i+1]. Min floor is RECURSIVE, not flat MIN_PANE_* (codex point 4):
  // each side's min fraction = subtreeMinExtent(child, splitAxis) / parentAvailableExtent.
  // Clamp delta so BOTH neighbors stay ≥ their recursive min BEFORE normalizeSizes; if both
  // are already at their recursive min the boundary is frozen. normalizeSizes then only
  // re-sums to 1, so it can never push a sibling below its recursive min.
normalizeSizes(sizes: number[]): number[]   // re-sum to 1
```

`deriveRects(state, viewportBounds): Record<PaneId, WorldRect>` is the pure dispatcher used by
the store after every structural mutation, and directly by tests.

`canvasStore.ts` changes are localized: `spawnPane`/`closePane` gain the planner commit +
`bumpVersion`; new `setMode`, `splitFocused`, `resizeSplit`, `applyPreset` actions; `movePane`/
`resizePane` stay version-frozen. The store keeps separating `layout` from `panes`, so viewer
subtrees stay referentially stable across layout-only changes.

---

## 5. tmux-like interaction model

This is the affordance that signals premium.

**Floating (unchanged plumbing):** drag header (`data-pane-drag-handle`) to move; drag corner
(`data-pane-resize-handle`) to resize. Already in `PaneFrame` + `PaneWindow`.

**Tiling separators:** render a `TilingSeparators` overlay in `LayoutCanvas`, derived from the
tree's internal boundaries (engine-owned, content-agnostic). Each separator is a
`role="separator"` element with `aria-orientation` (`vertical` for `row` splits, `horizontal`
for `column`), `aria-valuemin/max/now` reflecting the boundary fraction (fe-spec §6.2). Drag
calls `resizeSplit` and tracks the pointer 1:1 with **no FLIP** (version frozen) — exactly how
a tmux pane border feels. Keyboard: focus a separator, arrow keys nudge the fraction by a step.

**Focus toggle:** double-click header or leader-`z` zooms the active pane (focus mode / tmux
zoom); again toggles back.

**Keyboard (fe-spec §12 F2: "keyboard leader or command bar shortcuts"):** an **in-app leader
chord** (not a raw `Ctrl+\`` binding until conflicts are tested — Open Q#4, resolved with
codex) then: `|`/`v` vertical split, `-`/`h` horizontal split, `x` close focused **except the
picker** (`canvasStore.closePane` no-ops on `PICKER_PANE_ID` today at `canvasStore.ts:59-61`;
the key handler mirrors this — no close, no error chime, focus stays put), arrow keys move focus
to the nearest open pane center in that direction (spatial nav over rects), `z` zoom/focus,
`f`/`t`/`g` cycle floating/tiling/grid-reset, `1`–`4` presets, `p` focus picker, `0` reset view.

**Command bar (`CanvasCommandBar`) roving focus (APG toolbar, fe-spec §5.2):** grows mode
buttons + a preset menu. Exactly one toolbar control is in the tab order (`tabIndex=0`); the
rest are `tabIndex=-1`. Left/Right arrows move the roving tabstop between controls (Home/End
jump to ends); Enter/Space activate; the active control's id is the toolbar's
`aria-activedescendant`. Every keyboard shortcut above has a visible, focusable twin here, and
focus returns to the invoking control after a mode switch (fe-spec §5.2 "focus never
disappears").

---

## 6. Performance (60fps with ~12 panes)

- **Transform-only.** Motion `layout` animates translate + scale; we never animate `width`,
  `height`, `top`, `left`, grid tracks, or scroll position (fe-spec §7.3 binding rules).
- **`layoutDependency={layoutVersion}`** is the thrash guard: stream appends, content
  re-renders, pan/zoom, drag, and resize never bump it → no measurement, no FLIP. Only the 8
  discrete re-plan actions in §4 bump it.
- **Content isolation (must be BUILT — not true in F1; codex point 5).** Real F1
  `CanvasSurface.tsx` builds the `renderPane` closure inline (lines 44-72) and renders viewers
  without memo, so a layout-only store update re-renders every viewer. F2 introduces a
  `PaneSlot` component (`React.memo`; props = `paneId` + a stable `actions` ref + a per-pane
  `PaneRecord` selector) that subscribes only to its own content slice. Rect/layout changes flow
  through `PaneFrame` transforms and never reach `PaneSlot`, so viewers do not re-render on
  layout-only changes. Live stream appends mutate transcript content state inside the slot, not
  engine state. The design no longer *assumes* this seam — it ships it.
- **`will-change: transform`** applied for the duration of an animation, cleared on
  `onLayoutAnimationComplete` (no persistent `will-change`, which would bloat compositor
  memory at 12+ panes).
- **Direct manipulation bypasses FLIP.** Drag/resize/separator commit rects immediately,
  rAF-batched by `@use-gesture/react`, version frozen.
- **Pan/zoom is one world-layer transform** (existing `useCanvasViewport`), independent of and
  composing cleanly with per-pane transforms; drag deltas already divide by `data-canvas-scale`.
- **Stress harness extension (aligned to the REAL gate — codex point 7).** The existing
  `tests/perf/sessionCanvasStress.spec.ts` + `SessionCanvasStressRoute` gain: `setMode`
  floating↔tiling↔focus, preset switches, tiling separator resize, and the §3.3 non-1-zoom
  text-distortion visual proof, across the **existing** sweep
  `STRESS_COUNTS = [1, 2, 4, 8, 16, 30]`. The CI gate stays the **existing** bounded threshold
  `STRESS_P95_THRESHOLD_MS = 50` (`tests/perf/sessionCanvasStress.spec.ts:3`); the ~16.7ms
  one-frame figure is the *local* 60fps aspiration only. Per fe-spec §7.4 CI asserts a
  **bounded** p95 plus no layout-thrash warnings — I am **not** introducing a new unqualified
  16.7ms CI assertion. A slice cannot pass if it adds motion without extending the harness.

---

## 7. Edge cases

- **Tiny viewport.** `planTilingLayout` clamps leaves to `MIN_PANE_WIDTH/HEIGHT`. If the tree's
  min sizes exceed the viewport, the world overflows and pan/zoom-to-fit reaches it; a
  non-blocking "dense layout — try focus mode" hint surfaces. Floating's `overflowPenalty`
  already steers candidates away from clipping (Open Q #5).
- **Many panes (12–30).** Tiling stays crisp (exact O(n) rect math). Floating grid clamps cells
  to min and overflows; `overflowPenalty` keeps `balancedGrid` ahead of a degenerate single
  row/column.
- **Spawn placement.** tiling → focused leaf (axis by larger leaf dimension); floating → after
  focused in order, else after picker; focus → new rail.
- **z-order (floating).** `nextPaneZ` on focus (existing). Tiling/focus do not overlap, so `z`
  matters only for the closing-exit fade.
- **Pan/zoom mid-transition.** World transform is independent and in world units, so an
  in-flight FLIP stays zoom-stable. If a re-plan would land mid-drag, version gating means the
  drag owns the rect until release; the re-plan applies on the next discrete action.
- **Closing during a mode switch.** `treeFromPanes` and all planners consider only
  `lifecycle === "open"` panes; closing panes are excluded from the tree and from scoring.
- **Pinned + tiling.** `pinned` is a floating concept. Entering tiling clears pinned
  participation (every open pane joins the tree); leaving tiling restores `floatingRects`,
  which carried the pinned positions. Documented so it is not a surprise (Open Q #8).
- **Reduced motion.** Instant rect commit + short opacity (existing `REDUCED_TRANSITION`);
  separators stay keyboard-resizable; no parallax or stagger.

---

## 8. Reuse contract (littleorgans tmux-at-scale)

- `www/src/engine/**` imports **zero** viewer/session code. The boundary lint (fe-spec §7.1
  "boundary lint") stays the enforcement and must cover the new `layoutTree.ts` and
  `TilingSeparators`. It must **also** flag the existing reverse violation codex found
  (point 6): `SessionCanvasStressRoute.tsx:15-16` deep-imports
  `../../engine/perf/frameMeter` and `../../engine/planners/efficientLayout` instead of the
  `../../engine` barrel. fe-spec §3.2 (lines 86-93) requires `session-canvas → engine` through
  `index.ts` only. Fix: route those two imports through the barrel (which already re-exports
  both via `engine/index.ts`) and have the lint forbid deep `engine/*/*` imports from
  `session-canvas/**`.
- Everything is keyed by **opaque `PaneId`**. `PaneNode` and `LayoutTree` carry no `viewerId`,
  title, session id, or content ref (fe-spec §3.3: "Engine only. No viewer id…").
- **`renderPane(paneId): React.ReactNode`** (the `LayoutCanvas` prop) is the only content
  seam. The `PaneNode → PaneRecord` join lives in the feature layer (`CanvasSurface.tsx`),
  never in the engine.
- The split tree + scored planner + FLIP harness + separators + keyboard model together form a
  generic tmux-like layout kernel. A littleorgans consumer reuses it by supplying its own
  `renderPane` and its own out-of-engine join table — exactly the session-canvas pattern. No
  content concern leaks through the seam.
- New visual tokens (separator color, focus ring, density hint) are **named** in
  `www/src/styles/tokens.css` / `index.css`, never inlined (fe-spec §5.1). Planner constants
  (`WORLD_MARGIN`, `PANE_GAP`, `MIN_PANE_*`, `MAIN_FRACTION`, scoring weights) are world-unit
  math and stay as exported TS constants beside the planner.

---

## 9. Resolved positions (codex review round 1) + remaining for Stuart

All eight are **resolved with codex** at sign-off round 1; they remain open only for Stuart's
final adjudication.

1. **PaneFrame → Motion `layout` (size FLIP). RESOLVED: full `layout`** (not `layout="position"`)
   for mode switches, with the §3.3 **mandatory** mitigation — engine-owned counter-scaling
   content wrapper + deferred heavy work + non-1-zoom text-distortion visual proof in the
   harness. `layout="position"` is a per-viewer escape hatch only. This is the one change that
   touches the shipped F1 frame.
2. **Separator ownership. RESOLVED: engine-owned `TilingSeparators`** overlay derived from the
   tree (content-agnostic), not `PaneWindow` edge handles.
3. **`floatingRects` round-trip. RESOLVED: snapshot + restore** manual floating positions across
   a tiling/focus trip.
4. **Leader key binding. RESOLVED: in-app leader chord**, not a raw `Ctrl+\`` binding, until
   conflicts with terminal-style shortcuts (fe-spec §5.2) / browser defaults are tested.
5. **Tiny-viewport policy. RESOLVED: overflow + pan-to-reach** with a dense-layout hint; no
   auto-fallback to focus.
6. **Tiling-focus = tmux zoom. RESOLVED:** `focus` is the global mode; from tiling it zooms the
   active leaf and restores via the explicit `suspended` contract (§1.1
   `preFocusMode`/`preFocusTree`/`preFocusRects`), so identity/streams survive and the tree
   invariant holds.
7. **Persistence adapter (F3 seam). RESOLVED: interface only in F2, no storage.**
   `LayoutSnapshot = { schemaVersion: number; canvasKey: string; mode: LayoutMode; tree:
   LayoutTree | null; rects: Record<PaneId, WorldRect>; viewport: CanvasViewport; focusedPaneId:
   PaneId | null; paneOrder: PaneId[]; pinned: PaneId[]; floatingRects: Record<PaneId, WorldRect>
   | null }` behind `LayoutPersistenceAdapter { load(canvasKey): LayoutSnapshot | null;
   save(s: LayoutSnapshot): void }`. No storage backend wired in F2.
8. **`pinned` in tiling. RESOLVED: pinned does not affect tiling;** panes drop pin participation
   on entering tiling and restore manual position via `floatingRects` on return.

---

## Appendix: file-level change map (no code written in Phase 1)

| Path | F2 change |
| --- | --- |
| `engine/types.ts` | Add `SplitAxis`, `LayoutTree`/`LayoutLeaf`/`LayoutSplit`, `SuspendedLayout`; extend `EngineLayoutState` with `tree`, `layoutVersion`, `floatingRects`, `suspended`. |
| `engine/planners/efficientLayout.ts` | Two-stage selection (feasibility filter + normalized soft sum); 5 candidate generators; reordered tie-breaks; `subtreeMinExtent`; rename `planFocus`→`planFocusLayout`; add recursive-min `planTilingLayout`; export weights/constants. |
| `engine/reducers/layoutTree.ts` (new) | `treeFromPanes`, `insertIntoTree`, `pruneFromTree`, `resizeSplit` (recursive-min clamp before normalize), `normalizeSizes`, `subtreeMinExtent`, `assertTreeInvariant`, `deriveRects`. |
| `engine/reducers/layoutState.ts` | `setMode`, `bumpLayoutVersion`, `snapshotFloatingRects`, suspend/restore for focus-zoom; keep existing reducers. |
| `engine/react/PaneFrame.tsx` | Migrate to full `layout` + `layoutId` + `layoutDependency={layoutVersion}`; rect → layout box; `onLayoutAnimationComplete` will-change clear. |
| `engine/react/LayoutCanvas.tsx` | Wrap panes in `<LayoutGroup>`; render `TilingSeparators` overlay in tiling. |
| `engine/react/TilingSeparators.tsx` (new) | Tree-derived `role="separator"` resize handles. |
| `session-canvas/components/PaneWindow.tsx` | Add the engine/chrome counter-scaling `motion.div layout` wrapper around `renderPane` output (§3.3 distortion mitigation); tiling separator/keyboard affordances. |
| `session-canvas/components/PaneSlot.tsx` (new) | `React.memo` content seam (props: `paneId` + stable `actions` + per-pane selector) so viewers don't re-render on layout-only changes (§6). |
| `session-canvas/model/canvasStore.ts` | Wire planner commits on spawn/close; add `setMode`/`splitFocused`/`resizeSplit`/`applyPreset`; keyboard close respects the `PICKER_PANE_ID` guard. |
| `session-canvas/components/CanvasSurface.tsx` | Route `renderPane` through `PaneSlot`; stop rebuilding the closure inline per render. |
| `session-canvas/components/CanvasCommandBar.tsx` | Mode buttons + preset menu (APG toolbar roving focus). |
| `session-canvas/perf/SessionCanvasStressRoute.tsx` + `tests/perf/sessionCanvasStress.spec.ts` | Mode-switch / preset / tiling-resize + non-1-zoom text-distortion visual proof; keep `STRESS_COUNTS=[1,2,4,8,16,30]` and the `STRESS_P95_THRESHOLD_MS=50` gate. Fix the deep engine imports at lines 15-16 to use the `../../engine` barrel. |
| Boundary lint | Cover `layoutTree.ts` + `TilingSeparators`; forbid deep `engine/*/*` imports from `session-canvas/**` (catches the existing stress-route violation). |
| Tests | `efficientLayout.test.ts` (canonical winner+rects table, feasibility filter, normalized terms, reordered tie-breaks, spawn/close/pinned), `layoutState.test.ts` (split insert/prune/normalize, recursive-min overflow, focus suspend/restore, reduced-motion), `PaneWindow.a11y.test.tsx` (separator semantics, focus return, picker-close guard). |
