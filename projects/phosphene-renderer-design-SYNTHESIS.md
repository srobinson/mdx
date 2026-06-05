---
title: Phosphene Renderer-Agnostic Engine — Synthesis (consensus-hardened)
type: design
tags: [phosphene, renderer, svg, three, canvas2d, signal-form-container, design, synthesis, consensus]
summary: Two MoE design passes (Claude + Codex) converged on a retained draw-command seam; an adversarial consensus pass (both conditional sign-off, architecture verified sound) hardened the contract. This is the corrected design ready for engineering.
status: ready-for-engineering
source: orchestrator-synthesis
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Phosphene Renderer-Agnostic Engine — Synthesis (consensus-hardened)

Lineage: two independent codebase-analyst design passes (`-design-claude.md`, `-design-codex.md`)
over the shared base (`-bg-forms.md`, `-bg-runtime.md`), merged here, then an adversarial consensus
pass (`-consensus-claude.md`, `-consensus-codex.md`) that **verified the architecture against
three.js r0.184, the SVG2 spec, and R3F/drei/postprocessing internals first-hand**. Both reviewers
conditionally signed off: the seam is correct; the corrections below are locked in. Repo
`littleorgans/phosphene` @ `idea/svg-renderer`.

## Architecture (verified sound)

Add a **Renderer** layer to the existing Signal → Form → Container thesis:

```
Signal (signal.ts)  →  Form (scalar signal math)  →  Container (path projection → commands)  →  Renderer (three | svg | canvas2d | static)
  {level,time,freq}     sample/smooth, scalars        pathShape places samples → geometry          imperative scene consumer
```

The seam is a **retained draw-command stream** of typed primitives over caller-owned buffers mutated
in place. Verified convergence: `InstancedMesh` is already zero-alloc (`Spectrum.tsx` module `dummy`
+ `setMatrixAt` + `needsUpdate`); drei `Line2.setPositions` is the **sole** per-frame allocator
(`Waveform.tsx`, `Waterfall.tsx`); `three-mesh-bvh` is declared but unimported; straight-spectrum
geometry is preserved exactly by the unified bar projection (with the anchor fix below).

## Contract (hardened)

Three primitive kinds — `polyline`, `bars`, and `points` (the third is the dot-signature near-future
on `main`; added now so "no special-casing" is honest, cheap = positions + per-point size).

```ts
export type RGB = { r: number; g: number; b: number };
export interface Transform { position:[number,number,number]; rotation:[number,number,number]; scale:number }
export interface DirtyRange { start: number; count: number }   // touch only changed entries
export interface PrimitiveBase { id: string; visible: boolean; dirty: DirtyRange; topologyVersion: number }

// One continuous line. Oscilloscope = 1; waterfall = one per row.
export interface PolylinePrimitive extends PrimitiveBase {
  kind: "polyline";
  positions: Float32Array;  // flat xyz, capacity*3, written in place
  vertexCount: number;
  color: RGB; width: number; transform: Transform;
}

// A base-anchored bar FIELD that carries layer-capable embellishment.
// Today's spectrum = 3 layers (opaque bars, additive beams, y-mirrored reflection) over ONE field.
export interface BarFieldPrimitive extends PrimitiveBase {
  kind: "bars";
  count: number;
  centers: Float32Array;  // xyz of each bar's BASE on the path, capacity*3 (NOT the box center)
  heights: Float32Array;  // along-normal height, capacity
  widths:  Float32Array;  // along-tangent width, capacity
  angles:  Float32Array;  // z-rotation from the path normal, capacity (0 on straight)
  gradientT: Float32Array;// [0,1] per bar, the colorLow→colorHigh axis (per-vertex aBarT today)
  layers: BarLayer[];     // bars + beams + reflection; renderer derives matrices from field+layer
  transform: Transform;
}
export interface BarLayer { role: "bars"|"beams"|"reflection"; transform: Transform; style: BarStyle; dirty: DirtyRange }
export interface BarStyle {
  colorLow: RGB; colorHigh: RGB; baseGlow: number;
  topAlpha: number;        // beams/reflection fade their top toward 0
  additive: boolean;       // beams
  widthFraction: number;   // beams narrower than bars
}

export interface PointsPrimitive extends PrimitiveBase {  // near-future (dot face)
  kind: "points"; count: number; positions: Float32Array; sizes: Float32Array; color: RGB; transform: Transform;
}

export type DrawPrimitive = PolylinePrimitive | BarFieldPrimitive | PointsPrimitive;

export interface Frame { primitives: DrawPrimitive[]; container: Transform; camera: Camera }
export interface Camera { position:[number,number,number]; target:[number,number,number]; fov:number }

// Formalizes today's implicit Form convention; structuralKeys dedupes the scattered useMemo deps.
export interface FormModule<L> {
  createFrame(look: L): Frame;                         // mount / structural change only (may allocate)
  update(frame: Frame, signal: Signal, look: L): void; // per tick, zero alloc, in place
  structuralKeys: (keyof L)[];                          // ["count"] / ["rows","count"] / ["bars"]
}
```

