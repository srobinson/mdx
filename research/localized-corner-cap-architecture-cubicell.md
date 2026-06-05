---
title: Cubicell localized corner cap architecture candidate
type: research
tags: [cubicell, architecture, renderer, corners, instancing, thumbnails]
summary: Production design for soft cube corners using derived junction caps while keeping rails, faces, persistence, and content unchanged
status: active
source: codebase-analyst
confidence: high
created: 2026-08-16
updated: 2026-08-16
project: cubicell
---

# Cubicell localized corner cap architecture candidate

Baseline: `ee511b8a8557c3d4af48079af6dfb4d7a88aab59`. The current dirty tree contains a rejected rounded rail experiment. This document does not adopt that experiment.

## Usage, caller's view

Callers keep using the current scene APIs. Corner construction stays inside edge resolution and scene instance derivation.

### Live scene

```ts
const owner = createIncrementalCubeSceneOwner(renderInput, acceptedBatch);
const buckets = resolveCubeInstanceBuckets(owner.current.instances, owner.current.slotState);

renderCubeScenePartLayers({
  ...existingProps,
  instanceBuckets: buckets,
});
```

The caller passes no radius, body style, corner list, or special mesh. `createIncrementalCubeSceneOwner` derives the same corner caps as a full scene build. `renderCubeScenePartLayers` receives the new cap buckets with the existing face and edge buckets.

### Fresh scene and State thumbnail

```ts
const instances = createCubeSceneInstances(
  pose.cells,
  createSceneGridLayout(pose.grid, pose.cells),
  null,
  null,
);

const artifact = createThumbnailArtifact(pose, stencilAtlas, instances);
```

`createThumbnailArtifact` consumes the same authored layer specifications as the live scene. State thumbnails and storyboard frames therefore enroll corner caps without a second geometry decision.

### Stable incremental patches

```ts
const slotOwner = createCubeInstanceSlotOwner(initialInstances);
const patches = slotOwner.apply(changedCells);
const next = createCubeInstanceSlotState(slotOwner.registry, patches);
```

Cap slots follow the same changed cell map as faces and edges. Callers do not reconcile corner ownership or rebuild meshes after a local edit.

These examples are the contract. Product code gains no corner specific authoring API.

## Problem

Cubicell renders a cube as six planes and twelve resolved rectangular bars. Each bar remains straight, and `edgeJunctionResolution.ts` decides which bar owns material where bar ends meet. The rejected dirty experiment changes every bar to a rounded extrusion. That changes the rail shape across its full length and invalidates the rectangular junction proof.

A filled body behind the frame also misses the exterior corner. Current bars straddle the face boundary and extend beyond the cube body envelope. A body inside the six face planes cannot cover those bar ends. Expanding the body around them would need per edge thickness, visibility, color, opacity, selection, and ownership. It would also change what hidden or translucent faces reveal.

The production owner is the existing edge junction resolver. It already knows the incident bars, their world meeting point, their thickness, and the winning edge claim. It can reserve a small corner region, retreat the three straight bars, and emit one derived cap owned by the winning edge. The cap replaces material that the baseline bars already occupy. It never expands cube bounds.

## Project metadata

| Item | Current value |
| --- | --- |
| Language | TypeScript 6.0, React 19 |
| Renderer | Three 0.185.1, React Three Fiber 9.6.1, WebGL `MeshBasicMaterial` |
| Build | Vite 8, pnpm |
| State | Zustand 5, plain serializable domain records |
| Test | Vitest 4.1, Playwright 1.61, governed unit and Chromium contracts |
| Source scale | 501 indexed source files, 62,113 LOC |
| Baseline | `ee511b8a8557c3d4af48079af6dfb4d7a88aab59` |
| Repository state | Dirty rejected rail relief experiment, preserved unchanged |

The repository has an active FMM index. `ARCHITECTURE.md:149-166` assigns cube geometry to `cubeGeometry.ts`, edge resolution to the exposure and resolution modules, and stable GPU slots to the scene instance modules. `PRODUCT.md:19-25` keeps explicit faces and edges plus an opaque interior.

