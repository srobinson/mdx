# Cubicell shading scout: light direction and lattice occlusion

Phase 1 read-only audit. Baseline `main` at `67c6dde`. Tracked tree unchanged
(`CLAUDE.md` modified and `EXPORT.md` untracked are pre-existing and ignored).

Renderer premise verified: no light of any kind exists under `src`, and
`MeshBasicMaterial` is the only material constructed. A and B stay in colour.

## Reuse Map

- Reuse: `src/domain/worldGeometry.ts` `createRotationBasis` builds the world
  basis from a pose rotation, matching Three's XYZ Euler order. Its entry at
  the face's axis index, signed by the face's `positionSign`, is the face's
  world normal. A needs no new geometry.
- Reuse: `src/domain/cubeTopology.ts` `cubeFaceTopology` already carries `axis`
  and `positionSign` per face, which is the local face normal in decomposed
  form. No normal table exists as such; A should add one accessor here rather
  than inline a seventh copy of the axis/sign pair.
- Reuse: `src/domain/gridLayout.ts` `CubeLayoutPose.rotation` inside
  `SceneGridLayout` is the authored world rotation per cube, and it is the same
  value a turn writes. This is the world orientation the colour path lacks.
- Reuse: `src/scene/colorSpace.ts` `setLinearSrgbToOklab` and
  `setOklabToLinearSrgb` are the OKLab converters, with module scratch that
  keeps the per-frame path allocation free. They are module private, so A adds
  a signed operator beside `shiftLightnessForContrast` in this file and shares
  them.
- Reuse: `src/scene/instancedPartMeshCore.ts` `resolveTreatedPartColor` is the
  single point where every part colour is finalised, for faces, edges, slots,
  and face content alike. Its `ColorWriteContext` is the one carrier that would
  need to reach A and B.
- Reuse: `src/scene/cubeInstances.ts` `createCubeCellInstances` holds `pose` and
  `cellMatrix` while building each face instance. This is the correct place to
  resolve a per-cube, per-face delta once, keeping colour resolution free of
  matrix decomposition.
- Reuse: `src/domain/exposure.ts` `classifyEdgeJunction` already reads the
  four-quadrant occupancy mask around every edge and returns `convex`,
  `flat-seam`, `non-manifold`, `concave`, or `interior`. `concave` is the
  inside-corner signal B wants. It is an exported domain primitive already
  consumed by `src/domain/edgeClaimResolution.ts` and
  `src/domain/selectionAspects.ts`.
- Reuse: `src/domain/cubeTopology.ts` `getCubeFaceEdgeIds` returns the four
  edges bounding a face, which is how B turns per-edge junctions into a
  per-face occlusion weight.
- Reuse: `src/domain/neighbors.ts` `createOccupancyMap`, `OccupancyIndex`, and
  `getNeighborCoord` are the single owner of structural occupancy, documented
  as shared by the shadow shell and the exposure derivations. Nine call sites
  already consume it. B must not open a second occupancy pass.
- Reuse: `src/domain/incrementalCubeRenderResolution.ts` `updateBuriedFaces` and
  `collectFaceNeighborIds` already expand an edit to its face neighbours and
  recompute per-face topology incrementally. B's invalidation is this machinery,
  not new code.
- Reuse: `src/scene/instanceSlotRegistry.ts` `changedAttributes` is the dirty
  attribute diff that decides whether a slot uploads colour. A and B both
  depend on extending what it compares.
- Reuse: `src/shared/vec3.ts` `dotVec3` is the dot product for the light
  direction against the world normal.
- Reuse: `src/domain/cubeOperations.ts` `isViewLaneSceneOperation` defines the
  view lane: scene-level authored view state that lives on the document, never
  enters document history, and is non-reversible. `set-scene-polarity` is
  already in it. An authored light direction is the same shape.