**Renderer derives, never special-cases.** A `BarLayer` is data: the renderer builds each layer's
instance matrices from the shared field plus the layer's `transform` (reflection = `scale.y=-1`) and
`style` (beams = `additive`, `widthFraction`). Beams/reflection are layers of one field, not bespoke
renderer code — keeps the backend general while reaching exact parity.

## Container (hardened): one projector, two endpoint modes, base anchor

Extend the path sample with a **tangent**: `PathSample = { x, y, nx, ny, tx, ty }`. `pathShape` is the
one projector for lines and bars, but **lines and bars do not share a t-formula**:

- **Polyline (oscilloscope/waterfall):** `t = i/(count-1)` — inclusive endpoints, so first==last point
  closes the ring (verified by `tests/waveform.test.ts`).
- **Bars (spectrum):** `t = slot/bars` (or `(slot+0.5)/bars`) — **distributed/periodic**, so a closed
  ring does not collide bar 0 with bar `bars-1` at the seam.

**Base anchor (Blocker fix):** bars rise from the path, they do not straddle it. Today
`dummy.position=(x, height/2, 0)`. So the renderer computes box center as `base + normal·(height/2)`
where `base = path(t)`; `centers` carries the **base**. Height grows along the normal, width spans the
tangent, `angle = atan2(ny,nx) - π/2`. On `straight` this is exactly today's axis-aligned bar
(`path(t).x = barX`, normal `(0,1)`, angle 0). On `ring`/`arc` the bar tilts radially → radial EQ.
`barX` retires; waterfall unpins `makePathShape("straight")` → `look.shape`.

## Renderer interface (hardened)

```ts
export interface Renderer {
  mount(frame: Frame): void;
  reconcile(frame: Frame): void;   // primitive count/topology changed — MAY allocate
  draw(frame: Frame): void;        // per tick — MUST NOT allocate (WebGL/Canvas); SVG bounded
  resize(w: number, h: number): void;
  unmount(): void;
}
```

`reconcile` may allocate (count/rows/bars/form change); `draw` may not. **Per-Visualizer scoping
(required):** `Frame`, renderer resources, camera state, and structural caches are all owned per
`Visualizer` instance. In `?embed` (`EmbedGallery` mounts 4 Visualizers) the only shared object is the
injected `signalRef`.

### three backend — custom polyline resource (replaces drei `<Line>`, does not extend it)

drei `<Line>` creates its own `LineGeometry` and calls `setPositions` internally, so it must be
**dropped**. `ThreePolylineResource` seeds a `Line2`/`LineGeometry` once at `reconcile`, then on
`draw` writes the interleaved buffer directly — never `setPositions` again. Buffer sub-spec (this is
load-bearing; "write in place" alone is under-specified):

- `LineGeometry` stores **per-segment pairs**: N vertices → `2(N-1)` endpoints at stride 6;
  `instanceStart`/`instanceEnd` are two `InterleavedBufferAttribute` views over one
  `InstancedInterleavedBuffer`. **Each interior vertex is duplicated** across two adjacent segments —
  the writer maps vertex→two slots.
- Set `usage = DynamicDrawUsage` before first render; use `addUpdateRange(start, count)` for partial
  uploads (waterfall touches only the newest row); flip `needsUpdate` on the shared buffer.
- Set `frustumCulled = false` on the line (today only the InstancedMeshes set it) so a stale bounding
  sphere can't cull the moving line; this avoids a per-frame `computeBoundingSphere`.
- Plain `THREE.Line` has a 1:1 layout but cannot do premium `lineWidth>1`, so Line2 stays.

`InstanceFieldPrimitive` → keep the zero-alloc `InstancedMesh` path verbatim; `barMaterial.ts` moves
under the three backend. Bloom (`EffectComposer`) stays a three-only capability.

### svg backend — value is vector, not speed

SVG's justification is **product, not performance**: vector, exportable, DOM-inspectable,
CSS-themeable (matches the branch name and the gradient-waves seed). Point-list mutation
(`polyline.points.getItem(i).x/y`) avoids per-frame string GC, but the dominant SVG cost is
style-recalc → layout → **paint**, which point-list mutation does **not** avoid. So:

- **Spike success bar = correctness + geometric parity, NOT near-zero per-frame cost.**
- `reconcile` preallocates the `<polyline>`/`<rect>`/`<polygon>` nodes; `draw` mutates
  `points.getItem(i).x/y` in place. Never write `points`/`d`/`transform` strings per frame; never
  mutate `animatedPoints`. `rotation`/`scale` are look-static Leva values on a `<group>`, so the
  transform-string-churn caveat does not bite. (`d`-string is for static export only.)
- Smoke-test `DOMPoint` mutability on Safari (low-confidence cross-browser caveat, not a blocker).
- **Canvas2D** remains the documented *true* zero-alloc 2D path if SVG paint cost ever bites.

## Render loop (hardened): keep three on `always`

