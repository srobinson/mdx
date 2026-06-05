---
title: Canvas Lab spec — experimental /canvas-lab route + layout-strategy registry
type: sessions
tags: [transport-matters, session-canvas, canvas-lab, frontend, layout, registry, spec]
summary: A tiny experimental /canvas-lab route whose core abstraction is a layout-strategy registry (mirroring the viewer registry) so adding/tweaking a layout is one registerLayout call.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

# Canvas Lab Spec

Design only. No implementation. Scope was cut by Stuart from the full F2 layout manager
(`f2-layout-manager-design.md`, **PARKED**) to a small experimental route whose **single
goal is that adding or tweaking a layout is trivial**. We validate the *feel* first, then
adopt from the parked F2 design only what proves out.

The core abstraction is a **layout-strategy registry** that mirrors the existing **viewer
registry** (`www/src/session-canvas/viewers/registry.tsx`). A strategy is a pure
`plan(input, params) → rects` function plus a declarative list of `controls`; the lab
auto-renders the tweak panel from `controls` and re-plans live. Adding a new layout is one
`registerLayout(...)` call and zero other edits — that is the acceptance heart (§6).

## 0. Grounding: what we reuse (real F1 code, no engine rewrite)

| Reused piece | Path | Role in the lab |
| --- | --- | --- |
| `PaneNode`, `WorldRect`, `CanvasViewport`, `ViewportBounds`, `EngineLayoutState` | `engine/types.ts` | Pane/rect/viewport shapes; the lab store holds an `EngineLayoutState` so `LayoutCanvas` consumes it directly |
| `LayoutCanvas` | `engine/react/LayoutCanvas.tsx` | The world+pane renderer; `renderPane(paneId)` seam, `setViewport`, move/resize/focus callbacks |
| `PaneFrame` | `engine/react/PaneFrame.tsx` | Per-pane geometry + drag/resize plumbing (`data-pane-drag-handle`, `data-pane-resize-handle`, reads `data-canvas-scale`) |
| `useCanvasViewport` | `engine/react/useCanvasViewport.ts` | Pan/zoom, reused as-is; framing lives in the lab store over a pure reducer (§3.2), **not** in this hook |
| `zoomViewportAt`, `panViewport`, `clampScale`, `setViewport`, `createPaneNode`, `nextPaneZ`, `upsertNode`, `updateNodeRect`, `createInitialEngineLayoutState` | `engine/reducers/*` | Store reducers; `clampScale` bounds = 0.45–1.8 |
| Route selection | `route.ts` `selectRootRoute`, `main.tsx` lazy import | The `/canvas-lab` registration mirrors `/canvas` |
| Self-contained route pattern | `session-canvas/perf/SessionCanvasStressRoute.tsx` | **The template.** Local state, `LayoutCanvas`, a synthetic pane viewer, a command-bar toolbar — the lab is this plus the registry + controls panel + camera framing |

`SessionCanvasStressRoute` already proves the shape: it builds an `EngineLayoutState` with
`createPaneNode`/`upsertNode`, renders `<LayoutCanvas renderPane={...} setViewport={...}>`, and
drives layout with `planEfficientLayout`. The lab swaps the single hard-coded planner for the
**strategy registry** and adds the controls panel + camera framing.

**Locked (do not re-debate):** new route `/canvas-lab`; tiny dedicated store; reuse the four
engine pieces above; registry is the core abstraction; strategies own **rects**, the camera
owns the **view transform**; first strategy = grid-fit (width-first); add auto-organizes;
right-size to registry + typed params + three control kinds (no JSON DSL, no hot-reload, no
persistence wiring).

---

## 1. Registry seam (the core abstraction)

Lives in a new **engine** module `www/src/engine/layout/` (content-agnostic, reusable, sits
beside `engine/planners/`). It mirrors the viewer registry's array + upsert-by-id + resolve
shape exactly.

### 1.1 Types — `engine/layout/types.ts`

