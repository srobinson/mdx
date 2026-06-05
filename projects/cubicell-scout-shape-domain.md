# Cubicell Scout A: Shape Domain and Command Map

Date: 2026-07-31. Branch `feat/cube-edge-treatment` at `9f766b2` (identical to main). Scope: domain and command side of cube shape / edge treatment / material properties. Rendering and instancing belong to Scout B.

## Reuse Map

### What the approved design specified (Q1)

The spec (`docs/superpowers/specs/2026-07-12-negative-space-tooling-design.md`, section A Model) states verbatim:

> `CubeEdgeState` gains two fields, mirroring how visibility, thickness, and color already work per edge:
> - `treatment: 'sharp' | 'round' | 'chamfer'` (default `'sharp'`)
> - `shapeSize: number` (default 0)

Canvas-surface section adds: "`shapeSize` is in cube-local units, clamped topology-safe at half the smallest dimension adjacent to the edge", scrub is drag-only (wheel stays with camera zoom via `cameraGestureRuntime`), and the modifier ladder (plain = hovered edge, Shift = all twelve, Shift+Alt = matching edge across selection) is defined once beside `getCombineModeForModifiers` in `src/editor/affordances.ts`.

`TYPOGRAPHY.md` (Curve ownership section) records the authoritative contract with the literal identifier:

```ts
type CubeEdgeTreatment = "sharp" | "round" | "chamfer";
type CubeEdgeState = { color; opacity; shapeSize; thickness; treatment; visible };
```

Note: the identifier `CubeEdgeTreatment` appears only in `TYPOGRAPHY.md`; the spec names the field `treatment` without naming the union type. Zero occurrences of either identifier in `src/` confirmed (`grep -rn "shapeSize\|CubeEdgeTreatment" src` → nothing; hits only in the two docs).

Doc-vs-code verification (docs have lied before; these did not):
- `TYPOGRAPHY.md` claims lattice ops and gap overrides shipped, edge shaping pending. Code agrees: `src/domain/lattice.ts` (`LatticeOperation`, `insertLatticeLine`, `deleteLatticeLine`), `src/domain/grid.ts` (`GridFormat.gapOverrides`, `setGapOverride`) exist; no treatment code anywhere.
- Spec sequencing was B+C, then D, then A. B+C shipped. **D (insert-with-shift) is NOT in the code**: `LatticeOperation` carries only `delete-lattice-line` and `insert-lattice-line`; searches `grep -rn "wedge\|Wedge\|insert-with-shift\|shiftScope\|'run'" src` found nothing. This branch (phase A) is landing ahead of D. The spec calls A "renderer-heavy and independent of the others", so the reorder is legal, but it is a departure from the written sequence and should be an explicit decision.
- Terminology collision: `tests/edgeCoverageCore.test.ts` has a test titled "carries the workbench edge treatment of the boxes it covers" that is about colour-contrast treatment (`shiftLightnessForContrast`, `edgeLightnessDelta` in `src/scene/colorSpace.ts` / `src/theme`), unrelated to shaping. A builder grepping "edge treatment" will hit it; do not conflate.

### The reuse spine: one per-cube visual property end to end (Q2)

Exemplar: **edge thickness**. It lives on the same type (`CubeEdgeState`), rides the same operation the new fields must ride, and is the trace the spec itself says treatment/shapeSize mirror.

