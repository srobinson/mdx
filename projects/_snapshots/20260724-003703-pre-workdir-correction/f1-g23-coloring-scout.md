# F1 G23 Scout: Editor Edge/Face Coloring + New-Cube Inheritance

Read-only reconnaissance against main @ 333c398 (#91 merged). No implementation. Companion decisions: cm entry "Editor cube legibility: edge/face contrast + new-cube inheritance" (2026-07-17).

## Headline

The editor 3D view and the thumbnail/preview render share both the instance derivation and the color resolution path. The editor-only seam already exists: the `ScenePolarityConfig` value each caller passes at sync time. `App.tsx` selects `workbenchScenePolarities` for edit mode and `scenePolarities` for preview; thumbnails hardcode `scenePolarities`. G23 is a second workbench-only treatment riding the exact seam the existing "edit-mode tonal remap" already established.

## Reuse map

**Color resolution path (authored color to pixels):**
- `src/domain/cube.ts` — `CubePartColor = 'theme' | 'black' | 'white'` is the only authored color vocabulary. Per-part state: `CubeEdgeState` (color, opacity, thickness, visible), `CubeFaceState` (color, opacity, visible). Defaults: `defaultCubePartColor = 'theme'`, `defaultCubeEdgeThickness = 0.014`.
- `src/theme/scenePolarity.ts` — `resolveCubePartColor(color, polarity)` maps authored color to a hex string through the config ('theme' resolves to `polarity.contrast`). Two config families built by `createPolarityConfig`: `scenePolarities` (artifact truth, used by preview and thumbnails) and `workbenchScenePolarities` (edit-mode tonal remap of blacks/whites into the workbench range). This split is the editor-only precedent.
- `src/theme/themeTokens.ts` — `workbenchBlack` / `workbenchWhite` tokens back the remap.
- `src/scene/colorSpace.ts` — OKLab infrastructure from the ink-tween work: `resolvePartColor` / `resolveLerpedPartColor` plus module-private `setLinearSrgbToOklab` and the inverse inside `setOklabLerp`. The matrices for a lightness-shift helper are already here; the helper itself needs extracting and exporting.
- `src/scene/instancedPartMeshCore.ts` — `syncInstancedPartMesh(mesh, parts, polarity)` is the single place display color is computed (calls `resolvePartColor` per instance). It already contains a kind-scoped treatment precedent: meshes tagged `partKind: 'slot'` (read via `getInstancedPartKind`, stored in `userData.partKind`) take `polarity.selection` instead of a resolved part color. `InstancedPartKind` already includes `'edge'`; no mesh uses it yet.
- Material context: parts render with unlit `MeshBasicMaterial` (`createInstancedPartMeshWithGeometry`), so there is no lighting to give form. Color contrast is the only legibility lever, which is why G23 exists.

**Instance derivation (shared by canvas and thumbnails):**
- `src/scene/cubeInstances.ts` — `createCubeSceneInstances` / `createCubeCellInstances` turn `CubeCell` into typed lists: `CubeFaceInstance[]` (opaque/translucent/ghost) and `CubeEdgeInstance[]` (opaque/translucent/ghost plus `edgeHitTargets`). Instances carry the authored `CubePartColor`, never a resolved display color. The builder sees the whole `CubeCell`, so face-reference data for edges could be attached here if needed.
- `src/scene/CubeScene.tsx` — composes `InstancedPartMesh` layers. Face meshes and the neighbor-slot mesh set `partKind`; the three edge meshes (opaque, translucent, ghost) and the edge hit-target mesh do not set any `partKind` today.
- `src/scene/edgeCoverageCore.ts` + `EdgeCoverageLayer.tsx` — shader overlay guaranteeing edges a minimum screen thickness (`edgeCoverageCssPixels`). It renders the same `opaqueEdges` parts through the same `syncInstancedPartMesh` with the same polarity config. Any edge tone treatment must land here too or thin edges will show the untreated color; because it shares the sync function, tagging its mesh covers it for free.

**Thumbnail/preview/export path:**
- `src/thumbnail/thumbnailArtifact.ts` — `createThumbnailArtifact` builds meshes from the same `createCubeSceneInstances` output and syncs with `scenePolarities[pose.polarity]`. Its layer descriptors set no `partKind`.
- `src/thumbnail/thumbnailRenderer.ts` — background from `scenePolarities`. All thumbnail/export consumers funnel through these two files.
- `src/app/App.tsx` — the mode switch: `previewing ? scenePolarities[...] : workbenchScenePolarities[...]`, passed into `ConnectedCubeScene` as the `polarity` prop.

**Cube creation and edge thickness:**
- `src/domain/cube.ts` — `createCubeCell(id, options)`; `CreateCubeCellOptions` already accepts full `edges` / `faces` overrides and clones them, so the domain type is inheritance-ready. `cloneCubeEdges` / `mapCubeEdges` / `mapCubeFaces` exist for building patched part states. Inspector aggregation helpers `getCubeUniformPartColor` and `getAverageCubeEdgeThickness` already exist.
- `src/domain/neighbors.ts` — `placeCubesAt(scene, coords)` creates via `createCubeCell(id, { coord })` with pure defaults; it also reveals hidden occupants instead of creating, and collapses duplicate coords. `addNeighborCubes(scene, faces)` already resolves the source cell per face (`cellsById.get(face.cubeId)`) for coordinates, so the source's part states are one step away.
- `src/domain/scene.ts` — `createCubeGrid` seeds grid-composer cells with defaults (the no-selection territory).

## The critical seam

**Is the render path shared?** Yes, twice over. `createCubeSceneInstances` (derivation) and `syncInstancedPartMesh` (color resolution) feed both the live canvas and `createThumbnailArtifact`. Editing either unconditionally would restyle thumbnails and preview.

**The exact seam:** the `ScenePolarityConfig` value. It is the only input that differs per consumer: edit mode gets `workbenchScenePolarities`, preview (`editorMode === 'preview'` in `App.tsx`) and thumbnails get `scenePolarities`. Both families are built by the single `createPolarityConfig` constructor.

**Editor-only scoping without touching authored colors:** express the treatment as data on the config, applied at sync time, keyed on part kind.
1. Add an optional edge-contrast field to `ScenePolarityConfig` (for example `edgeLightnessDelta`), populated only for the `workbenchScenePolarities` family via `createPolarityConfig`. Artifact configs omit it.
2. In `syncInstancedPartMesh`, when `getInstancedPartKind(mesh) === 'edge'` and the config carries the field, shift the resolved color's OKLab lightness (new exported helper in `colorSpace.ts` reusing the existing matrices). This mirrors the existing `'slot'` special case exactly.
3. Tag the edge meshes: the three edge `InstancedPartMesh` usages in `CubeScene.tsx` and the coverage mesh in `edgeCoverageCore.ts` (its `createInstancedPartMeshWithGeometry` options already accept `partKind`). The `'face'` check in `CubeScene` face-drill filtering and the `'slot'` check in sync are unaffected.
4. Leave thumbnail layer descriptors untagged. Thumbnails are then provably outside the treatment twice: no `partKind` and no delta in their config.

Authored colors never change; the treatment exists only at display resolution time, the domain and persistence are untouched, and preview/thumbnail/export render exactly as today.

## Both-polarities mechanism

Computation at sync time, per edge instance:
1. Resolve the reference color through `resolveCubePartColor` as today.
2. Convert linear sRGB to OKLab (`setLinearSrgbToOklab` matrices), take lightness L.
3. Shift: `L' = L + sign * delta` where `sign = L < 0.5 ? +1 : -1` (dark faces get lighter edges, light faces get darker edges), clamp, convert back (inverse matrices already inline in `setOklabLerp`).

Deriving the sign from the resolved reference L rather than from the polarity name makes the flip automatic for polarity AND for authored non-theme colors: a black-colored cube in white polarity still reads correctly. This satisfies the hard constraint without any per-polarity branching.

Two application variants for "off the face color":
- **A1, self-relative:** shift each edge's own resolved color. No type changes. Identical to face-relative in the default and dominant case (edge and face both 'theme'). When an edge is authored a different color from its faces, the edge keeps its authored hue and still gains contrast.
- **A2, face-referenced:** attach the cube's face color to `CubeEdgeInstance` at build time in `cubeInstances.ts` (inert data; thumbnail sync ignores it since its config has no delta) and compute the edge display tone from the face reference. Literal reading of the decision; overrides authored edge colors in the editor view when they differ from faces.

Recommendation: A1. It degrades gracefully for authored edge colors and needs no derivation changes. Flag both to Stuart (see decisions).

Stuart's open detail, carried forward: always apply the delta, or only when authored edge/face contrast is already below a threshold (measurable at sync time as |L_edge - L_face|, but that requires A2's face reference).