```ts
import type { PaneId, ViewportBounds, WorldRect } from "../types";

// Declarative param values are intentionally narrow (right-sizing: no nested objects, no DSL).
export type ParamValue = number | boolean | string;
export type LayoutParams = Record<string, ParamValue>;

// The 3 — and only 3 — control kinds. The lab auto-renders one input per control.
export interface NumberControl {
  kind: "number";
  key: string;            // a key of the strategy's params
  label: string;
  min: number;
  max: number;
  step: number;
}
export interface ToggleControl {
  kind: "toggle";
  key: string;
  label: string;
}
export interface EnumControl {
  kind: "enum";
  key: string;
  label: string;
  options: ReadonlyArray<{ value: string; label: string }>;
}
export type Control = NumberControl | ToggleControl | EnumControl;

// What a strategy is given. Content-agnostic: pane ids + the world-space layout bounds only.
export interface PlanInput {
  paneIds: readonly PaneId[];
  viewport: ViewportBounds;                         // world units (scale-1 design space)
  currentRects?: Readonly<Record<PaneId, WorldRect>>; // for future stability-aware strategies; grid-fit ignores
}

// Strategies return RECTS ONLY. No camera data crosses the seam (codex r1 point 2): the lab
// computes any fit from the committed rect bounding box (§3.3), so a new strategy author never
// thinks about the camera. This is what keeps PlanResult minimal and the boundary literal.
export interface PlanResult {
  rects: Record<PaneId, WorldRect>;
  reason?: string;                                  // candidate/debug label, like efficientLayout's `reason`
}

// P is the strategy's own param shape; the registry stores strategies type-erased to LayoutParams
// (exactly as the viewer registry erases TRef behind canRender).
export interface LayoutStrategy<P extends LayoutParams = LayoutParams> {
  id: string;
  label: string;
  defaults: P;
  controls: readonly Control[];
  plan(input: PlanInput, params: P): PlanResult;    // PURE + deterministic
}

// Configs are DATA: a named (strategyId, params) pair. Built-ins are plain literals.
export interface LayoutConfig {
  id: string;
  label: string;
  strategyId: string;
  params: LayoutParams;
}
```

### 1.2 Registry API — `engine/layout/registry.ts`

Mirrors `registerViewer` / `resolveViewer` (array, upsert-by-id, throw-on-missing):

```ts
import type { LayoutStrategy } from "./types";

const registry: LayoutStrategy[] = [];

export function registerLayout(strategy: LayoutStrategy): void {
  validateStrategy(strategy);              // throw at registration on any control/defaults mismatch
  const i = registry.findIndex((s) => s.id === strategy.id);
  if (i >= 0) registry[i] = strategy;      // upsert (same semantics as registerViewer)
  else registry.push(strategy);
}

export function listLayouts(): readonly LayoutStrategy[] {
  return registry;
}

export function resolveLayout(strategyId: string): LayoutStrategy {
  const s = registry.find((entry) => entry.id === strategyId);
  if (!s) throw new Error(`No layout strategy registered for ${strategyId}.`);
  return s;
}

// Dev-time guard so the type-erased registry (LayoutStrategy<LayoutParams>) is SAFE
// (codex r1 points 1, 7). Every control.key must exist in defaults, its kind must match the
// default's runtime type, and an enum default must be one of its options. Throws like
// resolveViewer — caught at the strategy's first import, never silently at setParam.
export function validateStrategy(s: LayoutStrategy): void {
  const KIND_TYPE = { number: "number", toggle: "boolean", enum: "string" } as const;
  for (const c of s.controls) {
    if (!(c.key in s.defaults)) throw new Error(`[${s.id}] control "${c.key}" not in defaults`);
    const actual = typeof s.defaults[c.key];
    if (actual !== KIND_TYPE[c.kind])
      throw new Error(`[${s.id}] control "${c.key}" is ${c.kind} but default is ${actual}`);
    if (c.kind === "enum" && !c.options.some((o) => o.value === s.defaults[c.key]))
      throw new Error(`[${s.id}] enum default "${String(s.defaults[c.key])}" not in options`);
  }
}
```

Built-in strategies are **auto-discovered** so adding one is literally zero-edit (§6):
`engine/layout/index.ts` loads every strategy file with Vite's
`import.meta.glob("./strategies/*.ts", { eager: true })` (verified available: Vite 8.0.8 /
Vitest 4.1.4; not yet used elsewhere in the repo), then re-exports `types`, `registry`, and
`configs`. Each strategy file calls `registerLayout(...)` at module scope as its side effect.
Tests may import a strategy file directly (the glob is only the app/build auto-loader).

### 1.3 Built-in configs — `engine/layout/configs.ts`

```ts
import type { LayoutConfig } from "./types";

export const BUILT_IN_CONFIGS: readonly LayoutConfig[] = [
  { id: "grid-fit-default", label: "Grid (fit)", strategyId: "grid-fit", params: {} }, // {} → strategy.defaults
];
```

### 1.4 How the lab consumes the registry (data flow)

1. The controls panel enumerates configs (`BUILT_IN_CONFIGS`) into a picker, and `listLayouts()`
   for the strategy list.
2. On select, the store resolves the strategy (`resolveLayout(config.strategyId)`) and seeds the
   live params: `params = { ...strategy.defaults, ...config.params }`.
3. The panel auto-renders one input per `strategy.controls[i]`, bound to `params[control.key]`.
4. Any control change → `setParam(key, value)` → store re-runs `strategy.plan({paneIds, viewport},
   params)` → commits `result.rects` into the nodes → if `fitToContent` is on, the lab fits the
   camera to the committed bounding box (§3.3). The strategy returns rects only.