## Recommended shape

### One derived edge resolution

Replace the segment only result with one resolution value that contains straight segments and eligible corner caps.

```ts
export type EdgeDrawResolution = {
  segments: EdgeDrawSegments;
  cornerCaps: ReadonlyMap<string, ReadonlyMap<string, ResolvedCornerCap>>;
};

export type ResolvedCornerCap = {
  axis: AxisIndex;
  id: string;
  incidentEdgeIds: readonly [CubeEdgeId, CubeEdgeId, CubeEdgeId];
  ownerEdgeId: CubeEdgeId;
  position: Vec3;
  rotation: Vec3;
  size: Vec3;
};
```

The outer map key is the owner cube id. The inner key is stable for the winning edge end. `position`, `rotation`, and `size` use owner cell local coordinates, matching the existing `CubeEdgeSegment` boundary. No color, opacity, tween, selection, or Three object enters the domain result.

A junction qualifies for a cap only when all conditions hold:

1. Three mutually perpendicular, visually present bar ends meet.
2. Each line contributes one end.
3. All three ends belong to the same `CubeCell`.
4. The three edge ids form one cube vertex.
5. The generated cap stays inside the union of the baseline rectangular bar envelopes.

Shared, collinear, concave, non manifold, and incomplete junctions keep the current resolution. Hiding any incident edge removes the cap and restores the current square end behavior. Zero gap cube joins keep the current contention result.

The current owner line remains the visual owner. The cap inherits its edge id. The resolver retreats all three incident segments only after it has selected the owner. Cap size derives from the incident edge thicknesses and clamps to half the shortest available segment. This prevents negative rail length on small or heavily resolved edges.

### One canonical cap geometry

Add one canonical `BufferGeometry` factory for a trihedral corner connector. Its three sockets meet square straight rails. Curvature exists only around the outer vertex. The geometry has no rounded section along a rail.

```ts
export function createCornerCapGeometry(): BufferGeometry;

type InstancedPartMeshOptions = {
  capacity: number;
  geometryKind: "box" | "corner-cap" | "plane";
  // existing options unchanged
};
```

The factory owns the fixed curve count and profile. Callers cannot select segment count or radius. `ResolvedCornerCap.size` deforms the canonical cap through its instance matrix. Nonuniform incident thickness produces a bounded ellipsoidal corner that still meets each straight rail.

The implementation must allocate the geometry once per mesh, never per cell. The initial acceptance limit is at most 96 position vertices in the shared geometry and at most eight cap instances per cube. Record the generated count in a contract and set the final limit to the observed value if it is lower.

`MeshBasicMaterial` remains. The cap uses the existing edge color treatment and the winning edge's color tween. A lighting rig, normal shader, new material family, or mutable shader key would add unrelated policy.

### Edge owned scene instances

A cap is an edge owned render part. That preserves color, opacity, motion, and selection without a new authored state.

```ts
export type CubeCornerCapInstance = CubeEdgeInstance & {
  cornerKey: string;
};

export type CubeCellInstances = {
  cornerCaps: CubeCornerCapInstance[];
  edgeHitTargets: CubeEdgeInstance[];
  edges: CubeEdgeInstance[];
  faces: CubeFaceInstance[];
  ghostCornerCaps: CubeCornerCapInstance[];
  ghostEdges: CubeEdgeInstance[];
  ghostFaces: CubeFaceInstance[];
};

export type CubeSceneInstances = {
  edgeHitTargets: CubeEdgeInstance[];
  ghostCornerCaps: CubeCornerCapInstance[];
  ghostEdges: CubeEdgeInstance[];
  ghostFaces: CubeFaceInstance[];
  opaqueCornerCaps: CubeCornerCapInstance[];
  opaqueEdges: CubeEdgeInstance[];
  opaqueFaces: CubeFaceInstance[];
  translucentCornerCaps: CubeCornerCapInstance[];
  translucentEdges: CubeEdgeInstance[];
  translucentFaces: CubeFaceInstance[];
};
```