1. **User action**: Inspector edit-context control. `edgeThicknessBinding` and `cubeEdgeThicknessBinding` (`src/editor/controlBindings.ts`), each a `ControlBinding` whose `createCommand` builds the command; rendered through `ControlBindingField` / `useControlBinding` (`src/panels/useControlBinding.ts`, `src/panels/PartSection.tsx`, `src/panels/CubeSection.tsx`).
2. **Command**: `createSceneEditorCommand` (`src/editor/commands.ts`) wraps `SceneOperation { kind: "set-edge-state", patch: Partial<CubeEdgeState>, scope: CubeScope, target: CubeEdgeTarget }` (`src/domain/cubeOperations.ts`, `CubeOperation`).
3. **Bus**: `useEditorCommandDispatch` (`src/panels/editorCommandContext.ts`) → interaction core `CommandRegistry` (`src/interaction/commands/registry.ts`); the `"scene"` handler is registered in `registerDocumentCommands` (`src/interaction/commands/document.commands.ts`).
4. **Materialization**: `materializeSceneOperations` (`src/domain/sceneOperationMaterialization.ts`) resolves `selected` / `selection-set` scopes into `AuthoredSceneOperation` with concrete ids, so history replays deterministically.
5. **State**: `ports.document.dispatchAuthoredEdit` → `createAuthoredDispatcher` (`src/state/actions/authoredDispatcher.ts`) → `reduceAuthoredOperationState` (`src/state/actions/authoredReducer.ts`) → `applySceneOperation` → `applyCubeOperation` (`src/domain/cubeOperations.ts`; scope fan-out via `resolveCubeScope`, selection-set part fan-out via `applyPartStateToSelectionSet`, member targets via `applyPartStateToMembers`) → `applyCubeOperationToCell` (`src/domain/cubeCellOperations.ts`) → `setCubeEdgeState` (`src/domain/cube.ts`) writes `CubeCell.edges[edgeId].thickness`.
6. **History**: `HistoryCoordinator.recordEdit` (`src/state/actions/historyCoordinator.ts`) → `pushDocumentHistory` (`src/state/documentHistory.ts`).
7. **Render impact**: `classifyAuthoredRenderImpact` (`src/domain/authoredRenderImpact.ts`) diffs old vs new edge state field by field into `CubeEdgeRenderAttribute` (currently `"color" | "opacity" | "resolution" | "thickness" | "visibility"`).
8. **Scene consumption**: `createCubeEdgeSegments` (`src/domain/cubeGeometry.ts`) reads `cell.edges[edgeId].thickness`; shared-edge ownership resolves through `edgeClaimResolution.ts` / `edgeJunctionResolution.ts`; the value lands in `CubeEdgeInstance` (`src/scene/cubeInstances.ts`). Beyond that is Scout B.

**Live scrub**: the authored dispatcher already stages gesture previews (`coordinator.gesture` branch inside `createAuthoredDispatcher`, `recordHistory: false`) behind `ScrubGesturePort` / `GestureTransaction` (`src/interaction/gestureTransaction.ts`). A `shapeSize` drag reuses this and commits one history entry. No new preview machinery is needed.

### Where `treatment` belongs (Q3)

Owner: `src/domain/cube.ts`. Extend `CubeEdgeState` and `defaultCubeEdgeState`; declare `CubeEdgeTreatment` beside `CubePartColor` with a `cubeEdgeTreatments` const tuple and an `isCubeEdgeTreatment` guard, matching the existing `cubePartColors` / `isCubePartColor` pattern in the same file.

**No new operation kind is needed.** `set-edge-state` already carries `Partial<CubeEdgeState>`; `{ treatment, shapeSize }` patches flow through the entire spine above unchanged. Same for material-like properties: color/opacity precedent is `set-face-state` / `set-cube-color` in the same union.

### Existing infra a builder must touch (the new-field checklist)

Every `CubeEdgeState` field is enumerated in six places. Adding `treatment` and `shapeSize` without touching all six either silently drops the value or rejects the document on reload:

| Concern | Symbol | File |
| --- | --- | --- |
| Type + default | `CubeEdgeState`, `defaultCubeEdgeState` | `src/domain/cube.ts` |
| Persisted codec | `CompactEdge` tuple, `sameEdge` (sparse-encodes only non-default edges, so default sharp/0 costs zero bytes) | `src/persistence/recordCodecs/compactPose.ts` |
| Hydration validation | `hasOnlyKeys([...])` edge check | `src/state/workbenchValidation/pose.ts` — **rejects unknown keys; the field lands here or reload fails** |
| Operation validation | `set-edge-state` patch key allowlist | `src/state/authoredOperationValidation/scene.ts` |
| Selection aspects | `areEdgeStatesEqual`, `edgeStateDistance` | `src/domain/selectionAspects.ts` — spec explicitly requires treatment equality + shapeSize distance |
| Render-impact diff | edge field diff feeding `CubeEdgeRenderAttribute` | `src/domain/authoredRenderImpact.ts` — needs a new attribute (e.g. `"shape"`); Scout B's incremental path consumes it |

