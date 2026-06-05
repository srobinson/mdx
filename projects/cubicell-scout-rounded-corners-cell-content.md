---
title: Cubicell scout rounded corners as cell content
type: projects
tags: [cubicell, scout, reuse, cell-content, rounded-corners, bevels, renderer-relief]
summary: Read only reuse map of cell, occupant, pose, media, thumbnails, and storyboard against a proposal that a filled cell body owns bevels
status: active
created: 2026-08-16
updated: 2026-08-16
project: cubicell
confidence: high
---

# Cubicell scout: rounded corners as cell content

Baseline: `ee511b8a8557c3d4af48079af6dfb4d7a88aab59` (`feat/renderer-relief` HEAD equals this SHA). Dirty worktree is a rejected rounded-rail spike. Repository source was not written.

## Verdict

The proposal is feasible only after it is restated. A grid cell is a location. A cube occupant is a hollow assembly of six planar faces and twelve rectangular edge bars. `CubicellContent` is face (and later cell) media. None of those three owners is a filled solid, so none of them can own bevels today.

A filled body that softens **corners** can be added as cube-occupant **render** geometry behind the existing faces and rails. The dirty `src/scene/edgeRelief.ts` spike rounded the **rails** and is the wrong owner. A unified rounded cube that replaces the six face and twelve edge instances is already rejected by `~/.mdx/projects/cubicell-scout-renderer-spike.md`. Putting bevels on `CubicellContent` or on `GridState` would mix media, layout, and silhouette.

**Decisive feasibility fact:** a cell-filling body can own corner softening only as a new cube-occupant part kind in `createCubeCellInstances`; the grid cell, `CubicellContent`, and the dirty edgeRelief rails cannot.

## Baseline owners

| Noun | Baseline owner | What it actually is |
| --- | --- | --- |
| Grid cell location | `src/domain/grid.ts:GridCoord`, `GridState`, `GridFormat` | Address plus format (`cellSize`, `gap`, `gapOverrides`, `origin`). No occupant, no mesh, no bevel. |
| Occupancy | `src/domain/neighbors.ts:createOccupancyMap` | `Map` of coord key to `CubeCell`. One cube per occupied coord. |
| Cube occupant | `src/domain/cube.ts:CubeCell` | `id`, `placement`, `size`, `visibility`, twelve `edges`, six `faces`. Always a cube. No body field. No `CellOccupant`. |
| Authored dimensions | `src/domain/cubeTopology.ts:CubeSize`; `src/domain/cube.ts:setCubeDimension`, `resizeCubeAnchored`; `src/domain/cubeOperations.ts:CubeOperation` kinds `set-cube-size` and `resize-cube` | Per-cube width, height, depth. Default `cubeUnitSize` `1`. Independent of `GridFormat.cellSize`. |
| Cube pose (document) | `src/domain/scene.ts:Pose` = `CubicellScene` minus `score` | `cells`, `frameId`, `grid`, `polarity`, `projection`. |
| Layout pose (derived) | `src/domain/gridLayout.ts:createSceneGridLayout`, `CubeLayoutPose` | Home from `getGridLinePosition` (coord times `cellSize + gap`); render position adds `placement.offset`; rotation and scale from placement. |
| Structure asset | `src/domain/workbench.ts:StructureAsset` | Named library asset: `stateIds`, `posterStateId`, `score`, `gridLock`. Does not own cells. |
| Structure cells | `src/domain/workbench.ts:collectStructureCells` | Union of cells from each State's pose, plus working pose, deduped by cube id. |
| State | `src/domain/workbench.ts:State` | `pose: PoseRevision` plus optional `view` and `hidden`. |
| Pose revision | `src/domain/project.ts:PoseRevision`, `getPoseRevisionDocument` | Pose plus `id`, `assetId`, `stateId`. Document is `CompactPose`. |
| Persistence | `src/persistence/recordCodecs/compactPose.ts:encodeCell`; `poseRevisionRecordCodec.ts:poseRevisionRecordSchemaVersion` `4`; `structureRecordCodec.ts:structureRecordSchemaVersion` `2` | Cell wire: id, visibility, coord, optional size, optional offset/rotation/scale, sparse edges, sparse faces including `CubicellContent`. Structure records store State references only. |
| Faces | `src/domain/cubeGeometry.ts:createCubeFacePlanes`; `src/scene/instancedPartMeshCore.ts:createInstancedPartMesh` `geometryKind: "plane"` | Unit `PlaneGeometry` scaled to face size. Content on `cubeFaceStateOwner.fields.content`. |
| Face media | `src/domain/content.ts:CubicellContent` | `stencil \| text \| image \| video`. Location independent. Shader `src/scene/faceContentShader.ts:applyFaceContentShader` samples through plane UVs. Atlas `src/scene/stencilAtlas.ts:createStencilAtlas`. |
| Edges | `src/domain/cubeGeometry.ts:createCubeEdgeSegments`; resolver `src/domain/edgeResolution.ts` plus junction claims; live mesh unit `BoxGeometry` | Rectangular bars that overshoot corners by thickness. Coverage `src/scene/edgeCoverageCore.ts`. Hit targets stay separate boxes. |
| Burial / coupling | `src/domain/exposure.ts:isFaceBuried`; `src/domain/cubeRenderResolution.ts:createCubeSceneRenderResolution` | Planar face-to-face coverage plus resolved edge segments. Shared by renderer and impact classifier. |
| Live layers | `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` | Opaque/translucent/ghost faces and edges, coverage, edge hit targets, neighbor slots. No body layer. |
| Camera pose math | `src/pose/viewPose.ts` (and siblings) | View framing. Distinct from document `Pose`. |
| State thumbnails | `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact`; `thumbnailRenderer.ts`; `thumbnailCache.ts`; `stateThumbnailReader.ts:createStateThumbnailReader` | Same `createCubeSceneInstances` + `createInstancedPartMesh` as live. Layers: opaque/translucent faces and edges only. |
| Storyboard | `src/thumbnail/stateStoryboardImage.ts:createStateStoryboardReader`; UI `src/panels/motion/StateStoryboard.tsx`; MCP via `src/studios/editor/useStudioObservationControl.ts` | Reads each State's pose through the thumbnail cache and composites the blobs. |

