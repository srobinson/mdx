---
title: Phosphene renderer synthesis consensus
type: research
tags: [phosphene, renderer, svg, three, architecture, review]
summary: Adversarial consensus review found the renderer direction viable only after tightening bar placement, Spectrum layer, Drei Line, SVG mutation, loop, and per Visualizer scoping contracts.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

The merged Phosphene renderer design is directionally sound: keep form math renderer neutral, emit retained draw commands, and consume them from three.js and SVG backends. The contract should be revised before engineering starts because the current bar placement language would not preserve today's straight spectrum, the `bars` primitive is too lean for current Spectrum parity, and the three line path requires replacing Drei `<Line>` rather than extending it.

## Project Metadata

- **Project:** `littleorgans/phosphene`
- **Branch:** `idea/svg-renderer`
- **Stack:** Vite Plus, React 19, TypeScript 6, three.js 0.184, React Three Fiber 9, Drei 10, postprocessing
- **Package manager:** pnpm 11.5.2 through Vite Plus, see `package.json:35`
- **Validation status:** source review only; no repo edits. `git status --porcelain=v1` was empty after writing the consensus file outside the repo.
- **fmm status:** no `.fmm.db` in this checkout, so fmm structural navigation failed and analysis used targeted shell inspection.

## Architecture

Current Phosphene has three form components under one R3F `Visualizer`:

- `src/Waveform.tsx:13-36` owns oscilloscope buffers, samples `signal.time`, places a single polyline, and uploads via Drei `Line.geometry.setPositions`.
- `src/Waterfall.tsx:16-64` owns waterfall row state, updates only the newest row geometry, then mutates per row visibility, depth, rise, and color.
- `src/Spectrum.tsx:17-113` owns spectrum bar buffers and writes three instanced mesh matrix sets for solid bars, reflection, and beams.
- `src/Visualizer.tsx:40-71` creates one Canvas per visualizer, plus Starfield, form scene, Bloom, controls, and per form camera reset.
- `src/EmbedGallery.tsx:17-47` shares one audio source across four Visualizers, so renderer state and camera state must stay per Visualizer.

The proposed architecture should formalize the existing seam as:

`Signal -> Form state -> Container placement -> Frame -> Renderer`

The `Frame` should be explicit: `camera + polyline[] + barLayer[]`, with topology version, dirty ranges, transform, visibility, and style or material role per primitive.

## Key Patterns

- **Retained command stream:** The right abstraction is retained primitives over caller owned buffers, not raw form scalars and not one flat vertex buffer.
- **Bar layers, not bare bars:** Current Spectrum parity requires distinct bar, reflection, and beam layers with different materials and transforms.
- **Renderer resources own hot path mutation:** The three backend should own line buffers and instanced resources. React components should select resources and call render, not call allocator APIs per frame.
- **SVG reconcile versus render split:** SVG can preallocate nodes and point lists during reconcile, then mutate `DOMPoint` coordinates during render.
- **Per Visualizer isolation:** Multiple embedded panels can share `signalRef`, but not Frame, renderer resources, camera state, or structural caches.

## Detailed Findings

### 1. Bar placement does not preserve today's straight spectrum

The synthesis says bars use `center = path(t)`, height along the normal, width along the tangent, and `angle = atan2(ny,nx) - π/2` in `~/.mdx/projects/phosphene-renderer-design-SYNTHESIS.md:72-74`.

Current Spectrum base anchors boxes. `src/Spectrum.tsx:89-97` computes `x = barX(b, bars)`, `height`, then sets `dummy.position` to `(x, height / 2, 0)` and `dummy.scale` to `(width, height, width)`. Current straight placement is `src/spectrumBands.ts:52-59`, while `src/pathShape.ts:31-36` returns straight path y = 0 with normal `(0, 1)`. If `center = path(t)`, the straight bars straddle y = 0 instead of rising from it.

Ring slotting also needs a seam rule. `src/pathShape.ts:38-46` maps `t = 0` and `t = 1` to the same point, and `tests/waveform.test.ts:20-29` verifies closure. Using `slot/(bars - 1)` duplicates first and last bars on a closed ring.

**Action:** define a bar anchor. For current Spectrum parity, center should be `path(t) + normal * height / 2` with `anchor = base`. Closed paths need a slot rule such as `slot / bars`.

### 2. The `bars` primitive is too lean for Spectrum parity

The synthesis describes a lean bar payload with centers, sizes, angles, and gradientT in `~/.mdx/projects/phosphene-renderer-design-SYNTHESIS.md:57-59`.

