# Shape-shader spike archaeology

**Scope:** worktree `.claude/worktrees/shapes`, branch `spike/shape-shader` at `0aac4a2`. Read-only. Not merged to `main`.

**Adjacent product intent (from the brief, not from this branch):** cube FACE carrying an imported form (SVG mark as mask/alpha) through cubicell colour roles. This report separates that from what the spike actually built.

**Commits on the spike tip (not on main):**

| SHA | Subject |
| --- | --- |
| `b3bc35e` | `spike(scene): measure shader edge shaping` |
| `2bfdfc4` | `spike(scene): drive shaped edges by hand in the running app` |
| `0aac4a2` | `feat(editor): add cube edge shape controls` |

---

## 1. What was actually built?

**Mechanism:** per-instance **vertex-stage cross-section deformation** of **edge box instances** (and the matching edge-coverage overlay). Not geometry generation per signature, not a fragment/SDF disc, not a texture or alpha channel, not corner-rounding of a solid cube mesh. Cubicell has no cube-body mesh; edges are unit boxes scaled by instance matrix; the shader remaps the box cross-section in the plane perpendicular to the long axis.

**How it works in one pass:**

1. Edge meshes use a fixed subdivided unit box (`BoxGeometry` with 8 segments per axis) so the vertex stage has enough verts to bend the silhouette.
2. Two `InstancedBufferAttribute`s carry per-edge form: treatment index and size.
3. `MeshBasicMaterial.onBeforeCompile` injects GLSL that, under `USE_INSTANCING`, detects the long axis from `instanceMatrix` scale, then mixes the square cross-section toward a circle-like profile (round) or a chamfer scale (chamfer), weighted by `instanceShapeSize`.
4. The edge coverage overlay reuses the same attributes and recomputes screen-space half-width for round/chamfer so minimum CSS-pixel thickness tracks the shaped silhouette.
5. Domain fields `treatment` / `shapeSize` ride `CubeEdgeState` through the existing `set-edge-state` path; the Shape panel tab binds them.

**Entry points (file + symbol):**

| Role | Symbol |
| --- | --- |
| Shader inject + attrs | `src/scene/edgeShapeShader.ts` — `applyEdgeShapeShader`, `createEdgeShapeBoxGeometry`, `writeEdgeShapeAttributes`, `getEdgeShapeAttributes`, `edgeShapeAttributeNames`, GLSL `edgeShapeTransform` / `edgeShapeDeclarations` |
| Mesh wiring | `src/scene/instancedPartMeshCore.ts` — `createInstancedPartMesh` (uses shaped box when `partKind === "edge"`), `applyEdgeShapeShader` call, sync/patch of `"shape"` |
| Coverage co-shape | `src/scene/edgeCoverageCore.ts` — `createEdgeCoverageMesh` (chains shape compile, then coverage projection that reads `instanceShapeSize` / `instanceShapeTreatment`) |
| Instance payload | `src/scene/cubeInstances.ts` — edge instances copy `edgeState.shapeSize` / `edgeState.treatment` |
| Slot diff | `src/scene/instanceSlotRegistry.ts` — attribute `"shape"` when treatment/size change |
| Domain | `src/domain/cubeEdgeState.ts` — `edgeShapeTreatments`, fields `shapeSize` and `treatment` on `cubeEdgeStateOwner` (`renderAttribute: "shape"`) |
| Editor | `src/editor/controlBindings.ts` — `cube.edgeTreatment`, `cube.edgeShapeSize`; `src/panels/CubeSection.tsx` Shape tab |
| Measurement harness | `tests/shapeShaderSpikeBrowserDriver.ts` — `mountShapeShaderSpike`, `renderShapeShaderSpikeMode`; `tests/shapeShaderSpike.browser.test.ts` |

**Program cache:** fixed key fragment `cubicell-edge-shape-v1` appended in `applyEdgeShapeShader`; values never enter the key (same discipline as opacity / coverage).

---

## 2. How did form get in?

**Authored form:** parameters only. No path, SVG, SDF field, or raster.

