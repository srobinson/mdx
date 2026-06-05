---
title: Phosphene Renderer-Agnostic Engine — Design (Claude)
type: design
tags: [phosphene, renderer, forms, three.js, svg, canvas2d, signal-form-container, design]
summary: A draw-command contract (typed primitives over caller-owned buffers) lets the same forms render through three.js today and SVG next; the Renderer becomes an imperative Frame consumer, pathShape unifies bar placement, and one FrameClock ticks both backends with the no-per-frame-allocation doctrine preserved on WebGL/Canvas2D and bounded on SVG.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Phosphene Renderer-Agnostic Engine — Design

Phase 1 design. Independent positions; not coordinated with the other pane. Builds on the shared
factual base in `phosphene-renderer-bg-forms.md` and `phosphene-renderer-bg-runtime.md`. Repo
`littleorgans/phosphene` @ `idea/svg-renderer`. Citations are file + symbol; no line numbers.
Design only — no repo source edited.

## Thesis

The existing thesis is **Signal → Form → Container**. The missing layer is **Renderer**. The whole
design turns on one decision: **forms emit a retained draw-command list of typed primitives in
canonical unit space, backed by caller-owned buffers that mutate in place.** A primitive carries
*topology and semantics* (this is a polyline; this is a bar field), which a flat vertex buffer
cannot. That semantic layer is exactly what lets one Frame drive both a WebGL backend (which wants
vertex buffers and instance matrices) and an SVG backend (which wants `<path d>` and `<rect>`).
Everything else (the Renderer interface, container unification, the loop, the migration) follows
from that contract.

Final layering:

```
Signal (signal.ts)  →  Form (pure update → Frame)  →  Container (pathShape)  →  Renderer (three | svg | canvas2d)
   frame data            typed primitives,            placement of samples       Frame consumer:
   {level,time,freq}     buffers mutated in place      along a path normal        pokes nodes in place
```

---

## 1. Canonical geometry contract

### Position: a draw-command stream of typed primitives, **not** a flat geometry buffer.

Today three forms emit three shapes: oscilloscope writes flat xyz via `oscilloscope.ts:placeAlongPath`;
waterfall freezes scalar rows in `waterfallState.ts:pushWaterfallFrame` then places the newest into
xyz; spectrum writes scalar heights via `spectrumBands.ts:sampleBars` and resolves x via
`spectrumBands.ts:barX`. A renderer cannot consume three shapes without special-casing each.

A *flat buffer* contract (every form emits a `Float32Array` of positions) was the obvious
alternative and it is wrong, for one decisive reason: **a flat vertex buffer loses topology.** WebGL
is content to be told "draw these N vertices as a line strip", but SVG must be told *what kind of
thing this is* — a `<path>` for a polyline, `<rect>`s for bars. A bare buffer forces the SVG renderer
to reverse-engineer topology from a sidecar kind tag, which is a draw command wearing a disguise. So
the contract carries the semantics explicitly. This matches every real cross-backend graphics API
(Canvas2D paths, Skia, SwiftUI `Shape`): a retained list of typed primitives, never raw vertex soup.

The "stream" is **retained, not per-frame rebuilt**: the primitive list is allocated once per
structural config (count / rows / bars) and reused; each tick the form mutates the buffers *inside*
the primitives in place. Zero per-frame allocation is preserved (Decision 5).

### TS types (`src/render/contract.ts`, new)

