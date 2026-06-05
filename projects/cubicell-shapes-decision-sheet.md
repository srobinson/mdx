# Cubicell shapes decision sheet

Baseline `9f766b2`, branch `feat/cube-edge-treatment`. Sources: Scout A (domain), Scout B (render), capability-cost audit, structure census, discoverability audit.

Already decided, context only: (1) rebuild is off the table; RESTRUCTURE stands per the four-agent audit. (2) Phase A before phase D is approved; the spec calls A independent of the others.

## Table 1. Shapes slice findings

| # | Finding | Source | Disposition | Evidence |
| --- | --- | --- | --- | --- |
| 1 | `set-edge-state` already carries `Partial<CubeEdgeState>`; treatment and shapeSize need zero new operation kinds or command paths | Scout A, capability-cost | Reuse | `src/domain/cubeOperations.ts:CubeOperation` |
| 2 | The edge-thickness trace is the full authored spine to mirror: binding, command, materialization, dispatch, reduce, history, render impact | Scout A | Reuse | `src/editor/controlBindings.ts:edgeThicknessBinding`; `src/domain/sceneOperationMaterialization.ts:materializeSceneOperations` |
| 3 | Live scrub with one undo entry already exists via gesture staging in the authored dispatcher | Scout A | Reuse | `src/state/actions/authoredDispatcher.ts:createAuthoredDispatcher`; `src/interaction/gestureTransaction.ts:GestureTransaction` |
| 4 | The edge field set is hand-enumerated in six parallel places, and the hydration allowlist rejects unknown keys, so a partial add breaks reload; equality is already a known duplication cluster | Scout A, structure | Refactor-first | `src/state/workbenchValidation/pose.ts:isEdgeState`; `src/persistence/recordCodecs/compactPose.ts:sameEdge`; `src/domain/selectionAspects.ts:areEdgeStatesEqual` |
| 5 | Shaping also expands three more duplicated contracts: exact vec3 equality, cube size tuple conversion, cube operation kind vocabulary | Structure | Refactor-during | `src/domain/sceneOperationMaterialization.ts:isCubeOperation` vs `src/state/authoredOperationValidation/scene.ts:isCubeOperation` |
| 6 | Sparse codec means default sharp/0 costs zero bytes; bump the wire version and reset, no migration | Scout A | Reuse | `src/persistence/recordCodecs/compactPose.ts:CompactEdge`; `src/persistence/storageRecordTypes.ts:committedRecordSchemaVersion` |
| 7 | Per-instance treatment can ride an instanced buffer attribute plus one fixed `customProgramCacheKey`, the proven opacity and coverage pattern, at zero program growth | Scout B | Reuse | `src/scene/instancedPartMeshCore.ts:applyInstanceOpacity`; `src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh` |
| 8 | Geometry variants keyed by treatment cost O(V) programs, unbounded when every cell has a distinct signature; if variants prove necessary, a bounded signature-keyed registry shared with thumbnails is a required new owner | Scout B, capability-cost | Defer (pending Section 4 probe) | `src/scene/InstancedPartMesh.tsx:InstancedPartMesh`; `src/thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` |
| 9 | `CubeScene` is a 400-line function and the approved home of edge hover, tap cycling, and drag; it exceeds the 150-line limit today | Structure | Refactor-first | `src/scene/CubeScene.tsx:CubeScene` |
| 10 | `StructureSection` (398 lines) and `StructureSliceLayer` (165) host the slice-corner affordance and are also over the function limit | Structure, capability-cost | Refactor-first | `src/panels/StructureSection.tsx:StructureSection`; `src/panels/StructureSliceLayer.tsx:StructureSliceLayer` |
| 11 | Three required touch points are already over 500 lines and approach the 700 cap: the domain barrel, `CubeScene`, `controlBindings` | Structure | Refactor-during | `src/domain/index.ts`; `src/editor/controlBindings.ts:controlBindingList` |
| 12 | A new `CubeEdgeRenderAttribute` value (proposed `"shape"`) is the domain-to-render contract; the name must be agreed before either side builds | Scout A, Scout B | Reuse | `src/domain/authoredRenderImpact.ts:CubeEdgeRenderAttribute` |
| 13 | Downstream owners that must learn treatment: face burial when an incident edge is shaped, morph interpolation of shapeSize with treatment switching at the cut, coverage silhouette | Capability-cost, Scout B | Reuse | `src/domain/exposure.ts:isFaceBuried`; `src/evaluation/sceneMorph.ts:interpolateCell` |
| 14 | Scrub feel constants and any variant cache bound belong in named product configuration, never hardcoded | Capability-cost | Reuse | `src/config/cubicellConfig.ts` |
| 15 | Adopt `CubeEdgeTreatment` from the recorded TYPOGRAPHY.md contract; the modifier ladder lives beside the existing combine-mode ladder | Scout A | Reuse | `src/editor/affordances.ts:getCombineModeForModifiers` |