| Input | Representation | Where |
| --- | --- | --- |
| Treatment | Discrete enum `"sharp" \| "round" \| "chamfer"`, encoded as index 0/1/2 on the instance attribute | `edgeShapeTreatments` / `cubeEdgeStateOwner.fields.treatment` |
| Size | Continuous float, UI clamp 0..1, default 0 | `shapeSize` field + `instanceShapeSize` |
| Geometry base | Fixed subdivided box mesh (shared by all edge instances in a bucket) | `createEdgeShapeBoxGeometry` |
| Deformation | Analytic GLSL in the vertex stage (squircle-ish circle mix; L1-style chamfer scale) | `edgeShapeTransform` in `edgeShapeShader.ts`; mirrored half-width math in `edgeCoverageCore.ts` coverage projection |

**Relevance to face marks:** this spike never imported external form. There is no mask, alpha map, or face-plane shape attribute. Faces remain unit `PlaneGeometry` without the edge shape program (`createInstancedPartMesh` only applies `applyEdgeShapeShader` when `partKind === "edge"`). Shaping a cube edge and marking a face do **not** share a form pipeline on this branch; they only share the broader instancing/attribute pattern if a face mark later uses per-instance floats or textures the same way colour/opacity do.

---

## 3. What broke, and is the evidence on the branch?

### Evidenced on the branch

| Fact | Evidence |
| --- | --- |
| GPU program churn under distinct per-instance signatures **did not** occur | Browser gate `tests/shapeShaderSpike.browser.test.ts` expects `radiusMutationCreatedPrograms: 0` and `bandCrossingCreatedPrograms: 0`. Artifact `~/.mdx/projects/cubicell-s0-silhouettes/measurement.json` records both zeros, `capacityBefore: 16` → `capacityAfter: 32`, and non-zero buffer creation on band cross. |
| Silhouette screenshots were captured for round, chamfer, mixed, and coverage-only | Same harness writes under `~/.mdx/projects/cubicell-s0-silhouettes/`; driver labels modes as distinct per-instance size. |
| Throwaway global spike store was intentionally deleted when production fields landed | Commit `2bfdfc4` message orders deletion of `edgeShapeSpike.ts` and call sites once treatment/shapeSize travel on edge state; `0aac4a2` removes those files and wires domain + Shape tab. LESSONS adds: “A spike must leverage existing tested owners… Remove its parallel stores… when the production path lands.” |
| Branch is complete enough to look like a feature path, yet is not on `main` | `main` has no `src/scene/edgeShapeShader.ts`. On `main`, `TYPOGRAPHY.md` still says approved `treatment` / `shapeSize` remain absent. |
| Pre-spike design on main rejected **fragment** SDF rounding for a different reason | `docs/superpowers/specs/2026-07-12-negative-space-tooling-design.md` (present on this worktree as well): “Shader/SDF rounding was rejected: per-edge control in a fragment shader is painful and fights edge-line rendering and picking.” Preferred path in that doc: geometry variants keyed by shape signature. This spike **did not** implement that preferred path; it implemented the attribute+vertex path Scout B had argued for in external notes. |

### Not recorded on the branch

- **No abandon note, spike log verdict, LESSONS entry, commit message, TODO, or deleted-test trail states why `spike/shape-shader` was left unmerged.**
- **No branch text declares silhouette failure or “shapes settled in the negative.”** The measurement that was supposed to settle mechanism choice (decision sheet outside the repo: counts + eye judgment) has **passing counts** on disk; the eye judgment is not written into the branch.
- Therefore: **why the shapes question was settled negative is not evidenced by this branch.** Inferring a single root cause from the owner’s oral summary alone would invent history. Adjacent product memory (not branch) is noted only under §Notes.

### What the spike code itself treats as success criteria

The browser test asserts program flatness and that screenshots exist above 5 KB. It does **not** assert visual quality, rounded-solid correctness, or face/edge co-registration.

---

## 4. Does it collide with instancing?

**No. The spike was built to prove the opposite, and the recorded numbers agree.**

Cubicell edges already instance through `instancedPartMeshCore` (same family as faces/slots). Shape rides the same pattern as opacity and coverage:

- Per-instance attributes (`instanceShapeTreatment`, `instanceShapeSize`), not per-instance materials or programs.
- Fixed `customProgramCacheKey` (`…:cubicell-edge-shape-v1`).
- Growth resizes attributes with capacity bands; material identity retained (`growInstancedPartMesh` path).
- Patch path supports attribute set `"shape"` without rewriting matrix/color/opacity.
- Worst-case harness: mixed treatments, distinct sizes per instance, capacity 16→32; **0** programs created on value mutation and on band cross.

