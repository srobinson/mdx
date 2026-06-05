# Face-mark scout: reuse map

**Worktree:** `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/mark`  
**Branch / tip:** `feat/face-mark` @ `7d5e942` (`main` after PR #163 merge; content identical to prior `a708397` accent tip)  
**Staged forms:** `assets/marks/helioy.svg`, `assets/marks/manicure.svg` (untracked under worktree)  
**Scope:** read-only reuse map. No implementation.

**Carried forward from shape-shader archaeology** (`~/.mdx/projects/cubicell-shape-shader-archaeology.md`, branch `spike/shape-shader` @ `0aac4a2`):

- Mechanism was **edge** vertex cross-section deformation, not face form.
- Instancing wall: **none**. Fixed `customProgramCacheKey` + instanced attributes + patch ranges is the proven lane.
- Edge shape GLSL is the **wrong vehicle** for face marks. Reuse the **contract**, not the shader body.
- Edge-only shaping cannot own cube silhouette (faces own mass). Face marks attach to that mass layer.

**Governing product rule (brief, owner):** import form only, never appearance. Mark supplies partition geometry; cubicell supplies roles and polarity rails.

---

## Reuse Map

### 1. Where form can live on a face

**Per-face state owner today**

| Piece | Symbol | Notes |
| --- | --- | --- |
| State type | `src/domain/cube.ts` — `CubeFaceState` | `{ color, opacity, visible }` only |
| Defaults | `defaultCubeFaceState` | `color: defaultCubePartColor` (`"theme"`) |
| Mutators | `setCubeFaceState`, `setAllCubeFacesState` | Patch merge on one face or all faces |
| Operation | `src/domain/cubeOperations.ts` — `set-face-state` with `Partial<CubeFaceState>` | Same spine as edges; no new op kind needed for extra fields |
| Render impact | `src/domain/authoredRenderImpact.ts` — `changedFaceAttributes`, `CubeFaceRenderAttribute` | Currently `"burial" \| "color" \| "opacity" \| "visibility"`; mark fields need a new attribute (e.g. `"mark"`) |
| Aspects | `src/domain/selectionAspects.ts` — `areFaceStatesEqual` | Hand equality on three fields |
| Inheritance | `inheritCubePartStyle` | Copies face `color` only; opacity/visible reset |

There is **no** `createCubeFaceStateOwner` table. Edges have `src/domain/cubeEdgeState.ts` — `cubeEdgeStateOwner` / `defineCubeEdgeStateField` (codec, morph, renderAttribute in one place). Faces still use hand lists.

**Codec that persists face state**

| Piece | Symbol |
| --- | --- |
| Sparse compact wire | `src/persistence/recordCodecs/compactPose.ts` — `CompactFace = [faceIndex, colorIndex, opacity, visibleBit]`; encode/decode in `encodeCell` / `decodeCell`; `sameFace` sparsens defaults |
| Color as index | `cubePartColors.indexOf(face.color)` / `cubePartColors[color]` — same closed vocabulary as edges; accent is index 3 |
| Hydration allowlist | `src/state/workbenchValidation/pose.ts` — `isCurrentFaceState` `hasOnlyKeys(..., ["color", "opacity", "visible"])`; unknown keys **reject** the pose |
| Project asset kinds | `src/domain/project.ts` — `ProjectAssetKind = "animation" \| "structure"` only |
| Binary asset store | `src/persistence/storageRecordTypes.ts` — `StoredAssetBytes`; IndexedDB assets keyed by projectId+assetId (`indexedDbCommit`, `loadIndexedDbAsset`) — structure/animation documents today, not arbitrary mark blobs |

**Honest persistence options for a mark reference**

| Option | Shape | Fits accent pattern? | Cost |
| --- | --- | --- | --- |
| **A. Index into closed mark registry** | Face holds `mark: number` (0 = none) or enum id; registry is app-bundled (`helioy`, `manicure`, …) | **Yes** — same as `cubePartColors` index on the wire | Honest for shipped demos; wrong for open user import at scale |
| **B. Id reference off the pose** | Face holds `markId: string \| null`; form bytes live in a mark library / asset store; compact face stores id or null, not pixels | Matches project “reference + payload elsewhere” (pose revisions already hang off assets) | Needs a home for bytes (new asset kind, or a non-`ProjectAssetKind` mark store). `ProjectAssetKind` is closed today |
| **C. Inline form in face state** | Embed path data or base64 mask in pose | No | Bloats every State/pose; fights sparse `CompactFace`; do not |
| **D. Hybrid** | Registry index for built-ins **or** id for imports; one face field that is a tagged ref | Practical product shape | One codec branch; still keeps form off the compact colour tuple |

**Recommendation:** face state carries a **reference**, not form bytes: tagged `markRef` (registry index for closed set, or asset/id for imports) plus authored fit and role slots (below). That is the accent-shaped choice for **identity of form**, with the important difference that accent’s **payload** is a theme token, while a mark’s payload is geometry that must live outside `CompactFace`.

Also author on the face (not in the SVG):

- **figure / ground roles** (each a `CubePartColor`)
- **fit** (margin vs bleed: scale/offset or padding mode)
- **polarity pin** (follow rails vs pin figure/ground so a rail swap cannot invert a negative mark)

Wire: extend sparse face tuple or nest a compact mark sub-tuple; bump schema; reset (pre-release rule). Validation allowlist must grow or the document will fail reload.

---

### 2. The render path

**Today’s face path (file + symbol)**

1. Domain planes: `src/domain/cubeGeometry.ts` — `createCubeFacePlanes` (colour, opacity, size, pose from cell).
2. Instances: `src/scene/cubeInstances.ts` — `CubeFaceInstance` `{ color, opacity, faceId, matrix, … }`; burial skip via `context.buriedFaces`.
3. Buckets: `src/scene/cubeInstanceSlots.ts` — `opaqueFaces` / `translucentFaces` / `ghostFaces`.
4. Layers: `src/scene/renderCubeScenePartLayers.tsx` — `partKind="face"`, `geometryKind` plane.
5. Mesh core: `src/scene/instancedPartMeshCore.ts` — unit `PlaneGeometry`, `MeshBasicMaterial`, `setColorAt` / `instanceColor`, optional `instanceOpacity` when translucent.
6. Colour resolve: `resolveInstanceColor` → `resolvePartColor` / `colorSpace.ts` → `theme/scenePolarity.ts` — `resolveCubePartColor` + workbench `faceLightnessDeltaById`.

**One RGB per instance.** There is no second region, no UV-driven mask, no texture on face materials.

**Where a two-region partition hooks in**

| Layer | Hook | Collision |
| --- | --- | --- |
| Domain | Extend `CubeFaceState` + impact `"mark"` | Face field shotgun (see Quality) |
| Instance payload | Extend `CubeFaceInstance` with mark ref, figure/ground roles, fit, pin | Slot registry attribute set must learn `"mark"` (or split attrs) |
| Colour write | **Cannot** stay as single `resolveInstanceColor` → `setColorAt` alone | Two roles need two resolved colours; `instanceColor` can carry figure **or** be abandoned for dual attrs |
| Fragment program | New fixed-key `onBeforeCompile` family on face materials: sample partition form, mix figure/ground roles | New program family (opaque + translucent if both need it); must not key by mark id |
| Form GPU resource | Shared texture(s) / atlas keyed by mark identity | **If each distinct mark gets its own material.map**, materials and programs multiply → #116-class thrash. Must share one shader family and bind form by atlas UV / texture array index / bind-once atlas, with **instance attrs** for which mark + fit |
| Buckets | Optional: unmarked faces stay on current path; marked faces a parallel fixed material family | Cleaner than one mega-shader if unmarked majority; still O(1) program families |

**Shape-shader reuse (concrete)**

| From archaeology | Right vehicle for face marks? |
| --- | --- |
| Fixed `customProgramCacheKey` string | **Yes** — mandatory. Pattern already on this branch: `applyInstanceOpacity` (`instanceOpacityProgramKey`) |
| Instanced float/vec attributes + capacity resize + patch dirty ranges | **Yes** — for mark index, fit, figure/ground **role indices**, polarity pin bit |
| Vertex box cross-section GLSL (`edgeShapeShader` on shapes branch) | **No** — different primitive; not present on this worktree tip |
| Edge coverage co-shape | **No** — face marks do not drive edge thickness coverage |
| Browser `createdPrograms === 0` gate | **Yes** — extend with “many faces, many mark refs, mutate roles/fit, cross capacity band” |

**Faces need something shape-shader did not:** a **form resource** (partition field) sampled in the **fragment** stage. That is new machinery. The instancing contract still applies: form identity is data (atlas slot / shared texture), not material identity.

---

### 3. SVG to form

**Requirement from the two files (not relitigated)**

| File | Form nature | Naive single-alpha failure |
| --- | --- | --- |
| `helioy.svg` | Two solid black paths, coarse, margin in viewBox | Reads as positive form if alpha = filled paths |
| `manicure.svg` | Black field with face carved (path spans full square; identity in lashes/strokes); bleed | Single-alpha of “black coverage” yields a **filled square**; detail dies if ground is discarded |

Form is a **partition of the face into two regions** plus **role assignment**. Fit is authored (margin vs bleed).

**Representation options (costs only; no converter design)**

| Representation | Manicure / lash detail | Instancing fit | Codebase today |
| --- | --- | --- | --- |
| **Raster partition mask** (one channel: 0 ground / 1 figure, or signed) | Preserves lashes if resolution ≥ stroke width in face UV | One atlas or texture array; instance UV fit attrs | **None found** in app code |
| **SDF / multi-channel distance** from that partition | Thin strokes survive moderate res better than binary alpha under minification | Same GPU bind pattern as raster | **None found** |
| **Path / polygon geometry** (tessellate SVG → mesh) | Poor for hair-width features; even-odd field-as-ground is painful; two regions need two meshes or CSG | Extra instances or dynamic geo → signature explosion risk | **None found** in src; `three/examples/jsm/loaders/SVGLoader.js` exists in node_modules only |
| **Coverage / stroke expand** | Wrong model for filled field marks | — | Edge coverage is screen-thickness for **bars**, not face fills (`edgeCoverageCore`) |

**Searches run (src + tests):** `Texture`, `CanvasTexture`, `DataTexture`, `alphaMap`, `SVGLoader`, `SDF`, `msdf`, `createImageBitmap`, `ImageData`, `face-mark`, `markId`, `partition` — **no face-mark or SVG→GPU pipeline in application code.** UI SVG in `StructureSliceLayer` is chrome only. Dependencies: `three` present; no sharp/skia/potrace.

**Codebase lean:** GPU is unlit instanced `MeshBasicMaterial` + attribute inject (`applyInstanceOpacity`). Closest mental model is **fragment modulate by data**, not path extrusion. For manicure, the codebase therefore leans toward a **raster (or SDF-from-raster) partition texture** shared across instances, not live SVG path meshes.

**Recommendation:** **partition mask (raster, optionally SDF-encoded) as the runtime form**; SVG is import source only. Threshold and figure/ground authorship at import time so manicure’s field is ground and carved face is figure (or explicit author override). Detail budget = mask resolution vs face pixel footprint; that is a product constant later, not a scout invent.

---

### 4. Role collision

**Shipped vocabulary:** `src/domain/cubeEdgeState.ts` — `cubePartColors = ["theme", "black", "white", "accent"]`.

**Resolution:** `resolveCubePartColor` in `src/theme/scenePolarity.ts`:

- `"theme"` → `polarity.contrast` (inverts with polarity)
- `"black" | "white" | "accent"` → `polarity.partColors[…]` (accent has dual rails: `themeColorTokens.accent` / `accentOnLight`)

**Does the vocabulary serve mark regions directly?**

**Yes, as the type of each side.** Figure and ground should each be a `CubePartColor`. No need for a second colour universe or SVG fills.

**Does one face `color` field suffice?**

**No.** A marked face is a **pair of roles** plus form. Keeping a single `color` and overloading it loses ground (or figure). Unmarked faces keep today’s single `color`; marked faces need:

| Slot | Type | Why |
| --- | --- | --- |
| `figure` | `CubePartColor` | Region 1 |
| `ground` | `CubePartColor` | Region 2 (including “empty” reading via theme/black/white choice) |
| polarity pin / follow | discrete | Brief: pin so rail swap cannot turn negative portrait into positive. Absolute black/white pairs pin naturally; pure `theme` pairs invert. Pin is **policy**, not a fifth colour name |

Optional: leave `CubeFaceState.color` as the unmarked fill / fallback when `markRef` is none, so the unmarked path stays one `setColorAt`.

**Answer to the orchestrator’s phrasing:** **needs own slots** (figure + ground, still typed with the existing vocabulary), **not** a new closed colour union. Existing vocabulary **suffices for role values**; face state **needs two role slots** (and pin/fit/ref) beyond today’s single `color`.

**Polarity interaction (product, not code today):**

- Positive mark (helioy): figure=`theme` or `accent`, ground=`black` (or transparent-as-face-under) often fine under follow.
- Negative mark (manicure): figure/ground must stay a stable partition under rail flip → prefer absolute plate roles and/or explicit pin mode.

---

### 5. Quality map

| Issue | Evidence | Disposition |
| --- | --- | --- |
| **Face field shotgun** | Equality: `areFaceStatesEqual`, `sameFace`; impact: `changedFaceAttributes`; wire: `CompactFace` / `isCompactFace`; validation: `isCurrentFaceState` allowlist; inherit: manual colour copy | **Refactor first:** extract `cubeFaceStateOwner` mirroring `cubeEdgeStateOwner` before adding mark fields, or every new field lands in five places again. Edges already paid this tax (#148). |
| **No texture/mark pipeline** | Searches above empty | **New path** during build; not dead code |
| **Single-colour instance assumption** | `resolveInstanceColor` + `setColorAt` only | Boundary change during mark render; document that marked faces leave the one-RGB model |
| **Material-per-mark trap** | Growth keeps material identity; accent/opacity already fixed keys | **Avoid** during design; gate with program counts |
| **Face vs edge owner asymmetry** | Edges table-driven; faces hand-written | Same as first row |
| **Project asset kinds closed** | `ProjectAssetKind` | **Defer** expanding to `"mark"` until import-as-asset is required; registry index unblocks demos |
| **Shape-shader branch not on this tip** | mark worktree has no `edgeShapeShader.ts` | Do not couple face-mark PR to unmerged edge shape |
| **Thumbnail silent drop** | Thumbnails share instance derivation but not live-only chrome; mark must live in that shared path or posters omit form | **During:** land mark on `createCubeSceneInstances` + `instancedPartMeshCore`, not a canvas-only branch |
| **Morph single-colour face** | `sceneMorph.createPartColorTweens` reads only `cell.faces[faceId].color`; face opacity lerps; no mark channel | **During:** discrete-cut for mark ref/roles/pin; decide whether figure/ground tween like colour |

**Grooming recommendation:** **refactor first** on face state ownership (descriptor owner + single equality/codec/impact derivation), **during** for render dual-role + mask family + morph/thumbnail, **defer** open mark asset kind until two shipped SVGs prove the runtime.

---

## Plan

### Decision needed

1. **Runtime form:** partition mask (raster/SDF) vs path meshes — scout recommends **mask**; confirm.
2. **Persistence of form identity:** registry index only (v1 demos) vs hybrid id+registry — recommend **hybrid-ready schema, registry-first implementation**.
3. **Face colour model when marked:** replace `color` with figure/ground, or keep `color` for unmarked and add mark block — recommend **keep `color` for unmarked; mark block optional**.
4. **Polarity pin representation:** explicit enum vs “only absolute roles pin” convention — needs owner call; brief requires pin capability.
5. **Face state owner extraction** before fields vs during — recommend **before**.

### Ordered steps (bound to reuse map)

1. **Refactor:** `cubeFaceStateOwner` in domain (fields: color, opacity, visible); point compact pose, validation, aspects, impact, inherit at it. Tests: round-trip + allowlist. (Reuse edge owner pattern in `cubeEdgeState.ts`.)
2. **Domain mark block:** `markRef` (none | registry index), `figure`, `ground`, `fit`, `polarityPin`; defaults = no mark. `set-face-state` already carries patches. Impact attribute `"mark"`.
3. **Wire + validation:** sparse encode mark only when present; schema bump + reset; `hasOnlyKeys` / owner validation.
4. **Import offline (not live SVG on GPU):** convert staged SVGs to partition masks with authored figure/ground semantics for helioy vs manicure; store in mark registry assets under `assets/marks/` (or build-time pack). No converter architecture in this scout — only the requirement that manicure is not single-alpha-of-black.
5. **Render:** fixed-key face mark shader family; instance attrs for roles/fit/ref; shared atlas/texture bind; unmarked faces stay on current path. Hook in `cubeInstances` → `InstancedPart` → mesh core so **thumbnails inherit automatically**. Reuse `applyInstanceOpacity`-style inject and capacity resize. **Do not** use edge vertex deformer.
6. **Colour:** resolve figure and ground through `resolveCubePartColor` + existing lightness deltas; respect pin. Artifact polarity (`scenePolarities`) for thumbs/export; workbench deltas only on canvas.
7. **Morph:** extend face morph so mark ref/roles/pin cut discretely; colour tweens remain on `color` (and optionally figure/ground if product wants role morph).
8. **Controls:** face-scoped bindings beside existing `face.color` / `face.opacity` / `face.visible` (`controlBindings.ts`, `panelDefinitions.ts` face list); still `set-face-state`.
9. **Gates:** unit codec/aspects; browser GPU program flatness across many marked faces and capacity band; thumbnail PNG fixtures for both SVGs under both polarities with pin on/off; delivery budget for atlas.

### Tests and gates

| Gate | What |
| --- | --- |
| Compact pose | Marked + unmarked faces; default sparseness; accent still index-stable |
| Validation | Unknown face keys rejected; mark block accepted |
| `resolveCubePartColor` | Figure/ground under both polarities; pin freezes negative reading |
| Render impact | Mark field changes produce `"mark"` not full false rebuilds beyond design |
| GPU | `createdPrograms === 0` on role/fit mutation and capacity cross (shape-shader lesson) |
| Visual | helioy margin + manicure bleed/detail; polarity flip with pin |
| Thumbnail | Same poses through `createThumbnailArtifact`; marks visible without a second renderer path |
| Budget | Face shader family size; atlas weight in delivery budget |

---

## Residual pass (post #163 merge @ `7d5e942`)

Confirmed tip is `main` / `feat/face-mark` at `7d5e942`. Untracked only: `assets/marks/*`. No new bus mail on `cubicell-mark-scout`.

### Accent PR as the colour-role template

#163 touched a small, closed set: `cubePartColors` append, polarity `partColors` exhaustive maps, `themeTokens` accent rails, control enum options, compact index round-trip test, budget rebaseline. **Do not invent a parallel colour system for marks;** add face slots typed with that vocabulary the same way.

### `CubeFaceState` blast radius (consumers that must learn mark fields)

| Layer | Symbols / files |
| --- | --- |
| Domain type + mutators | `cube.ts` — `CubeFaceState`, `defaultCubeFaceState`, `setCubeFaceState`, `setAllCubeFacesState`, `inheritCubePartStyle`, `mapCubeFaces` |
| Ops | `cubeOperations.ts` `set-face-state`; `cubeCellOperations.ts`; `sceneOperationMaterialization.ts` |
| Wire | `compactPose.ts` `CompactFace` / `sameFace` / `isCompactFace` |
| Validation | `workbenchValidation/pose.ts` `isCurrentFaceState` / `isFaceState`; face patch via op validation (`set-face-state` uses face patch keys, edges use owner `isPatch`) |
| Impact | `authoredRenderImpact.ts` `changedFaceAttributes` / `CubeFaceRenderAttribute` |
| Aspects / similar | `selectionAspects.ts` `areFaceStatesEqual`, `faceStateDistance`; `selectionQuery` / `selectionCompile` face-state predicates |
| Editor | `controlBindings.ts` `face.color` / `face.opacity` / `face.visible`; `panelDefinitions.ts` face binding ids |
| Scene | `cubeGeometry.createCubeFacePlanes`; `cubeInstances` face loop; `instancedPartMeshCore.resolveInstanceColor` |
| Morph | `sceneMorph.ts` face opacity lerp; `createPartColorTweens` on **single** `faces[id].color` |
| Exposure / edges | `exposure.ts`, `edgeClaimResolution.ts` read face visibility/opacity for burial and claims — mark form should not break those unless product says so |
| Thumbnail | `thumbnailArtifact.createThumbnailArtifact` → `createCubeSceneInstances` + `createInstancedPartMesh` + `syncInstancedPartMesh` with **`scenePolarities`** (artifact rails, no workbench face lightness ramp) |
| Export recording | Canvas/studio capture only (`streamRecorder`); no separate face bake. Marks appear if the live/shared renderer draws them |

**Not a second colour path:** export/recording rides the canvas; thumbnails ride the **same instance + mesh core**. Mark implementation that only patches the live React layers will leave State posters blank of form.

### Thumbnail / artifact polarity detail

- Live workbench: `workbenchScenePolarities` + `faceLightnessDeltaById` on faces.
- Thumbnails: `scenePolarities` only (`thumbnailArtifact.ts`), so authored plate colours without workbench compression.
- Mark role resolve must use the polarity config **passed into** `syncInstancedPartMesh`, not hardcode workbench tokens, or thumbs and canvas diverge.

### Morph policy note

Face `color` already colour-tweens across states. Mark **form** and **pin** should discrete-cut (like edge treatment). Figure/ground role changes can either tween (reuse `PartColorTween` twice) or cut; product call. Leaving mark off morph entirely would flash at the cut, which is acceptable if documented.

### Limits still open

- Did not run the app or browser tests.
- Did not inventory every test fixture hardcoding four-tuple face wire shapes (grep will find them when fields land).
- Shape-shader code remains only on `spike/shape-shader`; lessons only.

---

## Bottom line

| Question | Answer |
| --- | --- |
| Form on face | Reference on `CubeFaceState`; form bytes off pose |
| Persist as | Registry index (accent-shaped) first; id hybrid when imports land |
| Form representation | Partition mask (raster/SDF); SVG is source only |
| Roles | Existing `CubePartColor` vocabulary; **own figure/ground slots** + polarity pin |
| Instancing | No wall if form is shared data + fixed program key; wall if material-per-mark |
| Biggest risk | Treating mark as single-alpha texture or material-per-mark, which kills manicure or program cache |
