---
title: Phosphene Renderer Design Codex
type: research
tags: [phosphene, renderer, design, svg, three]
summary: Design for a renderer agnostic Phosphene engine using retained draw commands, a unified loop, path based containers for every form, and backend owned zero alloc resources.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive summary

I choose a retained draw command contract, produced after the Container stage and consumed by renderer backends. Forms keep their current pure signal math, containers write stable command buffers, and renderers own backend resources such as Three geometries, instanced meshes, SVG point lists, and SVG polygons.

The seam is `Signal -> FormState -> ContainerGeometry -> Renderer`. This keeps SVG from learning waveform math, keeps Three from owning form state, and fixes the current allocation leak by replacing Drei `Line2.setPositions` with owned line resources.

## Project metadata

| Field | Design stance | Evidence |
| --- | --- | --- |
| Current app | React 19, TypeScript 6, Vite Plus | `package.json:dependencies`, `package.json:devDependencies`, `package.json:scripts` |
| Signal source | Keep as renderer neutral | `src/signal.ts:Signal`, `src/audio.ts:useAudioInput` |
| Current render host | R3F Canvas with per form `useFrame` | `src/Visualizer.tsx:Visualizer`, `src/Waveform.tsx:Waveform`, `src/Waterfall.tsx:Waterfall`, `src/Spectrum.tsx:Spectrum` |
| Current allocation risk | Drei line geometry upload | `src/Waveform.tsx:Waveform`, `src/Waterfall.tsx:Waterfall`, `node_modules/three/examples/jsm/lines/LineGeometry.js:LineGeometry.setPositions`, `node_modules/three/examples/jsm/lines/LineSegmentsGeometry.js:LineSegmentsGeometry.setPositions` |
| Structural lookup | fmm unavailable in this checkout | `mcp__fmm.fmm_list_files` |

## 1. Canonical geometry contract

### Position

Use a higher level draw command stream with typed array payloads. Flat triangle buffers are too low level for SVG, while raw form scalars are too incomplete for Three. A retained command stream gives both renderers semantic primitives without allocating command objects per frame.

The command stream is the output of Container, not raw Form math. Current pure helpers stay valuable: `src/oscilloscope.ts:sampleDisplacements`, `src/waterfallState.ts:pushWaterfallFrame`, and `src/spectrumBands.ts:sampleBars` still write scalar form state. Container projection then writes polylines or oriented bars in unit space.

### TypeScript contract

```ts
export type RendererKind = "three" | "svg" | "canvas2d" | "static";

export type CommandKind = "polyline" | "barStrip";

export type EngineTick = {
  nowMs: number;
  deltaMs: number;
  frame: number;
};

export type ContainerTransform = {
  scale: number;
  rotationRad: number;
  tiltRad: number;
};

export type DirtyRange = {
  start: number;
  count: number;
};

export type GeometryScene = {
  commands: readonly GeometryCommand[];
  transform: ContainerTransform;
  background: string;
  bloom: BloomLook;
  revision: number;
};

export type GeometryCommand = PolylineCommand | BarStripCommand;

export type GeometryCommandBase = {
  id: string;
  kind: CommandKind;
  visible: boolean;
  opacity: number;
  zIndex: number;
  dirty: DirtyRange;
  topologyVersion: number;
};

export type PolylineCommand = GeometryCommandBase & {
  kind: "polyline";
  count: number;
  points: Float32Array; // xyz, length >= count * 3
  stroke: StrokeLook;
  closed: boolean;
};

export type BarStripCommand = GeometryCommandBase & {
  kind: "barStrip";
  count: number;
  bars: Float32Array; // x y z tx ty nx ny halfWidth height value, length >= count * 10
  depth: number;
  fill: BarLook;
};

export type StrokeLook = {
  color: string;
  width: number;
};

export type BarLook = {
  colorLow: string;
  colorHigh: string;
  baseGlow: number;
  beamStrength: number;
  reflection: number;
};

export type BloomLook = {
  intensity: number;
  threshold: number;
  radius: number;
};
```

### Why this contract wins

- Oscilloscope emits one `PolylineCommand` after `sampleDisplacements`, `smoothDisplacements`, and container placement. Evidence: `src/Waveform.tsx:Waveform`, `src/oscilloscope.ts:placeAlongPath`.
- Waterfall emits a stable set of `PolylineCommand`s, one per row slot, backed by `src/waterfallState.ts:WaterfallState`. Only the newly written row is dirty. Evidence: `src/Waterfall.tsx:Waterfall`, `src/waterfallState.ts:rowAge`.
- Spectrum emits one `BarStripCommand`, plus optional renderer local beam and reflection resources derived from the same bars. Evidence: `src/Spectrum.tsx:Spectrum`, `src/spectrumBands.ts:sampleBars`.
- SVG can consume polylines and bars directly. Three can compile them into GPU buffers and instances. Neither backend needs signal or form internals.