`createCubeCellInstances` reads `context.edges.cornerCaps.get(cell.id)`. It resolves color, opacity, hidden ghost state, selection scale, and `options.colorTweens.edges.get(ownerEdgeId)` from the same edge data used by the winning rail.

`CubeCornerCapInstance` retains `cubeId`, `edgeId`, and `axis`, so selection styling can follow the owner edge. Its stable slot key is `corner:${cubeId}:${cornerKey}`. Rail keys remain unchanged.

### Shared authored layer specifications

Live and thumbnail layer metadata has already drifted. Baseline thumbnails omitted edge `partKind`, while the dirty spike patched only the thumbnail list. Fix that duplication before adding cap layers.

```ts
export type AuthoredCubePartLayer =
  | "opaqueCornerCaps"
  | "opaqueEdges"
  | "opaqueFaces"
  | "translucentCornerCaps"
  | "translucentEdges"
  | "translucentFaces";

export type CubePartLayerSpec = {
  doubleSide?: boolean;
  geometryKind: "box" | "corner-cap" | "plane";
  key: AuthoredCubePartLayer;
  partKind: "edge" | "face";
  raycast: "ignore" | "parts";
  translucent?: boolean;
};

export const authoredCubePartLayerSpecs: readonly CubePartLayerSpec[];
```

`renderCubeScenePartLayers.tsx` and `thumbnailArtifact.ts` consume this list. Editor only layers remain explicit: edge coverage, edge hit targets, ghosts, and neighbor slots. Ghost caps use the same canonical geometry and edge treatment.

This list owns geometry, material class, part kind, raycast policy, and opacity class. Callers still own their distinct jobs. The React caller attaches pointer handlers. The thumbnail caller creates disposable Three meshes. The specification does not absorb lifecycle or interaction code.

### Full and incremental resolution stay equivalent

```ts
export function resolveEdgeDrawResolution(
  occupancy: OccupancyMap,
  layout: SceneGridLayout,
): EdgeDrawResolution;

export type IncrementalEdgeResolution = {
  readonly current: EdgeDrawResolution;
  update(
    cellsById: ReadonlyMap<string, CubeCell>,
    changedEdges: ReadonlyMap<string, ReadonlySet<CubeEdgeId>>,
    reindexedEdges: ReadonlyMap<string, ReadonlySet<CubeEdgeId>>,
  ): IncrementalEdgeResolutionUpdate;
};
```

`resolveEdgeDrawSegments` is replaced in the same change. No compatibility wrapper remains. Both full and incremental paths call the same pure junction function that selects an owner, writes segment retreats, and returns an optional `ResolvedCornerCap`.

The incremental resolver stores caps by junction key. A changed cap rederives its old owner cell and new owner cell. That covers ownership changes after edge visibility, cell insertion, cell removal, resize, rotation, or gap changes. The existing `createCubeCellInstances` call chain stays unchanged.

## Data flow

1. `createEdgeClaimBarEnds` produces visible bar ends and stable quantized junction keys. Current source: `src/domain/edgeJunctionResolution.ts:106-122`.
2. `resolveJunction` groups parallel lines and selects one owner. Current source: `src/domain/edgeJunctionResolution.ts:137-177`.
3. The revised resolver returns a cap only for a same cell trihedral corner. It writes equal semantic retreats for the incident rails.
4. `CubeRenderResolutionPass` carries the complete edge draw result beside buried faces. Current source: `src/domain/cubeRenderResolution.ts:8-19`.
5. `createCubeCellInstances` emits faces, trimmed straight rails, hit targets, and owner edge caps. Current source: `src/scene/cubeInstances.ts:117-219`.
6. `collectCubeSceneInstances` partitions caps by opacity and hidden state beside edges and faces. Current source: `src/scene/cubeInstances.ts:221-249`.
7. Stable slots patch only changed cells. Current bucket and key owners: `src/scene/cubeInstanceSlots.ts:15-54,140-147`.
8. Live and thumbnail mesh creation share `authoredCubePartLayerSpecs`. Current separate callers: `src/scene/renderCubeScenePartLayers.tsx:23-121` and `src/thumbnail/thumbnailArtifact.ts:55-96`.
9. `thumbnailRenderer` supplies the same scene instances to atlas sync and artifact construction. Current source: `src/thumbnail/thumbnailRenderer.ts:105-143`.
10. Storyboards continue reading State thumbnails. No storyboard geometry path changes.

