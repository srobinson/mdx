---
title: Phosphene render layer scout for GlyphFieldPrimitive
type: scout
tags: [phosphene, render, glyph-field, presence, svg, three]
summary: The render layer has strong reusable resource and cache patterns, but Stage 2 should first absorb the dead PointsPrimitive stub and fix SvgRenderer kind dispatch before adding GlyphFieldPrimitive.
status: active
source: codebase-analyst
confidence: high
created: 2026-07-03
updated: 2026-07-03
---

## Executive Summary

Phosphene already has the right contract shape for a fourth primitive: forms own typed draw buffers, renderers own backend resources, and persistent form state lives in a `WeakMap<Frame, Resources>`. Stage 2 should not add a parallel point path. Replace the inert `PointsPrimitive` stub with `GlyphFieldPrimitive`, refactor SVG dispatch away from `frame.primitives[0]`, then bind presence simulation state to the existing frame resource pattern.

## Project Metadata

* Branch and baseline: `idea/presence` at `a0cc0fce763b074d728e5e605560ba4554745a3a`.
* Worktree: clean before scouting.
* fmm: `.fmm.db` present. `fmm validate` reported all 74 indexed files up to date.
* Size: 74 indexed files, 8,932 LOC. Render layer: 24 files, 2,823 LOC. SVG render: 10 files, 1,460 LOC. Three render: 9 files, 947 LOC. Shared render root: 5 files, 416 LOC.
* Stack: Vite+, React 19, Three 0.184, TypeScript 6, Vitest. Repo gate from README: `pnpm exec vp check && pnpm exec vp test && pnpm exec vp build`.
* Spec source: `docs/superpowers/specs/2026-07-02-presence-form-design.md`, sections 3 through 5 and staging item 2.

## Reuse Map

### Contract and primitive vocabulary

* `src/render/contract.ts :: PrimitiveBase`: shared `id`, `visible`, `dirty`, and `topologyVersion` fields for every primitive.
* `src/render/contract.ts :: DirtyRange`: existing primitive update vocabulary. Reuse for glyph buffer uploads and SVG point sampling.
* `src/render/contract.ts :: Frame`: the single carrier for `primitives`, `container`, and `camera`.
* `src/render/contract.ts :: FormModule`: the structural frame contract. Extend this for `dtSeconds` before presence simulation.
* `src/render/contract.ts :: PointsPrimitive`: stub only. Absorb this into `GlyphFieldPrimitive` or delete it.
* `src/render/primitive.ts :: createPolylinePrimitive`, `createBarFieldPrimitive`, `createBandFieldPrimitive`: exact factory pattern for allocating typed arrays once per structural frame.
* `src/render/primitive.ts :: requirePolyline`, `requireBarField`, `requireBandField`: exact runtime contract guard pattern. Add `requireGlyphField` beside these.
* `src/render/primitive.ts :: isPolylinePrimitive`, `isBarFieldPrimitive`, `isBandFieldPrimitive`: exact renderer type guard pattern. Add `isGlyphFieldPrimitive` beside these.
* `src/render/primitive.ts :: writeTransform`, `writeRgbFromHex`, `mixRgb`, `scaleRgb`: reuse these to avoid new color and transform helpers.
* `src/render/primitive.ts :: structuralSignature`: structural frame invalidation is keyed by look fields. Add presence structural fields there, for example particle count and glyph set key.

Searches run for absence: `fmm_search Glyph`, `fmm_search PointsPrimitive`, `rg "Glyph|glyph|Presence|presence|particle|PointsPrimitive|kind: \"points\"" src tests docs/superpowers/specs/2026-07-02-presence-form-design.md`. No `GlyphFieldPrimitive` implementation exists. `PointsPrimitive` appears only in the contract.

### Form state and simulation ownership