## 2. Container unification

### Position

All forms should flow through the path abstraction. Spectrum bars should no longer stay axis placed. `shape`, `arcSpanDeg`, `rotationDeg`, and `scale` are Container controls in `src/defaults.ts:WaveformLook` and `src/controls.ts:useWaveformControls`; users should not need to learn that only one form obeys them.

### Required path change

`src/pathShape.ts:PathShape` currently gives base point plus normal through `src/pathShape.ts:PathSample`. Bars also need tangent, so replace or extend that sample:

```ts
export type PathFrame = {
  x: number;
  y: number;
  nx: number;
  ny: number;
  tx: number;
  ty: number;
};

export type ContainerPath = (t: number, out: PathFrame) => void;
```

Straight uses tangent `(1, 0)` and normal `(0, 1)`. Ring and arc use tangent along the curve and normal radial from the center. `src/oscilloscope.ts:placeAlongPath` becomes a generic polyline writer that only needs base point and normal. A new bar writer uses base point, tangent, and normal.

### Result per form

| Form | Container result | Current evidence |
| --- | --- | --- |
| Oscilloscope | One path shaped polyline | `src/Waveform.tsx:Waveform`, `src/pathShape.ts:makePathShape` |
| Waterfall | Multiple path shaped polylines with row depth, rise, and fade | `src/Waterfall.tsx:Waterfall`, `src/waterfallState.ts:pushWaterfallFrame` |
| Spectrum | Oriented bars placed at `t` along the selected path; height grows along normal and width spans tangent | `src/Spectrum.tsx:Spectrum`, `src/spectrumBands.ts:barX` |

`src/spectrumBands.ts:barX` should retire after the bar writer lands. Its concept becomes `t = slot / (bars - 1)` plus `ContainerPath(t, frame)`.

## 3. Renderer interface

### TypeScript interface

```ts
export type Viewport = {
  width: number;
  height: number;
  dpr: number;
};

export type RendererHost = HTMLElement | SVGSVGElement | HTMLCanvasElement;

export interface PhospheneRenderer<THost extends RendererHost = RendererHost> {
  readonly kind: RendererKind;
  mount(host: THost, scene: GeometryScene): void;
  resize(viewport: Viewport): void;
  reconcile(scene: GeometryScene): void;
  render(scene: GeometryScene, tick: EngineTick): void;
  dispose(): void;
}

export interface RendererResource<TCommand extends GeometryCommand> {
  readonly id: string;
  readonly kind: TCommand["kind"];
  sync(command: TCommand): void;
  dispose(): void;
}
```

`reconcile` is allowed to allocate because it handles topology changes such as count, rows, bars, form changes, or renderer switches. `render` is not allowed to allocate. Per frame mutation stays inside `RendererResource.sync`.

### Three implementation

- `ThreePolylineResource` replaces Drei `Line`. `src/Waveform.tsx:Waveform` and `src/Waterfall.tsx:Waterfall` stop calling `geometry.setPositions`. The resource owns `BufferGeometry`, typed arrays, and a ribbon material. Per frame it copies `PolylineCommand.points` into owned attributes, marks `updateRange`, and flips `needsUpdate`.
- `Line2.setPositions` should be removed rather than moved. That API is the allocator.
- `ThreeBarStripResource` owns the current instanced mesh path. `src/Spectrum.tsx:Spectrum` stops calling `InstancedMesh.setMatrixAt`; the renderer resource does it from `BarStripCommand.bars`. Direct writes into `instanceMatrix.array` are also valid if profiling shows `setMatrixAt` overhead.
- `src/barMaterial.ts:createBarMaterial` and `src/barMaterial.ts:setBarColors` move under the Three renderer package. They are backend material code.
- `src/Visualizer.tsx:Visualizer` keeps the Canvas host initially, but `FormScene` should be replaced by a renderer mount component.

### SVG implementation

- `SvgPolylineResource` owns one `<polyline>` per command. It creates the point list at reconcile time and mutates `points.getItem(i).x` and `points.getItem(i).y` during `render`.
- `SvgBarStripResource` owns one `<polygon>` per bar. It creates four points per polygon at reconcile time and mutates those points from `x y tx ty nx ny halfWidth height`.
- Runtime SVG should prefer point lists over path `d` strings. Building a `d` string every frame allocates. A path `d` fallback is acceptable only for static export or browsers where mutable point lists are not viable.
- Style attributes and filters update only when `WaveformLook` changes. Per frame data updates touch dirty points and bars only.

## 4. Render loop abstraction

### Position

Introduce one engine loop. The audio source, form writers, container projection, and renderer flush tick in that order.

