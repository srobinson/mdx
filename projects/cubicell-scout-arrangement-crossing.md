# Scout: arrangement crossing — the resolved arrangement offset

Slice: make the resolved arrangement offset a first-class value, resolved per endpoint and crossed continuously across a transition gap, instead of recentring over endpoint B's full cell set (including presence-0 cells) from the first frame.

Read-only pass on `feat/arrangement-crossing` at `main @ 6b92c60`. Behavioural claims are marked **measured** (orchestrator's prior probes), **structural** (code read, no runtime probe), or **unverified**. This worktree has no fmm index and the brief forbids writes, so all evidence is from grep and targeted reads; every "none found" lists the searches run.

---

## Reuse Map

### 1. Ownership

The offset is not first-class today. It is derived on every call inside `src/domain/gridLayout.ts:getSceneGridAlignment` (alignment from `align` over base home positions, plus `origin`) and immediately folded into every `CubeLayoutPose.homePosition` by `gridLayout.ts:createSceneGridLayout`. There is no stored offset anywhere: no writers, only derivation. That is the root fact constraining the build.

| State | Owner | Writers | Readers | Which writer wins |
|---|---|---|---|---|
| `GridState.format` (align, origin, cellSize, gap, gapOverrides) | `domain/grid.ts:GridFormat` | Authored ops: `domain/scene.ts:applyGridPreset`, `domain/scene.ts:resizeGridSceneWithResult` (remaps gapOverrides), set-grid-gap operations. `align` has **no writer anywhere**: it is constant `"center"` from `grid.ts:defaultGridFormat` (searches: `grep -rn "\.format\.align\|align:" src` → only defaults and repair at `grid.ts:normalizeGridFormat`) | `gridLayout.ts:*`, `sceneMorph.ts:interpolateGridState`, persistence | Authored workbench writes; persisted verbatim inside the pose (`persistence/recordCodecs/compactPose.ts` stores `pose.grid` as `g`) |
| Transient frame `GridState` (during a gap) | `evaluation/sceneMorph.ts:interpolateGridState` (module-private) | Only `sampleSceneMorph` | The whole render pipeline, via the frame scene | Derived value, never persisted; endpoint grids untouched |
| Resolved alignment offset | `domain/gridLayout.ts:getSceneGridAlignment` | None (pure derivation per call) | Every `createSceneGridLayout` caller, plus `domain/seams.ts:createSeamModel` directly | n/a — single derivation path, no competing writers |
| `SceneGridLayout` (homePosition/renderPosition per cube) | `domain/gridLayout.ts:createSceneGridLayout` | n/a (derived per call site) | See consumer table below | Stability layer `scene/useStableGridLayout.ts:useStableGridLayout` preserves pose references across recomputes via `gridLayout.ts:isSameCubeLayoutPose` |
| Morph frame scene | `evaluation/sceneMorph.ts:sampleSceneMorph` | Only itself, via `evaluation/sceneTransition.ts:sampleSceneTransition` | `transport/stagedScene.ts:sampleStageSource`, `evaluation/pieceAt.ts:samplePieceAt` | `transport/stagedScene.ts:resolveStageSource` precedence: comparison scrub > armed piece > authored. One adapter (`createStagedSceneReader`) and one plan cache (`transport/activeTransitionPlan.ts:createActiveTransitionPlanCache`) |
| `Moment.presence` | `evaluation/scoreAt.ts:Moment` | Two writers: `sceneMorph.ts:sampleSceneMorph` (transition frames) and `scoreAt.ts:scoreAt` via `applyAssemblyTrack` (assembly playback) | `scoreAt.ts:getMomentCells`, `scoreAt.ts:applyMomentToLayout`, renderer | Adjudicated upstream by `evaluation/pieceAt.ts:resolvePieceSample`: static position → assembly owns; transition → morph owns exclusively (documented, ANIMATION.md invariant 3) |
| Presence application to layout | `evaluation/scoreAt.ts:applyMomentToLayout` (scale multiply), `getMomentCells` (filter) | n/a | `scene/useCubeSceneRenderState.ts` | **Ordering is the bug's mechanism**: `useCubeSceneRenderState` computes `baseLayout` from the frame scene's full cell set first, applies presence after. The recentre therefore sees presence-0 cells (structural, and consistent with the measured displacement) |
| Endpoint scenes | `domain/workbench.ts:getStateScene` (per State, fresh object per call), `getWorkingScene` (WeakMap-cached) | n/a | Comparison endpoints in `stagedScene.ts:resolveStageSource`; piece transition endpoints in `pieceAt.ts:resolvePieceSample` | Plan cache keys on pose revision identity (`state.pose.id`, `workbench.workingPose`), not scene identity |
| Grid tween progress (`gridProgress`) | Local in `sceneMorph.ts:sampleSceneMorph` | Only itself | Sole consumer: the one `interpolateGridState` call | See section 4 |
| `MorphSettings` | `domain/morphSettings.ts:MorphSettings` | Authored via `panels/motion/MorphInspector.tsx` (label "Moving" = `glide`), normalized by `patchMorphSettings`; carried per transition on `domain/score.ts:Transition.settings` (persisted in the piece score) | Morph scheduling | Comparison scrub bypasses authored settings: `stagedScene.ts:resolveStageSource` hardcodes `defaultMorphSettings` |
| Occupied extent / dimensions | `domain/scene.ts:getCellCoordBounds`, `getSceneGridBounds`, `getSceneGridDimensions` | n/a (derived over coords) | Resize/preset path, `panels/StructureSection.tsx`, `domain/sliceMap.ts`, `domain/seams.ts` | Coord-space, authored-path; distinct from the world-space extent inside `getAlignmentOffset` |

### 2. Consumers of the offset

The offset reaches consumers only through `CubeLayoutPose` positions, so the consumer set is the `createSceneGridLayout` caller set (search: `grep -rn createSceneGridLayout src`) plus the one direct `getSceneGridAlignment` caller. Verdicts assume the planned change **preserves endpoint resolution** (offset per endpoint = today's centre alignment over that endpoint's own full cell set) and changes only the crossing. If the build changes endpoint resolution too, the "breaks" column flips for camera and thumbnails; see Plan decision 2.

| Consumer | Path | Verdict | Evidence |
|---|---|---|---|
| Live render pipeline | `scene/useStableGridLayout.ts:useStableGridLayout` ← `scene/useCubeSceneRenderState.ts` → instances (`scene/cubeInstances.ts`, `scene/useCubeSceneInstances.ts`), selection chrome (`scene/selectionChromeInstances.ts`, `scene/SelectionChromeLayer.tsx`), neighbor slots, hit targets | This is the target seam; the fix lands here by construction | Structural |
| Per-State captured camera views | `domain/cameraTrack.ts:StateCameraView` = absolute `CameraPoseSnapshot` (world position/target/up/zoom) + projection. Captured by `domain/structureOperations.ts:bindViewToState` from an operation payload; compiled into a track by `domain/pieceCameraTrack.ts:compileStateViewCameraTrack` | **Does not break**: stores nothing derived from the offset. Views desync only if endpoint world positions change (steady-state resolution change), because they were authored aiming at the current centred layout | Structural (type + capture path read); the desync-if-endpoints-move claim is unverified (no live probe) |
| Standing / initial camera | `app/useEditorCommands.ts` frames `readStaged().scene` via `view/viewportFocus.ts:createGridFramedCamera` | Recomputed live, no stored derivation; does not break | Structural |
| Thumbnails | `thumbnail/thumbnailArtifact.ts:createThumbnailArtifact` → `createSceneGridLayout(pose.grid, pose.cells)`; framing via `thumbnail/thumbnailView.ts` → `createGridFrameTarget`; cache `thumbnail/thumbnailCache.ts:createStateThumbnailCache` | **Does not break**: renders endpoint Poses (all presence 1), and the cache is an in-memory WeakMap keyed by Pose reference — no persisted derived images to go stale. If endpoint resolution changed, thumbnails would re-render correctly through the same path | Structural |
| Shared edge tweens | `evaluation/sharedEdgeTweens.ts:planSharedEdgeTweens` builds **per-endpoint** layouts (`createSceneGridLayout(a.grid, a.cells)` and `(b.grid, b.cells)`) | Does not break: cross-endpoint group matching keys on `cellId+edgeId` (`sharedEdgeTweens.ts:sharedEdgeGroupKey`), not world positions; within-endpoint coincidence is invariant under a uniform translation. Also the proof that per-endpoint resolution already exists in the morph pipeline — a reuse anchor for the build | Structural |
| Burial / visibility | `domain/cubeVisibility.ts:getCubeVisibilityAnalysis` → `domain/exposure.ts:isCubeFullyBuried` | Does not break: relative geometry, uniform offset cancels; callers (`domain/cubeOperations.ts`, `domain/sliceMap.ts`) are authored-path | Structural |
| Focus / framing | `view/viewportFocus.ts:createViewportFocusGeometry` → `view/focusGeometry.ts:getFocusBounds` | Recomputed live, no stored state; but it is a presence-0 reader (section 3) | Structural |
| Incremental authored path | `scene/incrementalCubeSceneOwner.ts` (recomputes layout per journal entry) and `domain/authoredRenderImpact.ts:createLayouts` (previous/next layout compare via `isSameCubeLayoutPose`) | Consistent by construction (both sides recomputed with the one owner function). If steady-state resolution changed, every pose would compare unequal once → one full re-render, not a correctness break | Structural |
| Seams | `domain/seams.ts:createSeamModel` (direct `getSceneGridAlignment` caller) → `scene/SeamLayer.tsx` | Flag-off: `config/cubicellConfig.ts:seamSurfacesEnabled = false`. Must be kept in sync if the offset becomes a parameter | Structural |
| Persistence | `persistence/recordCodecs/compactPose.ts` stores `pose.grid` verbatim | No offset stored today. **If the build adds a field to `GridState`, the wire shape changes** → version bump and reset per the no-migrations policy. Keeping the offset derived (in the morph plan, not on `GridState`) avoids any wire change | Structural |

### 3. Presence-0 reads

Every place computing an extent, centre, or bound over a cell set without filtering by presence, that can receive a morph-frame scene:

1. `domain/gridLayout.ts:getSceneGridAlignment` (via `createSceneGridLayout`) — the recentre. Reached with frame scenes from `scene/useCubeSceneRenderState.ts:baseLayout`. **Measured** (orchestrator's probes; 1→2 growth displaces the pre-existing cube 0.75 x-units at frame one; symmetric 1→3 displaces nothing; displacement equals the change in the extent's centre).
2. `view/focusGeometry.ts:getFocusBounds` / `getCellsBounds` via `view/viewportFocus.ts:createViewportFocusGeometry` — receives the **staged** scene through `app/useEditorCommands.ts:readFramingInputs` and `view/interactionFraming.ts:computeGridFrame` ("Frame All against the staged scene" per its own doc comment). Frame All or selection framing issued mid-gap would fit bounds that include presence-0 cells. Structural; whether framing commands can actually fire mid-gap is **unverified** (no probe; comparison staging sets `interactive: false` except at progress 1, but I found no gate between the interaction core's framing commands and a transition in flight).
3. `domain/seams.ts:createSeamModel` — `getCellCoordBounds(scene.cells)` + `getSceneGridAlignment(scene.grid, scene.cells)` over the `CubeScene` scene prop, which is the staged scene. Currently flag-off (`seamSurfacesEnabled = false`).

Correct-by-design, listed to prevent false positives: `evaluation/sharedEdgeTweens.ts` per-endpoint layouts (endpoint resolution is the semantic); `domain/assemblyOrder.ts:resolveOrderOrigin` computes a coord-centre over the class's own cells only (stagger ordering, not world extent).

None found beyond these. Searches run: `grep -rn createSceneGridLayout src` (all callers enumerated above), `grep -rn getSceneGridAlignment src`, `grep -rn "getCellCoordBounds\|getSceneGridBounds" src` (hits: StructureSection.tsx, sliceMap.ts, seams.ts — the first two operate on authored/library cells, not frame scenes), `grep -rn "getFocusBounds\|getBoundsCenter" src`, `grep -rn "getMomentCells\|applyMomentToLayout" src` (the presence-aware sites: render state and shadow shell both consume filtered `stagedCells`).

### 4. The mis-shelved grid tween

Owner: local `gridProgress` in `evaluation/sceneMorph.ts:sampleSceneMorph` — `quantizeProgress(glideEase(globalProgress), plan.changed.motion.quantize)` where `glideEase = easingFor(plan.changed.motion.easing)` and `plan.changed = planClassMotion(topology.changedCells, settings.glide, …)`. `settings.glide` is the Moving tab (`panels/motion/MorphInspector.tsx` labels `glide` as "Moving"). No branch guards the empty-changed-set case, so the Moving tab's easing and quantize drive the arrangement crossing even in gaps where no cube moves. Structural; consistent with the brief's framing.

Sole consumer: the single `interpolateGridState(plan.a.grid, plan.b.grid, gridProgress, globalCut)` call in the same function. Related discrete switch: `align`/`overflow` hard-swap on `globalCut = globalProgress >= settings.cutAt`, independent of `gridProgress`.

Where it should live: with the arrangement crossing owner — a dedicated progress channel computed in `sampleSceneMorph` from an arrangement-owned curve, feeding both `interpolateGridState` and the new offset lerp, so the arrangement's inputs and its resolved offset finally cross under one clock. Whether that curve is a new persisted `MorphSettings` channel or derived from the global transition is a human call (Plan decision 3). Guard note: `tests/sceneMorph.test.ts` ("snaps scene and grid modes at the global cut") pins the current align hard-switch; when behavior changes it must be re-paired, not deleted (LESSONS.md invariant-pairing rule).

---

## Quality Map

| Finding | Disposition | Reason |
|---|---|---|
| `interpolateGridState` crosses the arrangement's three inputs three ways (origin/cellSize/gap/gapOverrides lerp; align/overflow hard-switch at cutAt; derived extent steps at endpoint boundaries) | **Refactor during** | This inconsistency is the defect under repair; it cannot be groomed separately from the fix |
| Grid tween borrowed from `plan.changed.motion` | **Refactor during** | Same seam; moving it is part of making the crossing first-class |
| Alignment derived at 8 call sites, no stored value | **No pre-groom needed** | Cohesion is good: one owner function. Making the offset first-class is an additive parameter/return on `gridLayout.ts`, not a consolidation job |
| `domain/seams.ts:createSeamModel` runs its own alignment + extent walk (its doc comment promises "without a second layout path", but it is a second alignment path) | **Defer** | Flag-off (`seamSurfacesEnabled = false`); builder must only keep its call signature compiling if `getSceneGridAlignment` changes shape |
| "glide" is overloaded: morph glide class (Moving tab) vs camera glide preferences (`preferences.glideMoveWorldUnitsPerSecond` etc. in `panels/SceneSection.tsx`) | **Defer** | Pre-existing; renaming is out of slice scope but the briefs should say "arrangement crossing", never "glide", to avoid the collision |
| "arrangement" as ubiquitous language does not exist in code (search: `grep -rni arrangement src` → zero hits in source) | **Decision needed** | Introducing the term (types, file, settings key) is a naming call the human should ratify before the build |
| `align` is persisted and honored but has no author anywhere in the UI | **Defer, do not remove** | Potentially a dormant feature, not dead metadata; `git log -S` before any removal. If the crossing folds alignment into a resolved offset, `align`'s hard-switch at cutAt becomes moot for the gap but the field stays authored-constant |
| Comparison scrub hardcodes `defaultMorphSettings` (`stagedScene.ts:resolveStageSource`) | **Refactor during (small)** | Any new arrangement channel must flow through the default too, or scrub and playback cross differently |
| Dead code in this area | None found | Searches: caller enumeration above plus `grep -rn "sampleSceneTransition\|sampleResolvedSceneTransition" src` (the dormant forced-cut path in `sceneTransition.ts` is documented as dormant in its own NOTE, not undocumented dead code) |

---

## Plan — decisions needing a human call before code

1. **Where the resolved offset lives.** Options: (a) resolved per endpoint inside the morph plan and lerped per frame, passed into layout creation as an explicit precomputed alignment (new optional parameter on `createSceneGridLayout`, or a resolved-alignment field on the frame's transient `GridState.format.origin`); (b) a stored field on `GridState` (wire change → version bump + reset); (c) folded into the frame grid's `origin` with alignment neutralized in frame grids only. Scout's read: (a) or (c) keep persistence untouched and endpoint resolution identical; (b) is the only option that moves every cube in every state and desyncs captured camera views. Recommend (a)/(c) family; the choice between them shapes the builder's seam.
2. **Endpoint resolution must not change.** The displacement is a crossing bug, not an endpoint bug: symmetric growth displaces nothing because endpoint centres agree. Keeping each endpoint's offset exactly today's centre alignment over that endpoint's full cell set preserves captured camera views, thumbnails, and every authored-path consumer. Ratify this as a constraint on the builder.
3. **What curve drives the crossing.** Reuse glide (status quo, wrong tab), the raw global progress (linear, no new settings), or a new arrangement channel in `MorphSettings` (persisted on `Transition.settings` → wire shape change → version bump + reset per policy). Human call; affects the Moving tab's meaning.
4. **The align/overflow hard-switch at cutAt.** Once the offset is lerped, `align`'s switch no longer moves cubes mid-gap; decide whether the switch stays (harmless, consistent with overflow) or the crossing owns it.
5. **Framing during gaps** (presence-0 bounds in Frame All, finding 3.2): in this slice or a follow-up? It is the same class of defect but a different consumer.
6. **Test pairing.** `tests/sceneMorph.test.ts` align-switch and gap tests pin current behavior; the build must re-pair them with the new invariant (offset continuity across the gap, endpoint identity at t=0 and t=duration), with a controlled-red proof for the continuity guard.