- Existing infra: `src/domain/cubeRenderResolution.ts` `createBuriedFaceIndex`
  and `resolveBuriedCubeFaces` produce a per-cube set of buried faces that
  `createCubeCellInstances` uses to cull. This is the proof that a directly
  abutting neighbour is never drawn, which is what reshapes B (below).
- Existing infra: `PERFORMANCE.md` sets the budgets A and B must respect.
  Principle 2, work scales with changed data not scene size. Principle 3, a
  settled viewport consumes no continuous render budget. The shipped P0
  incremental gate records zero full mesh synchronisations, two patch calls,
  one edited cell, five affected derivation cells, zero occupancy rebuilds, and
  156 uploaded bytes at 250 and 2,025 cells. It also states that opacity,
  colour, and selection overlays must not recreate topology.
- Existing infra: `tests/contracts/governance.json` with
  `scripts/check-test-governance.mjs` caps the contract suite by file
  allowlist, case count, and per-file lines.
- Existing infra: `src/config/cubicellConfig.ts` is the established home for
  scalar feel knobs, at 99 lines with room. Correct home for the ramp
  magnitudes. Wrong home for the direction itself, which is authored.

- Similar checked and rejected: `src/scene/colorSpace.ts`
  `shiftLightnessForContrast` shifts lightness *away from the nearer extreme*,
  choosing its direction from the resolved colour so dark lightens and light
  darkens. A needs a *signed* shift, because a face turned toward the light
  must brighten and a face turned away must darken irrespective of the
  authored colour. Reusing it would make a lit face and an unlit face move the
  same way on a mid-tone and invert across the 0.5 boundary. A needs a second
  operator in this file, not this one.
- Similar checked and rejected: `src/domain/exposure.ts` `isFaceBuried` answers
  "is this face covered by a neighbour" exactly, in world space, honouring
  transforms, gaps, scale, visibility, and opacity. It is wrong-shaped for B
  because a face it returns true for is culled before it reaches the renderer.
  It decides whether a face is drawn, not how a drawn face is shaded.
- Similar checked and rejected: `src/scene/seamGeometry.ts` and
  `src/scene/SeamLayer.tsx`. `seamSurfacesEnabled` in
  `src/config/cubicellConfig.ts` is `false`, parked since 2026-07-12 pending a
  UX rethink, and gates both `SeamLayer` in `src/scene/CubeScene.tsx` and
  `SeamRevealHold` in `src/studios/editor/EditorStudio.tsx`. The file computes
  pure geometry and reads no occupancy. B must not be built on it.
- Similar checked and rejected: `src/scene/edgeCoverageCore.ts` is a screen
  space edge coverage shader operating on pixel spans. It does no colour
  resolution and holds no occupancy.
- Similar checked and rejected: `src/theme/scenePolarity.ts`
  `cubeFaceLightnessDeltaById` is the constant table A replaces. It is keyed by
  `CubeFaceId` only, so it is local to the cube and rotates with it, which is
  the defect A exists to fix.

- None found: no world-space normal is available anywhere in the colour path.
  Searched `src/scene` and `src/domain` for `faceNormal`, `normalById`,
  `faceAxis`, `axisByFace`, and `faceDirection`. Only `getGridAxisNormal` in
  `src/domain/grid.ts` exists, and it returns a grid axis unit vector unrelated
  to a cube's rotation. A must derive the world normal from the pose basis.
- None found: no signed OKLab lightness operator. `oklab` appears in exactly
  three files under `src`, and in two of them only in prose comments
  (`src/theme/themeTokens.ts`, `src/theme/scenePolarity.ts`).
  `src/scene/colorSpace.ts` is the single implementation owner. No CSS `oklab`
  or `oklch` exists under `src/styles`, `src/index.css`, or
  `src/design-system`.
- None found: no ambient occlusion, cavity, or crevice term of any kind. New
  code is justified for the mapping from edge junction classification to a
  per-face occlusion weight, and for the signed OKLab operator. Nothing else in
  A or B is new.