```ts
import type { Signal } from "../signal";

// Canonical space: x,y,z in [-1,1]. z = 0 for planar forms; waterfall uses z for recession.
export type RGB = { r: number; g: number; b: number };

// Container / per-primitive placement. Renderer composes container ∘ primitive.
export interface Transform {
  position: [number, number, number]; // unit-space translation
  rotation: [number, number, number]; // euler radians (z for line forms; x adds tilt)
  scale: number;                       // uniform, matches today's single scale knob
}

// A continuous line in unit space. Oscilloscope = 1; waterfall = one per row.
export interface PolylinePrimitive {
  readonly kind: "polyline";
  positions: Float32Array;  // flat xyz, length capacity*3, written in place
  vertexCount: number;      // active vertices this frame (<= capacity)
  color: RGB;               // mutated in place (waterfall fades per row)
  width: number;            // unit-space width hint; backend maps to lineWidth / stroke-width
  transform: Transform;     // identity for single-line forms; per-row depth/rise for waterfall
  visible: boolean;         // waterfall hides unfilled rows
}

// A field of identical unit shapes placed per-instance. Spectrum bars / beams / reflection.
export interface InstanceFieldPrimitive {
  readonly kind: "instances";
  readonly base: "box";     // unit cube; SVG maps to rect, WebGL to instanced BoxGeometry
  count: number;            // active instances this frame
  centers: Float32Array;    // xyz per instance, length capacity*3, in place
  sizes: Float32Array;      // xyz per instance (w,h,d), length capacity*3, in place
  angles: Float32Array;     // z-rotation per instance (radians); 0 on straight axis, normal-derived on ring/arc
  gradientT: Float32Array;  // [0,1] per instance, the colorLow→colorHigh tint axis
  style: InstanceStyle;     // uniforms, set on change not per frame
  transform: Transform;
}

export interface InstanceStyle {
  colorLow: RGB; colorHigh: RGB;
  baseGlow: number; baseAlpha: number;
  additive: boolean;        // beams; SVG approximates with screen blend, may degrade
}

export type DrawPrimitive = PolylinePrimitive | InstanceFieldPrimitive;

// What a Form emits each tick: a stable list, mutated in place.
export interface Frame {
  primitives: DrawPrimitive[]; // length stable between structural changes
  container: Transform;        // the form's group transform (rotation/scale/tilt)
}
```

Two primitive kinds cover all three current forms and the obvious near-future:

| Form | Primitives | Notes |
|---|---|---|
| Oscilloscope | 1 × `polyline` | identity transform; z=0 |
| Waterfall | `rows` × `polyline` | each row a polyline with its own depth/rise transform + faded color |
| Spectrum | 3 × `instances` (bars, beams, reflection) | share `gradientT`; reflection is the `scale.y = -1` group today |

A third kind (`points`, for a return to the dotted face on `main`) drops in without disturbing the
contract — the renderer adds one `switch` arm.

### The Form contract (formalizes today's convention)

The forms doc found there is **no named `Form` interface** today — only a doctrine convention. Make
it a type. It splits structural allocation (mount / structural-key change) from per-tick mutation
(zero-alloc), which formalizes the scattered `useMemo` deps in the components:

```ts
export interface FormModule<L> {
  createFrame(look: L): Frame;                       // mount / structural change only
  update(frame: Frame, signal: Signal, look: L): void; // per tick, zero alloc, in place
  structuralKeys: (keyof L)[];                        // e.g. ["count"], ["rows","count"], ["bars"]
}
```

`structuralKeys` is the single source of the rebuild dependency that is today duplicated as
`[count]` in `Waveform.tsx:Waveform`, `[rows, count]` in `Waterfall.tsx:Waterfall`, `[bars]` in
`Spectrum.tsx:Spectrum`. (Answers runtime open Q1: **command stream, not flat buffer.**)

---

## 2. Renderer interface

### Position: the Renderer is an **imperative `Frame` consumer**, wrapped by a thin per-backend React host.

R3F mounts nodes declaratively (`<Line>`, `<instancedMesh>`); an SVG backend mounts `<path>`/`<rect>`
declaratively too. But the *hot path* — the thing that must not allocate and must be unit-testable —
is imperative: take a `Frame`, poke the existing nodes. So the seam that matters is an imperative
interface; React stays only at node-mount time.

```ts
// src/render/Renderer.ts (new)
export interface Renderer {
  mount(frame: Frame): void;                 // create backing nodes for the primitive list
  draw(frame: Frame, camera: Camera): void;  // per tick: write buffers/attrs in place. Zero alloc (WebGL/Canvas), bounded (SVG)
  reconcile(frame: Frame): void;             // primitive list changed shape (count/rows/bars): rebuild nodes
  unmount(): void;
}

export interface Camera { position: [number, number, number]; target: [number, number, number]; fov: number }
```