One `FrameClock` abstraction, but **drop "R3F demand-driven."** `@react-three/postprocessing` renders
the composer from `useFrame` at `renderPriority=1` and expects to drive each frame; an audio viz
animates every frame anyway, so demand-driven forces an `invalidate()` per frame for no benefit and
fights Bloom. Keep three at `frameloop="always"` with its own R3F RAF; `PhospheneLoop` is the thin
clock the **SVG** backend ticks. If the loops are ever unified, specify `invalidate` (demand) vs
`advance` (never) explicitly, with the composer rendering **after** geometry mutation. Splitting
`audio.ts:useAudioInput` (lifecycle + `SignalSource.tick`) stays deferred to bound blast radius.

## Scene furniture is backend-native

`Starfield` (1400 three `<points>`, the dot signature) and the Spectrum `<Grid>` floor are **not**
contract primitives and have no SVG path; they vanish under `?renderer=svg`. Classify them
backend-native (like Bloom). The spike compares **form-geometry parity, not scene parity** — a
reviewer toggling `?renderer=three|svg` will see the starfield pop in/out behind the oscilloscope.

## Migration (smallest-first, each shippable + `vp check`/`test`/`build` green)

1. **`contract.ts`** — `Frame`, the three `DrawPrimitive` kinds, `BarLayer`/`BarStyle`, `Transform`,
   `DirtyRange`, `FormModule`. Pure types + tests. No behavior change.
2. **Extract pure form-update modules** out of the three `useFrame` bodies (`updateOscilloscope`/
   `updateWaterfall`/`updateSpectrum`); add the `tx,ty` tangent to `PathSample` + the two endpoint
   modes behind a compat wrapper that preserves `placeAlongPath` numerics (verify straight/ring/arc).
3. **Forms write a `Frame`**, components read from it. Still three.js. **Seam exists.**
4. **Extract `ThreeRenderer`** — move `setPositions` + `setMatrixAt` out of the components; bars
   become a `BarFieldPrimitive` with the 3 `layers`, base anchor wired.
5. **Custom `ThreePolylineResource`** — drop drei `<Line>`, own the interleaved buffer per the
   sub-spec above. WebGL now true zero per-frame alloc; closes `NOTES/BACKLOG.md`.
6. **First SVG spike** — oscilloscope only, one `polyline` → one `<polyline>` mutated via
   `SVGPointList`, behind a **non-global** `?renderer=svg` scoped to the single-Visualizer app (embed
   stays three, or falls back to three per-form). Deterministic via `?audio=0.7`. Step 6 hand-rolls a
   RAF — **this RAF is the `PhospheneLoop` seed**, name it so. Success = same oscilloscope, same Leva
   `shape`/`amplitude`/`smoothing`, identical motion, zero change to `oscilloscope.ts`/`pathShape.ts`.
7. **`PhospheneLoop`** generalized from the step-6 seed; three stays `frameloop="always"`. (Audio
   lifecycle split still deferred.)
8. **Container + SVG breadth** — radial bars (anchor + `slot/bars` seam), unpin waterfall `shape`;
   SVG bars (`<polygon>`) + waterfall oblique projection. Most involved, last.

Plus: drop `three-mesh-bvh` from `package.json`.

## First spike (unanimous)

Oscilloscope through `SvgRenderer` behind a per-app `?renderer=svg`, single `<polyline>` mutated in
place on a RAF clock, parity-judged (not perf-judged), deterministic under `?audio=0.7`, zero change
to `oscilloscope.ts`/`pathShape.ts`. That node proves one `Frame` drives two backends.

## Consensus review outcome (applied)

Both panes: **conditional sign-off, architecture verified sound.** Applied: F1 base-anchor + closed-
shape seam (`slot/bars`, two endpoint modes); F2 custom polyline resource w/ interleaved-buffer
sub-spec; F3 SVG reframed to vector/parity not GC/perf; F4 layer-capable `bars` contract for the real
3-pass spectrum (THE pre-engineering fix); F5 keep `frameloop="always"`, drop demand-driven; F6
Starfield/Grid backend-native; F7 `points` kind added; F8 per-Visualizer scoping + non-global
`?renderer` toggle + step-6 RAF named as loop seed. No finding rejected the seam.

## Open product decisions (Stuart owns)

- **SVG waterfall is a stretch** (intrinsically 3D: oblique projection + painter-order sort). Parity
  goal = same geometry, backend-native styling, not pixel parity.
- **No SVG bloom / no SVG starfield-or-grid** — backend capabilities, not contract.

## Build note (S8 — tangent semantics)

`PathSample.tangent (tx,ty)` is a **fixed-rotation frame** (normal rotated -90°, so n×t z=-1 for
straight/ring/arc alike), **not** a direction of travel: it aligns with travel on straight/arc but
**opposes** the ring's CCW travel. It is currently unconsumed (bars use only the normal-derived
angle). The first consumer (ribbon end-caps, arrowheads, text-on-path) must treat it as a frame, or
ring will render mirrored vs arc. Also: arc bars use `t=slot/bars` (correct for the ring seam), so an
**open** arc is start-flush with an end-gap — cosmetic, design-driven, no action.