* `src/oscilloscope.ts :: createOscilloscopeFrame`: allocates primitive buffers and an `OscilloscopeFrameResources` object once.
* `src/oscilloscope.ts :: requireOscilloscopeResources`: canonical WeakMap guard for form private resources.
* `src/waterfallState.ts :: WaterfallState`: persistent per frame simulation state that is not part of the render contract.
* `src/waterfallState.ts :: createWaterfallFrame`: creates many primitives and stores `WaterfallFrameResources` in a frame keyed WeakMap.
* `src/waterfallState.ts :: updateWaterfallFrame`: mutates existing resources, writes one dirty row, and leaves older rows stable.
* `src/waterfallState.ts :: writeWaterfallAppearance`: sets `dirty` precisely, only the write head uploads geometry.
* `src/spectrumBands.ts :: writeSpectrumField`: simple full range dirty pattern for bar fields.
* `src/auroraBands.ts :: createAuroraFrame`: stores phase, smoothing buffers, surge state, and deterministic per band factors outside the primitive.
* `src/auroraBands.ts :: auroraBandCharacter`: deterministic seeded phase pattern worth copying for per particle seeds.
* `src/auroraBands.ts :: writeAuroraField`: full field update pattern for a generated field with typed arrays.

Per particle simulation state should live in `src/presence.ts :: PresenceFrameResources`, keyed by `WeakMap<Frame, PresenceFrameResources>`. The primitive should expose only render buffers: positions, intensity, size, glyph indices, colors, transform, and dirty range. Velocities, attractor targets, seeded phases, previous activity, energy, scratch buffers, and random seed state belong in the WeakMap resources. Renderers should never own simulation state.

### Loop and structural frame seams

* `src/render/useStructuralFrame.ts :: useStructuralFrame`: frame recreation on structural look changes. Use it for particle count and glyph set topology.
* `src/render/PhospheneLoop.ts :: tickPhospheneLoop`: the central update then draw ordering.
* `src/render/PhospheneLoop.ts :: usePhospheneLoop`: SVG RAF loop owner.
* `src/Aurora.tsx :: Aurora`, `src/Spectrum.tsx :: Spectrum`, `src/Waterfall.tsx :: Waterfall`, `src/Waveform.tsx :: Waveform`: R3F call sites that can pass `delta` into `tickPhospheneLoop`.
* `src/render/svg/SvgHost.tsx :: SvgHost`: SVG call site that needs RAF timestamp delta from `usePhospheneLoop`.

### Three renderer reuse

* `src/render/renderer.ts :: Renderer`: keep the backend lifecycle shape: `mount`, `reconcile`, `draw`, `resize`, `unmount`.
* `src/render/three/ThreeRenderer.ts :: ThreeRenderer`: owner for backend resource arrays and draw fanout.
* `src/render/three/ThreeRenderer.ts :: ThreeRendererNodes`: add `glyphFields?: readonly ThreeGlyphFieldNode[]` here.
* `src/render/three/ThreeRenderer.ts :: ThreeRenderer.reconcile`: calls polyline and band reconcilers before draw. Add glyph reconciliation here.
* `src/render/three/ThreeRenderer.ts :: ThreeRenderer.unmount`: trims resources to zero. Add glyph disposal here.
* `src/render/three/ThreeRenderer.ts :: ThreeRenderer.draw`: reconciles every frame, applies container transform, then draws resources.
* `src/render/three/ThreeBandRenderer.ts :: reconcileBandFields`: clean pattern for checking structural dimensions and attaching resources to the current parent.
* `src/render/three/ThreeBandRenderer.ts :: trimBandResources`: exact trim and dispose pattern to copy as `trimGlyphResources`.
* `src/render/three/ThreePolylineResource.ts :: ThreePolylineResource`: strongest dirty range upload pattern. Copy its `InstancedInterleavedBuffer`, cached `UpdateRange`, `clearUpdateRanges`, and `markDirtyRange` shape.
* `src/render/three/ThreePolylineResource.ts :: writePolylineSegmentRange`: exact pure function pattern for converting primitive dirty ranges into backend buffer dirty ranges.
* `src/render/three/ThreeBandResource.ts :: ThreeBandResource`: good example of a renderer owned geometry, material, attach, detach, and dispose lifecycle.
* `src/render/three/bandGeometry.ts :: writeBandPositionRange`: pure range writer for field geometry.
* `src/render/three/barMatrices.ts :: writeBarLayerMatrices`: allocation free instancing pattern via one shared `Object3D` scratch. Copy this if using `InstancedMesh`; prefer instanced buffer attributes for 12k glyphs.

### SVG renderer reuse