`Camera` is per-form (form-switch), not per-frame — it already exists as `Visualizer.tsx:FORM_VIEWS`
and is applied by `Visualizer.tsx:FormView`. It is passed at mount/reconfigure, not in the hot path.

### three.js implementation (`src/render/three/ThreeRenderer.ts`, new)

Absorbs every coupling the forms doc located:

- `PolylinePrimitive` → owns one line per primitive. **`draw` writes positions in place** (Decision
  5), replacing the `lineRef.current?.geometry.setPositions(positions)` calls in `Waveform.tsx:Waveform`
  and `Waterfall.tsx:Waterfall`. Color/width map to the line material; the per-row fade
  (`Waterfall.tsx` `line.material.color.copy(baseColor).lerp(bgColor, fadeT)`) becomes
  `material.color` set from `prim.color`, computed in the form's `update`, not the renderer.
- `InstanceFieldPrimitive` → owns three `InstancedMesh` (bars, beams, reflection), sharing the
  `BoxGeometry` from `Spectrum.tsx:createBarGeometry`. **`draw` is the relocated body of
  `Spectrum.tsx`’s `useFrame`**: the module-level `Object3D` dummy, `setMatrixAt(b, dummy.matrix)`,
  `instanceMatrix.needsUpdate = true` — already zero-alloc, moved verbatim. `angles` feeds
  `dummy.rotation.z` so ring/arc-bent bars orient along the path normal (Decision 3). Materials are
  the existing `barMaterial.ts:createBarMaterial` / `setBarColors`; `InstanceStyle` maps to its
  uniforms (`uColorLow/High`, `uBaseGlow`, `uBaseAlpha`).
- Bloom stays a three-only postprocessing pass (`Visualizer.tsx` `EffectComposer`/`Bloom`); it is a
  backend capability, not part of the contract.

### SVG implementation (`src/render/svg/SvgRenderer.ts`, new)

Consumes the *same* `Frame`:

- `PolylinePrimitive` → one `<path>` (or `<polyline>`). `draw` projects each xyz through the camera
  to 2D, builds the `d`/`points` string, and `el.setAttribute("d", …)` directly on the retained DOM
  node (no React re-render). For planar forms (z=0) the projection is an affine map of unit space to
  the viewBox; for waterfall it is the same oblique projection the three camera uses.
- `InstanceFieldPrimitive` → `count` retained `<rect>` nodes (or one `<path>` of all bars for fewer
  nodes). `draw` writes `x/y/width/height` (and `transform="rotate(...)"` for ring/arc) per instance.
  The `gradientT` tint resolves through a shared `<linearGradient>` (colorLow→colorHigh) or a
  per-rect interpolated `fill`. Additive beams degrade to `mix-blend-mode: screen`; there is no SVG
  bloom (see Risks).

The key property: **`Line2.setPositions` and `InstancedMesh.setMatrixAt` move out of the three
`.tsx` components into `ThreeRenderer`, and SVG never sees three.js at all** — it sees `Frame`.

---

## 3. Container unification (pathShape for bars)

### Position: **route bars through `pathShape` too; delete `barX`; bars gain a per-instance orientation from the path normal.**

`pathShape.ts:makePathShape` already yields a point + outward normal for any `t ∈ [0,1]`
(`straightShape`, `ringShape`, `makeArcShape`). `oscilloscope.ts:placeAlongPath` uses it to lay line
samples. `spectrumBands.ts:barX` is *exactly the straight-shape special case*: `x = t*2−1`,
implicit normal `(0,1)`, height along y. Bending a spectrum into a ring is a premium radial-EQ look
and falls straight out of the existing seam, so the special case should not survive.