**Not hit (no evidence of):** uniform/attribute slot exhaustion, per-instance texture limits, draw-call explosion from shape, or program-cache key pollution by signature.

**Implication for per-instance per-face variation:** the **mechanism class** (instanced buffer + fixed program key + patch ranges) is the safe lane this codebase already trusts. The edge shape **shader body** is edge-axis / box-cross-section specific and does not transfer to face masks.

---

## 5. What is reusable vs avoid?

### Bind to / reuse

| Asset | Why |
| --- | --- |
| `applyEdgeShapeShader` pattern (attrs + `onBeforeCompile` + fixed key) | Proven zero-program growth under distinct signatures |
| `cubeEdgeStateOwner` field descriptors (`renderAttribute: "shape"`, morph channels) | Single owner for codec, validation, morph, impact (post-#148) |
| `instanceSlotRegistry` `"shape"` attribute and dirty-range patching | Incremental update path already wired |
| Coverage co-awareness in `edgeCoverageCore` | Screen-thickness floor must track any silhouette change on edges |
| Browser measurement pattern (`observeWebGlResources` + capacity band cross) | The right CI gate for any new instanced shader family |
| ControlBinding + Shape tab path for authored `set-edge-state` | Production spine after throwaway spike removed |

### Deliberately avoid

| Trap | Why |
| --- | --- |
| Encoding shape values or signatures into `customProgramCacheKey` or React mesh identity | Reopens #116-class program recreation; LESSONS and Scout B both forbid it |
| Geometry variants per continuous signature without a bounded registry | Design doc’s option B; O(V) meshes/programs under “every cell distinct” |
| Parallel ephemeral writers (global spike store) next to domain state | Explicitly deleted; LESSONS forbids keeping them after production lands |
| Assuming edge deformation alone owns cube silhouette / organic fillet | Topology on this product is 6 face planes + 12 edge bars with no corner mesh; face planes stay square unless separately shaped. That is architecture, not a failed compile. |
| Reusing `edgeShapeTransform` math for face SVG/mask work | Wrong primitive (box cross-section vs plane fill/mask). Reuse the **instancing contract**, not the GLSL. |
| Fragment SDF as the default for per-edge treatment | Already rejected in the negative-space design doc for picking and edge-line conflict |

---

## Cube shape vs face mark (brief boundary)

| | Spike (this branch) | Adjacent ask (face form) |
| --- | --- | --- |
| Target part | Edge bars | Face planes |
| Form source | Enum + float parameters | Imported SVG as mask/alpha |
| Colour | Existing edge colour roles | Cubicell roles instead of SVG fills |
| Shared? | Instancing + attribute/program discipline | Possible reuse of plumbing |
| Shared form pipeline? | **No** on this branch | — |

---

## Notes outside the branch (labeled, not used as abandon proof)

These are **not** commit history. They sit under `~/.mdx/projects/` and interpret product constraints after the spike existed:

- `cubicell-shapes-decision-sheet.md`: settling criterion was “counts pass **and** acceptable silhouette”; counts path is what the spike automated; silhouette judgment left to eye.
- `cubicell-theory-signature.md`: “Faces own the silhouette… edge treatment cannot create a truly rounded solid… reads cleanly only through `shapeSize` 0.4.”
- `cubicell-theory-capability-audit.md`: lists edge shape deformation as ALREADY (instancing preserved); face-owned silhouette that filleted edges cannot round as KNOWN-WORK.

If the owner’s “settled in the negative” refers to **true rounded cubes / organic fillets via edge-only shader deformation**, that reading matches the theory notes and the product topology, **not** a failing test or crash on this branch. If it refers to **instancing or program cache**, the branch evidence contradicts that: those gates passed.

---

## Bottom line for the adjacent face-mark work

1. **Failed mechanism for “full cube reshape” is not a broken GPU path;** the branch never records a mechanism crash. What the code implements is **edge ink cross-section**, which cannot redefine face mass.
2. **Instancing is not the wall** for per-instance variation; it is the proven success of this spike.
3. **Do not rebuild edge shape GLSL for face SVG masks.** Reuse `InstancedBufferAttribute` + fixed program key + patch discipline if the face mark needs per-instance parameters; form import and mask sampling are a new pipeline.
4. **Branch does not record why it was left unmerged.** Treat “negative” as owner judgment about product fit of edge-only shaping for solid form, unless a later written decision appears on main.