Doc vs code: `CUBICELL.md` and `ARCHITECTURE.md` sketch `CellContent = empty | cube | nested grid` and `GridCell { coord, content }`. `MODEL.v2.md` Current model limits records that this union does not exist. `~/.mdx/projects/cubicell-spec-content-union.md` specifies a later `ContentOccupant = { kind: "content"; content: CubicellContent }` beside Cube and Empty. `fmm` export search for `CellOccupant` / `CellContent` in `src/` is empty.

## Spike versus baseline

Dirty tree only (absent at `ee511b8`):

- New `src/scene/edgeRelief.ts`: `createEdgeReliefGeometry`, `createEdgeReliefMatrix`, `applyEdgeReliefShader` (canonical Z rounded extrusion, axis-aware instance matrices).
- New `tests/contracts/edge-relief.contract.test.ts` plus `tests/contracts/governance.json` local list and `maxCases` 29 to 35.
- `src/scene/cubeInstances.ts:createCubeCellInstances` visible-edge matrix routed through `createEdgeReliefMatrix`.
- `src/scene/instancedPartMeshCore.ts:createInstancedPartMesh` substitutes relief geometry and shader for `partKind === "edge"` and not picking.
- `src/scene/edgeCoverageCore.ts` drops the axis attribute and square coverage box; uses relief geometry and a Z-only centerline.
- `src/thumbnail/thumbnailArtifact.ts` gives edge layers explicit `partKind: "edge"` (this part is a latent baseline fix; see Q1).
- `src/domain/cubeEdgeState.ts:defaultCubeEdgeThickness` `0.014` to `0.06`.
- `budgets/initial-delivery.json` remeasured.

Hit-target boxes, face planes, face content, occupancy, compact pose, Structure, State, and storyboard composition are unchanged in intent. The spike changes **how rails look**, not **what occupies a cell**.

## Proposal assessment

"Real geometry fills each cube grid cell as the content body and therefore owns bevels or rounded corners."

| Claim | Baseline fact | Consequence |
| --- | --- | --- |
| The grid cell is a volume that can own silhouette | Cell is `GridCoord` plus format. Occupant is `CubeCell`. Product decision 2026-08-09: cell is a location; occupant is a union. | Bevels cannot be a grid-cell property. |
| Content body already fills the cell | Faces are zero-thickness planes at `±halfSize`. Edges are twelve bars. No interior mesh. Default gap `0.5` sits **between** cells. | Filling `cellSize` with a solid is a new visual. Filling `cellSize + gap` would close seams and break burial and junction proofs. |
| Content owns bevels | `CubicellContent` is stencil, text, image, or video on a face. Specified `ContentOccupant` is the same media value standing alone. | Media cannot own corner radius. |
| Rounded rails are the same as rounded corners | Design feedback this session: keep crisp straight rails and rigid faces; soften corners and junctions only. | `edgeRelief` and Three `RoundedBoxGeometry` on bars are the rejected shape. |
| One rounded cube instance can replace parts | Picking, selection chrome, face content, incremental slots, and thumbnails all key on six face and twelve edge identities (`~/.mdx/projects/cubicell-scout-renderer-spike.md` risk table). | Unified rounded cube remains reject. |

