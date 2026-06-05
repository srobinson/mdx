# Scout: rounded cubes as a perimeter style ("shell")

Scouted by Fable (`cubicell:general:3:3.1`), 2026-08-17. Read only.
Branch `feat/renderer-relief` (PR #180), 3 commits on `main` (`ea9a2ff`, `c66d79a`, `f51a660`), HEAD `f51a660`.
Authority: `~/.mdx/projects/cubicell-decisions-shell-perimeter.md` (D1 to D10, O1 to O3).
Citations: `main:` means `git show main:<path>`; `HEAD:` means the branch working tree. Unprefixed symbols are unchanged between the two.

Worktree note: `tests/contracts/zz-scratch-shared-edge.contract.test.ts` is untracked and not mine (a reviewer's repro of finding 1). It must not ride into the PR.

## Reuse Map

One entry per capability. For each: owning symbol, writers, readers, which writer wins today, and what the reframe binds to.

### (a) Uniform edge colour and opacity as the shell colour source (D3)

| Item | Owner | Writes | Reads | Wins today |
| --- | --- | --- | --- | --- |
| Uniform part colour | `src/domain/cube.ts:getCubeUniformPartColor` | none (derived, pure) | `src/editor/cubeControlBindings.ts:cubeColorBinding.read` (HEAD; `main:src/editor/controlBindings.ts` before the split) | n/a |
| Siblings | `cube.ts:getAverageCubeEdgeThickness`, `cube.ts:getAverageCubeFaceOpacity` | none | `cubeControlBindings.ts:cubeEdgeThicknessBinding`, `cubeFaceOpacityBinding` | n/a |
| Whole-cube colour write | `src/domain/cubeCellOperations.ts:applyCubeOperationToCell` case `set-cube-color` (sets every edge and face colour) | reducer path | render via `cell.edges[id].color` / `cell.faces[id].color` | single writer |
| Edge colour at render | `src/scene/cubeInstances.ts:createCubeCellInstances` reads `edge.color` from the survivor `CubeEdgeSegment` (`src/domain/cubeGeometry.ts:createCubeEdgeSegments` copies `cell.edges[id].color`) | | `instancedPartMeshCore.ts:writeColor` | |
| Edge lightness cue | `src/scene/instancedPartMeshCore.ts:createColorWriteContext` (`partKind === "edge"` on main; HEAD already adds `"body"`) | | `writeColor` → `shiftLightnessForContrast` | |
| Body colour on HEAD | `HEAD:src/domain/cubeBodyState.ts` field `frameColor` (reuses `cubeEdgeStateOwner.fields.color`), read at `HEAD:cubeInstances.ts:createCubeCellInstances` (`color: cell.body.frameColor`), tweened at `HEAD:src/evaluation/sceneMorph.ts:createPartColorTweens` (`body`) | `applyCubeBodyStylePatch` | render, morph, snapshot | second colour owner for the perimeter: the defect D3 removes |

Facts that constrain D3:

- `getCubeUniformPartColor` spans faces **and** edges. There is no edges-only uniform helper. Searches: `rg getCubeUniform|getUniformPart|UniformEdge src` → only `getCubeUniformPartColor`. So "uniform edge colour" is **none found** as a symbol; the nearest owner is `getCubeUniformPartColor` and its home `cube.ts` (395 lines, room for one sibling `getCubeUniformEdgeColor` next to `getAverageCubeEdgeThickness`).
- Edge opacity per edge lives on `cubeEdgeStateOwner.fields.opacity`; there is no uniform edge opacity helper either (`getAverageCubeFaceOpacity` is the face precedent). Shell today is always opaque (`HEAD:cubeInstances.ts` body instance `stateOpacity: 1`).
- Colour tween: `sceneMorph.ts:createPartColorTweens` produces `edges: Map<CubeEdgeId, PartColorTween>`; `HEAD` adds a `body` tween keyed on `frameColor`. Under D3 the shell tween must derive from the edge tweens (see open decision A2).
- `createColorWriteContext` already treats `partKind "body"` like `"edge"` for `edgeLightnessDelta`: **reuse as is**; it is the exact "shell colour is edge colour" rule at the material.

### (b) Edge claim resolution and where a shell cell forfeits (D6)

| Item | Owner | Writes | Reads | Wins today |
| --- | --- | --- | --- | --- |
| Authored segments per cell | `src/domain/edgeClaimResolution.ts:createCellAuthoredEdgeSegments` (wraps `cubeGeometry.ts:createCubeEdgeSegments(cell, {includeHidden: true})`) | full: `createAuthoredEdgeSegmentIndex`; incremental: `src/domain/incrementalEdgeResolution.ts:indexCellClaims` | `collectEdgeClaimGroups`, `createEdgeClaimGroup` | single owner, both paths |
| Claims | `edgeClaimResolution.ts:createEdgeClaimIndex` / `createEdgeClaim` | full: index; incremental: `indexCellClaims`, `refreshContextualClaims` | `createEdgeClaimGroup` (own + `getStructuralEdgeClaims`) | |
| Group ownership | `edgeClaimResolution.ts:resolveEdgeClaimGroup` → `compareEdgeClaimPriority` (present, opaque, authored colour, then coord, then id) | | `resolveSurvivingSegments`, `incrementalEdgeResolution.ts:resolveChangedClaimGroups` | lowest coord wins ties: the reproduced defect 1 |
| Survivors → render | `EdgeDrawSegments` (`edgeResolution.ts:resolveEdgeDrawSegments` → `edgeJunctionResolution.ts` → `resolveSceneEdgeSegments`); incremental `IncrementalEdgeResolution.edgeSegments` | resolution | `cubeInstances.ts:createCubeCellInstances` via `context.edgeSegments` (**sole render consumer**; edges, ghost edges, edge hit targets all derive from it) | |
| Render-site drop (HEAD) | `HEAD:cubeInstances.ts:createCubeCellInstances` `const edgeSegments = rounded ? undefined : context.edgeSegments.get(cell.id)` | | | second guard D6 deletes |
| Impact → reindex | `src/domain/incrementalCubeRenderResolution.ts:getEdgeIndexChanges` (full reindex on `impact.occupancy | transform | visibility`; per edge on `impact.edges`) | `classifyAuthoredRenderImpact` | `IncrementalEdgeResolution.update(cellsById, resolve, reindex)` | |
| Body impact flag (HEAD) | `HEAD:src/domain/authoredRenderImpact.ts:CubeCellRenderImpact.body` (set from `cubeBodyStateOwner.areEqual`) | `classifyCellRenderImpact` | only `hasCellRenderImpact` (cell re-instanced). **No edge consumer**: `rg "impact\.body"` → none outside `authoredRenderImpact.ts` | |

Forfeit seam, verified by reading the three candidate points:

1. Skip the claim only (`createEdgeClaimIndex`): wrong. `resolveEdgeClaimGroup` returns `{claim: null, edge}` for a group with no own claim and `resolveSurvivingSegments` still adds it; the shell would draw its own edge.
2. Sort shell last (`compareEdgeClaimPriority`): wrong. A shell with no coincident neighbour is sole owner and still survives.
3. **Return no authored segments for a shell cell at `createCellAuthoredEdgeSegments`**: correct and single. No authored → no group → no survivor → no edge instances, ghosts, or edge hit targets; a sharp neighbour's `getStructuralEdgeClaims` finds no shell claim, so its own claim wins the coincident group (inherits the shared edge). Both full and incremental paths already go through this symbol.

Incremental invalidation answer for the brief: **no, a corners change on one cell does not invalidate the neighbour's edges today.** `getEdgeIndexChanges` ignores `impact.body`, so `set-cube-body-style` produces neither `reindex` nor `resolve` for the cell (the cell re-instances only). The fix is in `getEdgeIndexChanges`: treat `impact.body` (perimeter style change) like `occupancy | transform | visibility` (all twelve edges reindexed and resolved). Peer fan-out then already works: `incrementalEdgeResolution.ts:collectRelatedEdges` runs before `removeCellClaims` (sharp→shell picks up peers from the old claim) and again after `indexCellClaims` (shell→sharp picks them up from the new claim). Gate: `tests/contracts/incremental-scene-equivalence.contract.test.ts` needs a corners toggle next to a sharp neighbour at zero gap.

Edge case for the reviewer: `resolveEdgeClaimGroup` suppresses an interior edge only when `structural.length === 4`. With a shell in one quadrant the count is 3, so the sharp winner draws an edge that was previously suppressed. Probably right (the shell's rounded corner exposes it) but it is a behaviour change to name (open decision A6).

### (c) Workbench-only form cues and how deltas reach materials (D5)

| Item | Owner | Writes | Reads | Wins today |
| --- | --- | --- | --- | --- |
| Cue config | `src/theme/scenePolarity.ts:ScenePolarityConfig.edgeLightnessDelta`, `.faceLightnessDeltaById`; set only in `workbenchScenePolarities` via `createPolarityConfig(config, grooming)`; `scenePolarities` (artifact) omit them | theme module | `instancedPartMeshCore.ts:createColorWriteContext` → `writeColor` (CPU colour write per instance, `colorSpace.ts:shiftLightnessForContrast`) | single owner |
| Polarity choice | `src/studios/editor/EditorStudio.tsx` (`previewing ? scenePolarities : workbenchScenePolarities`); thumbnails `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` uses `scenePolarities[pose.polarity]` | | `InstancedPartMesh.tsx` effect → `syncInstancedPartMesh(mesh, slots, polarity)` on polarity change / `patchInstancedPartMesh` | |
| Uniform precedent | `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh` (owns uniform objects in closure, injects in `onBeforeCompile`, updates in `onBeforeRender`); `src/scene/faceContentShader.ts:applyFaceContentShader` (`shader.uniforms.cubicellStencilAtlas`) | | | |
| Per-mesh state precedent | `instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` `mesh.userData.partKind`, `mesh.userData.contentAtlas` | | `getInstancedPartKind`, `writeContent` | |
| Light on HEAD | `HEAD:src/scene/cubeBodyShader.ts` `fragmentShading` literal `0.68 + 0.32 * max(dot(n, normalize(vec3(-0.45, 0.65, 0.60))), 0)` | shader source | every body mesh incl. thumbnails (`createCubePartLayerMesh` applies it) | the defect D5 removes |

Binding for D5: add an optional workbench-only field on `ScenePolarityConfig` (e.g. `shellLight?: { direction: Vec3; ambient: number; diffuse: number }`) set through the existing `grooming` argument of `createPolarityConfig`, so artifact configs stay flat by construction (thumbnails, export, and preview all use `scenePolarities`). Deliver it to the material as uniforms owned at material creation (`edgeCoverageCore` pattern) and written in `syncInstancedPartMesh` (already receives `polarity`, already re-runs on polarity change and on growth). Shader default when the uniform is absent or zero: multiply by 1.

### (d) Per-part state owners and the deletion inventory (D2, D4)

| Item | Owner |
| --- | --- |
| Owner factory | `src/domain/cubePartStateOwner.ts:createCubePartStateOwner` / `defineCubePartStateField` (`hasValidFields`, `isState`, `isPatch`, `applyPatch`, `encode`, `decode`, `areEqual`, `getMorphChanges`, `interpolateMorph`, `inherit`, `changedRenderAttributes`) |
| Edge owner | `src/domain/cubeEdgeState.ts:cubeEdgeStateOwner` (fields `color`, `opacity`, `thickness`, `visible`); thickness `isValue: isFiniteNumber` (domain unbounded, UI bounds via `controlBindingTypes.ts:edgeThicknessSchema`) |
| Face owner | `src/domain/cube.ts:cubeFaceStateOwner` |
| Body owner (HEAD) | `HEAD:src/domain/cubeBodyState.ts:rawCubeBodyStateOwner` (fields `corners`, `radius`, `frameMargin`, `frameColor`), wrapped as `cubeBodyStateOwner` with overridden `applyPatch` (`applyCubeBodyStylePatch`), `decode`, `isState`, `isPatch`; **`hasValidFields` not overridden** (finding 7) |

Complete consumer list for the deletion (D2, D3), from `rg "frameMargin|frameWidth|frameColor|getCubeFrameWidth|CubeBodyStylePatch|applyCubeBodyStylePatch|bodyFrameWidth|hasValidFrame|maximumBodyInset|bodyInsetSchema" src tests scripts server *.md`:

- Domain: `cubeBodyState.ts` (`frameMargin`, `frameColor` fields, `CubeBodyStylePatch.frameWidth/frameColor`, `hasValidFrame`, `isPatch` key list, `getCubeFrameWidth`, `applyCubeBodyStylePatch` coupling), `domain/index.ts` exports (`applyCubeBodyStylePatch`, `getCubeFrameWidth`, `CubeBodyStylePatch`), `cubeCellOperations.ts:setCubeBodyStyle`, `cubeOperations.ts` `CubeOperation` `set-cube-body-style` patch type.
- Evaluation: `sceneMorph.ts:createPartColorTweens` (`body` tween on `frameColor`), `MutablePartColorTweens.body`, `scoreAt.ts:CubePartColorTweens.body`.
- Scene: `cubeInstances.ts` (`getCubeFrameWidth` import, `CubeBodyInstance.bodyFrameWidth`, `frameWidth`, `panelScale`, `color: cell.body.frameColor`), `instancedPartMeshCore.ts:InstancedPart.bodyFrameWidth` and `writeBodyShape` (`setXY(radius, frameWidth)`), `instanceSlotRegistry.ts:changedAttributes` / `fullAttributes` (`bodyFrameWidth`).
- Editor: `cubeControlBindings.ts` (`cubeFrameWidthBinding`, `cubeFrameColorBinding`, `bodyInsetSchema` shared with radius), `controlBindingTypes.ts:ControlBindingId` (`"cube.frameColor"`, `"cube.frameWidth"`), `src/panels/CubeSection.tsx` (`cube.frameWidth`, `cube.frameColor` fields).
- Control: `studioSnapshot.ts:composeStudioSnapshot` (`bodyStyle.frameColor`, `.frameWidth`, `getCubeFrameWidth` import).
- Tests: `tests/contracts/cube-body-style.contract.test.ts` (tests "owns radius and frame width conflict policy", "round trips the strict ten item compact cell", "validates authored patches and rejects out of range width", "cuts corners while interpolating body geometry and color", "keeps dormant sharp settings out of continuous morph channels" and fixtures), `rounded-body-rendering.contract.test.ts` (`bodyFrameWidth` assertions, `frameWidth` fixtures), `cube-body-style.browser.contract.test.ts` (Frame width scrub, Frame colour picker, `readBody` shape), `authored-operation.contract.test.ts` (patch fixture), `studio-observation.contract.test.ts` (`bodyStyle` shape), `tests/roundedInteriorBrowserHarness.ts` (`frameColor`, `frameWidth` fixtures).
- Docs: `LLMDRIVES.md` "per cube corner mode, radius, frame width, and frame colour".

After D2/D4 the wrapper in `cubeBodyState.ts` collapses to the raw owner: `hasValidFields`, `isState`, `isPatch`, `applyPatch` from `createCubePartStateOwner` are sufficient (`radius` `isValue` already bounds it), which closes finding 7 without new code. Radius bound: see open decision A5 (world units make the `< 0.5` unit-space bound wrong).

### (e) Buried face culling and O1

| Item | Owner | Reads |
| --- | --- | --- |
| Per face burial | `src/domain/exposure.ts:isFaceBuried` (needs an occupied neighbour whose opposite face is visible and `opacity === 1`, same rotation basis, coplanar and fully covering) | `cubeRenderResolution.ts:resolveBuriedCubeFaces` / `createBuriedFaceIndex`; incremental `incrementalCubeRenderResolution.ts:updateBuriedFaces` |
| Index → render | `CubeRenderResolutionPass.buriedFaces` | `cubeInstances.ts:createCubeCellInstances` (`context.buriedFaces.get(cell.id)?.has(face.id)` skips face instances); **sole consumer** |

O1 answer: the seam exists on the CPU side (per cell, per face, already in the `context` the shell instance is built from), so nothing new is needed to *know* a side is buried. What is missing is a way to *apply* it to a shell: the shell is one instance whose six sides live in one draw, so band culling needs either a per-instance side mask attribute (six bits packed into a float on the existing body shape attribute or a sibling) with a discard in `cubeBodyShader.ts` fragment, or six band instances per shell. Also the burial criterion differs: `isFaceBuried` requires an opaque opposite **panel**; two shells fight on the band regardless of panel opacity, so a shell-vs-shell test would key on the neighbour's `corners` rather than its face opacity. Not free; recommend keeping O1 out of this branch (open decision A7).

### (f) Instance attribute plumbing for radius (D7)

| Item | Owner | Writes | Reads |
| --- | --- | --- | --- |
| Attribute vocabulary | `HEAD:src/scene/instanceSlotRegistry.ts:InstanceSlotAttribute` `"bodyShape"`; `changedAttributes` / `fullAttributes` compare `bodyRadius`, `bodyFrameWidth` | registry diff | `patchInstancedPartMesh` |
| GPU attribute | `HEAD:src/scene/cubeBodyShader.ts:cubeBodyShapeAttributeName` (`instanceBodyShape`, vec2), created in `applyCubeBodyMaterial`; grown generically by `instancedPartMeshCore.ts:resizeCapacityBoundGeometryAttributes` (any `InstancedBufferAttribute`) | `HEAD:instancedPartMeshCore.ts:writeBodyShape` (`setXY(radius, frameWidth)`), `getBodyShapeAttribute` | `cubeBodyShader.ts` vertex (`vertexNormal`: `transformed = sign(position) * (0.5 - r) + normal * r`, unit cube space) and fragment (`fragmentShading` opening half size `0.5 - shape.y`) |
| Part fields | `HEAD:instancedPartMeshCore.ts:InstancedPart.bodyRadius?`, `.bodyFrameWidth?` (optional bag on the shared part type) | `cubeInstances.ts:createCubeCellInstances` | registry, writer |
| Body matrix | `HEAD:cubeInstances.ts:createCubeCellInstances` `cellMatrix * scale(size)`; `cellMatrix = createTransformMatrix(pose.renderPosition, pose.rotation, pose.scale)` | | shader `instanceMatrix` |
| Panels | `HEAD:cubeInstances.ts` `panelScale = 1 - frameWidth * 2` (unit ratio applied to `face.size`), `roundedPanelOutsetRatio = 0.002` | | face instances |
| Edge thickness units (precedent) | `src/domain/cubeGeometry.ts:createCubeEdgeSegments` size `[t, t, t]` with axis `size + t` in **cell units** (pre `pose.scale`) | | |

What changes for D7: the attribute carries radius in world units; the shader must divide per axis. Two ways to get the divisor, and they are not equivalent:

- Shader: `length(instanceMatrix[i].xyz)` per axis = `size[i] * pose.scale[i]` (rotation invariant). Radius then stays absolute under `pose.scale`, whereas edge thickness scales with `pose.scale`. Panels in `cubeInstances.ts` are computed in cell space, so parity needs `face.size - 2 * r / pose.scale`.
- CPU: `cubeInstances.ts` writes per-axis unit radii `r / size[axis]` (vec3) and the shader stays matrix free; radius behaves exactly like edge thickness (cell units), and panels are `face.size - 2 * r` in the same function. Recommended (open decision A3 records the deviation from D7's letter).

Either way `writeBodyShape` becomes a vec3 write and `changedAttributes` compares the radius only. Bound and clamp: see A5.

### (g) Face hit targets and pointer handler spread (D8)

| Item | Owner | Reads |
| --- | --- | --- |
| Hit target emission (HEAD) | `HEAD:cubeInstances.ts:createCubeCellInstances` pushes a full-size, `displayOpacity: 0` `CubeFaceInstance` into `faceHitTargets` for **every visible face of every cell** | `collectCubeSceneInstances`, `cubeInstanceSlots.ts` bucket `faceHitTargets`, `getCubeInstancePartKey` (`face-hit:`) |
| Layer (HEAD) | `HEAD:src/scene/renderCubeScenePartLayers.tsx` `key="face-hit-targets"` (`pickingOnly`, `partKind="face"`, `{...interactions.facePointerHandlers}`) | |
| Handler spread | `src/scene/useCubeSceneInteractions.ts:facePointerHandlers` spread on `opaque-faces`, `translucent-faces`, `ghost-faces` on `main`; HEAD adds the hit target layer (four) | `handleFacePointerDown/Up/Over/Out` |
| Picking layer lifetime | `src/scene/sceneSelectionGesture.ts:scenePickingLayer`; enabled for the editor lifetime by `src/camera/cameraGestureRuntime.ts` (`raycaster.layers.enable(scenePickingLayer)`) **on `main` already** for `edgeHitTargets`; meshes join via `createInstancedPartMeshWithGeometry` `pickingOnly` | |
| Slot yield | `useCubeSceneInteractions.ts:handleNeighborSlotPointerUp` uses `getInstancedPartKind(hit.object) === "face"`; hit targets carry `partKind "face"` so they participate correctly | |
| Body raycast | `HEAD:instancedPartMeshCore.ts:createInstancedPartMeshWithGeometry` `partKind === "body"` → `raycast = ignoreRaycast` (`src/scene/ignoreRaycast.ts`, shared with chrome and coverage meshes) | |

D8 binding: gate the `faceHitTargets.push` in `createCubeCellInstances` on `rounded` (the inset panel is what makes the target necessary; sharp faces are full size and already receive `facePointerHandlers`). Delete `CubePartLayerSpec.picking` (no reader: `rg "\.picking\b|picking:" src` hits only the spec literals). The layer spread and lifetime picking layer are pre-existing patterns; nothing to change there.

### (h) Persistence surface

| Item | Owner | Notes |
| --- | --- | --- |
| Compact cell | `src/persistence/recordCodecs/compactPose.ts:encodeCell` / `decodeCell` (`CompactCell` tuple; HEAD length 10, tail `cubeBodyStateOwner.encode(cell.body)` always present; decode rejects on `!body`) | Default omission precedents in the same function: placement fields encode `null` at default (`sameVec3`, `sameSize`), edges and faces omit default parts via `cubeEdgeStateOwner.areEqual(edge, defaultCubeEdgeState)`. Body can follow the placement rule: `null` at `areEqual(body, defaultCubeBodyState)`, decode `null` → default, tuple length stays 10 |
| Owner encode shape | `cubePartStateOwner.ts:encode` (positional array, trailing optional nulls trimmed) / `decode` | With `{corners, radius}` the tail is a 2-tuple |
| JSON pose validation | `src/state/workbenchValidation/pose.ts:isCubeCell` (loose; HEAD adds `cubeBodyStateOwner.hasValidFields(value.body)`), `isCurrentCubeCell` (strict keys incl. `body`; `cubeBodyStateOwner.isState`), `isPersistedPose`, `isPose`, `isPoseShape`, `completePersistedPose` (no per-cell defaults today; body is required in the JSON shape) | Callers: `workbenchValidation/aggregate.ts:completePersistedWorkbench`, `assets.ts`, `authoredOperationValidation/scene.ts` (`upsertCubes`, `restore-scene-patch`) |
| Operation validation | `src/state/authoredOperationValidation/scene.ts:isCubeOperation` case `set-cube-body-style` (`hasOnlyKeys(value, ["kind","patch","scope"]) && cubeBodyStateOwner.isPatch`) | With the raw owner `isPatch` the accepted keys shrink automatically |
| Schema versions (HEAD bumps) | `authoredOperations.ts:authoredOperationSchemaVersion` 6→7, `indexedDbSchema.ts:indexedDbProjectStorageVersion` 12→13, `draftRecordCodec.ts` 4→5, `localHistoryRecordCodec.ts` 4→5 and step 2→3, `outboxCommitRecordCodec.ts` 5→6, `poseRevisionRecordCodec.ts` 4→5, `storageRecordTypes.ts:committedRecordSchemaVersion` 3→4 | Amending in place (D10) keeps these bumps; no second bump for the tail reshape. `tests/contracts/cube-body-style.contract.test.ts` "bumps every direct pose and authored operation carrier" stays valid |

### (i) Studio snapshot and protocol version

| Item | Owner |
| --- | --- |
| Snapshot cell shape | `HEAD:src/control/studioSnapshot.ts:composeStudioSnapshot` adds `bodyStyle: {corners, frameColor, frameWidth, radius}` and a top-level `version: studioObservationProtocol.version` (new on HEAD, not on `main`); `edges.visibleCount` and `layer` (`getCubeLayerMode`) read authored `cell.edges` for every cell |
| Protocol | `src/control/studioProtocol.ts:studioObservationProtocol.version` 1→2 (HEAD), consumed by `describeStudioObservationProtocol`, `src/control/index.ts`, `HEAD:scripts/verifyMcpObservation.ts` (imports the constant; D9 reverts to a literal `2`), `tests/contracts/studio-observation.contract.test.ts` |
| Docs | `LLMDRIVES.md` "Supported slice" (version 2) and "Semantic read model" bullets |

Under D1 the authored edge state of a shell cell is preserved but not drawn, so `edges.visibleCount` and `layer` keep reporting authored state (finding 4). Whether the snapshot should report drawn perimeter (`perimeter: "wire" | "shell"`, count 0 for shells) or authored state is a read model decision (open decision A4). Also decide whether the top-level `version` on the snapshot stays; it duplicates `describe`.

### (j) Control bindings

| Item | Owner |
| --- | --- |
| Cube bindings | `HEAD:src/editor/cubeControlBindings.ts` (`cubeCornersBinding`, `cubeRadiusBinding`, `cubeFrameWidthBinding`, `cubeFrameColorBinding`, `createBodyCommand`, `bodyInsetSchema {max: 0.49, min: 0, step: 0.005}`), split out of `main:src/editor/controlBindings.ts` (667 lines on main; HEAD 454) with shared vocabulary in `HEAD:src/editor/controlBindingTypes.ts` (`ControlBindingId`, `partColorOptions`, `edgeThicknessSchema`, `partOpacitySchema`, `getControlSelectedCell`, `resolvePartEditScope`) |
| Gating | `HEAD:src/panels/CubeSection.tsx` (`cube.corners` always; `cube.radius`, `cube.frameWidth`, `cube.frameColor` when rounded; `cube.layers`, `cube.edgeThickness` when sharp) |
| Field aria | `HEAD:src/components/ui/scrub-field/ScrubField.tsx` `aria-label={`${label} value`}` (added for the browser test's `getByLabel("Radius value")`) |

Under D2/D3 delete `cubeFrameWidthBinding`, `cubeFrameColorBinding`, their ids, and their `CubeSection` fields; `cube.color` (`getCubeUniformPartColor`) already drives the shell colour. `bodyInsetSchema` becomes the radius schema; if radius moves to world units its `max` follows A5. The split into `cubeControlBindings.ts` / `controlBindingTypes.ts` is a good hygiene move on its own; keep it.

### (k) Tests, harness, governance

- `tests/contracts/cube-body-style.contract.test.ts` (10 cases): reshape 5 (conflict policy, ten item compact, patch validation, both morph cases and fixtures); keep dormant, inherit, scoped patch, version bumps.
- `tests/contracts/rounded-body-rendering.contract.test.ts` (6 cases): "keeps sharp cubes on full panels and authored rails" asserts `faceHitTargets` 6 for sharp (D8 → 0); "wraps inset panels..." asserts `bodyFrameWidth` and `panelScale`; "writes and patches distinct per cube body shapes" asserts `itemSize 2` and `frameWidth` patch (→ radius only, vec3 under A3); "shares rounded geometry and shader policy with thumbnails" asserts `normalShading` (goes with the mesh path consolidation below). Add: shared edge forfeiture (two cells, zero gap, lower coordinate cell shell: sharp neighbour owns the four shared edges; shell has zero edge and edge hit target instances) and neighbour inheritance in the incremental path (extend `incremental-scene-equivalence.contract.test.ts` with a corners toggle).
- `tests/contracts/cube-body-style.browser.contract.test.ts` (2 cases) and `tests/roundedInteriorBrowserHarness.ts`: drop Frame width and Frame colour steps; the harness renders with `scenePolarities` and its frame-vs-centre assertions (`whiteWhite.frame[0] > 140` vs `center[0] > 200`) depend on the shader light; under D5 render the lit case with `workbenchScenePolarities` and add a flat assertion under `scenePolarities` (frame equals centre for white/white). Set the shell colour through edges (`setAllCubeEdgesState` or `createCubeCell({edges: createCubeEdgesState({...})})`) instead of `frameColor`.
- `tests/contracts/studio-observation.contract.test.ts`, `authored-operation.contract.test.ts`: fixture shapes.
- `tests/contracts/governance.json`: HEAD raised local `maxCases` 29→44 and browser 6→7; recount after the reshape (some cases collapse) and re-baseline at zero headroom per the gates note.
- `budgets/initial-delivery.json`: HEAD raised five ceilings; re-measure after S2 (the light and coupling code shrink) and re-baseline at zero headroom.

### (l) Docs for O3

- `MODEL.v2.md`: `CubeCell` type block (no `body`) and "Edges and faces are separate authored parts."
- `ARCHITECTURE.md`: "Edges and faces are separate primitives." and the primitives paragraph.
- `LLMDRIVES.md`: version 2 bullets ("per cube corner mode, radius, frame width, and frame colour").
- No other doc mentions body, rounded, or corner (`rg -i "part famil|body|rounded|corner" *.md` → only the above plus `LLMDRIVES.md`).

## Quality Map

Findings on branch files, /code-hygiene lens. Measurements: `sceneMorph.ts` 657 (main 643), `instancedPartMeshCore.ts` 557 (main 519), `incrementalCubeRenderResolution.ts` 534, `incrementalEdgeResolution.ts` 509, `cubeInstances.ts` 460 (main 390), `controlBindings.ts` 454 (main 667). `createCubeCellInstances` is 149 lines (at the ~150 function threshold).

1. **Two mesh creation paths for the same layer.** `HEAD:src/scene/InstancedPartMesh.tsx` builds meshes inline (`createGeometry` / `geometryKind` union, `normalShading` → `applyCubeBodyMaterial`) while `HEAD:src/scene/cubePartLayerSpecs.ts:createCubePartLayerMesh` does the same for thumbnails and tests. Least resistance: extend the existing `instancedPartMeshCore.ts:InstancedPartMeshOptions.geometryKind` with a third kind (`"shell"`, geometry from `cubeRoundedBody.ts`) and hang the shell material on `partKind === "body"` inside `createInstancedPartMeshWithGeometry`, exactly where `translucent → applyInstanceOpacity`, `stencilAtlas → applyFaceContentShader`, and `partKind === "body" → ignoreRaycast` already live. Then `InstancedPartMesh.tsx` reverts to `geometryKind` only, `getCubePartLayerGeometryProps` and `CubePartLayerGeometryProps` disappear, and `createCubePartLayerMesh` is a thin spec-to-options mapper. The `normalShading` prop name also misdescribes what it does (cutout + light).
2. **Dead metadata.** `cubePartLayerSpecs.ts:CubePartLayerSpec.picking` has no reader (D8 deletes it).
3. **Boundary escape.** `HEAD:cubeBodyState.ts:cubeBodyStateOwner` overrides `isState`/`decode` but not `hasValidFields`, so `pose.ts:isCubeCell` accepts frames the strict path rejects (finding 7). Dissolves with D2/D4 (raw owner, no wrapper).
4. **Stringly dispatch.** `HEAD:cubeInstanceSlots.ts:getCubeInstancePartKey` uses `bucket.endsWith("Bodies")`; the sibling checks are exact bucket names. Prefer an exact set or a `bucketPartKind` map on `CubeInstancePartByBucket`.
5. **State relative patcher.** `HEAD:cubeBodyState.ts:applyCubeBodyStylePatch` (finding 2). Dissolves with D2.
6. **Optional bag on a shared type.** `HEAD:instancedPartMeshCore.ts:InstancedPart.bodyRadius?/bodyFrameWidth?` and `instanceSlotRegistry.ts:fullAttributes` probing `!== undefined`. Acceptable given `axis?`/`faceId?` precedent, but shrink to one field (`shellRadius`) under D2.
7. **Two literals for one number.** `HEAD:cubeRoundedBody.ts:templateRadius = 0.055` and `cubeBodyState.ts` radius `defaultValue: 0.055`. The template radius is arbitrary (re-radiused per instance) so name it as such or reference the default; do not leave two unrelated `0.055`.
8. **Magic numbers in render.** `HEAD:cubeInstances.ts:roundedPanelOutsetRatio = 0.002` (fine as a named constant, but it belongs next to `selectedEdgeThicknessScale` etc. with a comment on why panels sit outside the band); shader light constants (D5 moves them to `scenePolarity.ts`).
9. **Impact flag without consumer.** `HEAD:authoredRenderImpact.ts:CubeCellRenderImpact.body` is only read by `hasCellRenderImpact`; under D6 it must drive `getEdgeIndexChanges` (see (b)). Not dead, but incomplete.
10. **Half applied spec indirection.** `HEAD:renderCubeScenePartLayers.tsx` reads `specs.*` for five layers but inlines `face-hit-targets`/`edge-hit-targets`, and writes `translucent={specs.translucentFaces.opacity === "translucent"}` (a constant true). With finding 1 resolved the spec object should carry `translucent` and `geometryKind` directly, or the layer list should be data driven end to end; do not stop halfway.
11. **Order coupling.** `HEAD:thumbnailArtifact.ts:createThumbnailArtifact` destructures `[opaqueBodies, opaqueEdges, ...]` from `authoredCubePartLayerSpecList.map(...)`; a reorder of the list silently mislabels meshes. Build the record by `spec.key` (as `main` did with `Object.fromEntries`).
12. **Second colour owner for one role.** `frameColor` beside twelve `edges[id].color` (the D3 defect). Also `sceneMorph.ts:createPartColorTweens` gains a third tween family for it.
13. **Snapshot surface growth.** `HEAD:studioSnapshot.ts` adds `version` to the snapshot body (not in the decisions; duplicates `describe`). Decide (A4) rather than carry silently.
14. **File pressure.** `sceneMorph.ts` at 657 is 43 lines from the hard cap; the branch added 14 (body morph). The reframe removes the colour tween lines; do not add more here without a split (a `partColorTweens.ts` seam is visible: `MutablePartColorTweens`, `createPartColorTweens`, `PartColorTween` plumbing).
15. **Test provenance.** Untracked `tests/contracts/zz-scratch-shared-edge.contract.test.ts` in the worktree (asserts `toEqual({})`, a repro scratch). Not part of the branch; must not be committed.

Positive reuse already on the branch (keep): `createColorWriteContext` treating body as edge; `resizeCapacityBoundGeometryAttributes` growing the shape attribute generically; `ignoreRaycast` on body meshes; edge state field reuse for colour; the `controlBindings.ts` split.

## Plan

Three slices, each bound to the map. Amend PR #180 in place (D10); commits stay legible per slice.

### S1. Domain, persistence, bindings, snapshot shrink, claim forfeiture

Binds to: (a) `getCubeUniformPartColor` sibling in `cube.ts`; (b) `createCellAuthoredEdgeSegments`, `getEdgeIndexChanges`; (d) raw `createCubePartStateOwner`; (h) `compactPose.ts` placement-null precedent; (i) `studioSnapshot.ts`; (j) `cubeControlBindings.ts`, `CubeSection.tsx`.

- `cubeBodyState.ts`: fields `{corners, radius}`; export the raw owner as `cubeBodyStateOwner` (no wrapper, no `applyCubeBodyStylePatch`, no `getCubeFrameWidth`); `CubeBodyStylePatch` = owner patch type. Radius `isValue`: finite and `>= 0` (bound per A5). `domain/index.ts` exports shrink.
- Colour: shell colour = uniform edge colour via a new `cube.ts:getCubeUniformEdgeColor` (or extend `getCubeUniformPartColor` with a part filter) plus the fallback rule from A1; `sceneMorph.ts` drops the `body` tween and derives the shell tween from `edges` (A2).
- Forfeit: `createCellAuthoredEdgeSegments` returns `[]` for `corners === "rounded"`; `getEdgeIndexChanges` treats `impact.body` as a full edge reindex; delete the render-site drop in `cubeInstances.ts`.
- Persistence: compact tail `null` at default; `pose.ts` unchanged beyond the owner; keep HEAD's version bumps.
- Bindings/UI: delete frame width and frame colour bindings, ids, fields; `bodyInsetSchema` → radius schema.
- Snapshot: `bodyStyle` → `{corners, radius}` (or per A4).
- Tests: reshape `cube-body-style.contract.test.ts`, `authored-operation`, `studio-observation`; add forfeiture + inheritance case to `rounded-body-rendering` and a corners toggle to `incremental-scene-equivalence`; recount `governance.json`.
- Gate: `pnpm test`, `tsc -b`.

### S2. Renderer: light as polarity uniform, world unit radius, shell-only hit targets, one mesh path

Binds to: (c) `ScenePolarityConfig` grooming + `syncInstancedPartMesh` + `edgeCoverageCore` uniform pattern; (f) `writeBodyShape`, `changedAttributes`, `cubeBodyShader.ts`; (g) `createCubeCellInstances` `faceHitTargets`; quality 1, 2, 4, 6, 7, 10, 11.

- `scenePolarity.ts`: `shellLight` on the workbench family only; `cubeBodyShader.ts` reads it as uniforms with a flat default; `syncInstancedPartMesh` writes it from `polarity` for `partKind "body"` meshes. Thumbnails, preview, export stay flat by construction.
- Radius units per A3 (recommended: CPU per-axis unit radii vec3 from `cubeInstances.ts`, shader stays matrix free; panels `face.size - 2r`; clamp `min(r, minAxis/2)` at the same site).
- Hit targets only for shell cells; delete `CubePartLayerSpec.picking`.
- Mesh path: `geometryKind "shell"` + `partKind "body"` material inside `createInstancedPartMeshWithGeometry`; `InstancedPartMesh.tsx` back to `geometryKind`; `cubePartLayerSpecs.ts` becomes a spec-to-options mapper; `thumbnailArtifact.ts` builds meshes by `spec.key`.
- Optional (A8): rename render vocabulary `body` → `shell` (bucket names, `partKind`, layer keys) if taken.
- Tests: `rounded-body-rendering` (attribute shape, hit target counts, thumbnail parity flat), browser harness (lit under `workbenchScenePolarities`, flat under `scenePolarities`), `cube-body-style.browser` (no frame steps).
- Gate: `pnpm test`, `pnpm test:browser`, `tsc -b`.

### S3. Docs, verify literal, budgets

Binds to: (i) `verifyMcpObservation.ts` (D9); (k) `governance.json`, `budgets/initial-delivery.json`; (l) three docs.

- `scripts/verifyMcpObservation.ts`: literal `2`, drop the `studioProtocol` import.
- `MODEL.v2.md`, `ARCHITECTURE.md`, `LLMDRIVES.md`: one perimeter, two styles; `CubeCell.body: {corners, radius}`; snapshot bullets.
- Re-measure and re-baseline budgets and governance caps at zero headroom.
- Gate: `pnpm check`, `pnpm check:budget`, `pnpm test`, `pnpm test:browser`, `tsc -b`; integrator proves on `pnpm dev` and `pnpm preview` (preview must be flat).

### Open decisions D1 to D10 leave (numbered A for the orchestrator)

- **A1. Mixed edge colours.** `getCubeUniformPartColor` returns `null` when parts differ and it spans faces too. Rule needed for the shell when edges are not uniform: (i) new edges-only helper returning `defaultCubePartColor` on mix, (ii) first edge, or (iii) most common. Recommend (i): predictable, and `set-cube-color` makes it moot in practice.
- **A2. Shell colour tween.** Derive from `edges` tweens (any edge when uniform); no tween when edges are mixed. Recommend that.
- **A3. Radius divisor.** Shader `instanceMatrix` column length (absolute under `pose.scale`, differs from edge thickness which is in cell units) vs CPU per-axis unit radii (`r / size`, matches edge thickness, panels computed in the same function, shader matrix free). Recommend CPU; it meets D7's intent (circular corners on non cubic cells) with less shader surface. Note it deviates from D7's wording.
- **A4. Snapshot read model.** `edges.visibleCount` and `layer` for shell cells: authored (as today) or drawn; shape and name of `bodyStyle`; keep or drop the new top-level `version`. Recommend `bodyStyle: {corners, radius}`, keep authored counts, drop the top-level `version` (describe owns it).
- **A5. Radius bound and clamp in world units.** The `< 0.5` bound is unit space. Options: fixed domain cap like edge thickness (domain `>= 0` finite, UI schema max, render clamps to half the smallest axis so a large radius on a thin cell degrades to a full round instead of inverting). Recommend that; the clamp lives in `createCubeCellInstances` next to the panel inset so both agree.
- **A6. Interior edge suppression with a shell quadrant.** `resolveEdgeClaimGroup` needs four structural claims to suppress; a shell quadrant leaves three, so the edge is drawn by the sharp winner. Recommend accept and name it in the forfeiture test.
- **A7. O1 scope.** The burial seam exists (`buriedFaces`) but shell band culling needs a per-instance side mask and a shell-vs-shell criterion. Recommend out of this branch; record as a follow-up.
- **A8. Render vocabulary.** Domain keeps `body` (D4). Whether render buckets, `partKind`, and layer keys become `shell` (D1's word). Recommend rename in S2 only if the mesh path consolidation already touches every site (it does); otherwise defer.
- **A9. Shell opacity.** D3 says "if needed at all". Today shells are opaque regardless of edge opacity. Recommend leave opaque in this branch; note it.

## Searches run for "none found"

- `rg "getCubeUniform|getUniformPart|UniformEdge" src` → only `getCubeUniformPartColor` (no edges-only helper).
- `rg "impact\.body" src` → no consumer outside `authoredRenderImpact.ts`.
- `rg "\.picking\b|picking:" src` → spec literals only.
- `rg "buriedFaces" src` (outside resolution) → `cubeInstances.ts` only.
- `rg "edgeSegments|resolveSceneEdgeSegments|resolveEdgeDrawSegments" src` (outside resolution) → `cubeInstances.ts`, `view/focusGeometry.ts` (uses authored segments, unaffected).
- `rg "roundedInteriorBrowserHarness"` → wired only from the browser test via `page.addScriptTag`.
- `rg -i "part famil|body|rounded|corner" *.md` → `MODEL.v2.md`, `ARCHITECTURE.md`, `LLMDRIVES.md`.

## Addendum: findings from the /code-review fork (same session, 2026-08-17)

A `/code-review` pass over the branch ran alongside the scout. Items already covered above are omitted (finding 1 = D6/(b); mesh path duplication = quality 1; hit targets for every face = D8/(g)). New or sharpening items, with my verification status:

16. **Hover clears on the hit target layer.** `HEAD:renderCubeScenePartLayers.tsx` spreads the full `facePointerHandlers` (incl. `onPartPointerOut`) on `face-hit-targets`; with a shell cell the inset panel and the full-size hit target overlap, so panel → frame movement fires the panel's pointer-out and `handleFacePointerOut` (`useCubeSceneInteractions.ts`) clears cube hover while the cursor is still on the cube. Reasoning verified from `useCubeSceneInteractions.ts:handleFacePointerOut` and R3F per-object hover; not reproduced in a browser. Binding: give the hit target layer down/up handlers only, or make hover-out consult `event.intersections` for another face of the same cube. Belongs in S2 with D8.
17. **Edge pick mode and edge selection on shell cells.** `src/app/useSceneOperations.ts:selectFaceEdges` (via `handleFacePointerUp` when `pickMode === "edge"`) has no corners check (`rg corners src/app/useSceneOperations.ts` → none), so a shell cell yields an edge selection with no visual, no highlight (`selectedEdgeThicknessScale` lives in the segment loop that D6 forfeits), and edge edits with no visible effect. D1 preserves authored edge state, so this is a UX gate decision, not a domain one: **A10.** gate edge pick/selection on `corners === "sharp"` at the interaction layer, or accept edge edits as dormant on shells (they reappear on Sharp). Recommend gate.
18. **Layers trap.** `set-cube-layers` (`cubeCellOperations.ts`) sets face visibility; `HEAD:CubeSection.tsx` hides `cube.layers` when rounded. Sharp + Layers "Edges" (faces hidden) → Rounded leaves a shell with no panels and no UI path back except Sharp first. Verified from the two symbols. **A11.** either keep `cube.layers` visible for shells (edges option meaningless there) or normalise faces visible on the shell transition in the domain. Recommend keep the control visible; no domain coupling.
19. **Burial with a shell neighbour.** `exposure.ts:isFaceBuried` treats a shell neighbour as full flat coverage, so at gap 0 the sharp neighbour's seam face is culled while the shell recedes by `radius` at every edge, exposing a ring into the neighbour's interior. Extends O1/A7 beyond shell-vs-shell z-fighting to shell-vs-sharp interior exposure; strengthens the case to decide O1 explicitly (burial should not fire against a shell neighbour, or the shell should not recede at buried sides).
20. **No-op patch drift.** `HEAD:cubeBodyState.ts:applyCubeBodyStylePatch` recomputes `frameMargin` for corners-only patches; IEEE drift makes an idempotent patch return a new state (history step, render impact). Dissolves with D2 (raw owner `applyPatch` compares per field).
21. **Editor literals mirroring domain constants.** `HEAD:cubeControlBindings.ts` `bodyInsetSchema.max 0.49` mirrors the private `maximumBodyInset`; corner enum options hand-listed instead of derived from `cubeCornerStyles`; `value as "rounded" | "sharp"` re-declares `CubeCornerStyle`. `controlBindingTypes.ts:asCubePartColor` has zero callers (verified: `rg asCubePartColor src tests` → definition only). Fold into S1 (radius schema follows A5; derive options from `cubeCornerStyles`; delete `asCubePartColor`).
