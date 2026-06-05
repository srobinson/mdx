# Scout B: shape / smooth corners / materials (render + instancing)

Read-only scout of the rendering and instancing path for cube shape, smooth corners, and materials. Domain and command side owned by Scout A.

**Central risk (verified in code, not only docs):** PR #116 fixed program recreation on capacity growth. The danger for per-edge or per-cube shaping is reintroducing material churn or unbounded program-cache keys, especially under “every cell a distinct shaping signature.”

---

## Reuse Map

### Reuse

**Owner of the instanced mesh lifecycle**

| Role | Path | Symbol |
|------|------|--------|
| Capacity bands (power of two) | `src/scene/instancedMeshCapacity.ts` | `resolveGeometricInstanceCapacity`, `growInstancedMeshCapacity` |
| Mesh create / grow / sync / patch / dispose | `src/scene/instancedPartMeshCore.ts` | `createInstancedPartMesh`, `createInstancedPartMeshWithGeometry`, `growInstancedPartMesh`, `syncInstancedPartMesh`, `patchInstancedPartMesh`, `disposeInstancedPartMesh` |
| React mesh identity (capacity captured once) | `src/scene/InstancedPartMesh.tsx` | `InstancedPartMesh` (`initialCapacity` via `useRef(capacity).current`) |
| Edge coverage mesh + custom shader | `src/scene/edgeCoverageCore.ts` | `createEdgeCoverageMesh`, `syncEdgeCoverageMesh`, `patchEdgeCoverageMesh` |
| Edge coverage React layer (same grow path) | `src/scene/EdgeCoverageLayer.tsx` | `EdgeCoverageLayer` |
| Selection chrome grow | `src/scene/selectionChromeMeshCore.ts` | `syncSelectionChromeMesh` → `growInstancedPartMesh` |
| Slot packing / buckets | `src/scene/cubeInstanceSlots.ts` | `cubeInstanceBucketNames`, `resolveCubeInstanceBuckets` |
| Instance payloads (matrix, color, opacity) | `src/scene/cubeInstances.ts` | `createCubeCellInstances`, `collectCubeSceneInstances` |
| Scene composition | `src/scene/CubeScene.tsx` | `CubeScene` mounts `InstancedPartMesh` + `EdgeCoverageLayer` |
| Incremental owner (not domain persistence) | `src/scene/useCubeSceneInstances.ts`, `src/scene/incrementalCubeSceneOwner.ts` | `useCubeSceneInstances`, `createIncrementalCubeSceneOwner` |

**Growth path symbols (in order)**

1. `InstancedPartMesh` / `EdgeCoverageLayer` / `syncSelectionChromeMesh` call `growInstancedPartMesh(mesh, requiredSlotCount)`.
2. `growInstancedPartMesh` → `growInstancedMeshCapacity` → `resolveGeometricInstanceCapacity`.
3. Within band: publishes capacity mutation with `reason: "retain"`, returns `false`, no buffer swap.
4. Band cross: clones geometry, `resizeCapacityBoundGeometryAttributes`, reassigns `mesh.geometry` / `mesh.instanceMatrix` / `mesh.instanceColor`, same `InstancedMesh` object, **never reassigns `mesh.material`**, publishes `reason: "grow"`, returns `true` so callers full-sync slots.

**Code confirmation that mesh and material are retained on growth** (not docs):

