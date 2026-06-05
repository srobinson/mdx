# Face stencil spike: scout and plan

**Base:** `main` @ `7d5e942` (clean; `stencil-scout` worktree at same tip)
**Scope:** read-only reuse and quality map plus bounded delivery plan. No repository writes.
**Inputs consolidated:** the four face-mark reports (`cubicell-face-mark-{scout,authoring,domain,render}.md`), re-verified symbol by symbol against the current tip via fmm and rg. Vocabulary follows the domain report: the asset is a **Stencil**, the face field is **figure**; "mark" and "ground" are retired ("ground" collides with `FloorGridChrome`'s ground grid).

Every owner below was confirmed to exist at `7d5e942`. Two drifts from the older reports, both verified: morph now lives at `src/evaluation/sceneMorph.ts` (not `src/scene/`), and the face instance payload is the generic `instancedPartMeshCore.ts:InstancedPart` (`color`, `colorTween?`, `displayOpacity`, `faceId?`, `matrix`), not a `CubeFaceInstance` type.

---

## Reuse map

For each capability: the owning symbol, who writes, who reads, which writer wins.

### 1. cubeFaceState

| Piece | Owner |
| --- | --- |
| Type | `src/domain/cube.ts:CubeFaceState` — `{ color, opacity, visible }` |
| Defaults | `cube.ts:defaultCubeFaceState` (`color: defaultCubePartColor` = `"theme"`) |
| Writers | `cube.ts:setCubeFaceState`, `setAllCubeFacesState`, `inheritCubePartStyle` (copies face `color` only), `mapCubeFaces` |
| Command spine | `src/domain/cubeOperations.ts:set-face-state` with `Partial<CubeFaceState>`; `applyCubeOperation` fans the patch across the resolved scope. No new op kind needed |
| Precedence | Single writer path: every mutation flows through `set-face-state` → `setCubeFaceState`/`setAllCubeFacesState`. `inheritCubePartStyle` writes only at cube growth. No precedence conflict today; the stencil block must enter through the same patch or it creates the second-writer defect |

There is **no** face state owner table. That is the central structural fact (see quality map).

### 2. Edge field ownership (the template)

`src/domain/cubeEdgeState.ts:createCubeEdgeStateOwner` is already generic (`<const Fields extends Record<string, AnyCubeEdgeStateField>>`); nothing in it is edge-specific. Each `defineCubeEdgeStateField` entry declares `decode`, `defaultValue`, `encode`, `inherit`, `isEncoded`, `isValue`, `morphChannel`, `renderAttribute`, and the owner generates `isState`, `isPatch`, `encode`, `decode`, `areEqual`, `distance`, `matches`, `getMorphChanges`, `interpolateMorph`, `inherit`, `changedRenderAttributes`. Morph channels: `"color-tween" | "discrete-cut" | "numeric-lerp"`.

One gap, confirmed: `areEqual` compares `===` per key. An object-valued stencil block needs an optional `equals` on `CubeEdgeStateField`. Small, additive.

### 3. Library persistence

| Piece | Owner |
| --- | --- |
| Aggregate | `src/domain/workbench.ts:Workbench` (root), `Library` — `{ animations, states, structures }`; a `stencils` roster is the fourth array |
| Asset kinds | `src/domain/project.ts:ProjectAssetKind` — `"animation" | "structure"`, closed; gains `"stencil"` |
| Roster enumeration | `workbench.ts:getProjectAssetRoster` |
| Codecs | `src/persistence/recordCodecs/structureRecordCodec.ts`, `animationRecordCodec.ts`, `poseRevisionRecordCodec.ts` — the pattern a `stencilRecordCodec` follows |
| Binary bytes | `src/persistence/storageRecordTypes.ts:StoredAssetBytes` (IndexedDB via `indexedDbCommit.ts`) — the home for imported stencil bytes later; v1 registry is build-time and needs none of it |

Domain report conditions carried forward: content-address the stencil id (lost entries re-bind on re-import), keep the roster inside `Library` so the face reference stays intra-aggregate, and render absence as an explicit unresolved state, never a silent plain face.

### 4. Face pass, atlas, texture observation

| Piece | Owner |
| --- | --- |
| Face mesh | `src/scene/instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` (unit plane, `MeshBasicMaterial`); writes owned by `syncInstancedPartMesh` / `patchInstancedPartMesh` |
| Shader hook precedent | private `instancedPartMeshCore.ts:applyInstanceOpacity` — owns `material.onBeforeCompile` and `customProgramCacheKey` (`"cubicell-instance-opacity"`) on translucent meshes. The stencil hook **must compose** with it; a second assignment silently removes one behavior |
| Live path | `cubeInstances.ts:createCubeCellInstances` → `incrementalCubeSceneOwner.ts:createCellEntry` → `cubeInstanceSlots.ts:createCubeInstanceSlotOwner` → `instanceSlotRegistry.ts` → `patchInstancedPartMesh` |
| Texture code today | **None.** `rg "Texture" src/` is empty; no atlas, no `DataTexture`, no SVG→GPU pipeline anywhere in application code |
| GPU observation | `tests/webGlResourceObserver.ts:observeWebGlResources` counts **buffers and programs only** (`LiveGpuResources` has no texture field). Must grow texture counts before an atlas gate can mean anything |

Render report decision stands: one R8 2048² atlas (sixteen 512² slots), one packed `vec4` instance attribute (figure RGB + tile index, negative = no stencil), fixed program keys (e.g. `cubicell-face-stencil-v1` plus a fixed composed translucent key), applied at mesh construction even when no face carries a stencil. `instanceColor` remains the uncovered region (`color` keeps its name and meaning). A variant per stencil is a defect.

### 5. Face bindings

| Piece | Owner |
| --- | --- |
| Binding ids | `src/editor/controlBindings.ts:ControlBindingId` — `face.color`, `face.opacity`, `face.visible`; `faceColorBinding` is the template; `resolvePartEditScope` already gives multi-face stamping |
| Panel list | `src/panels/panelDefinitions.ts:faceBindingIds`; hosts `PartSection.tsx:FaceSection` mounted by both `Inspector.tsx` and `SelectorPanel.tsx` — new rows appear in both for free |
| Schema limit | `ControlValueSchema` enum options are **static**, and `ControlBindingContext` carries no library. A build-time registry keeps the stencil picker a static enum; the day stencils become document data, options must derive from context — the one place the machinery does not already bend |

Authoring surface: `face.stencil` (None/Helioy/Manicure), `face.figure` (Form/Field), `face.figureColor` (the existing `partColorOptions` — this **is** the polarity pin: `theme` follows rails, `black`/`white`/`accent` pin), `face.stencilFit` (Margin/Bleed). All Segmented rows via `ControlBindingField`, all writing `set-face-state`.

### 6. Transitions

| Piece | Owner |
| --- | --- |
| Cut vs morph | `src/domain/stateTransition.ts:resolveTransitionKind`, `defaultTransition`, `TransitionPatch` |
| Morph engine | `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology` / `sampleSceneMorph`; face colour tween via `createPartColorTweens.faces`; carried on `instancedPartMeshCore.ts:InstancedPart.colorTween` |
| Stencil policy | Ref/figure/fit ride `morphChannel: "discrete-cut"` (exists, costs nothing). No coverage-crossfade channel exists; `scoreAt.ts:Moment` carries part colour tweens only. Crossfade is out of scope and stated, not discovered |

### 7. Codecs

| Piece | Owner |
| --- | --- |
| Face wire | `src/persistence/recordCodecs/compactPose.ts:CompactFace` — positional `[faceIndex, colorIndex, opacity, visibleBit]`; `sameFace` sparsens defaults; `isCompactFace` guards. Edges encode via `cubeEdgeStateOwner.encode` — faces will too once the owner exists |
| Colour as index | `cubePartColors.indexOf` / append-only vocabulary (`cubeEdgeState.ts:cubePartColors`); the figure role rides the same closed index |
| Hydration allowlist | `src/state/workbenchValidation/pose.ts:isCurrentFaceState` — `hasOnlyKeys(["color","opacity","visible"])`; unknown keys **reject the pose**. Must grow in the same slice as the field |
| Migration rule | None. Schema bump + Reset (`LESSONS.md`, no-migrations rule). But note the domain report's distinction: a dangling stencil reference is content absence under an unchanged schema — the reset rule does not cover it; content addressing and explicit unresolved rendering do |

### 8. Selection matching

`src/domain/selectionAspects.ts:attributeAspects["face-state"]` hand-writes `match` (`candidate.color === reference.color && candidate.visible === reference.visible` + `faceStateDistance`), while `"edge-state"` binds `cubeEdgeStateOwner.matches` / `.distance`. A stencil field forgotten here compares unequal faces as equal and the selection language silently lies — a silent bug, not a type error. Owner extraction closes this class. `selectionSubjects` stays `["cube","face","edge"]`; a figure region is never independently selectable (aggregate condition #1 from the domain report).

### 9. Render impact

`src/domain/authoredRenderImpact.ts:CubeFaceRenderAttribute` is the hand union `"burial" | "color" | "opacity" | "visibility"`, while `CubeEdgeRenderAttribute` derives from the owner. Needs `"stencil"`, ideally by derivation after the owner refactor. Downstream, `src/scene/instanceSlotRegistry.ts:InstanceSlotAttribute` is `"axis" | "color" | "matrix" | "opacity"` — a stencil edit needs its own attribute classification or the incremental path retains stale GPU data.

### 10. Thumbnail and artifact rendering

`src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` → `createCubeSceneInstances` + `createInstancedPartMesh` + `syncInstancedPartMesh` with **`scenePolarities`** (artifact rails; no `faceLightnessDeltaById`, which is workbench-only per `scenePolarity.ts:ScenePolarityConfig`). Two verified traps:

- Thumbnail face meshes are created **without** `partKind: "face"` while `renderCubeScenePartLayers.tsx` sets it — a shader selected only through `partKind` disappears from thumbnails. The face mesh construction contract must be shared.
- Thumbnails run a separate WebGL context: CPU atlas bytes shared, GPU texture uploaded per context.

Export (`src/export/streamRecorder.ts:createRecordingController`) captures the workbench framebuffer, so it inherits the stencil for free once the live pass draws it. There is no second colour path to build.

### 11. Six-face orientation

`src/domain/cubeTopology.ts:cubeFaceTopology` owns each face's `axis`, `positionSign`, `rotation`, `sizeAxes` (front/back `[0,1]`, left/right `[2,1]`, top/bottom `[0,2]`). Those Euler rotations define each face's UV frame: back is front rotated π about Y, top/bottom rotate about X so texture "up" maps to ±world-z. **No UV convention is authored anywhere** — nothing today cares which way a face's texture points, because nothing has ever textured a face. This is the killed-feature risk from the authoring report: every automated gate passes and manicure on a side face reads sideways or mirrored. Countermeasure is a decision, not a control: fix one screen-readable per-face UV convention in `cubeFaceTopology` terms, hand-verify manicure on all six faces before judging the surface, hold a 0/90/180/270 rotation enum in reserve.

---

## Quality map

| # | Finding | Evidence | Disposition |
| --- | --- | --- | --- |
| 1 | Face vs edge owner asymmetry: six hand-written face sites (equality, distance, tolerance, encode, decode/guard, default-compare) that the edge owner generates | `selectionAspects.ts:attributeAspects["face-state"]`, `compactPose.ts:CompactFace`/`sameFace`/`isCompactFace`, `pose.ts:isCurrentFaceState`, `cube.ts:inheritCubePartStyle`, vs `cubeEdgeState.ts:cubeEdgeStateOwner` | **Refactor first.** Extract `cubeFaceStateOwner` from the existing generic factory before any stencil field lands, or the new field lands in six places and a missed one is a silent bug |
| 2 | Owner `areEqual` is `===` per key; stencil block is object-valued | `cubeEdgeState.ts:createCubeEdgeStateOwner` | **During slice 1:** optional `equals` on `CubeEdgeStateField`, required for the stencil entry |
| 3 | Four independent face fields would make invariant "figure iff stencil" unexpressible | domain report §3 | **Reuse shape:** one optional value object `stencil?: { stencilId; figure; fit }`; presence is one decision |
| 4 | Polarity pin field = second polarity authority against scene-level `Pose.polarity` (`compactPose.ts:CompactPose.p`) | domain report §3 | **Deviate-avoided:** no pin field. Pin is expressed through the figure colour role (`black`/`white` pin, `theme` follows), per authoring report |
| 5 | No texture pipeline, no atlas, no SVG→GPU code | `rg "Texture" src/` empty | **New path** during render slice; not dead code |
| 6 | GPU observer blind to textures | `tests/webGlResourceObserver.ts:LiveGpuResources` | **Refactor during:** add texture counts before the atlas gate; a gate that cannot see the resource it guards proves nothing |
| 7 | Thumbnail face mesh omits `partKind: "face"` | `thumbnailArtifact.ts:createThumbnailArtifact` vs `renderCubeScenePartLayers.tsx` | **Refactor during render slice:** shared face mesh construction so thumbnails inherit the stencil program by construction |
| 8 | Material-per-stencil trap (#116-class program thrash) | `applyInstanceOpacity` fixed-key precedent | **Avoid by design:** fixed keys, identity as instance data + atlas tile; gate `createdPrograms === 0` across stencil edits and capacity bands |
| 9 | `ProjectAssetKind` closed; no import UI exists anywhere | `project.ts:ProjectAssetKind`; authoring report search | **Defer** open import; v1 registry is build-time from `assets/marks/` (currently only in the `mark` worktree, untracked — must be committed by the build slice) |
| 10 | Stencil picker does not fit static enum schema once registry is document data | `controlBindings.ts:ControlValueSchema`, `ControlBindingContext` | **Defer:** static enum is honest while the registry is build-time; note the seam, do not widen the context now |
| 11 | Six-face UV orientation unauthored | `cubeTopology.ts:cubeFaceTopology` | **During + prove:** fix the convention deliberately; manicure-on-all-six-faces is the acceptance test no automated gate replaces |
| 12 | Workbench tonal compression vs artifact rails could make authored contrast drift on export | `scenePolarity.ts:workbenchScenePolarities` vs `scenePolarities` | **Prove:** one deliberate hand check of a stencilled face workbench vs thumbnail/export; resolve both roles through the polarity config passed into `syncInstancedPartMesh`, never hardcoded tokens |

Dead paths: none found bearing on this feature. Shape-shader code (`edgeShapeShader.ts`) exists only on `spike/shape-shader` @ `0aac4a2`; reuse its **contract** (fixed key, instanced attrs, capacity resize, zero-program gate), not its body. Face stencil must not couple to that unmerged branch.

---

## Bounded delivery plan

Slices are independently testable and ordered so each builds only on merged owners. Decisions the orchestrator/owner must record before slice 2: (a) UV convention accepted after the six-face hand check, (b) default figure colour role (recommend Field defaults pinned `black`, Form defaults `theme`), (c) `Stencil`/`figure` naming confirmed, (d) registry-first persistence confirmed.

1. **Face state owner (refactor, no behavior change).** Extract `cubeFaceStateOwner` via `createCubeEdgeStateOwner` (rename factory to `createCubePartStateOwner` or reuse as-is), add optional `equals` to the field descriptor. Point `compactPose`, `pose.ts` validation, `selectionAspects` face aspect, `authoredRenderImpact` face attributes, and `inheritCubePartStyle` at it; delete the six hand-written sites. Gate: unit round-trip + controlled red proving a mismatched field fails equality/codec.
2. **Domain stencil block.** One optional table entry `stencil?: { stencilId, figure, fit }` with `morphChannel: "discrete-cut"`, `renderAttribute: "stencil"`, `inherit: true`; defaults absent. Rides `set-face-state` unchanged. Gate: owner-generated equality/matches/impact cover the block; tolerance query distinguishes stencilled faces.
3. **Library + wire.** `StencilAsset` roster on `Library`, `ProjectAssetKind` + `"stencil"`, content-addressed ids, `stencilRecordCodec` beside the structure/animation codecs; sparse `CompactFace` extension encoded only when present; schema version bump + Reset; validation allowlist growth. Gate: encode/decode round-trip, unknown-key rejection, unresolved reference renders declared-unresolved (unit).
4. **Import offline.** Build-time SVG → R8 partition mask (512² tile) for the two staged assets with authored figure/field semantics (manicure is **not** single-alpha-of-black); commit `assets/marks/`. Gate: mask topology assertions (three foreground components for manicure at 512).
5. **Render.** R8 atlas + packed `vec4` instance attribute in `createInstancedPartMeshWithGeometry`; hook composes with `applyInstanceOpacity` under fixed keys; writes in `syncInstancedPartMesh`/`patchInstancedPartMesh`; `InstanceSlotAttribute` + `changedAttributes` learn `"stencil"`; unify thumbnail face mesh construction; extend `webGlResourceObserver` with texture counts. Gates: `createdPrograms === 0` across stencil edits and capacity bands; pinned buffer/texture counts; tile-scoped upload bound; both roles resolved through the supplied `ScenePolarityConfig`.
6. **Bindings.** Four rows appended to `faceBindingIds` + `ControlBindingId`; static enums; multi-face stamping via existing scope resolution. Gate: binding read/write unit tests incl. mixed-set read.
7. **Prove.** Manicure on all six faces by hand (orientation), workbench vs thumbnail vs export contrast check, Chromium pixel goldens for both stencils at thumbnail scale, workbench scale, close zoom, DPR 4, both polarities; delivery budget re-baselined at zero headroom for `shared-renderer` and `default-interactive`. Live UX gate before merge per standing rule (canvas-adjacent feel).

**Out of scope, stated:** polarity pin field, stencil crossfade morphs, import UI, dynamic binding options, multiple atlas pages (declare the sixteen-slot ceiling; eviction policy comes with imports).
