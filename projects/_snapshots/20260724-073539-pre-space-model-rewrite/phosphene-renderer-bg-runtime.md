---
title: Phosphene Renderer Background Runtime Recon
type: research
tags: [phosphene, renderer, runtime, signal, react-three-fiber]
summary: Factual base for Phosphene signal production, render loops, container placement, controls, dependencies, and allocation pressure before renderer split design.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive summary

Phosphene currently has a clear Signal to Form to Container seam in data shape and math helpers, while the rendered forms remain coupled to React Three Fiber, Drei, and Three. Audio sampling is source neutral once it reaches `Signal`, form math writes into caller owned buffers, and the largest renderer split risk is that line geometry updates still allocate inside Three line helpers each frame.

## Project metadata

| Field | Value | Evidence |
| --- | --- | --- |
| Repo | `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/phosphene` | `git rev-parse --show-toplevel` |
| Branch | `idea/svg-renderer` | `git branch --show-current` |
| App | React 19, TypeScript 6, Vite Plus | `package.json:scripts`, `package.json:dependencies`, `package.json:devDependencies` |
| Build commands | `vp dev`, `tsc -b && vp build`, `vp lint .`, `vp preview` | `package.json:scripts` |
| Package manager | `pnpm@11.5.2` | `package.json:packageManager` |
| Navigation note | No `.fmm.db` was present, so fmm structural lookup failed and this recon used targeted shell inspection. | `mcp__fmm.fmm_list_files` |

## 1. Signal frame shape and production lifecycle

### Exact frame shape

`src/signal.ts:Signal` is the canonical frame consumed by all forms:

| Field | Type | Range and meaning | Producer |
| --- | --- | --- | --- |
| `level` | `number` | Overall amplitude in `[0, 1]` | `src/audio.ts:updateSignal`, `src/signal.ts:writeDebugSignal` |
| `time` | `Float32Array` | Waveform samples in `[-1, 1]` | `src/audio.ts:updateSignal`, `src/signal.ts:writeDebugSignal` |
| `freq` | `Float32Array` | Spectrum magnitudes in `[0, 1]` | `src/audio.ts:updateSignal`, `src/signal.ts:writeDebugSignal` |

`src/audio.ts:createInitialSignal` calls `src/signal.ts:createSignal` with `FFT_SIZE` and `FFT_SIZE / 2`, so the live frame is 1024 time samples plus 512 frequency bins. `src/audio.ts:AudioSignalRef` wraps the frame as `MutableRefObject<Signal>`, which lets render components read the current frame without triggering React state updates.

### Lifecycle

`src/audio.ts:useAudioInput` owns the source lifecycle and exposes `{ disable, enable, error, signalRef, status }`.

1. Startup checks `src/audio.ts:readDebugAudioLevel`. If `?audio=<number>` exists, status starts as `debug` and microphone startup is skipped.
2. `src/audio.ts:createInitialSignal` seeds the frame. Debug mode immediately calls `src/signal.ts:writeDebugSignal`; normal mode starts at silence.
3. A manual `requestAnimationFrame` loop inside `src/audio.ts:useAudioInput` ticks the signal source. On each tick, debug mode calls `writeDebugSignal(signal, debugLevel, performance.now() / 1000)`. Active microphone mode calls `src/audio.ts:updateSignal`.
4. `src/audio.ts:enable` opens `navigator.mediaDevices.getUserMedia({ audio: true })`, creates an `AudioContext`, creates an `AnalyserNode`, allocates `frequencyData` and `timeData` once, then marks the source `active`.
5. `src/audio.ts:disable` and the effect cleanup cancel active work through `startTokenRef`, stop tracks through `src/audio.ts:stopTracks`, close the context through `src/audio.ts:stopAudio`, and clear the shared frame through `src/signal.ts:resetSignal`.

The source seam is already neutral after `Signal`: forms receive only `AudioSignalRef` and never touch browser audio APIs.

## 2. Render loop and per tick form updates

There are two loops:

| Loop | Driver | Purpose | Evidence |
| --- | --- | --- | --- |
| Signal source loop | Manual `requestAnimationFrame` | Write the latest `Signal` from debug synthesis or microphone analyser data | `src/audio.ts:useAudioInput` |
| Render loop | React Three Fiber `useFrame` | Consume the latest `Signal` and mutate rendered geometry or object transforms | `src/Waveform.tsx:Waveform`, `src/Waterfall.tsx:Waterfall`, `src/Spectrum.tsx:Spectrum`, `src/Starfield.tsx:Starfield` |

Form update paths:

| Form | Per frame work | Evidence |
| --- | --- | --- |
| Oscilloscope | `src/oscilloscope.ts:sampleDisplacements` samples `signal.time`, `src/oscilloscope.ts:smoothDisplacements` eases into state, `src/oscilloscope.ts:placeAlongPath` writes flat xyz positions, then Drei `Line.geometry.setPositions` receives the positions buffer. | `src/Waveform.tsx:Waveform` |
| Waterfall | `src/waterfallState.ts:pushWaterfallFrame` samples and freezes a new row into a ring buffer, `placeAlongPath` places the newest row, the current line gets `setPositions`, and each row group updates visibility, depth, rise, and faded color by age. | `src/Waterfall.tsx:Waterfall`, `src/waterfallState.ts:pushWaterfallFrame`, `src/waterfallState.ts:rowAge` |
| Spectrum | `src/spectrumBands.ts:sampleBars` aggregates `signal.freq` into log spaced bars gated by `signal.level`, `smoothDisplacements` eases heights, then a shared `Object3D` dummy writes instance matrices for bars, reflections, and beams. | `src/Spectrum.tsx:Spectrum`, `src/spectrumBands.ts:sampleBars`, `src/spectrumBands.ts:barX` |
| Starfield | Rotates a Three `Points` object by delta. It is ambient, not signal driven. | `src/Starfield.tsx:Starfield` |

## 3. Container shape, transform, and embed placement

### Container controls

`src/defaults.ts:WaveformLook` carries container parameters beside form and style parameters: `shape`, `arcSpanDeg`, `rotationDeg`, and `scale`. `src/controls.ts:useWaveformControls` exposes these under the Leva `Container` folder.

### Path shape

`src/pathShape.ts:PathShape` maps `t in [0, 1]` into a point and outward normal. `src/pathShape.ts:makePathShape` selects:

| Shape | Contract | Evidence |
| --- | --- | --- |
| `straight` | x moves through unit space `[-1, 1]`, y is `0`, normal is up. | `src/pathShape.ts:straightShape` |
| `ring` | unit circle point and radial normal. | `src/pathShape.ts:ringShape` |
| `arc` | clamped angular span centered on the top of the unit circle. | `src/pathShape.ts:makeArcShape` |

`src/oscilloscope.ts:placeAlongPath` is the container placement primitive: it asks the path for a base point and normal, then writes xyz positions as base plus displacement along the normal.

### Current form transforms

| Form | Transform and shape behavior | Evidence |
| --- | --- | --- |
| Oscilloscope | Uses `makePathShape(look.shape, { arcSpanDeg })`; wraps the line in a group with z rotation from `rotationDeg` and uniform `scale`. | `src/Waveform.tsx:Waveform` |
| Waterfall | Uses `makePathShape("straight")`; applies x tilt from `tilt`, z rotation from `rotationDeg`, and uniform `scale`. It currently ignores `shape` and `arcSpanDeg`. | `src/Waterfall.tsx:Waterfall` |
| Spectrum | Positions bars with `barX` across unit x space; applies x tilt from `spectrumTilt`, z rotation from `rotationDeg`, and uniform `scale`. It currently ignores `shape` and `arcSpanDeg`. | `src/Spectrum.tsx:Spectrum`, `src/spectrumBands.ts:barX` |

### `?embed` placement

`src/App.tsx:isEmbedMode` switches the app to `src/EmbedGallery.tsx:EmbedGallery` when the URL has `?embed`. `EmbedGallery` creates one `src/audio.ts:useAudioInput` source, then maps `src/EmbedGallery.tsx:PANELS` into multiple `Visualizer` instances with `interactive={false}` and `look={{ ...DEFAULT_LOOK, ...panel.look }}`. Current panels are oscilloscope, spectrum, waterfall, and ring.

`src/index.css:.embed-grid` places the visualizers in a CSS grid. `src/index.css:.embed-cell.wide` spans two columns. `src/index.css:canvas` and `src/Visualizer.tsx:Visualizer` make each R3F canvas fill its parent.

## 4. Leva control surface

`src/App.tsx:FullScreenApp` wires the live control surface by calling `src/controls.ts:useWaveformControls`, rendering the `Leva` panel, passing the returned `look` into `src/Visualizer.tsx:Visualizer`, and mirroring `look.background` into the CSS variable `--phosphene-bg`.

`src/controls.ts:useWaveformControls` exposes:

| Group | Tunables |
| --- | --- |
| Top level | `form`: `oscilloscope`, `waterfall`, `spectrum` |
| `Signal` | `gain`, `amplitude`, `smoothing`, `count` |
| `Container` | `shape`, `arcSpanDeg`, `rotationDeg`, `scale` |
| `Ribbon` | `lineWidth`, `color`, `background` |
| `Glow` | `bloomIntensity`, `bloomThreshold`, `bloomRadius` |
| `Waterfall` | `rows`, `rowAmplitude`, `depthSpacing`, `yRise`, `tilt`, `fade`, `flow` |
| `Spectrum` | `bars`, `sensitivity`, `floor`, `barWidth`, `heightScale`, `spectrumTilt`, `reflection`, `colorLow`, `colorHigh`, `baseGlow`, `beamStrength`, `beamHeight` |

`src/defaults.ts:DEFAULT_LOOK` is the single default source for both Leva initial values and embedded panel overrides.

## 5. Dependency surface and renderer coupling