Terminology trap: the existing test named "carries the workbench edge treatment" is colour contrast, not shaping (`tests/edgeCoverageCore.test.ts`, `src/scene/colorSpace.ts:shiftLightnessForContrast`). Builders grepping "edge treatment" must not conflate.

## Table 2. Structural findings off the shapes critical path

| # | Finding | Source | Disposition | Evidence |
| --- | --- | --- | --- | --- |
| 1 | 12 unreferenced declaration residues plus one test-only production helper; mechanical deletion with no behavior change | Structure | Refactor-during | `src/domain/cubeRenderResolution.ts:getCubeRenderResolutionPasses`; `src/domain/resolvedRenderClosure.ts:collectResolvedChangeClosure` |
| 2 | Lost feature: camera track controls are built and tested but unmounted since the Piece Motion cutover; mount or delete is a product decision | Structure, discoverability | Defer | `src/studio/CameraTrackControls.tsx:CameraTrackControls` |
| 3 | `GridOverflow` has never affected behavior since introduction; implement its contract or delete it (reports disagree, see Section 4) | Structure, Scout A | Defer | `src/domain/grid.ts:GridOverflow` |
| 4 | 5 lazy and 7 legacy direct-store side doors remain; the lazy five have existing command shapes and a stated enrollment order | Structure, Scout A | Refactor-during | `src/app/useSceneOperations.ts:toggleCubeBuilt`; `src/panels/SelectorPanel.tsx:SelectorPanelHeader` |
| 5 | 18 editor-bound modules in `src/app` block clean shell reuse by any second product studio; runtime studio registration already works | Structure | Defer | `src/app/StudioShell.tsx:StudioShell`; `src/studios/contract.ts:StudioModule` |
| 6 | Doc rot burns trust: ARCHITECTURE cites a nonexistent file, PERFORMANCE keeps stale open P1s and phantom paths, CAMERA.md describes an unmounted feature in present tense | Discoverability | Refactor-during | `ARCHITECTURE.md` vs `src/transport/stagedScene.ts:useStagedScene` |
| 7 | No one-page runtime map exists (boot chain, input classes, three state homes, not-user-reachable list); cold start wastes hours | Discoverability | Refactor-during | proposed root `MAP.md` |
| 8 | 15 further duplication clusters (vector algebra, JSON guards, listener sets, camera guards) sit off the shapes path | Structure | Defer | `src/domain/cameraOperations.ts:sameVec3` vs `src/persistence/recordCodecs/compactPose.ts:sameVec3` |

## Table 3. Proposed rules