## Quality Map

- Duplication / parallel implementation: `src/studios/editor/EditorStudio.tsx`
  `useStagePolarityAttribute` types its parameter as
  `keyof typeof scenePolarities` when `ScenePolarity` is exported from
  `src/theme` and already imported in that file. A named type restated as a
  structural one.
- Duplication / parallel implementation: `src/theme/scenePolarity.ts`
  `workbenchScenePolarities` repeats the identical grooming literal
  (`edgeLightnessDelta` and `faceLightnessDeltaById`) for both polarities.
  Harmless at two entries, but A adds a third field to the same literal.
- Boundary / design issue: `src/domain/exposure.ts` `getOppositeFaceId` is a
  private helper deriving the opposite face from `axis` and `positionSign`.
  `src/domain/cubeTopology.ts` is the owner of that vocabulary and already
  exports the comparable `getCubeDimensionFaceIds` and `getCubeFaceEdgeIds`. B
  will want opposite-face and face-normal accessors; both belong in
  `cubeTopology.ts`, not a second private copy in a consumer.
- Boundary / design issue: `src/scene/instanceSlotRegistry.ts`
  `changedAttributes` marks `color` dirty only when the part's authored colour
  or its tween changed. A matrix change never marks colour dirty. Under A, a
  cube turn changes the world normal and therefore the face colour, so a turn
  would upload a new matrix against a stale colour. This is the single defect
  A most likely ships with. The clean fix is to carry the resolved delta on the
  instance and compare it here, so a turn marks colour dirty as a consequence
  of the data rather than a special case.
- Boundary / design issue: `src/shared/vec3.ts` exports `dotVec3`,
  `crossVec3`, `lengthVec3`, and `scaleVec3` but no `normalizeVec3`. An
  authored light direction must be normalised. Without the helper, A will
  inline the division.
- Boundary / design issue: `src/domain/scene.ts` `Pose` is
  `Omit<CubicellScene, "score">`, and
  `src/state/workbenchValidation/pose.ts` asserts
  `hasOnlyKeys(value, ["cells", "frameId", "grid", "polarity", "projection"])`.
  Any authored scene field for A must pass through the pose type, the pose
  validator, the morph sampler, and persistence. This is the real cost of
  making the light direction authored rather than themed.
- Dead code / obsolete path: `src/theme/scenePolarity.ts`
  `cubeFaceLightnessDeltaById` is exported and re-exported through
  `src/theme/index.ts` via `export *`, yet its only reader is
  `scenePolarity.ts` itself. A public surface with no consumer. A replaces the
  table; the export should not survive it.
- Dead code / obsolete path: `seamSurfacesEnabled` is `false`, so
  `src/scene/seamGeometry.ts`, `src/scene/SeamLayer.tsx`, and `SeamRevealHold`
  are unreachable in the running app. Not B's problem to fix, but B must not
  assume they run.
- Test coverage: no contract test references `shiftLightnessForContrast`,
  `faceLightnessDeltaById`, `isFaceBuried`, `createBuriedFaceIndex`,
  `classifyEdgeJunction`, `syncInstancedPartMesh`, or
  `createCubeCellInstances`. The entire existing value ramp is unproven, and A
  and B extend it.
- Test governance is at its ceiling, proven by running `pnpm test:governance`:
  `local 9 files/34 cases; browser 4 files/6 cases`, against `maxCases` of 34
  and 6. There is zero headroom. Any new case fails the gate until the budget
  is raised or existing cases are consolidated. Plan for this before writing a
  test, not after.
- File sizes: no file under `src` exceeds 700 lines. The largest in this area
  are `src/scene/instancedPartMeshCore.ts` at 521 and
  `src/domain/incrementalCubeRenderResolution.ts` at 534. Both have room, and
  neither triggers the refactor-first rule.
