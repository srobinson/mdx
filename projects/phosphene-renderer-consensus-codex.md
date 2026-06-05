# Phosphene renderer consensus: Codex adversarial pass

Verdict: conditional signoff. The synthesis is directionally sound, but the first contract slice should be tightened before engineering starts.

## Findings

1. **Blocker: container unification does not preserve today's straight spectrum as written.**
   - **Design claim:** `phosphene-renderer-design-SYNTHESIS.md:72-74` says bars use `center = path(t)`, height along the normal, width along the tangent, and `angle = atan2(ny,nx) - π/2`.
   - **Evidence:** current bars are base anchored: `src/Spectrum.tsx:89-97` sets `dummy.position` to `(x, height / 2, 0)` and `dummy.scale` to `(width, height, width)`, so each box rises from y = 0. Current straight placement is `src/spectrumBands.ts:52-59` via `barX`. The straight path returns y = 0 and normal `(0, 1)` in `src/pathShape.ts:31-36`. If `center = path(t)`, straight bars straddle the baseline instead of preserving the existing output. Ring also needs an explicit seam rule: `src/pathShape.ts:38-46` maps `t = 0` and `t = 1` to the same point, and `tests/waveform.test.ts:20-29` verifies that closure, so `slot/(bars - 1)` duplicates the first and last radial bar.
   - **Required change:** define bar placement with an anchor, probably `base` for spectrum, and compute center as `path(t) + normal * height / 2`; define closed path slotting separately, for example `slot / bars` on rings.

2. **Major: one lean `bars` primitive is underspecified for current Spectrum parity.**
   - **Design claim:** `phosphene-renderer-design-SYNTHESIS.md:50-59` chooses two primitives and describes bar payload as `centers`, `sizes`, `angles`, and `gradientT` arrays.
   - **Evidence:** current Spectrum renders a grid plus three instanced bar layers. It creates bar, reflection, and beam materials in `src/Spectrum.tsx:22-38`, updates their distinct uniforms in `src/Spectrum.tsx:54-60`, writes three instance matrices in `src/Spectrum.tsx:89-112`, and renders the three layers in `src/Spectrum.tsx:134-156`. Reflection is a separate negative y group at `src/Spectrum.tsx:148-156`. The shader has material variants for additive blending, transparency, alpha, and glow in `src/barMaterial.ts:36-62`.
   - **Required change:** make the contract layer capable, for example `barLayers[]` with role, transform, style/material parameters, dirty ranges, and topology version. If beams or reflection are renderer derived, state that explicitly as a backend capability with parity limits.

3. **Major: the three zero allocation line path requires replacing or bypassing Drei `<Line>`.**
   - **Design claim:** `phosphene-renderer-design-SYNTHESIS.md:27-28` and `85-88` say to own `BufferGeometry` attributes and delete `Line2.setPositions`.
   - **Evidence:** current code calls the allocator from `src/Waveform.tsx:35` and `src/Waterfall.tsx:38`. Drei creates its own geometry in `node_modules/@react-three/drei/core/Line.js:22-36`, calls `geom.setPositions(pValues.flat())` at line 28, and attaches that internal geometry at lines 55-60. `node_modules/three/examples/jsm/lines/LineGeometry.js:50-70` allocates a new `Float32Array` and delegates to `LineSegmentsGeometry`. `node_modules/three/examples/jsm/lines/LineSegmentsGeometry.js:97-121` creates a new `InstancedInterleavedBuffer`, replaces `instanceStart` and `instanceEnd`, and recomputes bounds.
   - **Required change:** specify a custom `ThreePolylineResource` or R3F primitive that seeds `Line2` once, then mutates the shared interleaved buffer directly. Mark `instanceStart.data.needsUpdate = true`, use `data.addUpdateRange(start, count)` for partial uploads, and set `DynamicDrawUsage` before first render.