Declared runtime dependencies in `package.json:dependencies`:

| Dependency | Declared version | Current role | Renderer classification |
| --- | --- | --- | --- |
| `three` | `^0.184.0` | Core WebGL objects, materials, colors, textures, instancing, geometry. | Render backend specific |
| `@react-three/fiber` | `^9.6.1` | `Canvas`, `useFrame`, `useThree`, R3F host integration. | Render backend specific |
| `@react-three/drei` | `^10.7.7` | `Line`, `Grid`, `OrbitControls`. | Render backend specific |
| `@react-three/postprocessing` | `^3.0.4` | `EffectComposer`, `Bloom`. | Render backend specific |
| `postprocessing` | `^6.39.1` | Support package for postprocessing path; not imported directly from `src`. | Render backend specific support |
| `three-mesh-bvh` | `^0.9.10` | Declared but not imported from `src`. | Currently unused render support |
| `leva` | `^0.10.1` | React control UI for editing `WaveformLook`. | Renderer neutral control surface, still React specific |
| `react` | `^19.2.6` | Component and hook runtime. | App shell neutral |
| `react-dom` | `^19.2.6` | DOM root mounting. | App shell neutral |

The renderer neutral source modules today are `src/signal.ts`, `src/audio.ts` after the browser audio boundary, `src/pathShape.ts`, `src/oscilloscope.ts`, `src/waterfallState.ts`, `src/spectrumBands.ts`, and `src/defaults.ts`. Renderer specific modules are `src/Visualizer.tsx`, `src/Waveform.tsx`, `src/Waterfall.tsx`, `src/Spectrum.tsx`, `src/Starfield.tsx`, and `src/barMaterial.ts`.

## 6. No per frame allocation doctrine

### Honored in project source

| Area | Evidence |
| --- | --- |
| Signal storage is stable: `createSignal` allocates typed arrays once, `resetSignal` and `writeDebugSignal` mutate them in place. | `src/signal.ts:createSignal`, `src/signal.ts:resetSignal`, `src/signal.ts:writeDebugSignal` |
| Microphone analyser buffers are allocated once per audio start and copied into the shared `Signal` arrays each tick. | `src/audio.ts:enable`, `src/audio.ts:updateSignal` |
| Oscilloscope math writes into caller owned buffers and reuses a module level path sample scratch object. | `src/oscilloscope.ts:sampleDisplacements`, `src/oscilloscope.ts:smoothDisplacements`, `src/oscilloscope.ts:placeAlongPath` |
| Waveform component allocates positions, target, smoothed values, seed points, and path only through `useMemo` keyed by shape or count. | `src/Waveform.tsx:Waveform` |
| Waterfall component allocates ring state, row refs, positions, colors, seed points, and path through `useMemo`; `pushWaterfallFrame` writes into a preallocated ring buffer. | `src/Waterfall.tsx:Waterfall`, `src/waterfallState.ts:createWaterfallState`, `src/waterfallState.ts:pushWaterfallFrame` |
| Spectrum component allocates sample buffers, geometry, and materials through `useMemo`; per frame matrix updates reuse module level `dummy`. | `src/Spectrum.tsx:Spectrum`, `src/Spectrum.tsx:createBarGeometry` |
| Starfield positions and sprite texture are memoized; per frame work only rotates the points object. | `src/Starfield.tsx:Starfield`, `src/Starfield.tsx:makeDustTexture` |

### Violated today

| Violation | Evidence |
| --- | --- |
| Oscilloscope calls Drei line geometry `setPositions` every frame. The source passes a stable `Float32Array`, but Three line geometry converts it into segment buffers internally on every call. | `src/Waveform.tsx:Waveform`, `node_modules/three/examples/jsm/lines/LineGeometry.js:LineGeometry.setPositions`, `node_modules/three/examples/jsm/lines/LineSegmentsGeometry.js:LineSegmentsGeometry.setPositions` |
| Waterfall calls the same `setPositions` path for the newest row every frame, so it inherits the same allocation behavior. | `src/Waterfall.tsx:Waterfall`, `node_modules/three/examples/jsm/lines/LineGeometry.js:LineGeometry.setPositions`, `node_modules/three/examples/jsm/lines/LineSegmentsGeometry.js:LineSegmentsGeometry.setPositions` |

The source level doctrine is strongest in the neutral math modules and Spectrum instancing path. The active allocation risk sits at the current renderer adapter boundary, specifically the Drei line abstraction used by Waveform and Waterfall.

## Open questions for the design phase

1. Should canonical Form output be a flat geometry buffer contract shared by SVG and Three, or a higher level path and bar command stream consumed by renderer adapters?
2. Should Waterfall and Spectrum honor `shape` and `arcSpanDeg`, or should container shape be scoped to oscilloscope style line forms only?
3. Should `three-mesh-bvh` stay in dependencies when `src` does not import it?
4. Should the Three renderer replace Drei `Line` with owned buffer attributes to enforce the no per frame allocation rule?