5. Add/close panes and the Organize button also call `plan(...)` (auto-organize, §4/§5).

**Validation (codex r1 points 1, 7).** `registerLayout` runs `validateStrategy` (§1.2) so a
typo'd `control.key` or a kind/type mismatch throws at first import, never silently at `setParam`.
`setParam` additionally clamps `number` controls to `[min, max]` and ignores `enum` values outside
`options`. With this guard, the type-erased registry + the three control kinds are safe and
sufficient (no fourth kind needed for grid / single-row / masonry).

`plan` is pure, so the panel is a thin "edit params → re-plan → commit rects" loop with no
strategy-specific UI code. **That loop is the whole point.**

---

## 2. First strategy: `grid-fit` (width-first)

`engine/layout/strategies/gridFit.ts`. Pure, deterministic, content-agnostic.

### 2.1 Params, defaults, controls

```ts
interface GridFitParams extends LayoutParams {
  minW: number;          // 320
  minH: number;          // 240
  gap: number;           // 24
  margin: number;        // 48
  targetAspect: number;  // 4/3 ≈ 1.333
  lastRow: "left" | "center"; // "left"
}

const defaults: GridFitParams = {
  minW: 320, minH: 240, gap: 24, margin: 48, targetAspect: 4 / 3, lastRow: "left",
};

const controls: readonly Control[] = [
  { kind: "number", key: "minW", label: "Min width", min: 160, max: 640, step: 20 },
  { kind: "number", key: "minH", label: "Min height", min: 120, max: 560, step: 20 },
  { kind: "number", key: "gap", label: "Gap", min: 0, max: 64, step: 4 },
  { kind: "number", key: "margin", label: "Margin", min: 0, max: 120, step: 4 },
  { kind: "number", key: "targetAspect", label: "Target aspect", min: 0.5, max: 2.5, step: 0.05 },
  { kind: "enum", key: "lastRow", label: "Last row", options: [
    { value: "left", label: "Left-align" }, { value: "center", label: "Center" } ] },
];
```

**`zoomToFit` removed from grid-fit (codex r1 point 2).** grid-fit returns rects only; vertical
overflow is fitted by the lab's `Fit to content` camera op (§3.3, default ON). The orchestrator's
locked `zoomToFit=true` default is **relocated** from a grid-fit param to that lab-level toggle —
same default, same observable behavior, but strategies stay rects-only and the boundary is
literal. (Flagged for the orchestrator/Stuart in §9 since it touches a locked decision.)

### 2.2 Algorithm

Let `W = viewport.width`, `H = viewport.height`, `M = margin`, `G = gap`, `N = paneIds.length`.

```
if (N === 0) return { rects: {} }                   // empty-plan guard

cols  = selectColumns(N, viewport, params)          // see below — SIMULATES the zoom to pick cols
rows  = ceil(N / cols)
cellW = max(minW, (W - (cols-1)G - 2M) / cols)
cellH = max(minH, (H - (rows-1)G - 2M) / rows)      // min floors honoured; the lab zooms to fit

// Placement, row-major, last (partial) row aligned per `lastRow`:
for each pane i (0-based, creation order of paneIds):
  r = floor(i / cols); c = i % cols
  rowCount = (r === rows-1) ? (N - r*cols) : cols
  rowWidth = rowCount*cellW + (rowCount-1)*G
  startX   = (r === rows-1 && lastRow === "center") ? M + (W - 2M - rowWidth)/2 : M
  rect[i]  = { x: startX + c*(cellW+G), y: M + r*(cellH+G), width: cellW, height: cellH }

return { rects, reason: `grid-fit ${cols}x${rows}` } // rects only — no camera data
```

**Column selection (the fix).** The old selector chose columns from how many `minW` panes fit at
**scale 1** (a capacity cap), then the lab zoomed out *separately* to fit extra rows — leaving a
horizontal band empty once the zoom engaged. The new selector **simulates the final on-screen
result including that zoom** and maximizes displayed (post-zoom) pane area, penalized toward
`targetAspect`:

```
selectColumns(N, viewport, params):
  for cols in 1..N:
    rows  = ceil(N / cols)
    cellW = max(minW, (W - (cols-1)G - 2M) / cols)
    cellH = max(minH, (H - (rows-1)G - 2M) / rows)
    gridW = cols*cellW + (cols-1)G ; gridH = rows*cellH + (rows-1)G
    scale = fitScale(gridW, gridH, viewport)        // SHARED with the lab's Fit to content (§3.3)
    score = (cellW*scale)*(cellH*scale) * exp( -| ln( (cellW/cellH) / targetAspect ) | )
  pick max score ; tie-break fewer rows, then fewer cols (deterministic)

// fitScale (engine/layout/fit.ts) — the ONE shared helper the planner SIMULATES and the lab APPLIES,
// so they cannot drift. The strategy stays rects-only; only the lab moves the camera.
fitScale(contentW, contentH, bounds) = min(1, bounds.width/contentW, bounds.height/contentH)
```