Mechanism: a bar at slot `b` has `t = b/(bars−1)`. Its center is `path(t).{x,y}`; its **height axis is
the normal**; its width is tangential. On `straight` this is today's axis-aligned box. On `ring`/`arc`
each bar rotates by `atan2(normal.y, normal.x) − π/2` so height points radially — captured by the
`angles` array on `InstanceFieldPrimitive`. So `barX` is replaced by a shared `placeAlongPath`-style
bar placer that writes `centers` + `angles` from the same `PathShape`.

This unifies the container across all three forms and answers **runtime open Q2 directly: yes,
waterfall and spectrum should honor `shape` and `arcSpanDeg`.** Waterfall already calls
`placeAlongPath` but pins `makePathShape("straight")` in `Waterfall.tsx:Waterfall`; unpinning it to
`look.shape` is a one-line change once the contract lands. The result: `shape`/`arcSpanDeg` (today
`controls.ts` `Container` folder, ignored by two of three forms per the runtime doc) become
genuinely universal.

Sequencing note: line-form container is free (already pathShape). Bar orientation (`angles`,
per-instance rotation) is the more involved piece and lands *after* the seam (Migration step 6), so
the engine ships value before paying for it.

---

## 4. Render-loop abstraction

### Position: one `FrameClock`; three.js adapts R3F `useFrame` to it, SVG implements it with `requestAnimationFrame`.

Today there are two loops (runtime doc §2): the manual RAF in `audio.ts:useAudioInput` that writes
`Signal`, and R3F `useFrame` that reads it and mutates geometry. SVG has no `useFrame`.

```ts
// src/render/FrameClock.ts (new)
export type Tick = (dtSeconds: number) => void;
export interface FrameClock {
  subscribe(fn: Tick): () => void; // returns unsubscribe
  start(): void; stop(): void;
}
```

Per backend the *same* tick body runs `form.update(frame, signal, look)` then `renderer.draw(frame,
camera)`:

- **three.js** `FrameClock` = a thin adapter that registers its subscribers inside a single R3F
  `useFrame`. R3F keeps owning the WebGL render + the `Bloom` pass; our geometry mutation rides its
  loop. No second RAF.
- **SVG** `FrameClock` = a plain `requestAnimationFrame` loop (there is no R3F). Same subscriber
  contract.

The audio source's RAF in `audio.ts:useAudioInput` stays independent **for now** (it is
source-paced and its lifecycle — `enable`/`disable`/`startTokenRef`/`stopTracks` — is delicate;
merging it is out of scope and raises blast radius). The clean future is one clock that does
signal-write *then* draw in a single callback, guaranteeing the draw reads the freshest frame; I
recommend that as a follow-up, not part of the seam.

---

## 5. Zero-allocation across both backends

The doctrine ("no per-frame allocation in the render loop", `phosphene/CLAUDE.md`) is a WebGL-era
rule. State it precisely per backend:

- **three.js — shed the lone allocator.** The runtime doc and `NOTES/BACKLOG.md` pin the one
  violation: drei `<Line>` → `LineGeometry.setPositions`/`LineSegmentsGeometry.setPositions` rebuilds
  interleaved segment buffers every call, in `Waveform.tsx:Waveform` and `Waterfall.tsx:Waterfall`.
  Fix inside `ThreeRenderer`: own the `LineGeometry`, write directly into its interleaved
  `instanceStart`/`instanceEnd` `InterleavedBufferAttribute` arrays in place and set
  `needsUpdate = true` — **never call `setPositions` after init**. (BACKLOG's triangle-strip ribbon
  shader is the heavier alternative; the owned-attribute write is the smaller fix and enough.) The
  `InstancedMesh` path in `Spectrum.tsx` is already zero-alloc (module `Object3D` dummy reused) —
  keep as is. Net: WebGL hits true zero per-frame allocation, closing the BACKLOG item.
  (Answers **runtime open Q4: yes, replace drei `Line` with owned buffer attributes.**)

- **SVG — bounded, not zero.** Two irreducible truths: SVG path data is a string, and JS strings are
  immutable, so each *changed* `<path>` costs one string per frame. Mitigations: (a) only rebuild
  primitives whose buffers changed — waterfall already touches only the newest row
  (`Waterfall.tsx` writes `lineRefs[state.writeHead]`), so older rows are pure attribute no-ops; (b)
  mutate via `el.setAttribute`, never React state, so there is no reconciliation garbage; (c) reuse
  one scratch number-formatting path. The honest doctrine for SVG: *no per-frame allocation beyond
  the irreducible attribute string of changed primitives.*