* `src/render/svg/SvgRenderer.ts :: SvgRenderer`: root SVG backend. Refactor dispatch before adding glyphs.
* `src/render/svg/SvgRenderer.ts :: SvgRenderer.ensureRoot`, `requireRoot`, `requireDefs`: exact root and defs ownership pattern.
* `src/render/svg/SvgRenderer.ts :: SvgRenderer.clearBands`, `clearBars`, `clearPolylines`: exact stale node cleanup pattern. Add `clearGlyphs`.
* `src/render/svg/svgPolyline.ts :: SvgPolylineNode`: node cache shape with cached style fields.
* `src/render/svg/svgPolyline.ts :: ensureSvgPolylineNodes`: node reuse and trim pattern.
* `src/render/svg/svgPolyline.ts :: drawSvgPolylineNode`: draw function that updates style, respects visibility, and uses dirty ranges when possible.
* `src/render/svg/svgPolyline.ts :: ensureSvgPolylinePointCount`: topology only DOM point allocation pattern.
* `src/render/svg/svgBands.ts :: SvgBandNode`: richer node cache with color scratch and gradient stops.
* `src/render/svg/svgBands.ts :: ensureSvgBandNodes`: defs plus node ownership pattern.
* `src/render/svg/svgBars.ts :: SvgBarNode`, `ensureSvgBarNodes`, `drawSvgBarLayer`: simpler polygon node cache pattern.
* `src/render/svg/svgDom.ts :: writeSvgColorAttribute`, `writeSvgNumberAttribute`, `writeSvgVisibilityAttribute`: exact cached attribute writers to reuse for text glyphs.
* `src/render/svg/svgProjection.ts :: writeSvgProjectedPoint`: reuse for glyph position projection.
* `src/render/svg/svgProjection.ts :: writeSvgPolylinePointRange`: range writer pattern for projection without replacing DOM nodes.
* `src/render/svg/svgTransformCache.ts :: isSameSvgTransform`, `writeSvgTransformCache`: keep container transform caching instead of adding per glyph transform strings.

## Quality Map

### 1. Dead contract: `PointsPrimitive`

Recommendation: refactor first.

`src/render/contract.ts :: PointsPrimitive` is present in `DrawPrimitive`, but there is no factory, guard, renderer resource, SVG handler, Three handler, or test coverage. Adding `GlyphFieldPrimitive` beside it would create two point field contracts. Absorb it by replacing `PointsPrimitive` with `GlyphFieldPrimitive`, or delete it if the new primitive uses a distinct name and kind.

Behavioral acceptance test: `createGlyphFieldPrimitive` allocates every declared array at the right size, `requireGlyphField` rejects a polyline with the same error style as existing guards, and no `PointsPrimitive` or `kind: "points"` reference remains after the migration.

### 2. SVG kind dispatch leaks through `frame.primitives[0]`

Recommendation: refactor first.

`src/render/svg/SvgRenderer.ts :: SvgRenderer.reconcile` and `SvgRenderer.draw` choose bar, band, or polyline mode from only the first primitive. `src/render/svg/svgPrimitive.ts :: usesPerspectivePolylines` also assumes a multi primitive frame is all polylines. This works for current forms, but a fourth primitive will make mixed or reordered frames fragile.

Refactor to an explicit SVG classification step before adding glyphs. Good shape: `classifySvgPrimitives(frame)` returns buckets for glyph fields, bands, bars, and polylines, plus a mode decision. Then `SvgRenderer` clears stale node families and draws from buckets instead of `frame.primitives[0]`.

Behavioral acceptance test: SVG renders the same glyph field whether it is first or second in `frame.primitives`, and a form switch sequence polyline to glyph to band to polyline leaves no stale SVG nodes or defs.

### 3. Presence simulation needs `dtSeconds`, the current form loop has none

Recommendation: refactor during Stage 2 before implementing `presence.ts`.

The spec requires a CPU, allocation free, dt aware particle simulation. `src/render/contract.ts :: FormModule` exposes `update(frame, signal, look)` only. `src/render/PhospheneLoop.ts :: tickPhospheneLoop` cannot pass delta. R3F call sites receive delta through `useFrame`, while `src/render/PhospheneLoop.ts :: usePhospheneLoop` can compute delta from RAF timestamps.

Add `dtSeconds` to the form update path. Existing forms can ignore it. Presence should use it for integration, damping, affect decay, onset impulse decay, and attractor return.

Behavioral acceptance test: a test form receives the exact delta supplied by `tickPhospheneLoop`; SVG RAF clamps and forwards nonzero delta; presence produces near equivalent positions for one 32 ms step and two 16 ms steps within tolerance.

### 4. Existing dirty semantics contain inert fields