Determinism: no `Date.now`/`Math.random`; panes consumed in `paneIds` order; the `cols` loop and
its tie-break are deterministic. The aspect factor `exp(-|ln(r)|) = min(r, 1/r)` is 1 at the target
ratio and decays symmetrically away from it.

### 2.3 Edge cases + worked examples

Design space `W=1600, H=1000, M=48, G=24, minW=320, minH=240, targetAspect=4/3` (except the last
two rows, which use their own params). "lab fit" is the scale the lab's Fit to content applies
(`1.0` = fits at scale 1). `gridFit.test.ts` asserts every row's `cols×rows`: the N=5 and N=12
cell sizes are asserted **approximately at this 1600×1000 design space** (the fractional
`485.3`/`285.3`) and **exactly** at integer-friendly viewport variants (N=5 @1602, N=12 @1044);
the 13-pane and narrow-12 rows are asserted exactly.

| N | cols×rows | cellW × cellH | lab fit | note |
| --- | --- | --- | --- | --- |
| 1 | 1×1 | 1504 × 904 | 1.0 | sole pane fills the work area |
| 2 | 2×1 | 740 × 904 | 1.0 | side-by-side |
| 4 | 2×2 | 740 × 440 | 1.0 | balanced grid |
| 5 | 3×2 | 485.3 × 440 | 1.0 | **3 columns fill the width** — the zoom-aware selector prefers wider panes over the old 2×3 |
| 12 | 4×3 | 358 × 285.3 | 1.0 | balanced grid; cell aspect ≈ 1.25 ≈ target |
| 13 @1920×1048, `M0/G20/minW380/minH320` | 5×3 | 380 × 336 | ≈ 0.97 | **regression fix**: was 4×4 @ ≈0.78 with an empty right band; now fills the full width (5×380+4×20 = 1980 spans the 1920) |
| 12 @900×1000 (narrow) | 3×4 | 320 × 240 (clamped) | ≈ 0.893 | min floors hit; lab fits the 1008×1032 bbox: `min(1, 900/1008, 1000/1032) = 900/1008 ≈ 0.893` |

Other edges: **N === 0** → `{ rects: {} }` (guard). **Overflow at min sizes** (more rows/cols than
fit) → cells stay at the `minW`/`minH` floors and the lab zooms the camera to the committed
bounding box via the shared `fitScale` (§3.3). **Partial last row** → aligned by `lastRow`. Because
the selector now scores the *post-zoom* displayed size, it no longer leaves horizontal slack when
the zoom engages — that was the reported bug.

---

## 3. Camera framing (the view transform, owned by the camera — not strategies)

Hard boundary: strategies return rects; **the camera owns pan/zoom**. "Bring into view" is a
viewport op, never a strategy. The framing math is a pure reducer; the framing state and actions
live in the lab store (§3.2), so the shared `useCanvasViewport` hook is not modified.

### 3.1 Pure math — `engine/reducers/layoutState.ts` (add)

```ts
const FRAME_FRACTION = 0.8;  // pane fills ~80% of the viewport

// Target viewport so `rect` is centered and fills `fraction` of the screen `bounds`.
export function frameRectViewport(
  rect: WorldRect, bounds: ViewportBounds, fraction = FRAME_FRACTION,
): CanvasViewport {
  const scale = clampScale(fraction * Math.min(bounds.width / rect.width, bounds.height / rect.height));
  const cx = rect.x + rect.width / 2;
  const cy = rect.y + rect.height / 2;
  return { scale, panX: bounds.width / 2 - cx * scale, panY: bounds.height / 2 - cy * scale };
}
```

This reuses the existing transform contract (`screen = world*scale + pan`, fe-spec §5.1) and
`clampScale` (0.45–1.8). The `fit.scale` from §2.2 is applied the same way (scale only, recenter
on the rect bounding box).

### 3.2 Where framing lives — the LAB STORE, not the shared hook (codex r1 point 4)

`useCanvasViewport` is consumed **internally** by `LayoutCanvas` (`LayoutCanvas.tsx:25`), so its
return is unreachable from the lab route or the pane chrome — adding a `framePane` method there
would be uncallable. Framing therefore lives in the **lab store** over the pure
`frameRectViewport` reducer (§3.1). The shared hook and `/canvas` are **untouched** (zero blast
radius), which also keeps the experimental route trivially deletable.