4. **Minor: SVG point list mutation is viable, but only on a narrow hot path.**
   - **Design claim:** `phosphene-renderer-design-SYNTHESIS.md:66` and `89-90` choose point list mutation for SVG polylines.
   - **Evidence:** `SVGPolylineElement` extends `SVGAnimatedPoints` in `node_modules/typescript/lib/lib.dom.d.ts:33541-33545`. `points` and `animatedPoints` are readonly list references in `node_modules/typescript/lib/lib.dom.d.ts:31145-31150`, while `SVGPointList.getItem` returns mutable `DOMPoint` in `node_modules/typescript/lib/lib.dom.d.ts:33486-33515`, and `DOMPoint.x/y` are mutable at `node_modules/typescript/lib/lib.dom.d.ts:11793-11818`. Structural operations such as `appendItem` and `replaceItem` require `DOMPoint` objects in `node_modules/typescript/lib/lib.dom.d.ts:33474-33514`. Transform APIs expose mutable `baseVal` lists separately from animated values in `node_modules/typescript/lib/lib.dom.d.ts:31232-31244` and `34414-34480`.
   - **Required change:** say SVG reconciles by preallocating point and rect nodes, then per frame mutates `polyline.points.getItem(i).x/y`. Do not mutate `animatedPoints`. Do not write `points`, `d`, or `transform` strings per frame.

5. **Major: demand driven R3F is underspecified while Bloom owns a render priority subscriber.**
   - **Design claim:** `phosphene-renderer-design-SYNTHESIS.md:32` and `92-93` target one engine clock and a demand driven R3F loop.
   - **Evidence:** current audio updates run on a manual RAF in `src/audio.ts:130-145`, while geometry updates run in R3F `useFrame` in `src/Waveform.tsx:26-36`, `src/Waterfall.tsx:29-64`, `src/Spectrum.tsx:72-113`, and `src/Starfield.tsx:24-30`. `@react-three/postprocessing` renders the composer from `useFrame` with default `renderPriority = 1` in `node_modules/@react-three/postprocessing/src/EffectComposer.tsx:117-128`. R3F only renders demand frames when invalidated, `node_modules/@react-three/fiber/dist/events-b389eeca.esm.js:16085-16131`, and `invalidate` returns under `frameloop = "never"` at `16110-16114`; manual loops must call `advance`, shown at `16135-16142`.
   - **Required change:** keep `frameloop="always"` until the new loop owns the full render handoff, or specify exactly whether `PhospheneLoop` calls R3F `invalidate` for demand mode or `advance` for never mode, with composer rendering after geometry mutation.

6. **Minor: renderer resources must be scoped per Visualizer instance.**
   - **Design claim:** `phosphene-renderer-design-SYNTHESIS.md:25-26` says the renderer is an imperative scene consumer and camera is per form, not per frame.
   - **Evidence:** embed mode is selected in `src/App.tsx:8-17`. `src/EmbedGallery.tsx:17-47` creates one audio source and four `Visualizer` instances. Each `Visualizer` creates its own Canvas, Starfield, form scene, Bloom, controls, and form camera reset in `src/Visualizer.tsx:40-71`; per form camera data lives in `src/Visualizer.tsx:16-23` and is applied in `src/Visualizer.tsx:85-98`.
   - **Required change:** require `Frame`, renderer resources, camera state, and structural caches to be per `Visualizer`. The only shared object in `?embed` should remain the injected `signalRef` unless a later design explicitly scopes a shared renderer.

## One change before engineering starts

Revise the contract section before writing code: define `Frame` as `camera + polyline[] + barLayer[]`, with each primitive carrying topology version, dirty ranges, transform, visibility, and style/material role; define bar anchor and closed path seam semantics; state that the three polyline backend replaces Drei `<Line>` rather than extending it.

## Verification

- fmm was attempted first and failed because this checkout has no `.fmm.db`.
- Source and library claims above were verified against `src/`, `node_modules/@react-three/drei`, `node_modules/three/examples/jsm/lines`, `node_modules/@react-three/postprocessing`, `node_modules/@react-three/fiber`, and TypeScript `lib.dom.d.ts`.
- Repo worktree was clean before this pass. Final cleanliness was checked after writing this file.