```ts
export interface SignalSource {
  readonly signal: Signal;
  start(): Promise<void> | void;
  stop(): void;
  tick(tick: EngineTick): void;
}

export interface FormRuntime {
  readonly scene: GeometryScene;
  configure(look: WaveformLook): void;
  tick(signal: Signal, tick: EngineTick): void;
  dispose(): void;
}

export interface PhospheneLoop {
  start(): void;
  stop(): void;
  setPaused(paused: boolean): void;
}
```

The loop body is:

```ts
source.tick(tick);
form.tick(source.signal, tick);
renderer.reconcile(form.scene);
renderer.render(form.scene, tick);
```

This folds the current manual audio RAF from `src/audio.ts:useAudioInput` and the R3F `useFrame` calls from `src/Waveform.tsx:Waveform`, `src/Waterfall.tsx:Waterfall`, `src/Spectrum.tsx:Spectrum`, and `src/Starfield.tsx:Starfield` into one owner.

### Migration detail

The first migration can use an R3F backed loop adapter so visuals stay stable. The final Three backend should run R3F with a demand or never frameloop and let `PhospheneLoop` drive render. SVG has no R3F dependency and uses the same loop directly.

`src/audio.ts:useAudioInput` should split into two parts:

1. audio lifecycle, including `getUserMedia`, `AudioContext`, debug mode, and cleanup;
2. `SignalSource.tick`, which writes `src/signal.ts:Signal` with `src/audio.ts:updateSignal` or `src/signal.ts:writeDebugSignal`.

## 5. Zero alloc doctrine

### Rules

- Topology changes may allocate. Per frame render may not.
- Form state owns scalar buffers. Container geometry owns command buffers. Renderer resources own backend buffers.
- No renderer may convert stable typed arrays into fresh typed arrays during `render`.
- SVG runtime may not build `path d`, `points`, or `transform` strings each frame.

### Current honored paths

- `src/signal.ts:createSignal`, `src/signal.ts:resetSignal`, and `src/signal.ts:writeDebugSignal` mutate stable signal arrays.
- `src/audio.ts:updateSignal` copies analyser data into stable `Signal` arrays.
- `src/oscilloscope.ts:sampleDisplacements`, `src/oscilloscope.ts:smoothDisplacements`, and `src/oscilloscope.ts:placeAlongPath` write caller owned buffers.
- `src/waterfallState.ts:createWaterfallState` and `src/waterfallState.ts:pushWaterfallFrame` keep a ring buffer.
- `src/Spectrum.tsx:Spectrum` already uses memoized buffers and a shared `Object3D` for instance matrices.

### Required fixes

- Replace `src/Waveform.tsx:Waveform` Drei line with `ThreePolylineResource`.
- Replace `src/Waterfall.tsx:Waterfall` Drei rows with the same resource, one resource per row slot.
- Keep `src/Spectrum.tsx:Spectrum` instancing semantics but move them into `ThreeBarStripResource`.
- Add tests around command writers that assert stable buffer identity across ticks.
- Add a development allocation guard that fails when command arrays or renderer resources are recreated during steady state ticks.

## 6. Component migration map

| Current file and symbol | Future owner | Change |
| --- | --- | --- |
| `src/signal.ts:Signal` | `engine/signal` | Keep shape `{ level, time, freq }` as source neutral input. |
| `src/audio.ts:useAudioInput` | `engine/sources/audio` plus React hook wrapper | Keep mic and `?audio` lifecycle, move RAF tick into `SignalSource.tick`. |
| `src/defaults.ts:WaveformLook` | `engine/look` | Keep as neutral look contract. Add renderer selection only outside form math. |
| `src/controls.ts:useWaveformControls` | app shell | Keep Leva as renderer neutral controls. Optional `renderer` control can choose Three or SVG. |
| `src/pathShape.ts:PathShape` | `engine/container/path` | Extend sample to tangent through `PathFrame`. |
| `src/oscilloscope.ts:sampleDisplacements` | `forms/oscilloscope` | Keep signal sampling. Add command writer for one `PolylineCommand`. |
| `src/oscilloscope.ts:placeAlongPath` | `engine/container/geometry` | Generalize to `writePolylineAlongPath`. |
| `src/waterfallState.ts:WaterfallState` | `forms/waterfall` | Keep row state. Add command writer for row polylines. |
| `src/spectrumBands.ts:sampleBars` | `forms/spectrum` | Keep frequency aggregation. Add command writer for `BarStripCommand`. |
| `src/spectrumBands.ts:barX` | removed | Replace with path parameter placement. |
| `src/Waveform.tsx:Waveform` | Three renderer adapter | First consume `PolylineCommand`; later collapse into generic renderer host. |
| `src/Waterfall.tsx:Waterfall` | Three renderer adapter | First consume row commands; later collapse into generic renderer host. |
| `src/Spectrum.tsx:Spectrum` | Three renderer adapter | Move instancing and materials into `ThreeBarStripResource`. |
| `src/barMaterial.ts:createBarMaterial` | `renderers/three/materials` | Keep Three only shader code out of engine. |
| `src/Visualizer.tsx:Visualizer` | app host plus renderer switch | Own host selection, camera defaults, interaction policy, bloom controls. |
| `src/EmbedGallery.tsx:EmbedGallery` | app shell | Keep shared source and per panel looks. Renderer backend should be a panel level option if needed. |