Feasible restatement: keep the cube occupant; add an optional **body** instance (unit box or corner-only mesh) behind the six planes; keep straight `BoxGeometry` rails and planar face UVs; treat corner softness as look policy first (no pose field) unless authoring is later approved.

## Reuse Map

- Reuse: `src/domain/grid.ts:GridState` / `GridCoord` as location only. Do not put radius, treatment, or body kind on format.
- Reuse: `src/domain/cube.ts:CubeCell` as the current cube occupant. Size, placement, edges, and faces stay the cube primitive (`ARCHITECTURE.md` item 4).
- Reuse: `src/domain/cube.ts:setCubeDimension`, `resizeCubeAnchored`, `cubeOperations.ts` `set-cube-size` / `resize-cube` for authored dimensions.
- Reuse: `src/domain/gridLayout.ts:createSceneGridLayout` for world homes. Body matrices multiply the same `cellMatrix` already used for faces and edges.
- Reuse: `src/domain/content.ts:CubicellContent` and `src/scene/faceContentShader.ts:applyFaceContentShader` for media. Later `ContentOccupant` reuses this value; it does not become a mesh.
- Reuse: `src/domain/cubeGeometry.ts:createCubeFacePlanes` and `createCubeEdgeSegments` plus `src/domain/edgeResolution.ts` / `edgeJunctionResolution.ts`. Do not invent a second cube derivation.
- Reuse: `src/scene/cubeInstances.ts:createCubeCellInstances`, `createCubeSceneInstances`, `createCubeSceneInstanceContexts` (resolution via `createCubeSceneRenderResolution`).
- Reuse: `src/scene/instancedPartMeshCore.ts:createInstancedPartMesh` / `createInstancedPartMeshWithGeometry` for any new body geometry. Same sync, patch, grow, dispose path.
- Reuse: `src/scene/renderCubeScenePartLayers.tsx:renderCubeScenePartLayers` and `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` as the two surfaces that must both grow a body layer or the storyboard will omit it.
- Reuse: `src/thumbnail/stateThumbnailReader.ts:createStateThumbnailReader` and `src/thumbnail/stateStoryboardImage.ts:createStateStoryboardReader` without a second capture path.
- Reuse: `src/persistence/recordCodecs/compactPose.ts:encodeCell` unchanged if corner softness is look policy. Structure records stay out of cell geometry.
- Reuse: thickness spine in `~/.mdx/projects/cubicell-scout-shape-domain.md` if a later **authored** corner or edge treatment is approved (`set-edge-state` already carries `Partial<CubeEdgeState>`).
- Existing infra: `src/theme/scenePolarity.ts` optical face/edge lightness; `src/scene/colorSpace.ts:shiftLightnessForContrast`. Try this before physical bevels (`cubicell-scout-renderer-spike.md`).
- Similar checked and rejected: `src/scene/edgeRelief.ts` (dirty) and Three `RoundedBoxGeometry` on rails. Wrong owner; nonuniform scale distorts radius; junctions and coverage assume rectangles (`cubicell-scout-renderer-spike.md` Q3, Q4).
- Similar checked and rejected: one `RoundedBoxGeometry` per cube. Drops face and edge instance identity, face content slots, and part picking.
- Similar checked and rejected: `@react-three/drei/RoundedBox`. Bypasses instance slots, incremental patches, thumbnails.
- Similar checked and rejected: `MeshStandardMaterial` plus lights. Live and thumbnail paths are unlit `MeshBasicMaterial` with no lights.
- Similar checked and rejected: persist `bevel` on `GridState`, `CubicellContent`, `State`, or transitions for a first look pass.
- Similar checked and rejected: filling the gap as well as `cellSize`. Seams, neighbor slots, and `isFaceBuried` assume the gap remains empty.
- None found: `CellOccupant`, `CellContent`, body part kind, `shapeSize`, `CubeEdgeTreatment` in `src/` (fmm search). Occupant union and per-edge shaping remain specified, not shipped.