- Grooming recommendation: refactor during the slice. There is no blocking
  debt. Fold four small corrections into the work as it lands: delete the
  `cubeFaceLightnessDeltaById` export when A replaces it, add `normalizeVec3`
  to `src/shared/vec3.ts`, move the face normal and opposite-face accessors
  into `src/domain/cubeTopology.ts`, and correct the `ScenePolarity` type in
  `EditorStudio.tsx`.

## Answers to the audit questions

1. Colour resolution is owned end to end by
   `src/scene/instancedPartMeshCore.ts` `resolveTreatedPartColor`, which calls
   `resolvePartColor` in `src/scene/colorSpace.ts` and then applies at most one
   lightness shift. `shiftLightnessForContrast` is not the operator A needs; it
   is away-from-extreme, A needs signed. Its private OKLab converters are.
2. No. At `resolveTreatedPartColor` only `faceId` and `ColorWriteContext` are
   in scope, and the context is per mesh, not per cube. `InstancedPart.matrix`
   is on the part and does carry world rotation, since
   `src/scene/cubeInstances.ts` builds it as the cell matrix from
   `pose.renderPosition`, `pose.rotation`, and `pose.scale` multiplied by the
   face's local transform. Decomposing it per colour write is the wrong trade.
   `SceneGridLayout` in `src/domain/gridLayout.ts` is what knows world
   orientation, and `createCubeCellInstances` holds it already.
3. Yes, twice over, at two different granularities. `isFaceBuried` in
   `src/domain/exposure.ts` answers the literal question but culls the face.
   `classifyEdgeJunction` in the same file answers the useful question for a
   face that is still drawn. Occupancy has one owner in
   `src/domain/neighbors.ts` and is maintained incrementally by
   `src/domain/incrementalCubeRenderResolution.ts`. B needs no second pass.
4. Colour is change-driven, not frame-driven. `changedAttributes` in
   `src/scene/instanceSlotRegistry.ts` gates every upload, and the shipped P0
   gate records 156 uploaded bytes for a one-cell edit at both 250 and 2,025
   cells. B stays change-driven, because occupancy changes only on placement,
   visibility, grid format, or membership. A stays change-driven only while the
   light direction is authored scene state. If the direction is ever derived
   from the camera, every camera frame repaints every face, which breaks
   `PERFORMANCE.md` principle 3 and the demand-driven rendering work queued at
   position 4 in the delivery order. Flagged as the one way this work can go
   frame-driven.
5. `src/config/cubicellConfig.ts` owns scalar feel knobs.
   `src/theme/scenePolarity.ts` owns per-polarity render treatment.
   `src/domain/cubeOperations.ts` `isViewLaneSceneOperation` owns scene-level
   authored view state, and `set-scene-polarity` is the existing precedent for
   exactly this: a scene-wide visual property on the document, outside document
   history. That is where an authored light direction belongs. The ramp
   magnitudes belong in `cubicellConfig.ts`.
6. Confirmed. `scenePolarities` is built by `createPolarityConfig` with no
   grooming argument, so both `edgeLightnessDelta` and `faceLightnessDeltaById`
   are absent. `workbenchScenePolarities` passes both for both polarities.
   Consumers of `scenePolarities`: `src/thumbnail/thumbnailRenderer.ts`
   (background only), `src/thumbnail/thumbnailArtifact.ts` (full config into
   `syncInstancedPartMesh`), and `src/studios/editor/EditorStudio.tsx` when
   `previewing` is true. Consumer of `workbenchScenePolarities`:
   `src/studios/editor/EditorStudio.tsx` alone, when not previewing. Video
   export has no separate consumer; `src/export/streamRecorder.ts` captures the
   live canvas, so export inherits whichever family preview selected. The
   practical consequence for A and B: unless deliberately changed, both
   features are workbench-only and invisible in thumbnails, preview, and
   export.

## Plan