The call chain stays short. Junction policy lives in domain resolution. Matrix and bucket policy lives in scene derivation. Mesh allocation stays in the instanced mesh core.

## Module map

| File | Change | Ownership reason |
| --- | --- | --- |
| `src/domain/edgeResolutionTypes.ts` | Add `EdgeDrawResolution` and `ResolvedCornerCap` | Closed derived geometry contract |
| `src/domain/edgeJunctionResolution.ts` | Return an optional cap while resolving retreats | Already owns bar end contention and the winning line |
| `src/domain/edgeResolution.ts` | Replace segment only API with full edge draw resolution | One full scene entry point |
| `src/domain/incrementalEdgeResolution.ts` | Track segment and cap changes together | Keeps incremental output equivalent to full output |
| `src/domain/cubeRenderResolution.ts` | Carry `edges: EdgeDrawResolution` in each pass | Existing burial and edge resolution boundary |
| `src/scene/cornerCapGeometry.ts` | Create the one shared canonical cap geometry | Renderer only geometry, no document data |
| `src/scene/cubeInstances.ts` | Emit cap instances from resolved caps | Existing cell to instance translation |
| `src/scene/cubeInstanceSlots.ts` | Add cap buckets and keys | Existing stable GPU slot owner |
| `src/scene/cubePartLayerSpecs.ts` | Define shared authored mesh specifications | Removes live and thumbnail metadata duplication |
| `src/scene/instancedPartMeshCore.ts` | Accept `geometryKind: "corner-cap"` | Existing custom geometry and lifecycle owner |
| `src/scene/renderCubeScenePartLayers.tsx` | Render cap buckets with raycasts ignored | Existing live layer composition |
| `src/thumbnail/thumbnailArtifact.ts` | Build cap meshes from shared specifications | Existing State artifact geometry owner |

No persistence, grid, content, operation, panel, State, transition, or Structure module changes.

## Invariants

### Straight rails

Every rail remains `BoxGeometry`. The resolver changes length and center only at an eligible endpoint. Cross sections stay rectangular. A contract checks that the two cross dimensions equal the authored thickness and that the rail axis remains one of the cube axes.

### Local corner softness

The cap occupies only the material removed from the three baseline bar ends. Its world bounds must fit inside the union of those baseline bar boxes. This keeps focus bounds, selection chrome, camera framing, burial bounds, and seam extents valid.

### Face media

Faces remain `PlaneGeometry`. Face ids, UVs, content attributes, atlas slots, material hooks, and shader keys do not change. `CubicellContent` stays stencil, text, image, or video. Current media shader ownership: `src/scene/faceContentShader.ts` and `src/scene/stencilAtlas.ts`.

### Coverage

The live edge coverage mesh already consumes each edge instance matrix and axis at baseline `edgeCoverageCore.ts:148-181`. It therefore follows the trimmed straight rail without a second endpoint calculation. Cap meshes do not enter the screen width coverage pass. Their fixed geometry is larger than the one pixel rail guarantee, and they never extend coverage beyond the baseline bar envelope.

The dirty spike must not replace the coverage box with the rounded rail geometry. That change erases the axis attribute and makes coverage geometry own the visible shape.

### Picking and selection

Rail hit target boxes keep their current authored size and cover the cap neighborhood. Cap meshes ignore raycasts, so the current edge targets and face planes keep ownership of pointer grammar. This avoids a second picking system and preserves the handlers in `src/scene/useCubeSceneInteractions.ts:36-91`. Corner overlap between incident edge hit boxes remains the same as baseline.