## Quality Map

- Duplication / parallel implementation: live `renderCubeScenePartLayers` already tags edge `partKind`; baseline `createThumbnailArtifact` omitted edge `partKind`, so a part-kind treatment can miss State thumbnails and the storyboard. The dirty spike fixes this locally. Grooming: refactor first if any treatment keys on `partKind`.
- Duplication / parallel implementation: `CubeEdgeState` fields are enumerated in owner, `compactPose`, workbench validation, authored-operation validation, `selectionAspects`, and `authoredRenderImpact` (`cubicell-scout-shape-domain.md`). Adding `treatment` / `shapeSize` without one shared key list will drop the field on reload.
- Boundary / design issue: `CubeCell` still conflates location (`placement.coord`) with cube occupant. Building a cell-filling "content body" on that type hardens the missing `GridCell` / `CellContent` split (`MODEL.v2.md` limits).
- Boundary / design issue: `isFaceBuried` and junction proofs are planar/rectangular. Rounded rails or a rounded replacement cube invalidate coverage proofs without a new resolver.
- Boundary / design issue: face content UVs assume `PlaneGeometry`. A beveled face patch needs leftover planar regions or a new UV contract.
- Dead code / obsolete path: dirty `edgeRelief` plus thickness `0.06` should stay unmerged. Baseline coverage axis attribute is the live owner.
- Grooming recommendation: refactor first the thumbnail edge `partKind` classification if a body or corner treatment is shared. Defer occupant-union extraction until a body visual has a proven look. Defer authored `treatment` / `shapeSize` until design chooses per-edge shaping versus corner-only look policy.

## Plan

- Decision needed:
  1. Confirm the restatement: cube-occupant body plus corner softness; rails stay straight; faces stay planar.
  2. Look policy (theme / build flag) versus authored field. First pass should stay look policy so `encodeCell` and `authoredOperationSchemaVersion` (now `6`) stay still.
  3. Body behind faces versus replacing faces. Behind faces preserves content, burial, and picking.
  4. Relationship to the still-unbuilt occupant union and to the 2026-07-12 per-edge `treatment` spec. Corner-only look policy can ship without that spec; per-edge chamfer cannot.
- Proposed steps bound to the reuse map:
  1. Do not merge `feat/renderer-relief` dirty files as the corner solution.
  2. If a visual comparison is still wanted, keep the optical ramp path from `cubicell-scout-renderer-spike.md` on a scratch branch with a pristine tree.
  3. If a filled body is wanted after that, add `body` to `CubeCellInstances` / `CubeSceneInstances`, emit one instance from `createCubeCellInstances` using `cell.size` and `cellMatrix`, mount it in `renderCubeScenePartLayers` **and** `createThumbnailArtifact`, keep face planes and edge boxes.
  4. Corner softening: first a small look-system or shader treatment on the body only. Do not reuse `edgeRelief` rails.
  5. Prove live canvas, State thumbnails, and `createStateStoryboardReader` agree. Then decide whether occupant union work should precede any persisted radius.
- Tests and gates:
  - `pnpm exec vitest run tests/contracts/incremental-scene-equivalence.contract.test.ts tests/contracts/thumbnail-camera.contract.test.ts --project unit --no-cache --maxWorkers=1`
  - Browser face-media / stencil contract if faces stay the content carrier
  - `CUBICELL_MCP_VERIFY_WAIT_MS=30000 pnpm verify:mcp` for capture and storyboard
  - `pnpm build:budget` and `node scripts/check-delivery-budget.mjs` plus `pnpm measure:initial-delivery` if new geometry is added
  - No new file over 700 lines; `cubeOperations.ts` and `cubeInstances.ts` are the size watches
  - Final `git status --short` must match the snapshot below if the work stays read only

## Tree snapshot (read only)

```
 M budgets/initial-delivery.json
 M src/domain/cubeEdgeState.ts
 M src/scene/cubeInstances.ts
 M src/scene/edgeCoverageCore.ts
 M src/scene/instancedPartMeshCore.ts
 M src/thumbnail/thumbnailArtifact.ts
 M tests/contracts/governance.json
?? src/scene/edgeRelief.ts
?? tests/contracts/edge-relief.contract.test.ts
```

This scout wrote only `~/.mdx/projects/cubicell-scout-rounded-corners-cell-content.md`.