Also existing and reusable: `getCubeFaceEdgeIds` (`src/domain/cubeTopology.ts`) and `isFaceBuried` (`src/domain/exposure.ts`) for the per-face coverage constraint (consumers: `cubeRenderResolution.ts`, `incrementalCubeRenderResolution.ts`); scope ladder home `affordances.ts`; edge picking via existing `pickMode` and fat edge hit targets (`edgeHitTargets` in `src/scene/cubeInstances.ts`).

### Similar checked and rejected

- New `SceneOperation` kind (`set-edge-treatment`): rejected; `set-edge-state` patch already expresses it and every validation/materialization/history path is already built for it.
- Storing treatment as a preference or session state: rejected; it is document state (persisted, undoable, per edge), unlike feel knobs which belong in `preferences` (`patchPreferences`).
- `applyViewSceneOperation` view lane: rejected; view lane is deliberately non-reversible and out of history (`isViewLaneSceneOperation` doc comment in `cubeOperations.ts`); treatment must be undoable.

### None found (searches run)

- Any occurrence of `shapeSize`, `CubeEdgeTreatment`, `treatment` field in `src/`: `grep -rn "shapeSize\|CubeEdgeTreatment\|edgeTreatment" src` → none.
- Insert-with-shift / wedge (spec phase D): `grep -rn "wedge\|Wedge\|insert-with-shift\|shiftScope" src` → none.
- Geometry variant cache / shape signature (spec section A rendering): `grep -rn "signature\|variant" src/scene src/domain` → no shape-signature machinery exists yet (Scout B territory, noted here only as absent).

## Quality Map

- **Duplication (field-list shotgun)**: field-by-field `CubeEdgeState` equality exists twice — `areEdgeStatesEqual` (`src/domain/selectionAspects.ts`) and `sameEdge` (`src/persistence/recordCodecs/compactPose.ts`) — plus a third field-by-field diff in `authoredRenderImpact.ts` and two string allowlists in the validation files. Five parallel enumerations of the same field set is the exact surface where a new field gets silently dropped.
- **Boundary issue**: ~37 direct store-action references across ~18 component/hook files bypass the command bus (enumerated by `grep -rhoE "state\.(set|toggle|patch|dispatch|apply|...)[A-Za-z]+" src`). The ones that touch visual properties and would tempt a builder (Q4):
  - `dispatchAuthoredEdit` called directly in `src/app/useSceneOperations.ts` (`addNeighborAtSlot`, `addNeighborToSelectedFaces`, `toggleCubeBuilt`, `updateGridComposerDimensions`, `openGridComposer`). These carry visual state: `place-cubes` with `sourceCubeId` copies edge/face style via `inheritCubePartStyle` (`cube.ts`); `toggleCubeBuilt` writes `set-cube-visibility`. They exist because they need `selectionResult` / `resetHistory` options the bus does not express. Copying this pattern for edge scrub would skip `materializeSceneOperations` and the gesture staging; a new visual property must instead enter via `createSceneEditorCommand`.
  - `applyViewSceneOperation` (view lane: polarity/projection) — visual but intentionally history-exempt; wrong door for treatment.
  - `patchPreferences` (`src/panels/SceneSection.tsx`: `floorGridVisible`, `renderPixelRatio`, morph/glide feel) — the correct door for scrub feel constants per the config/pref/scene-knobs convention, and the wrong door for the authored per-edge value.
  - Session setters `setHoveredCube`, `setAxisHint`, `setSeamRevealActive` — the right home for a transient hovered-edge highlight, never for the committed value.