## New-cube inheritance

**Creation entry points (all funnel to two domain functions):**
1. Normal-mode slot click: `addNeighborAtSlot` in `src/app/useSceneOperations.ts` calls `addNeighborCubes` with `slot.sourceCubeId`. The source cube is already resolved inside `addNeighborCubes`; inheritance means building the new cell's `edges` / `faces` options from that source instead of defaults, per part id (edge and face ids are topological, so per-id copy preserves orientation mapping).
2. Multi-face add: `addNeighborToSelectedFaces` in the same file, same domain function, per-face source available.
3. Build-mode paint: `placeCubeAtSlot` dispatches a `'place-cubes'` scene operation (`src/domain/cubeOperations.ts`) that calls `placeCubesAt(scene, operation.coords)`. The operation carries only coords today; the slot's `sourceCubeId` is available at the dispatch site and would need to enter the operation payload (or a style template resolved at apply time). `StructureSection.tsx` also dispatches `'place-cubes'`.
4. Grid composer seed: `createCubeGrid` in `src/domain/scene.ts`, defaults only. This is the no-selection / first-cube case.

**Scope of the copy:** the decision names colors AND edge thickness. Cleanest domain shape: build the new cell's part states with `mapCubeEdges(defaults, copy color + thickness per edge id from source)` and `mapCubeFaces(defaults, copy color per face id)`, leaving opacity and visibility at defaults unless Stuart wants full-state inheritance (see decisions).