| # | Rule | Prevents | Enforcement |
| --- | --- | --- | --- |
| 1 | Invariant-bearing tests may not be deleted or rewritten in the change that alters the path they guard unless the invariant is reasserted with red-before evidence | Rewrite shipped green after deleting its guard tests | Review checklist; CI script pairing test deletions with replacement assertions |
| 2 | A regression gate counts only if stripping the production fix turns it red; test-owned appliers or harnesses are not coverage | Triple-reviewed fix whose suite stays green with the fix removed | CI controlled-red proof; checklist names the production symbol under test |
| 3 | An effect whose cleanup disposes a shared input or render resource must recreate it in setup, proved on both dev (Strict Mode) and preview | Dispose-only effects shipping dead camera and keyboard in dev | Review checklist; CI Chromium double-mount assertion |
| 4 | Gate green is raw command output from a re-run by someone other than the author | Builder self-reported browser green on a deterministically red SHA | Discipline (integrator seat) until CI owns the same command |
| 5 | Delivery budget ceilings re-baseline to measured gzip at zero headroom; the checker fails over-budget and over-slack | ~9.8 KB silent headroom masking a regression | CI: extend `scripts/check-delivery-budget.mjs` |
| 6 | An approved field or type name must have at least one `src/` occurrence and a test naming it, or carry an explicit parked marker | `shapeSize` / `CubeEdgeTreatment` approved with zero src hits, unnoticed | CI rg inventory over the decision table; review checklist |
| 7 | UI is live only with a production mount; docs may not describe unmounted surfaces in present tense | Camera-track class of built-but-unreachable features cleared as live | Review checklist ("show the mount site"); CI export scan |
| 8 | Feel-critical browser behavior needs at least one proof driving the production component tree, not only pure functions | Unit-green suites over runtime-dead input paths | CI browser tests; live UX gate before merge |
| 9 | GPU acceptance gates assert counts (programs, buffers, mesh and material identity), never timings; SwiftShader makes timing gates invalid here | Perf gates that cannot fail meaningfully in CI | CI: existing `observeWebGlResources` pattern; checklist |
| 10 | Program cache keys are fixed strings; per-instance values, capacity, or shape signatures never enter cache keys or mesh identity deps | #116-class program recreation returning via shaping | Browser gate asserting `createdPrograms === 0`; review checklist |

## Section 4. Conflicts and probes

**Mandatory item, reconciled.** Capability-cost's 49-file, 9-layer lower bound with fixed-geometry instancing as the tax (17 of 49 files) and Scout B's zero-program-growth measurement do not contradict each other; they cost different implementations. Capability-cost's bound assumes treatment becomes geometry identity: variant factories, a signature registry, variant slot buckets, per-signature coverage and thumbnail meshes (its rows 20-29). That is exactly Scout B's option B, which Scout B also rejects as O(V) programs, unbounded under distinct per-cell signatures. Scout B's measurement (instanced attribute plus fixed `customProgramCacheKey`, zero new programs on value change and band cross, per the existing gate in `tests/incrementalScene.browser.test.ts` via `observeWebGlResources`) applies to shader-side shaping (its options A/D), which never splits meshes and would collapse most of the 17-file instancing seam to attribute plumbing in `instancedPartMeshCore`. The reports agree on the mechanism costs; neither settles whether shader-side deformation is visually sufficient for round and chamfer silhouettes, including the coverage overlay that currently assumes a hard box cross-section (`src/scene/edgeCoverageCore.ts:createEdgeCoverageMesh`).

**The one measurement that settles it:** spike an instanced-attribute shaping shader on edge boxes plus coverage; fill a scene where every cell has a distinct signature; assert `createdPrograms` delta is 0 after mutating radii and after crossing a capacity band (reuse `runGpuCapacityBrowserDriver` patterns in `tests/incrementalSceneBrowserDriver.tsx`); then judge the rendered silhouette by eye. Counts pass plus acceptable silhouette selects the attribute path and voids most of the 17-file tax; silhouette failure forces geometry variants, and the 49-file bound with the new bounded variant registry stands.

**GridOverflow.** Scout A reads it as a documented reserved seam to leave alone; the structure census requires an implementation contract or deletion. Both agree it has never affected behavior. Disposition left to Stuart (Table 2 row 3).

**Side-door counts.** Scout A's ~37 across 18 files versus the census's 47 across 25 files (52 semantic flows) is method drift, not disagreement; the census is the measured current tree and supersedes.