## 7. Shippable migration sequence

1. Add `src/engine/geometry.ts` with the command types and pure tests. No runtime behavior change. Verify with `vp check`, `vp test`, and `vp build`.
2. Add `PathFrame` in `src/pathShape.ts:PathShape` and command writer helpers in a neutral container module. Preserve current `placeAlongPath` behavior through a compatibility wrapper. Verify straight, ring, and arc numeric output.
3. Convert `src/Waveform.tsx:Waveform` to write and render one `PolylineCommand` while still using the current visual host. This proves the contract with one form.
4. Replace the Waveform Drei line with `ThreePolylineResource`. This is the first visible zero alloc payoff.
5. Convert `src/Waterfall.tsx:Waterfall` to row `PolylineCommand`s, then replace its Drei lines with `ThreePolylineResource` rows.
6. Convert `src/Spectrum.tsx:Spectrum` to `BarStripCommand` and move `setMatrixAt` into `ThreeBarStripResource`.
7. Add `PhospheneLoop` and split `src/audio.ts:useAudioInput` into lifecycle plus `SignalSource.tick`. Bridge R3F through the loop, then switch Three to demand driven rendering.
8. Add `SvgRenderer` for oscilloscope only. Gate with `?renderer=svg&form=oscilloscope` or a hidden control. Use `?audio=<level>` for deterministic proof.
9. Extend SVG to waterfall rows, then spectrum bars. Add point list and polygon mutation tests where the DOM environment supports them.
10. Remove unused backend dependencies. `three-mesh-bvh` should leave `package.json:dependencies` unless a near term renderer feature imports it.

## 8. First SVG spike

Build the oscilloscope SVG spike first.

Scope:

- Reuse `src/signal.ts:Signal`, `src/audio.ts:useAudioInput` debug mode, `src/oscilloscope.ts:sampleDisplacements`, `src/oscilloscope.ts:smoothDisplacements`, and `src/pathShape.ts:makePathShape`.
- Produce one `PolylineCommand` from the same command writer used by Three.
- Mount an `<svg>` with one `<polyline>` and one optional filter or CSS glow.
- Mutate point list entries in place. Avoid `points` string assignment during runtime frames.
- Verify with `?renderer=svg&form=oscilloscope&audio=0.7`, then run `vp check`, `vp test`, and `vp build`.

Success criteria:

- Oscilloscope shape, rotation, scale, count, amplitude, gain, smoothing, color, and line width match the Three command input.
- Buffer identities stay stable across ticks.
- No Drei, R3F, Three, or postprocessing imports appear in the SVG renderer path.

## 9. Dependency stance

Renderer specific dependencies should be contained behind backend modules:

- Three backend: `three`, `@react-three/fiber`, `@react-three/drei` only during migration, `@react-three/postprocessing`, and `postprocessing`.
- SVG backend: browser DOM and React host only.
- Neutral shell: `react`, `react-dom`, `leva`.
- Candidate removal: `three-mesh-bvh`, because current `src` imports none of it.

Longer term, Drei should not be required for the core Three renderer. `OrbitControls` and `Grid` can stay in a demo shell, but line rendering should be owned by the backend.

## 10. Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| SVG mutable point list support varies by browser | Start with Chrome target, feature detect, and keep string fallback for static export only. |
| Three ribbon line quality can regress versus Drei Line2 | Ship Waveform first, use visual snapshots, then reuse the same resource for Waterfall. |
| SVG cannot match bloom exactly | Treat bloom as a renderer effect contract. SVG approximates through filters and opacity. |
| Ring and arc spectrum bars can become visually dense | Use `barWidth`, `bars`, and path tangent spacing. Add look presets for curved spectrum. |
| One loop may fight R3F defaults | Introduce the loop behind an adapter first, then switch `Canvas` frameloop after parity proof. |
| Command stream can become too generic | Keep only two primitive kinds until a fourth form proves another need. |

## 11. Decisions against runtime open questions

1. **Canonical output:** retained draw commands with typed array payloads.
2. **Waterfall and Spectrum container behavior:** both should honor `shape` and `arcSpanDeg`.
3. **Unused dependency:** remove `three-mesh-bvh` unless a concrete backend feature imports it.
4. **Drei line allocator:** replace it with owned Three buffer attributes and a backend line resource.
