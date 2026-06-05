---
title: Cubicell Cube Rendering Mastery — Coplanar Faces, Depth, Culling, Edges
type: reference
tags: [cubicell, threejs, r3f, voxel, z-fighting, depth-buffer, face-culling, polygon-offset, instancedmesh, rendering]
summary: The permanent expert reference on rendering cube grids without z-fighting or seam artifacts. Depth-buffer math, why coplanar faces are unresolvable by any depth encoding, the voxel-engine culling standard, the coverage-proof isFaceBuried predicate for cubicell, polygon offset for intentional coplanar layers, T-junction/inset notch mechanics, instanced transparency, picking consistency, and edge geometry (shared-line bar duplication, ownership arbitration, corner joins). Includes the cubicell fix mapped to the observed symptoms.
status: active
source: cube-render warroom (GPT renderer analysis, Opus theory analysis, Fable synthesis, two cited research passes)
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

# Cubicell Cube Rendering Mastery

Cubicell renders assemblies of axis-aligned cubes: six face planes and twelve edge boxes per cube, drawn through instanced `MeshBasicMaterial` meshes (`three` 0.185, `@react-three/fiber` 9). When two cubes touch, their opposing faces become mathematically coplanar. This document is the definitive reference on why that breaks, what the industry does about it, and exactly what cubicell does about it.

**The one-sentence thesis:** coplanar z-fighting is not a precision problem to be tuned away; it is a modeling problem. The buried face between two touching opaque cubes should never be drawn at all. Every depth trick (inset, bias, log depth, reversed-Z) is either a band-aid or the wrong tool for an exact depth tie. The voxel-engine industry settled this over a decade ago: cull interior faces at mesh construction.

---

## Part I — The domain reference

### 1. Why coplanar faces z-fight: the depth math

A perspective projection maps eye-space distance `z ∈ [n, f]` to window depth

```
d(z) = f/(f−n) − f·n / ((f−n)·z)
```