Recommendation: refactor during Stage 2, before copying patterns.

`src/render/contract.ts :: PrimitiveBase.topologyVersion` is initialized in primitive factories but never read. `src/render/contract.ts :: BarLayer.dirty` is written by `src/spectrumBands.ts :: writeLayerStyle`, but renderer code does not read it. These are shape without behavior, matching the Stage 1 weakness profile.

For glyphs, every field added to the contract must have a consumer or a test proving intentional non consumption. Prefer count and glyph set identity for topology reconciliation. Do not add `glyphLayer.dirty` or similar unless a renderer reads it.

Behavioral acceptance test: a focused search gate proves no unused topology or layer dirty fields remain, or tests prove every retained field changes renderer output.

### 5. Three lifecycle is ready, but glyphs need a complete resource owner

Recommendation: implement during Stage 2.

`src/render/three/ThreeRenderer.ts :: ThreeRenderer` owns resource arrays for polylines and bands and disposes them on `unmount`. `src/render/three/ThreeBandRenderer.ts :: reconcileBandFields` and `trimBandResources` provide the exact resource ownership seam.

Add a single `src/render/three/ThreeGlyphFieldResource.ts :: ThreeGlyphFieldResource` owner with geometry, material, glyph atlas texture, instance attributes, parent pointer, `attach`, `detach`, `dispose`, `draw`, and optional `resize`. Extend `ThreeRenderer` with one `glyphResources` array and one `glyphFields` node family.

Behavioral acceptance test: changing particle count disposes the old glyph resource exactly once, `unmount` detaches and disposes all glyph resources, and drawing with `dirty.count === 0` does not mark instance attributes for upload.

### 6. Dirty range upload pattern to copy: polyline, not band

Recommendation: implement during Stage 2.

`src/render/three/ThreePolylineResource.ts :: ThreePolylineResource` precisely maps primitive dirty ranges to GPU update ranges and restores `updateRanges` without allocation. `src/render/three/ThreeBandResource.ts :: ThreeBandResource` computes a dirty range, but only sets `positionAttribute.needsUpdate`; this is fine for small aurora bands, not for 12k particles.

For glyphs, copy the polyline pattern: preallocate typed buffers, keep one `UpdateRange` per dynamic attribute, update only the dirty span, and set `needsUpdate` only for attributes touched by the dirty range.

Behavioral acceptance test: dirtying one particle updates exactly one instance span in position, intensity, size, and glyph index attributes. Dirtying zero particles leaves all update ranges empty.

### 7. SVG node caching is reusable, but glyphs need a cap and stable sampling

Recommendation: implement during Stage 2.

`src/render/svg/svgPolyline.ts :: ensureSvgPolylineNodes`, `src/render/svg/svgBands.ts :: ensureSvgBandNodes`, and `src/render/svg/svgDom.ts :: writeSvg*Attribute` provide the right DOM reuse pattern. The spec caps SVG to about 400 visible text nodes, so glyph rendering should not create one DOM node per particle.

Add `src/render/svg/svgGlyphField.ts` with `SvgGlyphNode`, `ensureSvgGlyphNodes`, `trimSvgGlyphNodes`, and `drawSvgGlyphField`. Precompute or deterministically derive sample indices from particle count and cap. Reuse nodes across frames. Do not allocate sampled arrays per frame.

Behavioral acceptance test: a 12k particle field creates no more than 400 SVG text nodes, a second draw with the same topology reuses the same node identities, and changing visibility hides existing nodes rather than removing and recreating them.

### 8. Allocation pressure risk is concentrated in presence simulation and glyph rendering

Recommendation: implement during Stage 2 with explicit allocation tests or guardrails.

Existing render code favors typed arrays, cached SVG nodes, cached colors, and shared scratch objects. The Stage 2 implementation should name one owner for every mutable thing:

* Simulation arrays: `PresenceFrameResources` in `src/presence.ts`.
* Draw arrays: `GlyphFieldPrimitive` in `src/render/contract.ts` and `src/render/primitive.ts`.
* WebGL buffers and atlas: `ThreeGlyphFieldResource`.
* SVG nodes and cached attributes: `SvgGlyphNode` in `src/render/svg/svgGlyphField.ts`.

Behavioral acceptance test: repeated presence updates with fixed topology keep the same typed array identities for positions, intensity, size, glyph indices, velocities, and scratch buffers.