Selection chrome still derives from cube size and selection. The cap cannot enlarge the baseline edge envelope. A selected owner edge may scale its cap with `selectedEdgeThicknessScale`; no new selection kind enters `CubeSelection`.

### Seams and burial

Only same cell, three line exterior junctions qualify. Shared line junctions, occupied zero gap joins, concave joins, non manifold joins, and incomplete corners keep the current bar resolver. `isFaceBuried` and face coupling remain unchanged.

### Motion

Cap transforms derive from the staged cell layout. Cap color, opacity, and tween derive from the owner edge. `CubePartColorTweens.edges` already carries edge tweens at `src/evaluation/scoreAt.ts:38-42`. Presence zero still removes the whole cell before instance derivation. No transition field or persisted radius appears.

### Persistence

Corner softness is a renderer look policy. `CubeCell`, `CubeEdgeState`, `CubeFaceState`, `CompactPose`, record schema versions, and authored operation schema versions remain byte for byte compatible. This project permits breaking changes, but none is justified for a derived corner treatment.

### Cost

The design adds at most eight cap instances per cube. Opaque, translucent, and ghost cap buckets each own one long lived geometry and add at most three live draw calls. State artifacts use opaque and translucent cap meshes. No geometry allocation scales with cell count. Promotion requires measured bundle, draw count, frame time, and generated vertex counts.

## Interface depth

Most callers see no new method. `resolveEdgeDrawResolution` hides eligibility, ownership, retreat, clamp, and cap frame calculation. `createCubeCellInstances` hides color, tween, selection, and bucket mapping. `authoredCubePartLayerSpecs` hides live and thumbnail geometry classification.

Only the domain to scene boundary sees `ResolvedCornerCap`. That type contains the exact local transform data the scene needs and omits renderer objects and look constants. The interface stays smaller than the policy it hides.

## Synthesis decision

This file is one arena candidate, so cross candidate synthesis remains the judge's job. I recommend the edge junction cap shape as the base. It is the only examined shape that keeps rails straight, preserves face and edge identity, and changes the visible corner material at the owner that already resolves that material.

The filled body idea remains a separate product option. It does not solve the external frame corner without the same junction retreat work.

## Tradeoffs accepted

- We accept up to eight extra cap instances per cube and at most three live draw calls in exchange for localized curvature and stable edge identity.
- We accept a fixed renderer look in exchange for unchanged document, command, persistence, and transition schemas.
- We accept an ellipsoidal cap when three incident thicknesses differ in exchange for one canonical topology and bounded instancing.
- We accept square ends when a corner lacks three visible incident edges in exchange for honest visibility semantics and no floating cap.
- We accept the current owner edge's color at a mixed color junction in exchange for deterministic motion and selection with no invented body color.

## Alternatives considered

### Filled cube body behind faces and rails

One body instance per cube offers a small mesh interface. The apparent simplicity hides unresolved policy. The body needs a color and opacity owner. It changes what hidden and translucent faces reveal. Its surface sits inside the external rail envelope, so the existing bar junction still defines the visible corner. Expanding it to cover that junction requires per edge thickness and the same retreat algorithm as the recommended design. This alternative lost because it exposes product semantics while failing to remove the renderer work.

A later opaque interior body can reuse `createCubeSceneInstances`, custom geometry, stable slots, shared layer specifications, and thumbnails. It should arrive through an explicit product decision about face visibility and interior color.

### One rounded cube replacing faces and edges

This produces one body instance and a familiar rounded silhouette. It removes the six face instances and twelve edge instances that carry face media, part colors, picking, stable slot keys, selection, and motion. Recreating those semantics would expose face and edge partitioning through a large custom shader and picking protocol. The smaller draw count does not yield a deeper interface.

### Rounded edge bars

The dirty `edgeRelief.ts` experiment substitutes an extruded rounded cross section for every rail. It rounds the full rail and keeps square end caps. It also replaces the baseline coverage geometry and drops the axis attribute. The result changes the wrong dimension and conflicts with the current rectangular junction proof. No part of this geometry should become the corner solution.