- `growInstancedPartMesh` mutates the existing `InstancedMesh` in place. It never constructs a new mesh or `new MeshBasicMaterial`.
- `mesh.dispose()` only fires Three’s dispose event / morphTexture path (`node_modules/three/src/objects/InstancedMesh.js` `InstancedMesh.dispose`); it does **not** dispose material or geometry. Geometry is disposed separately after clone; material is left on the mesh.
- Unit gate: `tests/selectionChromeMeshCore.test.ts` “grows once across a capacity band without replacing mesh or material” asserts `state.mesh === mesh` and `mesh.material === material`.
- Unit gate: `tests/incrementalSceneReactMeshHandoff.test.tsx` “retains mesh buffers within one geometric capacity band” / “grows once across a band…” asserts same mesh identity and same material for part and coverage meshes.
- Browser gate: `tests/incrementalScene.browser.test.ts` “keeps live GPU resources flat across capacity bands and reuse cycles” asserts `stableMeshIdentities: true`, `stableMaterialIdentities: true`, and `createdPrograms: 0` on band crossing (`runGpuCapacityBrowserGate` in `tests/incrementalSceneBrowserDriver.tsx` via `observeCapacityEvents` + `observeWebGlResources`).

**What varies PER INSTANCE today**

| Channel | Mechanism | Writer | Notes |
|---------|-----------|--------|--------|
| Pose / size | `InstancedMesh.instanceMatrix` | `writeMatrix` → `mesh.setMatrixAt` | Faces: unit `PlaneGeometry` scaled in matrix. Edges: unit `BoxGeometry` scaled in matrix (`createCubeCellInstances`). |
| Colour | Three `instanceColor` (`InstancedBufferAttribute`, itemSize 3) | `writeColor` → `mesh.setColorAt` | Lazy-created by Three on first `setColorAt`. Patched with dirty ranges via `markInstancedBufferSlotsDirty`. |
| Opacity (translucent buckets only) | Custom geometry attribute `instanceOpacity` | `writeOpacity` / `applyInstanceOpacity` | Requires `material.onBeforeCompile` + **fixed** `customProgramCacheKey` `"cubicell-instance-opacity"`. |
| Edge axis (coverage overlay only) | Custom attribute `instanceEdgeAxis` | `syncEdgeCoverageMesh` / `patchEdgeCoverageMesh` | Same pattern: `onBeforeCompile` + fixed key `"cubicell-edge-coverage-v2"`. |

Colour is **not** a uniform and not a material property. Opaque face/edge colour is pure instanced attribute (`setColorAt`). Selection chrome uses material.color as a uniform-style material prop (`SelectionChromeLayer`), which is mesh-wide, not per instance.

**Buckets today (each is its own mesh + material family):** opaqueFaces, translucentFaces, opaqueEdges, translucentEdges, ghostFaces, ghostEdges, edgeHitTargets, plus EdgeCoverageLayer (opaque edges), selection chrome, neighbor slots. Geometry kinds: `plane` (faces) vs `box` (edges/slots). Materials: always `MeshBasicMaterial` from `createInstancedPartMeshWithGeometry`.

### Existing infra that maps cleanly to shaping

1. **Per-instance float/vec attribute + fixed program cache key** — proven by `applyInstanceOpacity` and `createEdgeCoverageMesh`. Growth already resizes all `InstancedBufferAttribute`s on the geometry via `resizeCapacityBoundGeometryAttributes`.
2. **Patch path** — `patchInstancedPartMesh` attribute set model (`"matrix" | "color" | "opacity"`) is the extension point for a new attribute name if domain supplies it.
3. **Capacity / program gates** — `observeWebGlResources` + `runGpuCapacityBrowserGate` already assert zero program creation across growth.

### Similar checked and rejected (for “distinct mesh per signature”)