`d` is affine in `1/z`, not in `z`. That is deliberate: 1/z is linear in screen space, which is what lets the rasterizer interpolate depth with simple incremental math and what makes early-Z / hierarchical-Z hardware work ([Reed, Depth Precision Visualized](https://www.reedbeta.com/blog/depth-precision-visualized/), also syndicated as [NVIDIA, Visualizing Depth Precision](https://developer.nvidia.com/blog/visualizing-depth-precision/)). The cost is that depth resolution is spent near the near plane and starved everywhere else. The smallest world-space step the buffer can resolve at distance `z` is approximately

```
Δz ≈ Δd · z² · (f−n) / (f·n)
```

where `Δd` is one depth-buffer quantum (2⁻²⁴ for a 24-bit buffer). Precision loss scales with the `f/n` ratio, not `f−n` ([Reed](https://www.reedbeta.com/blog/depth-precision-visualized/); [Khronos wiki, Depth Buffer Precision](https://wikis.khronos.org/opengl/Depth_Buffer_Precision)).

Cubicell's camera is `near 0.1, far 100` (`src/scene/CubeScene.tsx:345`), a modest 1000:1 ratio. At a typical working distance of z ≈ 10 with a 24-bit buffer, Δz ≈ 6×10⁻⁵ world units. Two faces separated by the old `cubeFaceInset = 0.002` sat ~33 quantization steps apart — comfortably resolvable, which is why the inset "worked" for the moiré. Precision was never cubicell's problem.

**Exactly coplanar faces are the degenerate case.** Two coincident planes interpolate to the *same* depth at every pixel. There is no offset for quantization to resolve; the winner is decided by floating-point rounding noise in each triangle's setup, per pixel, per frame. That is why coplanar fighting looks like chaotic shimmer rather than a stable wrong ordering ([Wikipedia, Z-fighting](https://en.wikipedia.org/wiki/Z-fighting)).

Cubicell also renders orthographic (`scene.projection`), where depth is linear and uniformly precise. Coplanar faces still tie exactly. Any fix must be projection-independent — a second strike against depth-space tuning.

### 2. Why no depth encoding fixes an exact tie

Two techniques redistribute depth precision; neither breaks a tie:

- **Reversed-Z** (near→1, far→0 with a float32 depth buffer) makes precision near-uniform across the range — Reed measured 0% comparison error versus 45% for the conventional setup. It needs clip-control: native in WebGPU, `EXT_clip_control` in WebGL2. three.js has `reversedDepthBuffer` on `WebGLRenderer` (renamed at r183, still incomplete: shadows/SSAO/DoF bugs, issues [#31413](https://github.com/mrdoob/three.js/issues/31413), [#31661](https://github.com/mrdoob/three.js/issues/31661)) and landed WebGPU support in r183 ([#32967](https://github.com/mrdoob/three.js/releases/tag/r183)). It maps two coincident planes to the same (different, but still identical) value. No help for coplanarity.
- **Logarithmic depth** (`logarithmicDepthBuffer: true`) writes `gl_FragDepth = log2(vFragDepth) · logDepthBufFC · 0.5` per fragment ([three.js shader source](https://github.com/mrdoob/three.js/blob/dev/src/renderers/shaders/ShaderChunk/logdepthbuf_fragment.glsl.js); technique from [Outerra, 2013](https://outerra.blogspot.com/2013/07/logarithmic-depth-buffer-optimizations.html)). Writing `gl_FragDepth` disables early-Z, a real cost on overdraw-heavy scenes ([discourse](https://discourse.threejs.org/t/beware-of-logarithmic-depth-buffer-it-can-degrade-scene-performance/88495), [#17384](https://github.com/mrdoob/three.js/issues/17384)), and coincident planes still encode identically. three.js maintainers regard it as obsolete once reversed-Z is stable ([discourse](https://discourse.threejs.org/t/does-three-js-webgpu-support-reverse-z-buffer/87687)).

Conclusion: for genuinely coincident geometry the only correct moves are (a) don't draw one of them, or (b) bias one of them on purpose. Everything else in the taxonomy is a variant of those two.

### 3. The voxel-engine standard: hidden face culling

The universal first-order technique in every cube-grid engine: **never emit a face shared between two solid voxels.** A face exists in the mesh only when its neighbor is empty (or does not fully occlude — see the transparency rule).

- The three.js manual's voxel chapter names interior faces as "the biggest issue... faces inside the cubes that we can actually never see" and demonstrates a full 256³ volume crashing out-of-memory without culling ([Voxel Geometry](https://threejs.org/manual/en/voxel-geometry.html)).
- Mikola Lysenko's canonical meshing series presents culling as the baseline before greedy meshing ([0fps, Meshing in a Minecraft Game](https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/)).
- Production engines confirm: interior faces between solids are always culled; chunk boundaries are the classic correctness pitfall ([Vercidium, Voxel World Optimisations](https://vercidium.com/blog/voxel-world-optimisations/)).

Culling kills coplanar z-fighting *at the source*: the coplanar pair never reaches the GPU. It is also the only technique that simultaneously fixes occlusion errors (a buried face can never bleed) and reduces vertex load.

**The transparency exception (the Minecraft glass rule).** A solid face adjacent to a *transparent* voxel is never culled — it is visible through the glass ([Minecraft Wiki, Opacity](https://minecraft.wiki/w/Opacity)). Two adjacent transparent blocks of the same type cull their shared face; different transparent types do not cull each other. Bedrock formalizes this as declarative culling rules (`same_block`, `same_culling_layer`) ([Microsoft Learn, Block Culling](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/blockcullingreference/examples/blockcullingrules/block_culling)). The transferable principle: **culling is a visual-occlusion judgment, not an occupancy judgment.** The occluder must actually block sight.

### 4. Polygon offset: the tool for intentional coplanar layers

When two surfaces are coplanar *on purpose* (a decal on a wall, highlight lines over a fill), the standard tool is depth bias: `glPolygonOffset(factor, units)`, applied after interpolation and before the depth test:

```
offset = factor · DZ + r · units
```

`DZ` is the polygon's maximum depth slope in window space, so `factor` scales bias with viewing angle (grazing polygons need more). `r` is the implementation's smallest guaranteed-resolvable depth step, so `units` provides a flat, angle-independent floor — essential for face-on polygons where `DZ = 0` ([Khronos glPolygonOffset](https://registry.khronos.org/OpenGL-Refpages/gl4/html/glPolygonOffset.xhtml); [docs.gl](https://docs.gl/es3/glPolygonOffset)). three.js exposes it 1:1 as `Material.polygonOffset` / `polygonOffsetFactor` / `polygonOffsetUnits` ([docs](https://threejs.org/docs/#api/en/materials/Material.polygonOffset)). Start at `1, 1`; raise `units` if silhouette-angle flicker persists.

Pitfalls, all confirmed:
1. **Per-material, whole draw call.** You bias an entire mesh, not the pixels that happen to coincide with a particular neighbor.
2. **Raycasting never sees it.** The bias exists only in the GPU depth pipe; `Raycaster` intersects true geometry. Offset-separated coplanar meshes can pick differently than they draw — a drawn==picked violation if used as the primary z-fight fix.
3. **Glancing-angle drift.** The `factor · DZ` term grows with slope and can visibly detach the layer ([discourse](https://discourse.threejs.org/t/the-polygon-offset-is-not-correct-when-viewed-from-the-front/57631)).
4. **`r` is hardware-defined.** Tuned values are "enough headroom," not exact physics.

The lineage is instructive: polygon offset was introduced for exactly the hidden-line problem — filled mesh pushed back, wireframe drawn at true depth wins the tie (OpenGL Programming Guide, Ch. 6, the `polyoff` example). It has always been the tool for *deliberate* coplanar layering, never for geometry that should not exist.

### 5. The rest of the coplanar taxonomy, and when each is right

| Technique | Mechanism | Right when |
|---|---|---|
| **Hidden-face culling** | Don't emit the buried face | Geometry is genuinely invisible (touching opaque solids). Fixes rendering, picking, and perf together. First choice. |
| **Polygon offset** | Post-interpolation depth bias | Intentional coplanar layers (decal, highlight-over-fill). Not pickable-consistent by itself. |
| **`depthFunc` LEQUAL + `depthWrite:false` overlay** | Second draw at equal depth passes by function choice; draw order arbitrates | Controlled-order overlays. Note three.js already defaults to `LessEqualDepth` precisely so equal-depth redraws can win. |
| **Stencil decal** | Stencil marks base pixels; decal drawn with relaxed depth test only where marked | Pixel-exact decals with partial occluders, where offset drift is unacceptable (SIGGRAPH 2000 course notes §3.5). |
| **`renderOrder` + `depthTest:false`** | Reorders draw calls; disabling the test lets the last draw paint unconditionally | UI-style always-on-top chrome. Wrong for world geometry — it also stops occlusion against everything else. Cubicell already uses this correctly for selection chrome (`CubeSelectionChrome.tsx`, `AxisHintChrome.tsx`). |
| **Geometric shrink/offset (e.g. `cubeFaceInset`)** | Move real vertices | Almost never for adjacent solids: it breaks watertightness (§6) and shifts picking geometry. Acceptable only where the gap itself is the desired look and seams are covered. |

### 6. Watertightness: why the inset produced corner notches

GPU rasterizers guarantee crack-free, double-draw-free seams via the top-left fill rule: when two triangles share an edge **with bit-identical vertex positions**, every boundary pixel is owned by exactly one of them ([ryg, A trip through the Graphics Pipeline, part 6](https://fgiesen.wordpress.com/2011/07/06/a-trip-through-the-graphics-pipeline-2011-part-6/)). The guarantee is conditional on literal shared coordinates. Break the condition and rounding decides pixel ownership independently per triangle — this is the mechanism behind greedy meshing's T-junction cracks (vertices mid-edge of a merged quad; [0fps part 2](https://0fps.net/2012/07/07/meshing-minecraft-part-2/) concedes "greedy meshing will produce them", with cross-vendor gap-pixel reports in the comments).

An epsilon inset breaks the condition *by construction*. Each face's boundary retreats along its own normal, so:
- at a **cube edge**, two faces that met at a shared line are now separated — a hairline crack;
- at a **cube corner**, three mutually orthogonal faces each retreat along a different normal; their planes now intersect inside the cube and the true corner is covered by nothing — a visible triangular notch.

This is exactly what Stuart observed toggling `cubeFaceInset` between 0 (moiré) and 0.002 (notches). The inset traded a depth artifact for a geometry artifact. (Cubicell's edge boxes straddle the surface and hide most of the crack, which is why only the corners read as notches.) The industry rule generalized: **never move face geometry that must seam with a neighbor; achieve visual gaps or lines with an overlay pass instead.**

### 7. Transparency ordering with InstancedMesh

`InstancedMesh` does not depth-sort instances. Rendering draws them in buffer order; with a transparent material, blending happens in write order, not back-to-front ([issue #27170](https://github.com/mrdoob/three.js/issues/27170)). three.js sorts *objects*, never instances within one. Workarounds, in practical order: CPU per-frame sort of the instance buffer; splitting translucents into non-instanced meshes to inherit object sorting; OIT (depth peeling / weighted-blended, [#9977](https://github.com/mrdoob/three.js/issues/9977)); `alphaTest` for binary transparency. Community libraries (`@three-ez/instanced-mesh`) formalize sorting + BVH raycasting on top.

Cubicell's mitigation is already structurally right: translucent parts live in **separate** instanced meshes with `depthWrite: false` (`instancedPartMeshCore.ts:56`), and opaque parts keep depth writes. Buried-face culling reduces the translucent population that could ever mis-blend. Residual instance-order blending among overlapping translucent faces is a known, accepted limit until instance sorting is warranted.

### 8. Picking consistency: drawn == picked

`InstancedMesh.raycast` bounding-sphere-tests the whole mesh, then loops **every** instance `0..count` — O(n) per ray, no per-instance visibility flag exists ([source, dev branch](https://github.com/mrdoob/three.js/blob/dev/src/objects/InstancedMesh.js); [#22102](https://github.com/mrdoob/three.js/issues/22102)). Two consequences:

1. **Anything in the buffer up to `count` is pickable.** A face you did not want drawn but left in the buffer is still hit by rays. The only pattern that removes an instance from *both* drawing and picking is not writing it (or shrinking `count`).
2. **Therefore cull on the CPU, before instance creation.** Shader-discard tricks hide pixels but leave phantom pick targets. Cubicell's architecture makes the right thing the easy thing: parts are plain arrays rebuilt in `createCubeCellInstances`, `syncInstancedPartMesh` sets `mesh.count = parts.length`, and pointer handlers resolve `event.instanceId` against the *same* array (`InstancedPartMesh.tsx:81`). Filtering the array is simultaneously the render cull and the pick cull. Drawn == picked holds by construction.

---

## Part II — The cubicell fix

### Root cause

Occlusion knowledge already exists in the domain — `createOccupancyIndex` (`src/domain/neighbors.ts:49`), `isFaceExposed` / `isCubeExposed` / `classifyEdgeJunction` (`src/domain/exposure.ts`) — but **none of it is wired into rendering**. `createCubeCellInstances` (`src/scene/cubeInstances.ts:105`) emits all six faces of every cube, filtered only by the per-face `visible` flag. Every buried face between touching cubes is drawn, picked, and blended. All three symptoms follow. `cubeFaceInset = 0.002` (`src/domain/cubeGeometry.ts:49`) is a band-aid over coplanar pairs that should not have been drawn, and it costs corner notches (§6).

### Why `isFaceExposed` is not the render predicate

`isFaceExposed` answers coordinate adjacency over *structural* occupancy: hidden spacer cells count as occupied (the spacer contract — correct for the shadow shell and build semantics). Rendering needs a stronger, geometric, visual claim. Two independent failure modes if reused directly:

1. **Gap.** `getGridStep = cellSize + gap` and the default gap is 0.5 (`src/domain/grid.ts:36`). Coordinate-adjacent cubes have visible air between them; culling the facing faces would open holes you can see into. At gap 0.5 the correct cull set is *empty*.
2. **Occluder visibility.** A hidden spacer occupies its coordinate but draws nothing (or a translucent ghost in edit mode). A neighbor with a translucent or per-face-hidden touching face does not block sight. Culling against structural occupancy would punch see-through holes.

### The predicate: `isFaceBuried` (coverage proof)

Keep the occupancy index for what it is good at — O(1) candidate discovery — then **prove full world-space coverage** before omitting a face. Since the occupancy `Set` cannot return the neighbor, the index gains a coord-key → cell map (`getGridCoordKey`/`getNeighborCoord`, still O(1)).

A face is buried, and only then culled, when its facing neighbor satisfies **all** of:

1. **Plane coincidence.** The neighbor's opposing face plane coincides with this face's plane in world space: zero effective gap on that axis and both cells sized/scaled to actually meet (resized-to-meet counts; the default gap 0.5 fails here, correctly culling nothing).
2. **Full 2D coverage.** The neighbor's face rectangle fully covers this face's rectangle (size, offset, scale). A smaller neighbor covering part of a larger face does **not** cull it — partial overlap keeps the face and lets depth handle it (the pair is not coplanar over the uncovered region; the covered region is occluded regardless of winner).
3. **Compatible rotation.** Both poses must place the faces truly coplanar and opposed; any relative rotation voids coincidence.
4. **Opaque occluder.** The neighbor cell is visible, its touching face is visible, and that face's opacity is 1. A translucent neighbor never buries — the face behind it is seen through it and transparency ordering still needs it. (Consequence: of a translucent-against-opaque coplanar pair, the translucent face is the one culled, the opaque one draws. Exactly one face per coincident plane survives.)

Structural occupancy and the burial predicate coexist deliberately: **occupancy answers "can I build here," burial answers "can anyone see this."** Hidden spacers stay occupied for the shadow shell and never bury for rendering.

### Renderer mechanics

Cull on the CPU by **not emitting the instance** in `createCubeCellInstances` — no shader discard, no zero-scale. This preserves drawn == picked through the single `mesh.count` path (§8) at zero extra render cost; it strictly shrinks buffers. `createCubeSceneInstances` already sees the full cell list and builds per-cell context, so the coord→cell index is built once per pass and threaded down, matching the existing `createOccupancyIndex` consumer pattern.

Edges are unaffected: edge boxes straddle the surface (length + thickness, centered on the boundary, `cubeGeometry.ts:115`), so they protrude thickness/2 proud of the face plane. A culled face leaves no recess for them to expose, and — being proud, not coplanar — they never z-fight faces. No polygon offset needed on edges.

`cubeFaceInset` retires to 0 and is deleted. Faces return to exact surface planes; shared boundaries become bit-identical again; watertightness (§6) eliminates the corner notches. `material.polygonOffset` is **reserved** for future intentional coplanar layers (e.g. flat highlight lines over a face fill) and is not applied to cube faces.

### Symptom → fix map

| Symptom (Stuart's screenshots) | Cause | Fix |
|---|---|---|
| 1. Z-fight moiré where touching cubes meet | Both faces of the buried coplanar pair drawn; exact depth tie resolved by rounding noise per pixel (§1) | `isFaceBuried` culling deletes the pair at the source; no coincident planes reach the GPU |
| 2. Notch/gap artifacts at edges and corners | `cubeFaceInset` breaks the shared-vertex watertight contract; three inset planes miss the true corner (§6) | Inset retired; faces at exact planes; rasterizer watertightness restored |
| 3. Face bleeding/floating where it should be occluded | Buried face still drawn (and pickable); with translucent/`depthWrite:false` or instance-order blending it shows through | Buried face no longer exists; translucent blending population shrinks (§7) |

### Invariants

1. **Drawn == picked.** Face culling happens once, at instance-array construction; rendering and raycasting consume the same array. No GPU-only bias (polygon offset) may ever be the mechanism that decides visibility of world geometry.
2. **Only opaque, visible, fully-covering, plane-coincident neighbors bury.** Translucency, hidden cells, hidden faces, partial coverage, gaps, resizes that break contact — all keep the face.
3. **Structural occupancy is not visual occlusion.** Spacers count as occupied for build semantics (shadow shell, slots) and never bury for rendering. The two predicates stay separate in `domain/`.
4. **Default gap 0.5 culls nothing.** The predicate must be exact, not coordinate-approximate.
5. **Face geometry is never inset/shrunk to dodge depth artifacts.** Visual gap effects, if ever wanted, are overlay passes.

### Edge geometry: shared-line duplication, ownership arbitration, corner joins

Faces were only half the coplanarity story. Cubicell's twelve edge bars per cube are t×t boxes centered on each edge line, axially sized `length + thickness` (`createCubeEdge`, `cubeGeometry.ts`). Both choices are deliberate and both create coincident geometry:

- **The straddle** (cross-section centered on the boundary) means two cubes touching at gap 0 place their bars along a shared grid line as *identical boxes* — same line, same cross-section, same span. Every outer surface coincides.
- **The axial overshoot** (`+ thickness`, present since the geometry was first modeled) is the **corner join**: each bar protrudes t/2 past the corner so the three orthogonal bars jointly cover the outer t/2 octant at every corner. With exact-length bars that octant is covered by nothing — a notch at every corner. **Shortening the bars is therefore ruled out**; the overshoot's side effect is that the three bars of one cube co-occupy a t³ region at each corner with pairwise coincident outer faces.

**The three coincidence configurations:**

| Config | Geometry | Induced by |
|---|---|---|
| (i) Corner caps | One cube's three orthogonal bars co-occupy the t³ corner region; pairwise coincident outer faces | Overshoot (intra-cube) |
| (ii) Collinear joint patches | Adjacent cubes' collinear bars overlap for a t-length patch straddling a gap-0 seam | Overshoot (inter-cube) |
| (iii) Parallel seam bars | Stacked cubes at gap 0 draw two fully identical boxes on the shared line; also corner-touching (non-manifold) neighbors, where face culling never fires | Straddle — exists with or without overshoot |

**The visibility law.** `MeshBasicMaterial` is unlit: coincident surfaces with identical opaque color resolve to identical fragments, so the z-fight is invisible. Cubicell's defaults (edge opacity 1, color `theme`) hide all three configurations. The artifact appears exactly when the coincident surfaces *differ*: per-edge authored colors (competing wedge/moiré — the observed stacking artifact), translucent edges (blend stacking: triple-dark corner blobs, double-dark seam bars), or edit-mode ghosts (alpha 0.12 bar over an opaque coincident bar, per-pixel rounding shimmer). Edge-versus-face coincidence does not exist: bar outer surfaces sit at ±t/2 off every face plane.

**The fix family is ownership, never epsilon** — the exactly-one-survives principle applied to bars:

1. **Discovery via the quadrant model.** A grid edge line is shared by up to *four* cells, not two; `classifyEdgeJunction` already classifies the line (flat-seam = 2 coincident bars, concave = 3, interior = 4). Ownership arbitrates among all incident bars; a pairwise rule double-draws at concave and interior lines.
2. **Coincidence is geometry-proven, adjacency is only discovery** — the `isFaceBuried` lesson verbatim. Prove same world line and same cross-section through the layout (pose, scale, offset, cell size, thickness). Gap > 0 dedupes nothing; resized cubes, differing thickness, and partial axial overlap keep both bars (mirrors the face partial-coverage ruling; a thinner bar hides inside a thicker one harmlessly).
3. **Interior-line cull-all requires an opaque coverage proof.** Bars on an `interior` junction line vanish only when all four quadrant cells are visible and the surrounding surfaces opaque; a translucent or ghost quadrant keeps them. Visual occlusion, never structural occupancy.
4. **The survivor is chosen by a priority ladder**, all comparisons translation-invariant: visible beats ghost (kills the edit-mode shimmer; the spacer stays discoverable through its non-coincident parts) → opaque beats translucent → **authored style beats default `theme`** (lowest-coord-first would sometimes hide the edge the user just recolored — the recolor-does-nothing trap) → lowest coord as the final deterministic tie-break. Accepted costs: adding or removing a cube can flip a contested bar's style, and two *differently authored* coincident edges still resolve by coordinate — whose style owns a shared grid line is a genuine domain-model question (per-cube edge parts versus grid-line entities), parked for a product ruling.
5. **Cull only the drawn bar, never the hit target.** Edge picking already deviates from drawn geometry by design (`edgeHitTargetThickness` fattens pick boxes to 0.12), so keeping every authored edge's hit target preserves canvas-selectability of a non-owner edge for restyling. This is the one deliberate, scoped departure from the face-world drawn==picked rule: the invariant's substance — no phantom *drawn* geometry, picking never resolves to something invisible that shouldn't exist — still holds; pick affordances exceeding drawn geometry was already the edge contract.

### Slice plan

1. **Domain: `isFaceBuried`** in `src/domain/exposure.ts` + an occupancy *map* (coord key → cell) beside the existing Set. Pure, translation-invariant, fully unit-tested: gap 0.5 → nothing buried; gap 0 touching → mutual burial of opaque pairs; translucent/hidden/partial/resized/rotated → not buried; spacer → not buried. *(Shipped: PR #48.)*
2. **Scene: wire into instance creation.** Thread the map through `createCubeSceneInstances` → `createCubeCellInstances`; skip emitting buried faces (visible and ghost paths). Delete `cubeFaceInset` (remove the constant and its doc comment). Tests on instance counts. *(Shipped: PR #49, live-validated — Layers=Faces clean.)*
3. **Edge-burial dedup** per the edge-geometry section: pure domain predicate over `OccupancyMap` + layout reusing `classifyEdgeJunction`; config (iii) parallel seam bars first (the observed artifact); priority-ladder survivor; hit targets preserved. RED coverage: gap-0 dedup, gap-0.5 keep-both, resized/thickness keep-both, interior cull-all vs translucent-quadrant keep, authored-beats-default, hit-target preserved.
4. **Verify live.** Stacked cubes at gap 0 (face moiré and edge wedge gone), corners (no notches), translucent-over-opaque (no bleed), gap 0.5 (nothing missing), build mode with spacers (ghosts intact, no seam shimmer), picking on formerly-buried planes and non-owner edges. Confirm orthographic and perspective both clean.

---

## Sources

Depth precision and coplanar techniques: full cited pass in `~/.mdx/research/coplanar-surface-rendering-webgl-threejs.md`. Voxel practice, meshing, watertightness, instancing: full cited pass in `~/.mdx/research/voxel-cube-grid-rendering-practice.md`. Key primaries: [Reed, Depth Precision Visualized](https://www.reedbeta.com/blog/depth-precision-visualized/) · [NVIDIA, Visualizing Depth Precision](https://developer.nvidia.com/blog/visualizing-depth-precision/) · [Khronos, Depth Buffer Precision](https://wikis.khronos.org/opengl/Depth_Buffer_Precision) · [Khronos, glPolygonOffset](https://registry.khronos.org/OpenGL-Refpages/gl4/html/glPolygonOffset.xhtml) · [three.js manual, Voxel Geometry](https://threejs.org/manual/en/voxel-geometry.html) · [0fps, Meshing in a Minecraft Game](https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/) ([part 2](https://0fps.net/2012/07/07/meshing-minecraft-part-2/)) · [ryg, Graphics Pipeline part 6](https://fgiesen.wordpress.com/2011/07/06/a-trip-through-the-graphics-pipeline-2011-part-6/) · [Minecraft Wiki, Opacity](https://minecraft.wiki/w/Opacity) · [three.js InstancedMesh source](https://github.com/mrdoob/three.js/blob/dev/src/objects/InstancedMesh.js) · [three.js #27170, instance sorting](https://github.com/mrdoob/three.js/issues/27170) · [three.js Material.polygonOffset](https://threejs.org/docs/#api/en/materials/Material.polygonOffset).