- **Canvas2D — the truly zero-alloc 2D backend.** A Canvas2D renderer builds paths with
  `moveTo`/`lineTo` and never materializes a string. If 2D performance ever bites, Canvas2D is the
  zero-GC 2D path; SVG earns its keep through DOM-inspectability and clean static/vector export
  (`?embed` panels, share images). The contract serves all three identically.

---

## 6. Migration path (smallest-first, each step shippable + `vp check`/`test`/`build` green)

| Step | Change | Visual delta | Why it is safe |
|---|---|---|---|
| 1 | **Extract pure form-update modules.** Move the `sampleDisplacements → smoothDisplacements → placeAlongPath` pipeline out of `Waveform.tsx:Waveform` into `updateOscilloscope`; wrap the `Waterfall.tsx`/`Spectrum.tsx` `useFrame` bodies into pure `updateWaterfall`/`updateSpectrum`. | none | pure refactor; now unit-testable without R3F |
| 2 | **Land `contract.ts`** (`Frame`, `DrawPrimitive`, `Transform`, `FormModule`). Form updates write into a `Frame` instead of loose buffers; components read positions/instances from the `Frame`. Still three.js. | none | additive types; same buffers underneath |
| 3 | **Extract `ThreeRenderer`.** Move `setPositions` and `setMatrixAt` out of the three components into `render/three/ThreeRenderer.ts` consuming `Frame`. Components shrink to: own `Frame` (memo on `structuralKeys`), run `form.update` in `useFrame`, hand `Frame` to `ThreeRenderer`. | none | **the seam now exists**; behavior identical |
| 4 | **Shed the Line2 allocator** in `ThreeRenderer` (owned interleaved attribute, in-place write). | none | perf only; closes BACKLOG + runtime Q4 |
| 5 | **First SVG spike.** `render/svg/SvgRenderer.ts` + `SvgHost` React component (plain `<svg>`, RAF `FrameClock`) consuming the **same `Frame` for oscilloscope only** (z=0, one polyline → one `<path>`). Add `?renderer=svg` switch in `Visualizer.tsx:Visualizer`. | new backend, same scope | proves one `Frame` drives two backends |
| 6 | **Container unification + SVG breadth.** Route spectrum bars through `pathShape` (`angles`, delete `barX`), unpin waterfall `shape`; extend SVG to bars + waterfall projection. | bars/waterfall gain ring/arc | done last; most involved, least urgent |

**What lands first:** steps 1–3 — the pure-refactor extraction that *creates the seam* with zero
visual change and a fully green tree. **The first SVG spike** is step 5: the oscilloscope rendered
through `SvgRenderer` behind `?renderer=svg`, a single `<path>`, proving the contract is real on a
second backend. Smallest possible proof, exactly mirroring how the branch's first three.js spike
proved Signal→Form→Container.

### Component-by-component migration map (file + symbol)