Current Spectrum creates three materials at `src/Spectrum.tsx:22-38`, updates distinct uniforms at `src/Spectrum.tsx:54-60`, writes solid, reflection, and beam matrices at `src/Spectrum.tsx:89-112`, and renders those layers at `src/Spectrum.tsx:134-156`. Reflection uses a negative y group at `src/Spectrum.tsx:148-156`. Material variants are visible in `src/barMaterial.ts:36-62`: additive blending, transparency, alpha, and glow are layer specific.

**Action:** replace a single `bars` primitive with `barLayer[]` or make derived beam and reflection layers explicit renderer capabilities with stated parity limits.

### 3. Drei `<Line>` cannot provide the three zero allocation line path

Current components call Drei line geometry upload from `src/Waveform.tsx:35` and `src/Waterfall.tsx:38`.

Drei constructs internal line geometry in `node_modules/@react-three/drei/core/Line.js:22-36`, calls `geom.setPositions(pValues.flat())` at line 28, and attaches that geometry internally at lines 55-60. Three `LineGeometry.setPositions` allocates a new `Float32Array` in `node_modules/three/examples/jsm/lines/LineGeometry.js:50-70`. `LineSegmentsGeometry.setPositions` creates a new `InstancedInterleavedBuffer`, replaces `instanceStart` and `instanceEnd`, and recomputes bounds in `node_modules/three/examples/jsm/lines/LineSegmentsGeometry.js:97-121`.

**Action:** implement a custom `ThreePolylineResource` or R3F primitive. Seed `Line2` once, mutate `geometry.attributes.instanceStart.data.array`, set update ranges, set `needsUpdate`, and configure dynamic usage before first render.

### 4. SVG point list mutation is viable with constraints

`SVGPolylineElement` extends `SVGAnimatedPoints` at `node_modules/typescript/lib/lib.dom.d.ts:33541-33545`. The `points` and `animatedPoints` properties are readonly list references in `node_modules/typescript/lib/lib.dom.d.ts:31145-31150`. `SVGPointList.getItem` returns `DOMPoint` in `node_modules/typescript/lib/lib.dom.d.ts:33486-33515`, and `DOMPoint.x/y` are mutable in `node_modules/typescript/lib/lib.dom.d.ts:11793-11818`.

Structural list methods allocate because `appendItem`, `initialize`, `insertItemBefore`, and `replaceItem` take `DOMPoint` objects in `node_modules/typescript/lib/lib.dom.d.ts:33474-33514`. Transform APIs have animated list shapes in `node_modules/typescript/lib/lib.dom.d.ts:31232-31244` and `34414-34480`, so hot path transform string writes should be avoided.

**Action:** preallocate polyline points and bar nodes during reconcile. During render, mutate `polyline.points.getItem(i).x/y`. Do not write `animatedPoints`, `points`, `d`, or transform strings per frame.

### 5. Demand driven R3F needs an explicit render contract

The audio signal source currently has its own RAF in `src/audio.ts:130-145`. Geometry updates happen through R3F `useFrame` in `src/Waveform.tsx:26-36`, `src/Waterfall.tsx:29-64`, `src/Spectrum.tsx:72-113`, and `src/Starfield.tsx:24-30`. `@react-three/postprocessing` renders the composer through `useFrame` with default `renderPriority = 1` in `node_modules/@react-three/postprocessing/src/EffectComposer.tsx:117-128`.

R3F demand and manual modes require explicit handoff. The R3F loop runs subscribers and renders only when active or invalidated in `node_modules/@react-three/fiber/dist/events-b389eeca.esm.js:16085-16131`. `invalidate` returns under `frameloop = "never"` at `16110-16114`. Manual ownership uses `advance`, shown at `16135-16142`.

**Action:** keep `frameloop="always"` until `PhospheneLoop` owns the handoff, or specify whether the loop invalidates demand frames or calls `advance` in never mode. Composer rendering must remain after geometry mutation.

## Dependencies

- `@react-three/drei`: current `<Line>` abstraction; useful for ergonomics, but not for the target line hot path.
- `three/examples/jsm/lines`: supports `Line2` and `LineGeometry`, but `setPositions` is an allocator.
- `@react-three/fiber`: owns Canvas, `useFrame`, frame invalidation, and manual advance.
- `@react-three/postprocessing`: Bloom and composer render via `useFrame`; loop migration must preserve render priority.
- TypeScript DOM types: confirm SVG `DOMPoint` mutation support for `<polyline>` points.

## Relevance to Helioy

The review reinforces a Helioy pattern: define retained, instance scoped contracts before backend migration. Renderer portability works when state ownership, structural rebuild rules, dirty ranges, and backend capability gaps are explicit up front.

## Open Questions

1. Should beams and reflections be first class `barLayer[]` primitives, or renderer derived capabilities?
2. Should grid remain a three only renderer decoration, or become a separate primitive?
3. Should `PhospheneLoop` use R3F demand invalidation or manual `advance`?
4. What browser matrix should certify SVG point list mutation performance?