- Decision needed: is the light direction authored document state or a theme
  constant? Authored means a new field on `CubicellScene`, therefore on `Pose`,
  therefore through `src/state/workbenchValidation/pose.ts` `hasOnlyKeys`, the
  morph sampler, and persistence, plus a view-lane operation beside
  `set-scene-polarity`. Themed means one vector in `ScenePolarityConfig` beside
  the existing deltas, zero persistence cost, and no authoring. The brief says
  authored; the cost is the pose surface.
- Decision needed: do A and B apply to artifacts, or stay workbench-only like
  the ramp they replace? Today `scenePolarities` carries no deltas, so
  thumbnails, preview, and export show authored colours. Shading a form in the
  workbench and not in the artifact is a defensible product line, but it must
  be a decision rather than an inherited default.
- Decision needed: B as briefed says "a neighbouring cell sits against it".
  That face is buried and culled by `createBuriedFaceIndex`, so it is never
  drawn. Confirm that B means occlusion on *visible* faces bordering an inside
  corner, which `classifyEdgeJunction` already classifies as `concave`.

Proposed steps, each bound to the reuse map above:

1. Add `normalizeVec3` to `src/shared/vec3.ts` and a face normal accessor plus
   an opposite-face accessor to `src/domain/cubeTopology.ts`, next to
   `getCubeFaceEdgeIds`. Move the private `getOppositeFaceId` out of
   `src/domain/exposure.ts` onto the new accessor.
2. Add a signed OKLab lightness operator to `src/scene/colorSpace.ts` beside
   `shiftLightnessForContrast`, sharing the existing private converters and
   module scratch. Do not add a second OKLab implementation.
3. Carry a resolved lightness delta on the face instance in
   `src/scene/cubeInstances.ts` `createCubeCellInstances`, computed once per
   cube from `createRotationBasis(pose.rotation)` and the face's axis and sign.
   Extend `changedAttributes` in `src/scene/instanceSlotRegistry.ts` to compare
   it, so a turn marks colour dirty.
4. Replace the `faceId` table lookup in
   `src/scene/instancedPartMeshCore.ts` `resolveTreatedPartColor` with the
   carried delta, and delete `cubeFaceLightnessDeltaById` and its export from
   `src/theme/scenePolarity.ts`. Keep the edge path unchanged.
5. Place the light direction per the first decision, and the ramp magnitude in
   `src/config/cubicellConfig.ts`.
6. B only after A lands. Derive a per-face occlusion weight from
   `classifyEdgeJunction` over `getCubeFaceEdgeIds`, resolved in the same
   per-cube pass as step 3 and summed into the same delta, so occlusion costs
   no second colour write. Extend `collectFaceNeighborIds` invalidation if the
   weight reads beyond the faces already treated as affected.

Tests and gates:

- Resolve the governance ceiling first. `pnpm test:governance` currently
  reports `local 9 files/34 cases` against a limit of 34. Either raise
  `maxCases` in `tests/contracts/governance.json` with justification, or
  consolidate. Cases cannot simply be added.
- Natural home for A and B coverage is
  `tests/contracts/incremental-scene-equivalence.contract.test.ts`, currently
  one case and 138 lines against a 700 line cap. It already proves incremental
  patches equal a full rebuild, which is exactly the property a turn-dependent
  colour must satisfy. `tests/contracts/shared-vector-maths.contract.test.ts`
  is the home for `normalizeVec3` and the signed OKLab operator.
- The specific regression to prove: turn a cube, and assert the patched slots
  equal a full rebuild, so a stale colour against a fresh matrix fails.
- Full gate, all six: `pnpm format`, `pnpm lint`, `pnpm test:governance`,
  `pnpm test`, `pnpm test:browser`, `pnpm build`. Only `pnpm build`
  typechecks.
- Budget gate if delivery closure moves: `pnpm check:budget`.
- Live proof in the app, since the renderer is unlit and shading either reads
  as form or does not: turn a cube and confirm the face value tracks the world
  light rather than the cube, and build an inside corner and confirm it darkens.