## Plan

### Step 1: Replace the point stub with the glyph contract

Reuse: `PrimitiveBase`, `DirtyRange`, `createBandFieldPrimitive`, `requireBandField`, `isBandFieldPrimitive`, `writeRgbFromHex`.

Actions:

1. In `src/render/contract.ts`, replace `PointsPrimitive` with `GlyphFieldPrimitive`.
2. Use kind `"glyph-field" and arrays: `positions: Float32Array`, `intensity: Float32Array`, `sizes: Float32Array`, `glyphs: Uint8Array`, at least two reusable `RGB` colors, and `transform`.
3. In `src/render/primitive.ts`, add `createGlyphFieldPrimitive`, `requireGlyphField`, and `isGlyphFieldPrimitive` beside the existing primitive helpers.
4. Delete the point stub completely unless it has been renamed and fully implemented as the glyph contract.

Behavioral acceptance tests:

* Factory creates arrays with lengths `count * 3`, `count`, `count`, and `count`, initializes `dirty` to the full range, and initializes `visible` to true.
* Guard rejects a non glyph primitive with an owner qualified error.
* Search gate finds no remaining `PointsPrimitive` or `kind: "points"` references.

### Step 2: Add delta to the form loop

Reuse: `tickPhospheneLoop`, `usePhospheneLoop`, `FormModule`, R3F `useFrame` call sites.

Actions:

1. Change `FormModule.update` to accept `dtSeconds`.
2. Change `tickPhospheneLoop` to pass `dtSeconds` to forms.
3. Pass R3F `delta` from `Waveform`, `Waterfall`, `Spectrum`, and `Aurora`.
4. Change `usePhospheneLoop` to call its tick with clamped RAF delta, then pass that through `SvgHost`.
5. Update existing form modules to accept and ignore `dtSeconds` until they need it.

Behavioral acceptance tests:

* `tests/phospheneLoop.test.ts` proves update receives delta before draw.
* A SVG loop test proves RAF delta is positive, clamped, and forwarded.
* Existing form tests remain behaviorally unchanged.

### Step 3: Add `presence.ts` with the WeakMap resource pattern

Reuse: `createOscilloscopeFrame`, `requireOscilloscopeResources`, `WaterfallState`, `createWaterfallState`, `auroraBandCharacter`, `writeAuroraField`.

Actions:

1. Create `src/presence.ts` with `presenceForm: FormModule<WaveformLook>`.
2. Create `PresenceFrameResources` in a `WeakMap<Frame, PresenceFrameResources>`.
3. Store velocities, seeded phases, attractor weights, energy, previous state, and scratch buffers in resources.
4. Store only render data in the `GlyphFieldPrimitive`.
5. Make `createPresenceFrame` allocate all arrays once.
6. Make `updatePresenceFrame` mutate resources and primitive arrays in place, set `dirty` explicitly, and avoid runtime randomness.

Behavioral acceptance tests:

* Two frames created with the same seed and look produce identical positions after the same fixed dt sequence.
* Particles stay bounded under long waiting, thinking, and speaking runs.
* Energy ordering holds: sleeping below waiting, speaking above waiting, excited above neutral.
* A particle displaced by an onset impulse returns toward its attractor within N ticks after onset decays.
* Repeated updates preserve typed array identities for simulation and draw buffers.

### Step 4: Add the Three glyph resource

Reuse: `ThreeRenderer`, `ThreeRendererNodes`, `reconcileBandFields`, `trimBandResources`, `ThreePolylineResource`, `writePolylineSegmentRange`, `writeBarLayerMatrices`.

Actions:

1. Add `src/render/three/ThreeGlyphFieldResource.ts`.
2. Prefer `InstancedBufferGeometry` with one quad and per instance attributes for position, size, intensity, and glyph index.
3. Generate or cache the SDF glyph atlas in the resource owner, then dispose the texture with the material.
4. Add `ThreeGlyphFieldNode` and `glyphFields` to `ThreeRendererNodes`.
5. Add `glyphResources` to `ThreeRenderer`, with reconcile, draw, trim, and unmount handling.
6. If an `InstancedMesh` route is used, copy `barScratch` and `writeBarLayerMatrices`; do not allocate one object or matrix per particle per frame.

Behavioral acceptance tests:

* Initial draw uploads all glyph instance attributes.
* A one particle dirty range updates only that particle span in each dynamic attribute.
* A zero dirty range produces no GPU upload marks.
* Changing count or glyph atlas key disposes the previous resource and creates one replacement.
* `unmount` detaches and disposes geometry, material, and texture.

### Step 5: Refactor SVG dispatch and add SVG glyph nodes

Reuse: `SvgRenderer.clear*`, `ensureSvgPolylineNodes`, `SvgPolylineNode`, `SvgBandNode`, `writeSvg*Attribute`, `writeSvgProjectedPoint`, `writeSvgTransformCache`.

Actions:

1. Add a `classifySvgPrimitives(frame)` helper before adding glyph draw branches.
2. Add `src/render/svg/svgGlyphField.ts` with `SvgGlyphNode`, `ensureSvgGlyphNodes`, `trimSvgGlyphNodes`, and `drawSvgGlyphField`.
3. Cap SVG to about 400 text nodes.
4. Use deterministic sampling from primitive count to node count.
5. Cache glyph text, color, opacity, size, and visibility on each node.
6. Use `writeSvgProjectedPoint` and existing container transform behavior rather than per node transform object churn.
7. Add `clearGlyphs` to `SvgRenderer`.

Behavioral acceptance tests:

* A 12k particle field creates no more than 400 text nodes.
* A second draw with unchanged topology reuses node identities.
* Dot skin renders glyph index 0 as the configured dot glyph.
* Intensity visibly affects opacity or fill according to the chosen mapping.
* A frame with glyph not first still renders glyphs after classification refactor.
* Switching glyph to bar to band to polyline leaves no stale text nodes or defs.

### Step 6: Register the presence form and demo path

Reuse: `WAVEFORM_FORMS`, `formModuleFor`, `Visualizer`, `SvgHost`, `Hud` presence debug controls.

Actions:

1. Add `presence` to `WAVEFORM_FORMS` and `WaveformLook` structural fields.
2. Add `presenceForm` to `formModuleFor`.
3. Add a Three component path or a generic render host path that can mount `ThreeRenderer` with `glyphFields`.
4. Ensure `?form=presence&renderer=svg` and `?form=presence` both work.
5. Keep host inference out of Phosphene. Consume director state and signal only.

Behavioral acceptance tests:

* `?state=thinking.confused&form=presence&audio=0.7` changes particle motion compared with waiting.
* SVG and Three both render the dot skin from the same primitive buffers.
* No transcript parsing or host event mapping appears in Phosphene.

### Step 7: Gates for the implementer

Focused gates:

* `vp test tests/phospheneLoop.test.ts`
* `vp test tests/threeGlyphFieldResource.test.ts`
* `vp test tests/svgGlyphField.test.ts tests/svgRenderer.test.ts`
* `vp test tests/presence.test.ts`
* `rg "PointsPrimitive|kind: \"points\"" src tests` should return no matches after absorption.
* `rg "\.\.\." src/presence.ts src/render/three src/render/svg` should be reviewed manually so per frame object spreads do not reappear.

Repo gates:

* `vp check`
* `vp test`
* `vp build`

## Dependencies

* React and R3F provide the WebGL animation loop and component hosts.
* Three provides geometry, materials, instancing, textures, and disposal APIs.
* SVG backend uses DOM nodes directly, with cached attribute writers in `svgDom`.
* Vite+ owns lint, typecheck, test, and build gates.

## Open Questions

1. Glyph atlas ownership: per `ThreeGlyphFieldResource`, per renderer instance, or module cache keyed by glyph set. Prefer single owner with deterministic disposal, then cache only if tests prove lifecycle safety.
2. Contract color shape: one base color plus intensity, or low and high colors. The spec says colors, so settle this before implementation and test the observable mapping.
3. SVG primitive mixing policy: fully support mixed primitive frames, or declare one primitive family per frame except waterfall polylines. The current SVG leak should still be removed so the policy is explicit.
4. Allocation guard: Vitest cannot reliably prove zero allocation, but it can prove stable object identities for all typed arrays and node caches across repeated updates.

## Verification Performed

* `fmm validate`: all 74 indexed files are up to date.
* `git status --short`: clean before report write.
* fmm structural reads: render topology, render outlines, dependency graphs, and targeted symbol reads listed above.
* No `vp check`, `vp test`, or `vp build` was run during the scout because the brief constrained this pass to a read oriented report artifact and no code changes were made.