**Interaction details found in `placeCubesAt`:**
- It reveals hidden occupants rather than creating. A revealed cube should keep its own styling, not be restyled by inheritance (recommended; confirm).
- Duplicate coords collapse to one cube; with multiple source faces pointing at the same coord, which source's style wins needs a deterministic rule (first face in the list is the natural one).
- Undo is snapshot-based via history units, so a `sourceCubeId` in the operation payload resolves against pre-op cells deterministically at apply time.

**No-selection / first-cube fallback options:**
- (a) Status quo defaults: 'theme' color, `defaultCubeEdgeThickness`. Zero surprise, works with polarity by construction.
- (b) Sticky last-authored style: session-remembered style template applied when no source exists.
- (c) Project-level default style knob (per the surface-feel precedent that feel constants live in config, a default style could live in scene or preferences).
Recommendation: (a) now, (b) as a follow-up if authoring friction shows.

## Decisions needed (Stuart)

1. **Edge tone application:** A1 self-relative (edge keeps authored hue, gains contrast; recommended) vs A2 face-referenced (edge display tone derived from face color, overrides authored edge colors in the editor).
2. **Always vs conditional:** apply the delta unconditionally, or only when authored edge/face contrast is below a threshold (requires A2's face reference to measure).
3. **Delta magnitude:** a feel constant; per the surface-feel rule it belongs in the polarity config, not hardcoded in sync. Needs a starting value to tune live (suggest around 0.12 OKLab L, tuned on the workbench background).
4. **Inheritance scope:** colors + edge thickness only (per decision text, recommended) vs full part states including opacity and visibility.
5. **Build-mode source:** inherit from the slot's source cube (the cube it grows from; covers build mode where selection is deliberately untouched; recommended) vs strictly the current selection. The decision text equates them, which holds for normal-mode slot adds but diverges in build mode.
6. **No-selection fallback:** option (a) defaults now, (b) sticky style later.
7. **Reveal semantics:** confirm a revealed hidden occupant keeps its own styling.

## Tests and gates

- `tests/colorSpace.test.ts` (exists): lightness-shift helper: delta 0 is identity, sign flips around mid L, clamping near gamut extremes, applied color remains valid linear sRGB.
- `tests/instances.test.ts` / new sync-level test: an edge-tagged mesh under `workbenchScenePolarities` resolves shifted colors; the same parts under `scenePolarities` resolve unchanged; face and slot meshes unchanged under both; both polarities shift in opposite directions.
- `tests/thumbnailArtifact.test.ts` (exists): regression pin: thumbnail edge instance colors byte-identical before and after the feature.
- `tests/edgeCoverageCore.test.ts` (exists): coverage mesh carries the edge part kind and picks up the same treated color as the resolved edge boxes.
- `tests/neighbors.test.ts` (exists): `addNeighborCubes` copies per-part colors and edge thickness from the face's source cube; reveal does not restyle; duplicate-coord winner deterministic; grid-composer and no-selection paths keep defaults.
- Build-mode: `'place-cubes'` operation with a source template inherits; without one keeps defaults.
- Gates: pnpm test, pnpm lint, pnpm build. Editor tone tuning needs Stuart's live gate (canvas-visual change; ship behind the config value so tuning is a one-liner).