Store actions (§4.2): `framePane(paneId)`, `unframe()`, `resetView()`. Each reads the node rect +
current `bounds`, computes `frameRectViewport`, and commits via the store's `setViewport` (which
`LayoutCanvas` already threads to the world layer).

Lab interaction contract:

- **Frame a pane** → `store.framePane(paneId)`: stash current viewport as `framing.priorViewport`,
  set `framing.framedPaneId = paneId`, `setViewport(frameRectViewport(rect, bounds))`. Triggers
  (codex r1 point 5 — **not** mouse-only): a dedicated **Frame** button in the pane header AND a
  keyboard shortcut on the focused pane; title-bar double-click stays as a convenience.
- **Unframe** → `store.unframe()` (Frame-again / `Esc`): restore `framing.priorViewport`, clear
  `framedPaneId`.
- **Precondition:** active only when `paneCount > 1`. With one pane it is a no-op (it already
  fills the work area).
- **Reset view** → `store.resetView()` → `setViewport({ panX: 0, panY: 0, scale: 1 })` (button +
  shortcut, independent of framing).
- **The "fly":** a scoped `transition: transform <FRAME_MS> cubic-bezier(...)` class on the
  `canvas-world` layer for the frame/unframe duration, then cleared. Pan/zoom keep their normal
  (transition-less) behavior. `prefers-reduced-motion` → instant. (The world layer is a plain
  transformed div, `LayoutCanvas.tsx:41-48`, so a scoped CSS transition is the cheapest "fly".)

### 3.3 Fit to content (lab-side, generic — replaces strategy `zoomToFit`)

After every re-plan the lab computes the bounding box of the committed rects and zooms the camera
to fit it via the **shared `fitScale`** (§2.2) — the exact same helper the grid-fit planner
*simulates* when choosing its column count, so the two cannot drift. A **Fit to content**
command-bar toggle (default ON — where the locked `zoomToFit=true` now lives) gates it; the box is
centred in the full viewport, and the engine `clampScale` bounds apply when the viewport is
committed. For the narrow N=12 case (`3×4`, bbox `1008×1032`) this yields
`min(1, 900/1008, 1000/1032) = 900/1008 ≈ 0.893`. Strategy-agnostic: every strategy benefits without
emitting any camera data, which is exactly what keeps `PlanResult` rects-only (§1.1).

---

## 4. Lab route + tiny store

### 4.1 Route registration (mirror the stress route)

- `route.ts`: extend `RootRoute` to `"canvas" | "canvas-lab" | "legacy"`; `selectRootRoute`
  returns `"canvas-lab"` for `pathname === "/canvas-lab"`.
- `main.tsx`: add the lazy branch alongside the existing `canvas`/`legacy` split:
  `selectedRoute === "canvas-lab"` → `import("./session-canvas/lab/CanvasLabRoute")`.
- New files live in `www/src/session-canvas/lab/` (sibling subtree to `perf/`), so the lab is
  isolated from the production `/canvas` surface and trivially deletable.
- Static fallback: same posture as `/canvas` (dev-first; if prod direct-load needs SPA fallback,
  reuse whatever makes `/canvas` load — out of scope for the experiment).

### 4.2 Tiny store — `session-canvas/lab/canvasLabStore.ts`

A small zustand store (mirrors `canvasStore.ts` but minimal). It holds an `EngineLayoutState` so
`LayoutCanvas` consumes it unchanged.

```ts
interface CanvasLabState {
  layout: EngineLayoutState;                 // nodes + viewport + focusedPaneId (mode stays "floating")
  bounds: ViewportBounds;                    // world-space layout bounds (from the measured route element)
  activeConfigId: string;
  params: LayoutParams;                      // live-edited params for the active strategy
  fitToContent: boolean;                     // §3.3 lab-level toggle (replaces grid-fit zoomToFit), default true
  framing: { framedPaneId: PaneId | null; priorViewport: CanvasViewport | null };

  addPane(): void;                           // create stub pane → organize() (auto-organize)
  closePane(paneId: PaneId): void;           // remove node → organize()
  setConfig(configId: string): void;         // resolveLayout, reseed params = {...defaults, ...config.params} → organize()
  setParam(key: string, value: ParamValue): void; // clamp/validate → organize() (live re-plan)
  organize(): void;                          // resolveLayout(config).plan({paneIds, bounds}, params); commit rects; lab-side fit
  setBounds(bounds: ViewportBounds): void;   // ResizeObserver → organize()
  framePane(paneId: PaneId): void;           // §3 frame (guarded by paneCount > 1)
  unframe(): void;                           // restore framing.priorViewport
  resetView(): void;
  setViewport(v: CanvasViewport): void;      // pan/zoom passthrough → setEngineViewport
}
```