### Shader only corner mask

A fragment mask on face planes cannot create correct depth or arbitrary view silhouettes. A shader on edge boxes either rounds the rail cross section or discards bar ends without supplying replacement depth. It also has to compose with opacity and face content hooks. This alternative hides little and leaks shader policy into several materials.

## Red flag screen

### Shallow modules

No new coordinator with several public methods is proposed. The junction resolver returns one complete value. The canonical geometry factory has no caller options. The layer specification is data consumed by two existing lifecycle owners.

### Information leakage

Curve count, radius profile, eligibility, owner choice, and retreat calculation each have one owner. Persistence and product types never see them. Three types never enter the domain resolver.

### Temporal decomposition

Full resolution and incremental resolution use the same junction function. There is no sequence of public `find`, `trim`, `cap`, and `commit` calls. `resolveEdgeDrawResolution` completes the operation.

### Pass through methods

`resolveEdgeDrawSegments` is replaced. A compatibility wrapper would leave two names for one operation and is rejected. `createInstancedPartMesh` remains the geometry and lifecycle owner rather than adding a corner mesh facade.

## First implementation slice

Work in a clean worktree at `ee511b8`. Preserve the rejected dirty spike in its current worktree. First, extract `authoredCubePartLayerSpecs` and make live plus thumbnail callers consume it. Prove current face and edge output unchanged, including baseline edge `partKind`. Then add `EdgeDrawResolution` and `ResolvedCornerCap` to the full and incremental domain resolvers with no renderer output yet. The slice ends when a contract proves full and incremental segment plus cap results remain equivalent through add, remove, resize, rotate, edge visibility, and gap changes.

## Remaining implementation sequence

1. Add `cornerCapGeometry.ts` with one fixed profile and a geometry count contract.
2. Add cap instance types, opacity buckets, stable keys, and incremental slot patches.
3. Render cap layers live and in State thumbnails from the shared specifications.
4. Keep cap raycasts ignored and prove existing edge hit targets cover the cap neighborhood.
5. Add real browser proof for edge mode picking, face media, hidden edges, mixed thickness, nonuniform cube size, motion scrub, zero gap joins, and compact viewports.
6. Run State capture and storyboard verification through `verify:mcp`.
7. Measure production build size, draw calls, geometry counts, idle frame time, and scrub frame time. Update only justified delivery budget fields.
8. Compare the live result head on and at 45 degrees. Reject the geometry if rails appear rounded, caps float, seams close, or mixed thickness creates holes.

## Verification gates

```sh
pnpm exec vitest run \
  tests/contracts/incremental-scene-equivalence.contract.test.ts \
  tests/contracts/thumbnail-camera.contract.test.ts \
  --project unit --no-cache --maxWorkers=1

pnpm test:browser
CUBICELL_MCP_VERIFY_WAIT_MS=30000 pnpm verify:mcp
pnpm build:budget
node scripts/check-delivery-budget.mjs
CUBICELL_MEASUREMENT_OUTPUT=/tmp/cubicell-corner-caps.json pnpm measure:initial-delivery
```

Add focused contracts for cap eligibility, owner stability, rail retreat, cap bounds, stable slot patches, owner edge tween, and generated geometry counts. Browser proof must click an actual cap and inspect the selected edge. Pixel proof must compare the live canvas, a State thumbnail, and the storyboard for the same pose.

## Open questions and risks

- Does the fixed cap profile read as a soft corner with the current unlit material at both head on and oblique views?
- Should a mixed color junction use the current line owner color, or should mixed color corners remain square?
- Should selected cap scale follow only the owner edge or the largest selected incident edge?
- What observed vertex count and frame cost should become the permanent cap geometry limit after the first real mesh exists?
- Does an opaque interior body remain a product goal once localized cap geometry solves the frame corner?

The first three questions need visual and interaction evidence. They do not require persisted state.