- **Capacity as mesh identity** — historically broke programs (PERFORMANCE.md P1 / #116). Code now freezes identity in `useMemo` deps minus capacity. Do not reintroduce capacity (or shape signature) into mesh identity keys.
- **New material per growth** — would drop program cache refcounts and recompile. Growth deliberately keeps material.
- **Uniform radius on one shared material** — works only if **all** instances share one treatment; cannot express per-cube signatures without splitting meshes.
- **Discrete geometry variants without a bucket plan** — each variant needs its own `InstancedMesh` (and usually its own material). Continuous “every cell distinct” signatures explode into one mesh per cell → reintroduces the program recreation problem at scale.

### None found + searches run

- No `RoundedBoxGeometry`, no corner-radius field on `CubeFaceInstance` / `CubeEdgeInstance`, no shaping signature type in `src/scene/`.
- Grep: `RoundedBox|cornerRadius|edgeTreatment|shapingSignature|bevel` under `src/` → no render-side hits (only UI CSS radius and structural “corners” in edge claim geometry).
- Searches: `growInstancedPartMesh`, `resolveGeometricInstanceCapacity`, `setColorAt`, `instanceColor`, `customProgramCacheKey`, `onBeforeCompile`, `createdPrograms`, `observeWebGlResources`.

---

## Quality Map

### Duplication

- `InstancedPartMesh` and `EdgeCoverageLayer` duplicate the same grow/patch/sync control flow. Acceptable thin wrappers; any new per-instance attribute should land in `instancedPartMeshCore` (or a shared helper used by both), not a third copy.
- Capacity logic correctly lives once in `instancedMeshCapacity.ts`.

### Boundary issue

- **Program cache keys are global strings** (`instanceOpacityProgramKey`, `edgeCoverageProgramKey`). Any new shader family must use one stable key per shader text, never a key that embeds per-instance or per-radius values.
- **Geometry clone on grow** creates/deletes GPU buffers (allowed and gated). It must never create materials or change `customProgramCacheKey`.
- Translucent path already pays **one extra program family** vs opaque. A shaping shader should either (a) live in both opaque and translucent materials with two fixed keys, or (b) be designed so opacity and radius share one compiled family.

### Dead code

- None specific to this path. `observeInstancedPartMeshMutations` is test/driver instrumentation, not dead.

### Grooming recommendation

- If shaping lands: extend `InstancedPart` + write/patch attribute set in one place (`instancedPartMeshCore`), mirror the opacity attribute lifecycle, and extend the browser GPU capacity gate with a “distinct shaping signature” scenario that asserts `createdPrograms === 0` after fill and after band cross.
- Do **not** add timing assertions; headless Chromium is SwiftShader (counts only).

---

## Plan

### Decision needed

**Can per-cube corner radius / edge treatment ride the existing per-instance mechanism?**

**Yes, if and only if** treatment is encoded as **instanced buffer data** (and optionally shader math), with **stable material identity** and a **fixed** `customProgramCacheKey`. That matches colour (`setColorAt`) and opacity (`instanceOpacity`).

**No**, if treatment is encoded as **distinct geometry meshes or distinct materials per signature**: under “every cell a distinct shaping signature” that becomes unbounded mesh/material families and reopens #116-class program recreation.

### Option costs (Three program-cache terms)

Do not pick a winner on elegance; costs only.

| Option | What it is | Program-cache cost | Buffer / mesh cost | Fits “every cell distinct signature”? |
|--------|------------|--------------------|--------------------|----------------------------------------|
| **A. Instanced attribute + shader** | e.g. `instanceCornerRadius` `InstancedBufferAttribute`; `onBeforeCompile` deforms or softens; **one** `customProgramCacheKey` string (pattern of `applyInstanceOpacity` / edge coverage) | **O(1) compiles per material family** at first use of that material (opaque + translucent if both need it). Growth: **0** new programs if material retained (same as today). Changing radius values: **0** recompiles (attribute upload only). | Resize existing instanced attrs on band cross (buffers yes, programs no). | **Yes** for continuous float params. |
| **B. Geometry variants keyed by treatment** | Discrete rounded boxes / chamfer meshes; bucket instances by treatment signature into separate `InstancedMesh`es | **O(V)** programs where V = number of variant×family pairs (each mesh’s material compiles once). Growth per mesh: 0 programs if materials retained. **Unbounded V** if signatures are continuous or per-cell unique → program count tracks V, and React remount of many meshes recreates materials → programs thrash. | O(V) meshes, O(V) geometries. Band growth multiplies buffer churn by V. | **Only for small fixed discrete set.** Fails the named worst case. |
| **C. Rounded-box geometry + uniform radius** | Shared unit rounded geometry; `material.uniforms.radius` or single morph | **O(1)** program if shader uses fixed cache key; **0** if pure baked geometry with no shader change. | One mesh family. | **No** for per-cube: one uniform is mesh-wide. Per-cube would require option A or B. |
| **D. SDF / shader-side rounding** | Fragment or vertex SDF / smoothmin driven by instanced attrs (and/or matrices) | Same as A: **O(1)** fixed-key program family; growth **0** programs. Heavier fragment work (not measurable under SwiftShader). | Attribute buffers only. | **Yes** for continuous params. |

**Forced distinct geometry or materials?** Only option B (or a mistaken implementation that keys materials by radius). Options A and D ride the existing instanced-attribute + fixed-key material pattern. Option C does not support per-instance variation.

### Proposed steps (bound to reuse map)

1. **Domain handoff (Scout A):** add a numeric or discrete treatment field that can land on `InstancedPart` without new mesh identity keys.
2. **Render path:** extend `createInstancedPartMeshWithGeometry` / `applyInstanceOpacity`-style helper to attach treatment attributes; extend `write*` + `patchInstancedPartMesh` attribute set; ensure `resizeCapacityBoundGeometryAttributes` already covers new instanced attrs (it does for any `InstancedBufferAttribute` on geometry).
3. **Shader:** one fixed `customProgramCacheKey` per family; never encode radius into the key.
4. **Do not** put treatment into `InstancedPartMesh` `useMemo` deps in a way that recreates the mesh; capacity is already frozen in a ref for this reason.
5. **Edges vs faces:** faces are planes, edges are boxes + coverage overlay. Shaping that changes silhouette may need both resolved edge boxes and `edgeCoverageCore` shader awareness; coverage currently assumes hard box cross-section (`instanceEdgeAxis` projection).

### Tests and gates

| Gate | Path | What it asserts |
|------|------|-----------------|
| Program + buffer counts | `tests/webGlResourceObserver.ts` → `observeWebGlResources` | `createdPrograms`, `deletedPrograms`, live `programs` / `buffers` |
| Browser acceptance (exists) | `tests/incrementalScene.browser.test.ts` “keeps live GPU resources flat…” | Within band: all zeros; band cross: buffers churn, **`createdPrograms === 0`**, live resources flat; cycles: no growth |
| Mesh/material identity | `tests/incrementalSceneReactMeshHandoff.test.tsx`, `tests/selectionChromeMeshCore.test.ts` | Same mesh + same material across band |
| Counter that catches program-recreation regression | **`createdPrograms`** (delta and/or live `programs` size) from `observeWebGlResources().snapshot()` | Already asserted `=== 0` on band crossing in the GPU capacity browser gate |

**Measurement to settle option 3 empirically**

1. Build a browser driver scenario that fills the scene so **every live cell has a distinct shaping signature** (worst case named in the brief).
2. Snapshot `observeWebGlResources` after first paint → record `createdPrograms` / live `programs`.
3. Mutate radii without adding cells → assert **`createdPrograms` delta is 0**.
4. Cross a capacity band (add cells past next power of two) → assert **`createdPrograms` delta is 0**, buffers may rise, `stableMaterialIdentities` true (reuse `observeCapacityEvents` pattern in `incrementalSceneBrowserDriver.tsx`).
5. **Do not** assert frame time or GPU ms: headless Chromium uses SwiftShader; **acceptance gates in this repo are COUNTS, never timings.** Any proposal that needs a timing gate is invalid for CI here (flag for local GPU profiling only).

### Flag: timing gates

Any option whose only success criterion is “smoother at 60 fps” or “cheaper SDF” cannot be gated in this suite. Gate **program counts**, **live program/buffer counts**, and **material/mesh identity**. Fragment cost of SDF (option D) is a local profiler concern, not a SwiftShader acceptance gate.
