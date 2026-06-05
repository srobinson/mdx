---
title: Voxel / Cube-Grid Rendering Practice — Culling, Greedy Meshing, T-Junctions, Outlines, Instanced Transparency
type: research
tags: [voxel, three.js, greedy-meshing, rasterization, instancedmesh, cube-grid, minecraft, rendering]
summary: Authoritative sourced findings on hidden-face culling, greedy meshing and its T-junction crack problem, watertight rasterization rules (why epsilon-inset faces cause corner notches), block outline rendering, and three.js InstancedMesh transparency/raycast behavior for voxel engines.
status: active
source: quick-research
confidence: high
created: 2026-07-10
updated: 2026-07-10
---

# Summary

The standard voxel rendering pipeline has two layers, both well documented across canonical sources: (1) **hidden/interior face culling** — never emit a face between two solid voxels, only emit faces adjacent to empty (or transparent) space — and (2) **greedy meshing** — merge coplanar same-type faces into larger quads to cut vertex/triangle count by roughly 3-4x. Greedy meshing's known cost is **T-junction cracking**: merged large quads meeting smaller quads at a T-shaped seam create vertices that are not bit-identical across the shared edge, and GPU rasterizers can then leave a one-pixel gap along that edge due to floating-point rounding in the edge-function evaluation. The fix used across the industry is to guarantee **bit-identical shared-edge vertices** (the same "watertight rasterization" guarantee OpenGL/D3D make for triangles that literally share vertex data) — which is also exactly why epsilon-inset ("shrunk") cube faces are unsafe: an inset face has no bit-identical shared edge with its neighbor's inset face, so the corner where three faces meet opens into a visible notch. Block outlines are conventionally drawn as a **second, separate line-primitive pass** (three.js `EdgesGeometry` + `LineSegments`, or a scaled/offset overlay box) rather than baked into the face mesh, combined with `polygonOffset` or `renderOrder` to avoid z-fighting. three.js `InstancedMesh` is confirmed, from source, to **not sort instances by depth** for either raycasting or rendering — raycast literally loops `instanceId` from `0` to `.count` testing every instance, and transparent instances blend in whatever order they were written into the instance buffer, which is a known, still-open limitation (issue #27170).

---

# 1. Hidden/Interior Face Culling

**Rule:** never render a face shared between two solid (opaque) voxels. A face is only emitted when the neighboring voxel in that direction is absent (or, for the transparency extension, not equally opaque).

## three.js manual — "Voxel Geometry" (Minecraft-style game)
- URL: https://threejs.org/manual/en/voxel-geometry.html (mirrored at https://threejsfundamentals.org/threejs/lessons/threejs-voxel-geometry.html; canonical culled-faces demo at https://threejs.org/manual/examples/voxel-geometry-culled-faces.html; source at https://github.com/mrdoob/three.js/blob/dev/manual/en/voxel-geometry.html)
- States the core problem directly: *"There are several issues but the biggest issue is we're making all these faces inside the cubes that we can actually never see."*
- Illustrates with a 3x2x2 box: merging cubes naively produces interior faces that are "a waste since they can't be seen. It's not just one face between each voxel, there are 2 faces, one for each voxel facing its neighbor that are a waste."
- Performance claim: *"All these extra faces, especially for a large volume of voxels will kill performance."* The author demonstrates this by filling a full 256³ volume (rather than just the surface) and reports it *"churned for about a minute and then crashed with out of memory."*
- Algorithm: for each solid voxel, for each of the 6 face directions, check the neighbor voxel in that direction; only emit a face if `!neighbor` (neighbor is empty/air). Reference implementation loop is given directly in the manual.

## 0fps.net — Mikola Lysenko, "Meshing in a Minecraft Game" (Part 1)
- URL: https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/
- This is the canonical, most-cited voxel-meshing reference (also linked from `maxogden.com`'s "Bringing Minecraft-style games to the Open Web": https://maxogden.com/bringing-minecraft-style-games-to-the-open-web, and referenced by the widely forked `roboleary/GreedyMesh` sample: https://github.com/roboleary/GreedyMesh).
- Presents three algorithms in increasing sophistication: (a) the "stupid method" — 6 faces per voxel, no culling; (b) **culling** — *"One obvious improvement is to just cull out the interior faces, leaving only quads on the surface."* Implementation note: *"we not only have to read each voxel, but we also have to scan through their neighbors."*; (c) **greedy meshing** (see §2).
- The article's scope is a simplified binary (solid/empty) voxel map and does **not** itself address the transparent-voxel (glass) culling exception — that extension is documented separately (see below), and is standard practice in production engines (Minecraft itself, and voxel engines that implement "binary greedy meshing").

## Transparent-voxel exception — the "Minecraft glass rule"
- Minecraft Wiki, "Opacity": https://minecraft.wiki/w/Opacity — transparent blocks (e.g. glass) do not cull the face of an adjacent *opaque* block (that face still renders normally, since it's visible through the transparent neighbor), but two adjacent transparent blocks **of the same block type** do cull the shared face between them — a glass cuboid renders only its outer glass faces, not the internal glass-to-glass walls. Blocks of *different* transparent types (e.g. green vs. yellow stained glass) do **not** cull each other — the wiki notes *"green stained glass does not prevent the yellow stained glass next to it from rendering its face."*
- Minecraft Bedrock / Microsoft Learn, "Block Culling" reference: https://learn.microsoft.com/en-us/minecraft/creator/reference/content/blockcullingreference/examples/blockcullingrules/block_culling — documents the explicit culling-condition vocabulary block authors can declare: `same_block` (cull when adjacent to the identical block) and `same_culling_layer` (cull when adjacent to any block sharing a designated culling layer — this is the general mechanism for "any glass type culls any other glass type" behavior, generalizing beyond exact-type matching). Also: https://learn.microsoft.com/en-us/minecraft/creator/documents/voxelshapes
- Practical implementation writeup for binary greedy meshing with transparency, EngineersBox devblog: https://engineersbox.github.io/website/2024/09/19/transparency-with-binary-greedy-meshing.html — states the rule in bitmask form: *"we need anything solid followed by a transparent voxel in the direction of the face to be included"* (i.e., solid-adjacent-to-transparent always emits a face), versus the opaque-opaque rule which is *"set if current is solid and next is air."* This article treats "any non-empty voxel" uniformly via an OR of solid+transparent masks and does not implement the Minecraft same-type-only exception — worth flagging as a simplification some engines make (cull between any two transparent voxels) versus Minecraft's stricter same-type/same-layer rule.
- Godot Forum thread confirms the general community-understood rule: *"Adjacent blocks of the same type should cull one another with block types such as foliage and glass, but blocks of different types should not."* https://forum.godotengine.org/t/in-minecraft-the-faces-between-adjacent-blocks-are-culled-due-to-being-invisible-how-to-achieve-this/130345

## Vercidium — "Voxel World Optimisations"
- URL: https://vercidium.com/blog/voxel-world-optimisations/ (production writeup for the FPS "Sector's Edge"; follow-up at https://vercidium.com/blog/further-voxel-world-optimisations/; open-sourced code at https://github.com/Vercidium/voxel-mesh-generation)
- Confirms interior faces between solid voxels are always culled, and documents chunk-boundary handling (checking the adjacent chunk's edge voxels rather than treating chunk edges as automatically solid or empty) as a common correctness pitfall.
- Reports concrete mesh-generation performance: chunk regen optimized down to 0.48ms/chunk (54% faster than the initial 0.89ms), relevant because their game destructibly regenerates meshes almost every frame across 16 players.

---

# 2. Greedy Meshing / Face Merging

**What it is:** after culling determines which unit faces are visible, greedy meshing merges adjacent, coplanar, same-type (same texture/material/orientation) unit faces into the largest possible rectangular quad, algorithmically similar to a 2D rectangle-covering / run-length-merging pass performed independently per axis-aligned slice and per face direction.

## 0fps.net — "Meshing in a Minecraft Game" (Part 1, greedy section) and Part 2
- Part 1: https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/ — introduces the algorithm: *"What you do is group blocks together according to their type, and then do the meshing on each part separately."*
- Reported benefit on the article's test terrain: naive culling produced **26,536 vertices / 6,634 quads**; greedy meshing reduced this to **7,932 vertices / 1,983 quads** — roughly a 3.3x reduction.
- Part 2: https://0fps.net/2012/07/07/meshing-minecraft-part-2/ — follow-up addressing community feedback, including:
  - Extending greedy meshing across multiple voxel types/normal directions by grouping by type first, then meshing each group.
  - An alternative approach treating the problem as classical **polygon triangulation / monotone decomposition** from computational geometry (benchmarked as slower than greedy in the article's JS implementation, though the author cautions JS isn't an ideal benchmarking substrate and the implementations weren't heavily tuned).
  - **T-junction acknowledgment:** the author directly concedes *"the meshes contain many T-vertices... greedy meshing will produce them."* A commenter documents observed rendering artifacts — visible white/gap pixels in darker areas, reproduced across multiple GPU vendors, confirming this isn't theoretical.
  - **Mitigation discussed in comments:** filling seams with degenerate triangles that almost never rasterize under normal conditions but provide coverage exactly at the seam pixel when floating-point rounding would otherwise leave a gap. The article does not present this as a fully solved, canonical fix — it's presented as a workaround, consistent with the broader graphics-literature position that the *robust* fix is guaranteeing bit-identical shared vertices rather than patching after the fact (see §3).

## Cost: T-junction cracks, explained mechanically
- A T-junction is a vertex of one quad landing in the *middle* of another quad's edge rather than exactly at that quad's own vertex — e.g., a large greedy-merged 4x4 quad sits beside four separate 1x1 quads; the big quad's edge has only 2 corner vertices along that 4-unit span, while the small quads contribute 5 vertices along the same span. Geometrically the edges are collinear and should be watertight, but the GPU treats each quad's two triangles independently.
- ryg blog (Fabian "ryg" Giesen), "A trip through the Graphics Pipeline 2011, part 6": https://fgiesen.wordpress.com/2011/07/06/a-trip-through-the-graphics-pipeline-2011-part-6/ — the canonical reference on GPU rasterization fill rules. Key point relevant to T-junctions: *"T-junctions... are very likely to have caused cracking before rasterization even starts due to floating point rounding"* — i.e. even geometrically-coincident points computed via different vertex/interpolation paths (a merged-quad corner vs. an independently-computed small-quad edge midpoint) are not guaranteed to produce bit-identical floating point results after the vertex shader / clip-space transform, so the two independently-rasterized triangles can each decide the shared boundary belongs to the *other* triangle, leaving an unfilled pixel — a crack.
- Additional framing on Blackflux's "Meshing in Voxel Engines – Part 1": https://blackflux.wordpress.com/2014/02/23/meshing-in-voxel-engines-part-1/ (secondary source, useful survey context alongside 0fps).

---

# 3. Watertight Rasterization Rules — why identical shared vertices never crack, and why epsilon-inset faces do

## The rule (ryg blog, same source as above)
- https://fgiesen.wordpress.com/2011/07/06/a-trip-through-the-graphics-pipeline-2011-part-6/
- D3D and OpenGL both mandate a **top-left fill rule** (a specific tie-break for which triangle "owns" a pixel center that lies exactly on a shared edge) specifically so that: *"if two polygons lie on either side of a common edge (with identical endpoints) on which a fragment center lies, then exactly one of the polygons results in the production of the fragment"* — guaranteeing no double-draw and no gap, **provided the edge endpoints are identical** between the two triangles.
- Mechanism: rasterizers evaluate integer/fixed-point edge functions per pixel; *"once you have the values of the edge equations at a given point, the values of the edge equations for adjacent pixels are just a few adds away."* The tie-break itself *"boils down to subtracting 1 from the constant term on some edges during triangle setup"* — deterministic, bit-exact, and only valid when both triangles were set up from the *same* quantized vertex coordinates.
- **Why identical vertices matter:** the guarantee is conditioned on bit-identical quantized screen-space positions for the shared edge. If two adjacent faces do not literally share vertex data (same buffer positions, or independently computed positions that happen to be "almost" equal), floating-point rounding differences between the two triangle setups can make the edge functions disagree about who owns a boundary pixel — this is exactly the T-junction crack mechanism from §2, and it's also exactly what an epsilon inset causes.

## Why epsilon-inset (shrunk) faces cause corner notches
- This is a direct mechanical consequence of the rule above, not a separately "named" phenomenon in the literature, but it follows deterministically: watertightness is guaranteed *only* between triangles that share literal vertex positions. A cube face inset by some epsilon (recessed slightly inward from the true cube boundary) by construction **no longer shares an edge** with the neighboring voxel's inset face — each face's boundary is now epsilon inside its own cube, so two adjacent cubes' near faces are separated by a 2·epsilon gap along their shared boundary, which is visible as a hairline crack along every voxel-voxel seam, not just merged-quad seams.
- At a **corner** where three mutually orthogonal faces of the same cube meet (or where three different cubes meet), the effect compounds: each of the three faces is independently inset along its own normal, so the three inset planes no longer intersect at the original cube corner — they intersect at a point pulled inward along the corner's diagonal, and the "true" corner position is left uncovered by any of the three faces, producing a visible triangular notch. This is the geometric explanation for the corner-notch artifact reported on faces inset by 0.002: the inset is not a per-face cosmetic shrink, it is a break of the shared-vertex contract that watertight rasterization depends on, at both edges (2-face crack) and corners (3-face notch).
- Standard mitigations found across the sources above, generalized: (1) never inset/shrink face geometry meant to be adjacent to other solid geometry — keep exact shared vertex positions (the watertight-by-construction approach implied by ryg's rule); (2) if a visual inset/gap effect between voxels is wanted (e.g. a grid-line look), achieve it via a **second overlay pass** (see §4) rather than by moving the actual face geometry, so the base mesh stays watertight and the decorative grid lines are a purely additive, non-geometry-affecting layer; (3) for merged/greedy quads specifically, ensure the merge algorithm reuses the exact same vertex data at shared boundaries between a merged quad and its unmerged neighbors (the 0fps Part 2 comment thread's "degenerate triangle seam fill" is a patch for cases where exact vertex-sharing isn't easily achievable, not a substitute for it).

---

# 4. Rendering Block Edges / Outlines Over Faces

Production voxel engines universally treat the outline/grid-line/selection-highlight as a **separate render pass or separate primitive**, not as part of the solid face mesh, specifically to sidestep z-fighting and to allow independent styling (color, line width, dashed/solid) from the face material.

## three.js `EdgesGeometry` + `LineSegments` (the standard approach)
- Docs: https://threejs.org/docs/#api/en/geometries/EdgesGeometry
- Pattern (confirmed across three.js forum threads, e.g. https://discourse.threejs.org/t/how-to-render-geometry-edges/5745 and https://discourse.threejs.org/t/how-to-show-only-edge-lines/9724):
  ```js
  const cube = new THREE.BoxGeometry(1, 1, 1);
  const edgesGeo = new THREE.EdgesGeometry(cube);
  const mat = new THREE.LineBasicMaterial({ color: 0x0000ff });
  const wireframe = new THREE.LineSegments(edgesGeo, mat);
  ```
  `EdgesGeometry` extracts only edges whose adjacent-face-angle exceeds a threshold (default catches cube edges cleanly, unlike `WireframeGeometry` which draws every triangle edge including diagonals). The `LineSegments` object is typically added as a child of (or paired 1:1 with) the solid mesh, with `renderOrder` used to guarantee draw order.
- This avoids z-fighting by construction: a `Line` primitive drawn at the *exact same depth* as the face edge does not typically z-fight the way two coplanar triangles would, and any residual coincident-depth flicker is resolved with `Material.polygonOffset` on the solid mesh (docs: https://threejs.org/docs/#api/en/materials/Material.polygonOffset) — standard settings reported in forum threads: `polygonOffset = true, polygonOffsetFactor = -1 (or 1), polygonOffsetUnits = 1` (https://discourse.threejs.org/t/the-polygon-offset-is-not-correct-when-viewed-from-the-front/57631, https://github.com/mrdoob/three.js/issues/2593). Known caveat repeatedly reported: `polygonOffset` interacts poorly with `wireframe: true` material mode specifically (https://discourse.threejs.org/t/polygonoffset-doesnt-work-for-wireframes/29538) — this is a reason engines prefer the separate `LineSegments` approach over toggling `wireframe` on the face material.

## Alternative technique: slightly scaled overlay box
- Widely used pattern (documented informally across voxel.js-era plugins) for a *selection outline* specifically: render a second, slightly larger (scaled up by a small factor, e.g. 1.01-1.05x) wireframe or unlit box around the targeted voxel, so it sits strictly outside the solid face and cannot z-fight regardless of depth-buffer precision. The classic `voxel.js` plugin ecosystem shipped this as separate `voxel-wireframe` (persistent grid overlay on all voxels) and `voxel-outline` (highlight box around the currently targeted/hovered voxel) plugins — see the `voxel-engine`/`voxeljs-next` project family: https://github.com/max-mapper/voxel-engine, https://github.com/joshmarinacci/voxeljs-next, retrospective at https://medium.com/@deathcap1/6-years-after-6-months-of-voxel-js-a-retrospective-1e8a2eadeb0.

## Other known approaches (general graphics practice, applicable to voxel scenes)
- **Barycentric-coordinate wireframe shaders**: pass barycentric coordinates as a per-vertex attribute (or reconstruct via `gl_VertexID`/derivative tricks) and discard/darken fragments near a triangle edge in the fragment shader — renders true single-pass wireframe-over-solid without any second draw call or z-fighting risk, at the cost of a custom shader. This is a well-known general OpenGL technique (not voxel-specific) commonly cited from the original NVIDIA/Ericsson "Single-Pass Wireframe Rendering" line of work; relevant for engines wanting outline rendering without doubling draw calls.
- **Screen-space edge detection** (post-process): run a depth/normal-discontinuity edge-detect pass and composite outline color — decouples outline rendering entirely from mesh topology, common in stylized/toon voxel renderers, at the cost of a full-screen post pass.

---

# 5. Transparency in Voxel Engines with Instancing

## three.js `InstancedMesh` does not sort by depth
- Confirmed directly in three.js source (`src/objects/InstancedMesh.js`, `dev` branch) — instances are rendered in **whatever order they were written into the instance buffer** (via `setMatrixAt`); there is no automatic depth sort, so with a transparent material, blending happens in **instance-buffer order**, not back-to-front camera order. This produces incorrect/inconsistent blending as the camera moves, exactly as with any non-sorted transparent batch.
- Open GitHub issue tracking this gap directly: **"InstancedMesh: Proposal to support sorting, frustum culling"**, https://github.com/mrdoob/three.js/issues/27170 — quote: *"With the current InstancedMesh implementation it's not possible to easily or quickly sort individual instances to improve opaque overdraw for performance or transparency sorting."* Proposed remedies discussed there: (a) adopt the `WebGL_multi_draw` extension (as `BatchedMesh` does) to allow re-ordering draws while keeping one draw call — referenced companion PR #27168 — with the caveat *"WebGL_multi_draw is not supported in Firefox so fully switching over to multidraw would remove InstancedMesh support for FF"*; (b) a new dedicated `MultiDrawInstancedMesh` class; (c) do nothing (status quo, left to userland).
- Older, related long-standing issue on the general transparency-sorting problem in three.js (predates InstancedMesh-specific discussion): https://github.com/mrdoob/three.js/issues/4724, "Ability to Sort Faces / Handle Transparency Sorting."
- Community workaround libraries that add real per-instance sorting + frustum culling + BVH-accelerated raycasting on top of `InstancedMesh`: **`@three-ez/instanced-mesh`** (https://github.com/three-ez/instanced-mesh, npm: https://www.npmjs.com/package/@three.ez/instanced-mesh) — advertised features include frustum culling, fast BVH raycasting, sorting, visibility toggling, and LOD; and the older **`three-instanced-mesh`** (https://github.com/lume/three-instanced-mesh). Their existence is itself evidence that core `InstancedMesh` intentionally omits these features for baseline performance, leaving it to userland/plugins.
- Practical workarounds discussed across the ecosystem for voxel-instance transparency specifically: (1) CPU-side per-frame instance sort by camera-space depth, rewriting the instance matrix buffer in sorted order before each draw (expensive at scale — O(n log n) per frame plus a full buffer rewrite, the exact problem #27170 is trying to solve natively); (2) split transparent voxel types into their own, typically much smaller, non-instanced `Mesh`/`Group` so ordinary scene-graph transparency sorting (three.js sorts *objects*, not instances within an object, by default) applies; (3) Order-Independent Transparency (depth peeling / weighted-blended-OIT) to sidestep sorting entirely — see the community depth-peeling demo https://discourse.threejs.org/t/demo-order-independent-transparency-with-depth-peeling/88044 and long-standing proposal issue https://github.com/mrdoob/three.js/issues/9977; general discussion thread https://discourse.threejs.org/t/order-independent-transparency-oit/56765 (approaches surveyed there: alpha hashing, dithered/stochastic transparency, depth peeling/dual depth peeling, weighted-blended accumulation); (4) alpha-testing / alpha-to-coverage as a cheaper partial substitute — using `alphaTest` to fully discard below-threshold fragments avoids blend-order artifacts entirely for binary-transparency cases (e.g. leaves, foliage voxels) at the cost of no soft edges, referenced in https://r105.threejsfundamentals.org/threejs/lessons/threejs-transparency.html.

---

# 6. Instanced Rendering Specifics in three.js (raycasting, visibility, coplanar guidance)

## Raycasting `InstancedMesh` tests every instance up to `.count`
- Verified directly from source (`InstancedMesh.raycast`, `src/objects/InstancedMesh.js`, three.js `dev` branch, fetched 2026-07-10):
  ```js
  raycast( raycaster, intersects ) {
      const matrixWorld = this.matrixWorld;
      const raycastTimes = this.count;
      ...
      // test with bounding sphere first
      if ( this.boundingSphere === null ) this.computeBoundingSphere();
      _sphere.copy( this.boundingSphere );
      _sphere.applyMatrix4( matrixWorld );
      if ( raycaster.ray.intersectsSphere( _sphere ) === false ) return;
      // now test each instance
      for ( let instanceId = 0; instanceId < raycastTimes; instanceId ++ ) {
          this.getMatrixAt( instanceId, _instanceLocalMatrix );
          _instanceWorldMatrix.multiplyMatrices( matrixWorld, _instanceLocalMatrix );
          _mesh.matrixWorld = _instanceWorldMatrix;
          _mesh.raycast( raycaster, _instanceIntersects );
          ...
      }
  }
  ```
  There is exactly **one** early-out: a single bounding-sphere test against the *entire* `InstancedMesh` (all instances combined), computed once. If that sphere is hit, the loop then tests **every single instance from `0` to `.count`** individually against the ray with no further spatial acceleration (no per-instance bounding volume hierarchy, no octree) — confirming the commonly-reported behavior that raycasting a large `InstancedMesh` (e.g. tens of thousands of voxels) is O(n) per ray and can become a real bottleneck; this is the exact gap the `@three-ez/instanced-mesh` BVH-accelerated raycasting addresses (https://github.com/three-ez/instanced-mesh). Related community discussion: https://github.com/mrdoob/three.js/issues/17906 ("InstancedMesh how to use raycast for every instance?"), https://discourse.threejs.org/t/raycaster-with-instancedmesh/10028.

## Per-instance visibility: CPU-side rebuild is the documented/idiomatic pattern; shader discard is a known workaround
- There is **no built-in per-instance `.visible` flag** on `InstancedMesh` as of the versions surveyed — confirmed by the still-open feature request https://github.com/mrdoob/three.js/issues/22102 ("Add per-instance visibility support to InstanceMesh") and the broader tracking issue https://github.com/mrdoob/three.js/issues/30403 ("Add support for hiding, deleting, or managing individual instances in InstancedMesh").
- Documented/community-idiomatic patterns, per the three.js forum threads (https://discourse.threejs.org/t/how-to-show-and-hide-an-instance-in-instance-mesh/28198, https://discourse.threejs.org/t/invisible-instancedmesh-instances/27515, https://discourse.threejs.org/t/remove-or-making-instanced-mesh-invisible/31770):
  1. **Zero-scale trick**: `setMatrixAt(i, matrix.makeScale(0,0,0))` to collapse a hidden instance to a degenerate (invisible, non-rendering) triangle — simplest, keeps `.count` fixed, but wastes a raycast/vertex-shader iteration on every "hidden" instance since the loop above still visits it.
  2. **Swap-and-shrink `.count`**: swap the matrix of the instance you want to hide with the matrix at index `count - 1`, then decrement `InstancedMesh.count` by 1 (`InstancedMesh.count` docs: https://threejs.org/docs/#api/en/objects/InstancedMesh.count) — this is the pattern that actually reduces both draw and raycast work, at the cost of instance indices being unstable across hide/show operations (index `i` no longer maps to a fixed logical voxel).
  3. **Fragment-shader discard driven by a per-instance attribute**: pack a visibility flag into a custom `InstancedBufferAttribute` and `discard` in the fragment shader (or push instances off-screen via the vertex shader) when hidden — avoids CPU-side buffer rewrites/reordering, at the cost of GPU still doing vertex/rasterization work per hidden instance, referenced generally across the InstancedMesh forum threads as an alternative to CPU rebuilds for high-churn hide/show workloads.
- Given the raycast-and-render-loop both walk `0..count` with no gap-skipping, the swap-and-shrink `count` approach is the only one of the three that reduces per-frame *and* per-raycast cost, and is the pattern the `@three-ez/instanced-mesh` and `three-instanced-mesh` community libraries formalize and automate.

## Coplanar / z-fighting guidance for instanced voxel scenes
- No voxel-specific documented guidance was found beyond general three.js z-fighting practice, which does apply directly to instanced cube-grid scenes: (1) avoid literally coplanar geometry between two different draw calls/instances — z-fighting arises from depth-buffer precision limits, not from a InstancedMesh-specific bug; standard three.js remedies are `logarithmicDepthBuffer: true` on the renderer for scenes with large depth ranges, and/or `Material.polygonOffset` for cases where a second overlay pass must render at effectively the same depth as a base face (https://threejs.org/docs/#api/en/materials/Material.polygonOffset). (2) shadow acne on voxel-cube shadow casters (a related but distinct coplanar-adjacent artifact from self-shadowing) is addressed via `shadow.normalBias` / `shadow.bias` on the light, per https://discourse.threejs.org/t/shadow-acne-banding-what-i-learned/43666 and https://lucidmodules.com/blog/threejs/how-to-fix-shadow-acne/ — normal-bias pushes the shadow-map sample outward along the surface normal to avoid a face self-shadowing itself, conceptually parallel to (but a different mechanism from) the face-inset problem in §3: both are attempts to solve an adjacency artifact by nudging geometry/sampling, and both carry the standard trade-off that too large a bias visibly detaches the effect (a shadow that "floats" off the object, an inset that visibly recesses/cracks the face) from the true surface.

---

# Source URL List

## Hidden face culling / voxel geometry fundamentals
- https://threejs.org/manual/en/voxel-geometry.html
- https://threejs.org/manual/examples/voxel-geometry-culled-faces.html
- https://threejsfundamentals.org/threejs/lessons/threejs-voxel-geometry.html
- https://github.com/mrdoob/three.js/blob/dev/manual/en/voxel-geometry.html
- https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/
- https://maxogden.com/bringing-minecraft-style-games-to-the-open-web
- https://github.com/roboleary/GreedyMesh

## Transparent-voxel / glass culling rule
- https://minecraft.wiki/w/Opacity
- https://learn.microsoft.com/en-us/minecraft/creator/reference/content/blockcullingreference/examples/blockcullingrules/block_culling
- https://learn.microsoft.com/en-us/minecraft/creator/documents/voxelshapes
- https://engineersbox.github.io/website/2024/09/19/transparency-with-binary-greedy-meshing.html
- https://forum.godotengine.org/t/in-minecraft-the-faces-between-adjacent-blocks-are-culled-due-to-being-invisible-how-to-achieve-this/130345

## Greedy meshing / T-junctions
- https://0fps.net/2012/07/07/meshing-minecraft-part-2/
- https://fgiesen.wordpress.com/2011/07/06/a-trip-through-the-graphics-pipeline-2011-part-6/
- https://blackflux.wordpress.com/2014/02/23/meshing-in-voxel-engines-part-1/
- https://vercidium.com/blog/voxel-world-optimisations/
- https://vercidium.com/blog/further-voxel-world-optimisations/
- https://github.com/Vercidium/voxel-mesh-generation

## Block outlines / edge rendering
- https://threejs.org/docs/#api/en/geometries/EdgesGeometry
- https://discourse.threejs.org/t/how-to-render-geometry-edges/5745
- https://discourse.threejs.org/t/how-to-show-only-edge-lines/9724
- https://threejs.org/docs/#api/en/materials/Material.polygonOffset
- https://discourse.threejs.org/t/the-polygon-offset-is-not-correct-when-viewed-from-the-front/57631
- https://github.com/mrdoob/three.js/issues/2593
- https://discourse.threejs.org/t/polygonoffset-doesnt-work-for-wireframes/29538
- https://github.com/max-mapper/voxel-engine
- https://github.com/joshmarinacci/voxeljs-next
- https://medium.com/@deathcap1/6-years-after-6-months-of-voxel-js-a-retrospective-1e8a2eadeb0

## Instanced transparency and sorting
- https://github.com/mrdoob/three.js/issues/27170
- https://github.com/mrdoob/three.js/issues/4724
- https://github.com/three-ez/instanced-mesh
- https://www.npmjs.com/package/@three.ez/instanced-mesh
- https://github.com/lume/three-instanced-mesh
- https://discourse.threejs.org/t/demo-order-independent-transparency-with-depth-peeling/88044
- https://github.com/mrdoob/three.js/issues/9977
- https://discourse.threejs.org/t/order-independent-transparency-oit/56765
- https://r105.threejsfundamentals.org/threejs/lessons/threejs-transparency.html

## Instanced raycasting, per-instance visibility, coplanar guidance
- https://github.com/mrdoob/three.js/blob/dev/src/objects/InstancedMesh.js (raycast source, `dev` branch, fetched 2026-07-10)
- https://github.com/mrdoob/three.js/issues/17906
- https://discourse.threejs.org/t/raycaster-with-instancedmesh/10028
- https://github.com/mrdoob/three.js/issues/22102
- https://github.com/mrdoob/three.js/issues/30403
- https://discourse.threejs.org/t/how-to-show-and-hide-an-instance-in-instance-mesh/28198
- https://discourse.threejs.org/t/invisible-instancedmesh-instances/27515
- https://discourse.threejs.org/t/remove-or-making-instanced-mesh-invisible/31770
- https://threejs.org/docs/#api/en/objects/InstancedMesh.count
- https://discourse.threejs.org/t/shadow-acne-banding-what-i-learned/43666
- https://lucidmodules.com/blog/threejs/how-to-fix-shadow-acne/

# Open Questions

- The Minecraft-specific "same block type only" glass culling rule versus the more general "any transparent voxel culls any other transparent voxel" simplification (used by e.g. the EngineersBox binary-greedy-meshing writeup) is a real design fork; worth deciding explicitly for this project rather than assuming Minecraft's exact behavior.
- No primary source was found that names the "epsilon inset causes corner notches" failure mode explicitly in voxel-engine literature — the explanation given in §3 is derived directly from the watertight-rasterization rule (ryg blog) rather than quoted from a source that discusses cube-face insetting specifically. If a citable source for this exact failure mode surfaces later, it should be added.
- Barycentric single-pass wireframe shaders and screen-space edge-detection outlines are described from general graphics knowledge/practice; no specific voxel-engine implementation URL was located during this pass and could be searched further if the project wants to adopt one of these instead of the `EdgesGeometry` overlay approach.
- Did not deeply verify three.js `r180`-specific behavioral changes beyond confirming current `dev`-branch source; if the project pins an older three.js version, the `InstancedMesh.raycast` source should be re-checked against that exact tag since the sorting/BVH gap has been an active area of proposals (#27170, #27168) that could land in a future release.
