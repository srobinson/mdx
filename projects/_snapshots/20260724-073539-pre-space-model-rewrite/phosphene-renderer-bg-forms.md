---
title: Phosphene Renderer Background — The Form ↔ Render Boundary
type: research
tags: [phosphene, renderer, forms, three.js, svg-renderer, signal-form-container]
summary: Form modules are fully three.js-free and emit plain Float32Arrays in unit space; all three.js coupling lives in the R3F .tsx components, but there is no unified canonical-geometry contract across forms.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Phosphene Renderer Background — The Form ↔ Render Boundary

Phase 0 recon for a renderer-agnostic engine (three.js today, SVG next). Repo:
`littleorgans/phosphene` @ `idea/svg-renderer`. Read-only pass. Citations are file + symbol;
no line numbers per brief. **Note:** repo is not fmm-indexed (no `.fmm.db`); findings are from
direct source reads of `src/`.

## 1. The Form contract

**There is no single named `Form` TS interface.** The contract is a *convention* enforced by
doctrine (`phosphene/CLAUDE.md`: "New forms implement the Form contract and consume the existing
Signal"), not by a type the compiler checks. Concretely the convention is:

- **Input frame** — `Signal` (`src/signal.ts`, type `Signal`):
  `{ level: number; time: Float32Array /* [-1,1] */; freq: Float32Array /* [0,1] */ }`.
  Source-agnostic (mic today, TTS later). Helpers: `createSignal`, `resetSignal`, `writeDebugSignal`.
- **Output** — plain `Float32Array`(s) written into **caller-owned buffers**, in canonical unit
  space, with **zero per-call allocation**. The form "never knows its size, orientation, or
  placement" (`oscilloscope.ts` header).
- **Shape of the module API** differs per form (no shared signature):
  - Form 1 oscilloscope (`src/oscilloscope.ts`): `sampleDisplacements`, `smoothDisplacements`,
    `placeAlongPath` + `type DisplacementOptions`.
  - Form 2 waterfall (`src/waterfallState.ts`): `createWaterfallState`, `pushWaterfallFrame`,
    `rowAge`, `readRow` + `type WaterfallState`; reuses form-1 `sampleDisplacements` /
    `smoothDisplacements`.
  - Form 3 spectrum (`src/spectrumBands.ts`): `sampleBars`, `barX` + `type SpectrumOptions`;
    reuses form-1 `smoothDisplacements` (in the component).

The tunable surface is `WaveformLook` (`src/defaults.ts`), which deliberately separates **Signal**
params (count, amplitude, gain, smoothing) from **Container** params (shape, rotation, scale) from
**styling** (ribbon, glow). `DEFAULT_LOOK` is the single source of truth; `src/controls.ts`
(`useWaveformControls`) builds the leva panel from it.

**Implication for renderer work:** a swappable Renderer cannot consume "a Form" through one type
today, because no such type exists. Step one of the engine is to *define* the canonical-geometry
contract that all forms emit.

## 2. Per form: geometry emitted and coordinate space

| Form | Module | Emits | Coordinate space |
|---|---|---|---|
| Oscilloscope | `oscilloscope.ts` | flat xyz `Float32Array`, length `count*3`, **z always 0** (`placeAlongPath`) | unit `[-1,1]`, bent by `PathShape` |
| Waterfall | `waterfallState.ts` | **scalar** displacement rows: `disp` (`rows*count`, row-major) + live `incoming` (`count`) | unit `[-1,1]` deflection; xyz built later in component |
| Spectrum | `spectrumBands.ts` | **scalar** bar heights `Float32Array`, length `bars`, each `[0,1]` (`sampleBars`) + x helper `barX → [-1,1]` | per-bar height `[0,1]`, x `[-1,1]`; matrices built in component |

Key nuance: **only the oscilloscope module emits actual xyz positions** (via `placeAlongPath`,
which is the *container* step but lives in `oscilloscope.ts`). Waterfall and spectrum emit **scalar
magnitudes**; their positions/matrices are assembled inside the `.tsx` component. So the three forms
do not share an output shape — one emits points, two emit scalars.

## 3. The exact seam where geometry becomes three.js

The coupling lives **entirely in the R3F components (`*.tsx`)**, never in the form modules.
Confirmed: `grep` for `three` / `@react-three` imports across `oscilloscope.ts`, `pathShape.ts`,
`waterfallState.ts`, `spectrumBands.ts`, `signal.ts` returns **none**.

- **Oscilloscope → `src/Waveform.tsx`** (`Waveform`, in `useFrame`):
  `lineRef.current?.geometry.setPositions(positions)` on a drei `<Line>` (`@react-three/drei`,
  backed by `Line2`/`LineGeometry`). This is the single coupling point; styling is `color` +
  `lineWidth` props on `<Line>`, glow is the bloom pass.
- **Waterfall → `src/Waterfall.tsx`** (`Waterfall`, in `useFrame`): per-row drei `<Line>`s;
  newest row uploaded via `lineRefs[writeHead].current.geometry.setPositions(positions)` (positions
  built by the form-1 `placeAlongPath`), plus depth/rise via `group.position.z/.y` and fade via
  `line.material.color.copy(baseColor).lerp(bgColor, fadeT)` (three `Color`).
- **Spectrum → `src/Spectrum.tsx`** (`Spectrum`, in `useFrame`): three `InstancedMesh` ×3 (bars,
  beams, reflection) sharing one `BoxGeometry` (with per-bar `aBarT` `InstancedBufferAttribute`)
  and a custom `ShaderMaterial`. Seam = `mesh.setMatrixAt(b, dummy.matrix)` (three `Object3D`
  dummy) + `mesh.instanceMatrix.needsUpdate = true`. Material/shader in `src/barMaterial.ts`
  (`createBarMaterial`, `setBarColors`; GLSL vertex/fragment with `uColorLow/High`, `uBaseGlow`…).

The scene shell is `src/Visualizer.tsx` (`Visualizer` → `<Canvas>`, `FormScene` switch by
`look.form`, `FormView` per-form camera, `Starfield`, `EffectComposer`/`Bloom`).

## 4. VERDICT: renderer-agnostic or three.js-coupled?

**Split verdict, and the distinction is the whole point of the renderer pivot:**

- ✅ **The form modules are renderer-agnostic.** `oscilloscope.ts`, `waterfallState.ts`,
  `spectrumBands.ts`, and `pathShape.ts` have **zero** three.js / R3F / drei imports (verified by
  grep). They import only `./signal` and each other, and emit plain `Float32Array`s in unit space.
  A form does not build a `Line2` or touch a material.

- ❌ **But there is no renderer-agnostic *geometry contract*, and the `.tsx` layer is hard-coupled
  to three.js.** Two problems block a swappable renderer today:
  1. **No unified output type.** Oscilloscope emits xyz points; waterfall emits scalar rows;
     spectrum emits scalar heights + an x helper. A renderer would have to special-case each.
  2. **The components are the renderer.** Each `.tsx` hardcodes both the geometry upload
     (`Line2.setPositions` for lines, `InstancedMesh.setMatrixAt` for bars) *and* the styling
     (drei `<Line>` props, three `Color` lerp, custom `ShaderMaterial`). Swapping to SVG means
     replacing every `useFrame` body and every JSX primitive.

**Bottom line:** Form *math* is already clean and portable; the Form↔render *boundary* is not yet
a seam — it is fused inside three R3F components, each emitting a different array shape. The engine
work is (a) define one canonical geometry contract the forms emit (e.g. unit-space polyline(s) for
line forms, unit-space quads/heights for bar forms), and (b) lift the three.js calls out of
`Waveform/Waterfall/Spectrum` into a `Renderer` interface with three.js and SVG implementations.

## 5. Per-frame allocation hotspots and owning layer

- **Form modules: zero per-frame allocation.** Caller-owned buffers throughout; the one shared
  mutable is a module-level `scratch: PathSample` in `oscilloscope.ts`. Clean.
- **`Waveform.tsx`:** `positions`/`target`/`smoothed` are `useMemo`'d. The single hotspot is
  `Line2.setPositions(positions)` — documented in `NOTES/BACKLOG.md`: "Line2 setPositions allocates
  per frame… rebuilds the interleaved segment buffers each call" (~256 pts, one line, small today).
  **Owner: the drei `<Line>` / `Line2` render layer**, not the form. Backlog cure: in-place
  triangle-strip ribbon shader with miter joins.
- **`Waterfall.tsx`:** same `setPositions` hotspot, but only for the **newest** row each frame;
  older rows are pure transform updates. `Color.copy().lerp()` mutates memoized colors in place
  (no alloc). Owner: same `<Line>`/`Line2` layer.
- **`Spectrum.tsx`:** **already allocation-free.** Module-level `dummy` `Object3D` reused;
  `setMatrixAt` writes into the existing `instanceMatrix`; only `needsUpdate` flags flip. The
  InstancedMesh path is the model for a zero-alloc renderer.

Net: the lone documented per-frame allocator is **`Line2.setPositions`**, owned by the line-render
layer and shared by Waveform + Waterfall. An SVG renderer sidesteps it entirely (it would diff a
`points`/`d` attribute), and the InstancedMesh bar path already shows the zero-alloc target.

## 6. How `pathShape` bends the parameter axis (the portability seam)

`src/pathShape.ts` is the load-bearing flexibility seam.

- **Types:** `PathSample = { x, y, nx, ny }` (a base point + outward unit normal);
  `PathShape = (t: number, out: PathSample) => void` (writes into a caller-owned sample, no alloc);
  `PathShapeKind = "straight" | "ring" | "arc"`. Built by `makePathShape(kind, options)`.
- **Mechanism:** for each parameter `t ∈ [0,1]` the shape yields a point and an outward normal.
  `placeAlongPath` (in `oscilloscope.ts`) displaces each sample **along that normal**:
  `out = base + normal * disp[i]`, with `z = 0`. The form only ever computes scalar `disp[i]`;
  *where* that deflection lands is entirely the path's job.
- **Shapes:**
  - `straight`: `x = t*2−1, y = 0`, normal `(0,1)` → classic horizontal scope, vertical deflection.
  - `ring`: `angle = t·2π`, point `(cos,sin)` on the unit circle, normal `(cos,sin)` radial → radial waveform.
  - `arc`: angular sweep `arcSpanDeg` (default 220°, `WaveformLook.arcSpanDeg`) centered on top;
    same point=normal radial pattern over a partial circle.
- **Why it is the portability seam:** one oscilloscope renders straight / ring / arc with **zero
  change to the form** — only the path function swaps. This is the "flexibility is a property of the
  data" thesis made concrete.

**Caveats for renderer design:**
- `placeAlongPath` lives in `oscilloscope.ts` and is **reused by `Waterfall.tsx`** (form 2 lines
  follow the path too — currently pinned to `"straight"`).
- **Spectrum does NOT use `pathShape`.** It places bars with its own `barX` (a straight axis only)
  and InstancedMesh matrices. So the path-shape seam today serves the two **line** forms; the **bar**
  form is on a separate placement path. A unified engine must decide whether bars also flow through
  a path abstraction or stay axis-placed.

---

### One-line map for the next phase
Forms (`*.ts`) = pure, three-free, unit-space arrays. Boundary fused inside `Waveform/Waterfall/
Spectrum.tsx` via `Line2.setPositions` (lines) and `InstancedMesh.setMatrixAt` (bars). `pathShape`
already proves container portability for line forms. The renderer pivot needs a canonical geometry
contract + a Renderer interface lifted out of the three `.tsx` components.