- **Dead code**: `GridOverflow` (`src/domain/grid.ts`) remains declared, defaulted, cloned, and validated (`workbenchValidation/pose.ts`) with no behavioral reader — matches the spec's "dormant field" statement; it is a documented reserved seam, leave it.
- **Grooming recommendation**: before adding the two fields, extract one shared edge-state field descriptor or comparator in `src/domain/cube.ts` (e.g. export `areCubeEdgeStatesEqual` and reuse it from `selectionAspects.ts` and `compactPose.ts`), so the new fields touch one comparator instead of three. The two validation allowlists can at minimum reference a single exported `cubeEdgeStateKeys` tuple. This is a small, mechanical DRY repair squarely on the path of this feature.

## Plan

### Decision needed

1. **Sequencing**: phase A is landing before phase D (insert-with-shift), inverting the spec's order. Spec permits it ("renderer-heavy and independent"); Stuart should confirm.
2. **Render attribute name** for the new impact class in `CubeEdgeRenderAttribute` (`"shape"` proposed) — shared contract with Scout B's instancing work; agree before either side builds.
3. **Type name**: adopt `CubeEdgeTreatment` from TYPOGRAPHY.md's contract (recommended; it is the recorded approved contract) even though the spec itself never names the union.

### Proposed steps (bound to the reuse map)

1. Grooming pre-step: unify edge-state equality/keys in `domain/cube.ts`; point `selectionAspects.areEdgeStatesEqual` usage and `compactPose.sameEdge` at it (tests first).
2. Domain: add `CubeEdgeTreatment`, extend `CubeEdgeState` + `defaultCubeEdgeState` (`treatment: "sharp"`, `shapeSize: 0`); add the topology-safe clamp helper beside the existing size math in `cube.ts` or `cubeGeometry.ts` (half smallest adjacent dimension per spec).
3. Validation + persistence: extend the `workbenchValidation/pose.ts` edge check, `authoredOperationValidation/scene.ts` patch allowlist, and `compactPose.ts` `CompactEdge` tuple; bump `committedRecordSchemaVersion` (`src/persistence/storageRecordTypes.ts`). No migration; single user, bump and reset per repo rule.
4. Aspects + impact: `selectionAspects.ts` treatment equality and `shapeSize` distance; `authoredRenderImpact.ts` new edge attribute.
5. Controls: two new `ControlBinding`s in `controlBindings.ts` (mirror `edgeThicknessBinding` for the single-edge and all-edges forms) dispatching `set-edge-state` patches; edit-context exposure through the existing aspects path.
6. Canvas scrub (with Scout B's picking): tap-cycle + drag-scrub built on `ScrubGesturePort` and the authored dispatcher's gesture staging; scope ladder from `affordances.ts`; feel constants into preferences/config knobs, not hardcoded.
7. Coverage: `isFaceBuried` per-face incident-edge rule using `getCubeFaceEdgeIds` (spec Constraints section).

### Tests and gates

- Domain: `set-edge-state` with `{treatment, shapeSize}` through `applySceneOperation` for every scope kind incl. selection-set member fan-out; clamp behavior at the topology-safe bound; defaults cost nothing in `compactPose` round-trip (sparse encoding), non-default round-trips exactly.
- Validation: hydration accepts new fields, rejects unknown ones; operation validation accepts the new patch keys.
- History: one scrub gesture = one history entry; undo restores prior treatments.
- Aspects: treatment equality and shapeSize distance cases (spec-mandated).
- `isFaceBuried`: shaped neighbor with all-sharp touching face still covers; `shapeSize` 0 covers; shaped incident edge does not (spec-mandated).
- Repo gates: no file crosses 700 lines (`cubeOperations.ts` at ~604 and `controlBindings.ts` are the ones to watch), no function past ~150 lines, zero duplication (step 1 is the enforcement).