| Today (file:symbol) | Becomes | Coupling removed |
|---|---|---|
| `Waveform.tsx:Waveform` (useFrame: sample/smooth/place + `setPositions`) | `oscilloscope.ts:updateOscilloscope` (pure) writes a 1-polyline `Frame`; `ThreeRenderer.draw` uploads it | drei `Line`, `setPositions` leave the component |
| `Waterfall.tsx:Waterfall` (per-row `setPositions` + depth/rise + color lerp) | `waterfallState.ts:updateWaterfall` writes N-polyline `Frame` (per-row `transform` + `color`); `ThreeRenderer.draw` uploads | drei `Line`, `Color` lerp, `setPositions` leave; `makePathShape("straight")` → `look.shape` |
| `Spectrum.tsx:Spectrum` (instanced `setMatrixAt` ×3, `barX`) | `spectrumBands.ts:updateSpectrum` writes 3-instance `Frame` via shared path placer (`angles`); `ThreeRenderer.draw` does `setMatrixAt` | `InstancedMesh`/`Object3D`/`barX` leave the component; `barMaterial.ts` becomes a `ThreeRenderer` detail |
| `Spectrum.tsx:createBarGeometry`, `barMaterial.ts:createBarMaterial`/`setBarColors` | move under `render/three/` | three-only styling localized to the three backend |
| `Visualizer.tsx:FormScene` (switch by `look.form`) | switch selects `FormModule`; `Visualizer.tsx:Visualizer` selects backend host (`ThreeHost`/`SvgHost`) by `?renderer` | backend choice becomes a single swap point |
| `Visualizer.tsx:FORM_VIEWS`/`FormView` | feed the `Renderer` `Camera` at mount/reconfigure | camera leaves the per-frame path |
| `pathShape.ts` (unchanged) | shared by line **and** bar placement | the portability seam now serves all forms |
| `audio.ts:useAudioInput` (RAF) | unchanged in the seam; candidate to merge into `FrameClock` later | lifecycle untouched (blast-radius control) |

---

## Risks

1. **Waterfall is intrinsically 3D.** Stacked rows recede in z with occlusion (`Waterfall.tsx` sets
   `group.position.z/.y`, opaque rows for the Unknown-Pleasures read). SVG/Canvas2D are 2D: faithful
   waterfall needs an oblique projection + painter's-order sort in the renderer. The contract carries
   z so this is *possible*, but SVG waterfall is a stretch goal. **Parity goal is "same geometry,
   backend-native styling", not pixel parity.**
2. **No SVG bloom.** Glow is a three `EffectComposer`/`Bloom` pass; SVG has no equivalent (CSS
   `filter: blur` + `screen` blend approximates). The premium glow look will differ across backends —
   acceptable if framed as backend capability, not contract.
3. **Per-instance bar rotation** (`angles` for ring/arc) adds real complexity to both the bar placer
   and `ThreeRenderer`/`SvgRenderer`. Deferred to step 6 specifically to keep the seam cheap.
4. **Owned-attribute Line2 fix must survive resize.** Count change reallocates the `LineGeometry`;
   the in-place write path must only run after a `reconcile`. Guard on `structuralKeys`.
5. **SVG must not re-render through React.** All per-frame mutation is `el.setAttribute` via retained
   refs; a stray state update per frame would reintroduce GC and defeat the doctrine.
6. **Clock unification touches audio lifecycle.** Keep `audio.ts:useAudioInput`’s RAF independent in
   the seam; merging into `FrameClock` is a follow-up with its own verification.
7. **Dead dependency.** `three-mesh-bvh` is declared but unimported in `src` (both docs). Not my
   design surface, but recommend dropping it unless a future picking/raycast form needs it
   (answers **runtime open Q3: drop it**).

## First spike I would build

**Oscilloscope through `SvgRenderer`, behind `?renderer=svg`.** Land steps 1–3 first (the seam, no
visual change, green), then step 5: one `FormModule` (oscilloscope) emitting a one-`polyline` `Frame`,
consumed by both `ThreeRenderer` (unchanged look) and a new `SvgHost`/`SvgRenderer` drawing a single
`<path>` updated via `setAttribute` on a RAF `FrameClock`. Toggle `?renderer=three|svg` in
`Visualizer.tsx:Visualizer`. Success = the same oscilloscope, the same Leva `shape`/`amplitude`/
`smoothing` controls, identical motion, two backends, zero change to `oscilloscope.ts` or
`pathShape.ts`. That single `<path>` is the proof the renderer seam is real.

---

### One-line thesis
A retained draw-command contract (typed primitives over caller-owned buffers) is the missing
Renderer seam: it carries the topology that both three.js instancing and SVG `<path>` need, lets
`pathShape` unify every form's container, and preserves zero per-frame allocation on WebGL/Canvas2D
while bounding it on SVG — shippable in three pure-refactor steps before the first one-`<path>` SVG
spike.