`organize()` is the one re-plan path: read open `paneIds`, call the active strategy's `plan`,
write `result.rects` into nodes via `updateNodeRect`/`upsertNode`, then — if `fitToContent` is on
(§3.3) and the committed bounding box exceeds `bounds` — zoom the camera to that bbox. **No fit
data comes from the strategy.** Manual drags (`onMovePane`) write rects directly without
re-planning; **Organize** re-applies the plan (tidies after dragging).

### 4.3 Stub viewers (1–2, content is irrelevant)

Strategies are content-agnostic, so the lab needs only placeholder content to fill panes. Two
tiny stubs demonstrate that layout is independent of content:

- `LabCardPane` — a labeled card showing `paneId` (mirrors `SyntheticPane` in the stress route).
- `LabRulerPane` — shows live `width × height` of its rect (handy when eyeballing a strategy).

These are plain components chosen round-robin on add; **not** a registry (right-sizing — the lab
proves the *layout* registry, not a content registry). `renderPane(paneId)` returns
`<PaneChrome …><LabCardPane/|LabRulerPane/></PaneChrome>` — the shared extracted chrome (§5,
codex r1 point 5), not a copy of `PaneWindow`.

---

## 5. The 4 MVP affordances

All four live in a command-bar toolbar (mirror `SessionCanvasStressRoute`'s `canvas-command-bar`).

Pane chrome is a **shared, extracted** `PaneChrome` component — copying `PaneWindow.tsx` would
violate this repo's zero-tolerance DRY rule (codex r1 point 5). `PaneChrome` takes **primitive
props** (`title`, `badge`, `state`, `closeDisabled`, `onClose`, `onFrame`, `onHeaderDoubleClick`,
`children`) — **not** `PaneRecord`. `PaneWindow.tsx` is refactored into a thin adapter that maps
`PaneRecord → PaneChrome` props (its existing JSX moves into `PaneChrome`); the lab renders
`PaneChrome` directly. One chrome, two callers, variation in props.

1. **Add button** (command bar) → `store.addPane()` → auto-organize. A "−"/count chip shows N.
2. **Frame + close** (per pane, in `PaneChrome`):
   - A dedicated **Frame** header button (`onFrame` → `store.framePane(paneId)`) **and** a
     keyboard shortcut on the focused pane — framing is keyboard-accessible, not double-click-only
     (codex r1 point 5; fe-spec §5.2 keyboard-equivalents). Title-bar double-click
     (`onHeaderDoubleClick`, distinct from drag via `@use-gesture`) stays as a convenience. No-op
     at `paneCount <= 1`.
   - Close button (`onClose` → `store.closePane(paneId)` → organize).
3. **Organize button** (command bar) → `store.organize()` — re-applies the active config after
   manual dragging (tidy).
4. **Strategy/config picker + auto-controls panel** (command bar / side rail):
   - A `<select>` over `BUILT_IN_CONFIGS` (+ `listLayouts()` for raw strategies) → `setConfig`.
   - Below it, the **auto-rendered** controls: map `strategy.controls` → one input each
     (`number`→range/number input, `toggle`→checkbox, `enum`→select), value bound to
     `params[control.key]`, `onChange` → `setParam(control.key, value)` → live re-plan. Zero
     per-strategy UI code.

---

## 6. Extensibility proof (the acceptance heart)

**Claim: adding a new layout = one `registerLayout(...)` call + ZERO edits to the route, store,
picker, controls panel, or camera.** Because the picker enumerates `listLayouts()` and the panel
auto-renders from `controls`, a newly registered strategy appears with a working tweak panel
automatically.

Worked example — add a **single-row** strategy in its own file
`engine/layout/strategies/singleRow.ts` and register it:

```ts
import { registerLayout } from "../registry";
import type { Control, LayoutParams, PlanInput, PlanResult } from "../types";

interface SingleRowParams extends LayoutParams { minW: number; gap: number; margin: number; }

const controls: readonly Control[] = [
  { kind: "number", key: "minW", label: "Min width", min: 120, max: 640, step: 20 },
  { kind: "number", key: "gap", label: "Gap", min: 0, max: 64, step: 4 },
  { kind: "number", key: "margin", label: "Margin", min: 0, max: 120, step: 4 },
];

registerLayout({
  id: "single-row",
  label: "Single row",
  defaults: { minW: 320, gap: 24, margin: 48 },
  controls,
  plan({ paneIds, viewport }: PlanInput, p: SingleRowParams): PlanResult {
    const n = Math.max(1, paneIds.length);
    const w = Math.max(p.minW, (viewport.width - 2 * p.margin - (n - 1) * p.gap) / n);
    const h = viewport.height - 2 * p.margin;
    const rects: Record<string, { x: number; y: number; width: number; height: number }> = {};
    paneIds.forEach((id, i) => { rects[id] = { x: p.margin + i * (w + p.gap), y: p.margin, width: w, height: h }; });
    return { rects, reason: "single-row" };
  },
});
```

**Zero other edits, literally.** The file lands in `engine/layout/strategies/` and the
`import.meta.glob("./strategies/*.ts", { eager: true })` auto-loader (§1.2) discovers it — no
import line, no array entry, no edit to the route, store, picker, or controls panel. An optional
`configs.ts` literal only adds a *named preset*; the strategy already appears in the picker via
`listLayouts()`, with its three sliders auto-rendered from `controls`, re-planning live on drag.
`registerLayout` validates the new strategy at load (§1.2), so a `control.key` typo fails loudly.
A **masonry** sketch (columns by width; place each pane in the running-shortest column;
deterministic heights from a param or `paneId` hash) fits the identical seam — proving non-grid
layouts need no new machinery. This single-file-add is what the whole spec is judged on.

---

## 7. Reuse / seam contract

- `engine/**` (including the new `engine/layout/**`) imports **zero** viewer/content code.
  `PlanInput` carries only `paneIds` + `viewport` (+ optional `currentRects`); strategies are
  content-agnostic, keyed by opaque `PaneId`, returning `WorldRect`s.
- **Boundary lint is NOT real yet (codex r1 point 6).** `biome.json:21-40` has no
  import-restriction rule, and `SessionCanvasStressRoute.tsx:15-16` already deep-imports
  `engine/perf` + `engine/planners` (bypassing the `engine` barrel). Before any boundary claim is
  trustworthy, the lab/F2 work must (a) **add** a biome `noRestrictedImports` rule — forbid
  `session-canvas/**` → deep `engine/*/*` and forbid `engine/**` → `session-canvas/**` — and
  (b) **fix** those two existing deep imports to use the `engine` barrel. The boundary is work to
  do, not an assumption.
- **Strategy ⟂ camera (rects-only).** A strategy returns rects and nothing else — no `fit`, no
  camera data (codex r1 point 2). The **lab store** owns every camera op (`framePane`, `unframe`,
  `resetView`, `fitToContent`) over the pure `frameRectViewport` reducer. "Strategies own rects,
  camera owns transform" is literally true.
- The lab's content seam reuses `LayoutCanvas`'s `renderPane(paneId)` render-prop unchanged.
- Persistence is **shape-reserved, not built**: the lab's `LayoutConfig`/`params` align with the
  parked F2 `LayoutSnapshot` config seam (`f2-layout-manager-design.md` §9 Q7) so a future
  adapter can persist `{ activeConfigId, params }` — no storage wired now.

---

## 8. Test surface (light)

- `engine/layout/strategies/gridFit.test.ts` — **pure planner table tests**: the §2.3 rows
  (N=1/2/4/5/12 exact rects), vertical-overflow → `fit.scale` (the narrow-12 row), narrow screen
  → `cols=1`, partial last row left vs center. Exact rect + fit assertions (pure → trivial).
- `engine/layout/registry.test.ts` — `registerLayout` upsert-by-id, `listLayouts` order,
  `resolveLayout` throws on unknown id (mirrors any viewer-registry test).
- `engine/reducers/framing.test.ts` — `frameRectViewport`: 80% fit + centering math; `clampScale`
  bounds respected; a known rect/bounds → known viewport.
- Lab interaction (1 light test) — `framePane` toggles and restores `priorViewport`; guarded off
  at `paneCount <= 1`. No stress/perf gate required for the experiment (it reuses the proven
  engine motion path; the existing `tests/perf/sessionCanvasStress.spec.ts` already covers engine
  60fps).

---

## 9. Resolved positions (codex review round 1) + remaining for Stuart

Resolved with codex round 1; open only for Stuart's final adjudication.

1. **`targetAspect` cap semantics. RESOLVED (keep the aspect-cap formula):** the brief's
   `cols=clamp(floor((W−2M+G)/(MIN_W+G)),1,N)` is the width **capacity** (upper bound); actual
   `cols = min(capacity, round(√(W·N/(H·targetAspect))))`, yielding N=4→2×2 and N=12→4×3 (raw
   capacity alone gives 4×1 slivers). Codex verified the table math. Stuart confirms the exact
   aspect rule.
2. **Camera fit location. RESOLVED (lab-side, rects-only):** `PlanResult.fit` and strategy-owned
   `zoomToFit` are **removed**; the lab computes fit from the committed rect bounding box (§3.3).
   **Lock-touch flag for the orchestrator/Stuart:** this relocates the locked `zoomToFit=true`
   grid-fit default to a lab-level `Fit to content` toggle (same default, same behavior, cleaner
   boundary). Confirm the relocation is acceptable.
3. **Camera ops home. RESOLVED (lab store, not the shared hook):** `useCanvasViewport` is consumed
   internally by `LayoutCanvas` (`LayoutCanvas.tsx:25`) so its return is unreachable; pure
   `frameRectViewport` lives in `engine/reducers`, framing state/actions live in the lab store.
   `/canvas` untouched.
4. **Registry location. RESOLVED: `engine/layout/**`** (reusable, content-agnostic kernel beside
   `engine/planners/`; the parked F2 path can adopt it).
5. **Route form. RESOLVED: pathname `/canvas-lab`** via `selectRootRoute` + `main.tsx` lazy.
6. **Params typing. RESOLVED: type-erasure + validation.** The registry stores
   `LayoutStrategy<LayoutParams>`; `validateStrategy` (§1.2) makes the erasure safe (codex r1
   points 1, 7). No fourth control kind needed.
7. **Framing accessibility. RESOLVED: dedicated Frame button + keyboard shortcut** (double-click
   is a convenience only), so framing is not mouse-only (codex r1 point 5; fe-spec §5.2).
8. **Right-sizing held:** no hot reload, no persistence wiring, no JSON DSL (codex r1 point 7).

---

## Appendix: file-level change map (no code written in Phase 1)

| Path | Change |
| --- | --- |
| `engine/layout/types.ts` (new) | `ParamValue`, `LayoutParams`, `Control` (number/toggle/enum), `PlanInput`, `PlanResult` (**rects-only, no `ViewportFit`**), `LayoutStrategy<P>`, `LayoutConfig`. |
| `engine/layout/registry.ts` (new) | `registerLayout` (+ `validateStrategy`), `listLayouts`, `resolveLayout` (mirror viewer registry). |
| `engine/layout/configs.ts` (new) | `BUILT_IN_CONFIGS` literals. |
| `engine/layout/strategies/gridFit.ts` (new) | `grid-fit` strategy (§2): zoom-aware `selectColumns` + `registerLayout`. |
| `engine/layout/fit.ts` (new) | Shared `fitScale(contentW, contentH, bounds)` used by the planner's column scoring AND the lab's Fit to content, so they cannot drift. |
| `engine/layout/index.ts` (new) | **`import.meta.glob("./strategies/*.ts", { eager: true })`** auto-loader; re-export types/registry/configs/fit. |
| `engine/reducers/layoutState.ts` | Add pure `frameRectViewport` (+ `FRAME_FRACTION`). **No change to `useCanvasViewport`.** |
| `engine/react/LayoutCanvas.tsx` | Add the scoped `framing` transition class hook on the world layer (CSS "fly"); no API change. |
| `session-canvas/components/PaneChrome.tsx` (new) | **Extracted** content-agnostic pane chrome (primitive props incl. `onFrame`/`onHeaderDoubleClick`); the DRY-correct home for `PaneWindow`'s JSX. |
| `session-canvas/components/PaneWindow.tsx` | Refactor into a thin adapter mapping `PaneRecord → PaneChrome` props (no duplicated JSX). |
| `route.ts` | `RootRoute` += `"canvas-lab"`; `selectRootRoute("/canvas-lab")`. |
| `main.tsx` | Lazy branch for `canvas-lab` → `CanvasLabRoute`. |
| `session-canvas/lab/CanvasLabRoute.tsx` (new) | Route shell: command bar (Add / Organize / Fit-to-content / picker) + controls panel + `LayoutCanvas`; mirrors `SessionCanvasStressRoute`. |
| `session-canvas/lab/canvasLabStore.ts` (new) | Tiny zustand store: panes, params, `fitToContent`, framing state; `organize`/`framePane`/`unframe`/`resetView` (§4.2). |
| `session-canvas/lab/viewers/{LabCardPane,LabRulerPane}.tsx` (new) | Two stub content components rendered inside `PaneChrome`. |
| `session-canvas/lab/ControlsPanel.tsx` (new) | Auto-renders `strategy.controls` → params inputs (number/toggle/enum). |
| Tests | `gridFit.test.ts` (table incl. N=0, narrow-12 fit), `registry.test.ts` (+ `validateStrategy` rejects bad control/defaults), `framing.test.ts`, one lab framing-toggle test (§8). |
| **`biome.json`** | **Add** a `noRestrictedImports` boundary rule (forbid `session-canvas/**`→deep `engine/*/*` and `engine/**`→`session-canvas/**`); it does not exist today (codex r1 point 6). |
| `session-canvas/perf/SessionCanvasStressRoute.tsx` | Fix the existing deep imports at lines 15-16 to use the `engine` barrel (prerequisite for the boundary rule). |
