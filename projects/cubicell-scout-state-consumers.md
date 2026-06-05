# Scout C — State consumers and the camera seam

Baseline: `cubicell` main @ `71098b4` (clean tree, verified). Read-only pass; no repo writes.
Citations are path + symbol. Scout A (State shape) and Scout B (camera runtime) findings are taken as given and not re-derived.

**Headline:** the framing owner already exists and is singular (`CameraTrack` under a possession runtime). A camera on a shared `State` creates a second authored owner the possession model has no arbitration for, and it lands on exactly the records whose caches, no-op guards, and validators key on `pose` identity, so it goes stale silently. Ship it as **(a) per-user recall on `UserProjectState`**.

---

## Findings

### 1. Every consumer of a State

**Domain projection and evaluation**

| Consumer | Path + symbol | What it does with the State |
| --- | --- | --- |
| Scene projection | `src/domain/workbench.ts:getStateScene` | Pure projection: `getPoseRevisionDocument(state.pose)` + the structure's score into a `CubicellScene`. Reads `pose` and `assetId` only. |
| Cell union | `src/domain/workbench.ts:collectStructureCells` | Unions cells across a structure's States for assembly ordering. Pure, cells only. |
| Lookup | `src/domain/workbench.ts:findState` | Id lookup. Pure. |
| Piece sampling | `src/evaluation/pieceAt.ts:resolvePieceSample` | Static hold → `getStateScene`; transition → two endpoints `{ revision: state.pose.id, scene: getStateScene(...) }`. |
| Frame sampling | `src/evaluation/pieceAt.ts:samplePieceAt` | Pure projection of a resolved sample. Never sees a State. |
| Transition sampling | `src/evaluation/sceneTransition.ts:sampleResolvedSceneTransition` | Consumes endpoint **scenes**, never States. |
| Morph kernel | `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`, `:sampleSceneMorph` | Cells, grid, ink. Never sees a State. |

**Transport and the retained plan**

| Consumer | Path + symbol | What it does with the State |
| --- | --- | --- |
| Stage source | `src/transport/useStagedScene.ts:resolveStageSource` | Comparison scrub builds the "saved" endpoint as `{ revision: state.pose.id, scene: getStateScene(...) }` against `{ revision: workbench.workingPose, scene }`. |
| Stage sampling | `src/transport/useStagedScene.ts:sampleStageSource` | Feeds the endpoint pair to the plan cache and samples it. |
| **Morph plan cache** | `src/transport/activeTransitionPlan.ts:createActiveTransitionPlanCache` | Retains one prepared plan keyed on `Object.is(fromRevision)` / `Object.is(toRevision)` — i.e. on `state.pose.id`. **This is the #137 defect surface.** |

**Score and sequence**

| Consumer | Path + symbol | What it does with the State |
| --- | --- | --- |
| Sequence track | `src/domain/score.ts:findStateTransitionTrack`, `src/domain/stateTransition.ts` (`StateTransitionTrack.keyframes[].stateId`) | The ordered sequence references States **by id**. Never reads State content. |
| Sequence repair | `src/domain/stateTransition.ts:repairStructurePieceScore`, `src/domain/structureSequenceOperations.ts:applyStructureSequenceOperation` | Keeps keyframes and `stateIds` in sync. Id-only. |
| Piece preset | `src/domain/structureOperations.ts:applyPiecePreset` (`apply-piece-preset`) | Rebuilds the assembly order from `collectStructureCells` and resets every transition to `defaultTransition`. **Cells only**; no other State field participates. |

**Document operations**

| Consumer | Path + symbol | What it does with the State |
| --- | --- | --- |
| Capture builders | `src/panels/stateCapture.ts:createStateCapture`, `:createNewStateFromSelected`, `:createStateUpdate` | Build `capture-state` / `new-state-from-selected` / `update-state` from `workbench.workingPose`. |
| Capture / duplicate | `src/domain/structureOperations.ts:captureState`, `:createStateFromSelected` | Create the `State` record and append a sequence keyframe atomically. |
| Update | `src/domain/structureOperations.ts:updateState` | Swaps `pose`. **No-ops when `createJsonDiff(oldPose, newPose).length === 0`.** |
| Apply | `src/domain/structureOperations.ts:restoreState` (`restore-state`) | Sets `working` + `workingPose` only. Pure domain; touches nothing else. |
| Delete / rename | `src/domain/structureOperations.ts:deleteState`, `:renameState` | Id and name. |
| Undo derivation | `src/domain/authoredInverse.ts:deriveInverseBody` → `deriveDocumentInverse` | `update-state` inverts to **`restore-state-pose`** (poseRevision + score only). `restore-state` inverts to `restore-working`. |
| Undo application | `src/domain/documentRestoreOperations.ts:applyDocumentRestoreOperation` | `restore-state-entry` carries a whole `PositionedEntity<State>`; `restore-state-pose` carries only a `PoseRevision`; `restore-structure-sequence` / `restore-structure-asset` carry `Array<PositionedEntity<State>>`. |

**Session, selectors, UI**

| Consumer | Path + symbol | What it does with the State |
| --- | --- | --- |
| **Modified indicator** | `src/state/pieceSessionSelectors.ts:createActiveStateStatusSelector`, `:isPoseModified` | The one source of "this State has drifted". Memoized on **`Pose` reference identity** for the saved side. |
| Reference repair | `src/state/sessionReferences.ts:repairEditorSessionReferences`, `:repairActiveStateReference` | Prunes `activeStateId` and `morphScrub.stateId` to live States. Id-only, runs after every mutation, history move, and rehydrate. |
| **Apply seam** | `src/state/actions/documentActions.ts:selectActiveStateRecipe`, `:completeActiveStateSelection` | Dispatches `restore-state`, sets `activeStateId`, clears `morphScrub`, records history only when live drift is discarded. |
| Motion model | `src/panels/motion/usePieceMotionModel.ts:usePieceMotionModel` | The single derivation feeding both the dock filmstrip and the right-rail inspector. |
| Filmstrip | `src/panels/motion/PieceStateStrip.tsx:PieceStateStrip` (`PieceStripState`) | Card summaries: `{ id, modified, name, pose }`. |
| Panel wiring | `src/panels/motion/PieceMotionPanel.tsx:PieceMotionPanel` | `snapshot()` → capture + select; `onSelectState` → `selectActiveState`; `onUpdateState` → `createStateUpdate`. |
| Compare | `src/panels/motion/MotionInspector.tsx:StateComparisonControls` | Sets `morphScrub` `{ stateId, t }`, the saved-vs-live scrub. |

**Thumbnails / previews**

| Consumer | Path + symbol | What it does with the State |
| --- | --- | --- |
| **Thumbnail cache** | `src/thumbnail/thumbnailCache.ts:createStateThumbnailCache` | `WeakMap<Pose, Promise<OrthographicThumbnailSet>>`. The doc comment states the contract outright: pose reference identity **is** the invalidation key. |
| Thumbnail framing | `src/thumbnail/thumbnailView.ts:createOrthographicThumbnailView` | Three fixed axis views derived deterministically from pose via `createGridFrameTarget`. **Deliberately camera-independent** ("Thumbnails never orbit"). |
| Poster resolution | `src/thumbnail/assetPoster.ts:resolveAssetPosterState`, `:resolveAssetThumbnailSet` | Resolves a structure's `posterStateId` to a State and renders its pose. Exported from `src/thumbnail/index.ts`; **no production consumer today** (reverse-dependency closure is `index.ts` plus seven test files). Forward-declared for the asset browser, not dead. |

**Persistence**

| Consumer | Path + symbol | What it does with the State |
| --- | --- | --- |
| Structure record | `src/persistence/recordCodecs/structureRecordCodec.ts:StructureStateReferenceV1`, `:encodeStructureRecord`, `:decodeStructureRecord` | Persists `{ id, name, poseRevisionId }` per State. Decode enforces `hasOnlyKeys(candidate, ["id","name","poseRevisionId"])`. |
| Pose revision record | `src/persistence/recordCodecs/poseRevisionRecordCodec.ts` + `:compactPose.encodeCompactPose` | The pose content itself, compacted. |
| Projection | `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` | Fans a Workbench into structure records, pose-revision records, history, draft, outbox, and `UserProjectState`. |
| Local history | `src/persistence/recordCodecs/localHistoryRecordCodec.ts` | Serializes every history step's workbench, including `library.states`, with an ownership/shape cross-check. |
| **Validators** | `src/state/workbenchValidation/assets.ts:isState`, `:readStates`, `:isPoseRevision` | `isState` uses `hasOnlyKeys(["assetId","id","name","pose"])`. `readStates` **rebuilds each State field by field** from a whitelist. |
| User project state | `src/persistence/recordCodecs/userProjectStateRecordCodec.ts:UserProjectState` | `{ activeAssetId, activeStateId, panelLayout, projectId, userId }`. Private, per user, per project. |

**Export:** no export path consumes a State today. `PROJECT.EXPORT.md` is an unimplemented decision doc; both of its options compile recorded framing into a `CameraTrack`, never into a State.

---

### 2. Per consumer: CHANGE, IGNORE, or SILENTLY WRONG

Assume the naive shape: `State` gains a sibling field `camera: CameraPoseSnapshot | null` next to `pose`.

**Hard blockers — the feature does not run without these**

| Consumer | Verdict | Why |
| --- | --- | --- |
| `isState` (`workbenchValidation/assets.ts`) | **CHANGE (rejects)** | `hasOnlyKeys` fails on the extra key. Every State is rejected. |
| `readStates` (same file) | **CHANGE (drops)** | Rebuilds `{ assetId, id, name, pose }` explicitly. A camera survives no rehydrate. Fails open and silent. |
| `decodeStructureRecord` | **CHANGE (rejects)** | `hasOnlyKeys(candidate, ["id","name","poseRevisionId"])` on each state reference. |
| `encodeStructureRecord` | **CHANGE** | Emits the three-field reference; nothing else is persisted. |

**Silently wrong if they ignore it**

| Consumer | Verdict | Failure |
| --- | --- | --- |
| **`createActiveTransitionPlanCache`** | **SILENTLY WRONG** | Retains one plan keyed on `Object.is(fromRevision, …)` where `fromRevision` is `state.pose.id`. A camera-only edit leaves `pose.id` untouched, the comparison scrub re-enters with the same key, and the retained plan (and anything framing-derived hanging off it) serves the previous camera. This is precisely the #137 shape: a field on the endpoint record that the endpoint's identity does not cover. |
| **`createStateThumbnailCache`** | **SILENTLY WRONG the moment posters are meant to show captured framing** | Keyed `WeakMap<Pose, …>`. A camera-only edit yields the same `Pose` reference → the stale image is served forever. Today it is safely IGNORE only because `createOrthographicThumbnailView` is axis-locked by design and never reads a camera. The instant anyone renders a poster from a State's captured view, this cache is wrong and its key must move off `Pose`. |
| **`createActiveStateStatusSelector` / `isPoseModified`** | **SILENTLY WRONG** | The "modified" flag diffs poses only. A camera-only change never lights the indicator, so the user sees a clean State and has no signal that anything is unsaved. |
| **`updateState`** | **SILENTLY WRONG** | Returns `workbench` unchanged when the pose diff is empty. Move the camera, press Update, nothing happens, no error. |
| **`createStateFromSelected`** | **SILENTLY WRONG (inverted)** | Requires the pose diff to be **empty**. If a camera ever entered `Pose`, duplicating a State after touching the camera would silently refuse. |
| **`deriveDocumentInverse` (`update-state` → `restore-state-pose`)** | **SILENTLY WRONG** | The inverse carries `poseRevision` + `score` only. Undo after a camera-bearing update restores the old pose and leaves the new camera. Needs either a new field on `restore-state-pose` or a new restore operation. |
| `restoreState` (`restore-state`) | **SILENTLY WRONG for the product** | Sets `working` + `workingPose` and nothing else. The camera cannot move from here: the domain is pure and the camera lives in the interaction runtime. Applying a State would leave the captured view unused unless a side effect is added at `selectActiveStateRecipe`. |

**Safe to ignore**

`getStateScene`, `collectStructureCells`, `findState`, `resolvePieceSample`, `samplePieceAt`, `sampleResolvedSceneTransition`, the whole `sceneMorph` kernel, `findStateTransitionTrack` and the sequence operations, `applyPiecePreset`, `renameState`, `deleteState`, `repairEditorSessionReferences`, `createOrthographicThumbnailView`, `encodeCompactPose`. All are pure projections over `pose`, cells, or ids. They neither see nor need a camera.

**Structurally safe by accident**

`restore-state-entry`, `restore-structure-sequence`, `restore-structure-asset` carry whole `State` values (`PositionedEntity<State>`), so a new field rides along, and the `jsonValuesEqual(restored, workbench)` guards pick it up. Same for `localHistoryRecordCodec`, which serializes whole workbenches. These work only because they are structural; the *targeted* pose paths above are where it breaks.

**The pattern:** every consumer that is safe reads `pose`. Every consumer that breaks silently identifies a State **by** `pose`. Adding a durable field beside `pose` that `pose.id` does not cover reproduces #137 in four separate caches and guards at once.

**And the shape that would be worse:** putting the camera *inside* `Pose` (`src/domain/scene.ts:Pose = Omit<CubicellScene, "score">`) is strictly more destructive. `sceneFromPose` spreads pose into `CubicellScene`, so a camera would leak into every scene consumer, the morph kernel, `poseFromScene`'s whitelist, `encodeCompactPose`, `isPoseShape`, and every `createJsonDiff` no-op guard. Do not put it in `Pose`.

---

### 3. Precedence — the crux

**Precedence exists today, and it is a possession model with exactly one authored claimant.**

`src/camera/cameraTrackAuthority.ts` implements it: `beginCameraTrackPossession` marks the authored track as the active owner with `poseFollowing` / `projectionFollowing` armed; `setCameraTrackPose` anchors the live pose while following; `detachCameraTrackPose` drops following the instant a user gesture starts (`src/camera/cameraAuthorityRuntime.ts:beginCameraAuthorityGesture` calls it first, before anything else); `rearmCameraTrackFollow` re-arms; `releaseCameraTrackPossession` hands control back. The single claimant is the animation camera track, wired through `CameraAuthority.beginTrackPossession` / `setTrackPose` / `releaseTrackPossession` in `src/camera/cameraAuthorityRuntime.ts:createCameraAuthority`.

The state machine has exactly two states: authored possession, or live user control, with the gesture always winning the moment it starts. It has **no arbitration between two authored sources** because there has never been more than one.

The doctrine says why there is only one, and says it as a lock. `STUDIO.ANIMATION.md` "One lane per asset, one camera lane": *"Exactly one camera lane. The camera is stage-owned and singular, so it is never a per-asset lane."* `STUDIO.PROJECT.md` "What a State captures (locked)": *"nothing about the camera. The viewpoint is stage-owned and never baked into a State."* `STORAGE.md` classifies authored camera keyframes as asset state and the editor viewport camera as Presence, memory only.

**Two authored owners is unacceptable, and I would not adopt a precedence rule to paper over it.** A rule ("track wins during playback, State wins on manual apply") is implementable, but it makes framing conditional on transport mode, which is a rule the user has to hold in their head and which the possession runtime would have to grow a second claimant to express. The single owner of *authored* framing is and stays `CameraTrack` on the Animation `StageScore`.

The correct resolution is that the two things are not the same kind of thing. Authored framing is one owner. What Stuart is asking for is **navigation recall**: a private "put me back where I was looking when I made this". Classify it as Presence/workspace-session under `STORAGE.md`, keep it out of the authored document entirely, and there is no second owner and no precedence question. That reclassification is the whole design.

---

### 4. UX contract: does the camera move on apply?

**Recommendation: yes, always — but only for States the user explicitly framed. No preference toggle.**

The "camera jumping is hostile" concern assumes applying a State is how you compare configurations. In this codebase it is not. Comparison is `morphScrub`, driven by `StateComparisonControls` in `src/panels/motion/MotionInspector.tsx`, sampled by the `"comparison"` branch of `resolveStageSource`, and it never applies anything — the working pose stays put and the scrub blends saved-against-live in place. `PieceMotionPanel`'s `onSelectState` makes the split explicit in a comment: the active card deliberately never restores, *"restoring would discard live drift, making Compare unreachable"*.

So applying a State is already a hard context switch that replaces `workingPose` wholesale. Moving the camera with it is consistent with what apply already means, not a new intrusion.

The hostility is fully neutralised by making capture explicit (finding 5). A State with no recalled view leaves the camera exactly where it is. Only States the user deliberately framed move it. That is opt-in at the granularity that matters — per State, at capture time — which is strictly better than a global preference the user sets once and then forgets.

**No toggle belongs.** For the record, the surface that would host one is `CubicellPreferences` in `src/state/cubicellState.ts` (rendered by `src/panels/SceneSection.tsx`, defaulted by `createDefaultPreferences`, normalized by `src/state/preferencePort.ts:normalizeGlobalPreferences`) — it already carries `selectionFocusMode`, `viewportMode`, and the camera-feel knobs. Adding a "restore view with State" boolean there would be a global answer to a per-State question, and a preference nobody discovers is worse than a behaviour that only fires where it was asked for.

One implementation note: apply should route through the existing `restore` view command (`src/editor/commands.ts:createRestoreViewCommand`, `ViewCommand` kind `"restore"`) so framing motion inherits the established view-command semantics rather than inventing a second path.

---

### 5. Automatic or explicit capture?

**Explicit.** And the current code argues for it twice.

The three capture/update builders are `src/panels/stateCapture.ts:createStateCapture`, `:createNewStateFromSelected`, `:createStateUpdate`, dispatched from `PieceMotionPanel`'s `snapshot()` and `onUpdateState`. All three read `workbench.workingPose` and nothing else.

- **Automatic capture at save time is actively hostile here.** `snapshot()` is the fast, repeated gesture that builds a sequence: the user is orbiting to inspect the model while snapshotting, and every incidental viewing angle would become durable framing. States would silently acquire cameras nobody chose, and then finding 4's apply behaviour would start yanking the view on every card click.
- **`update-state` cannot re-capture a camera even if you wanted it to.** `src/domain/structureOperations.ts:updateState` returns the workbench unchanged when the pose diff is empty, and `createActiveStateStatusSelector` never marks a camera-only change as modified, so the Update affordance would not even be enabled. Routing camera recall through `update-state` means fighting both guards. Routing it around them (option a, a non-document write) means neither guard is in the path at all.

So: an explicit per-card affordance — a small "set view" control on the State card in `PieceStateStrip`, reading the live pose through `useCameraSnapshotReader` (already provided to the Editor by `src/studios/editor/EditorStudio.tsx` as `readCameraSnapshot={core.getState}`, the same reader `src/studio/CameraTrackControls.tsx` uses for `createCameraCapture`). Re-invoking it overwrites; a clear affordance removes it.

---

### 6. Separability from the animation studio

**They are separable, cleanly, because the animation studio's camera primitive already exists and already ships.**

`CameraTrack` / `CameraKeyframe` / `CameraPoseSnapshot` (`src/domain/cameraTrack.ts`), located via `src/domain/score.ts:findStateTransitionTrack`'s sibling `findCameraTrack` and `src/domain/workbench.ts:getCameraTrack`, authored by `src/studio/cameraCapture.ts:createCameraCapture` and `src/studio/CameraTrackControls.tsx`, validated by `src/state/cameraTrackValidation.ts:repairPersistedCameraTrack`, undone via `restore-animation-score` (`src/domain/authoredInverse.ts`), and driven at runtime by the possession model in finding 3. `CAMERA.md` "Persistence" settles the keyframe fields; `STUDIO.ANIMATION.md` settles per-keyframe placement binding. The studio does not need a new camera primitive from this work, and does not need camera-per-State.

So the answer to "redundant second primitive, correct independent one, or actively wrong shape":

- **As authored framing on `StructureStateReferenceV1` (option b): actively wrong, and someone would have to undo it.** It contradicts a locked doctrine line in two documents, adds a second authored claimant to a possession runtime built for one, and lands on records whose caches key on `pose.id` (finding 2). The wire cost is a `structureRecordSchemaVersion` bump on the shared structure document, paid by every reader forever, for a field the animation studio will never consult.
- **As per-user recall (option a): a correct, independent concern.** It is not framing authorship at all; it is a private navigation aid, the same class as `activeStateId` and `panelLayout`.

**The seam that keeps them independent:** authored framing lives in `AnimationAsset.score` as a `CameraTrack` and is the only thing that ever possesses the camera during playback. Recall lives in `UserProjectState`, is per user, is never read by any evaluation or sampling path, and only ever fires as a one-shot `restore` view command at the moment a user clicks a State card. The two never share a type, a record, or a code path — the sole overlap is `CameraPoseSnapshot` as a value type, which is correct reuse, not coupling.

One optional convenience, explicitly not a dependency: a recalled pose could seed a `capture-camera-keyframe` later. `createCameraCapture` already takes a `{ pose, projection }` snapshot from any source, so that lands as a caller change with zero shape impact if it is ever wanted.

---

### 7. Verdict, blast radius, and PR split

**Verdict: (a) per-user recall on `UserProjectState`.** It is the only option that does not violate locked doctrine, does not create a second authored framing owner, does not touch the shared structure wire format, and does not route through the pose-diff guards that would silently swallow a camera-only edit. Option (b) buys shared, versioned framing that nothing in the product asked for, at the cost of a doctrine reversal and a defect class we already paid for once in #137.

The one honest cost of (a): recall is private and does not travel with a shared structure. Given `STORAGE.md` V1 is single-writer and cross-project sharing is deferred, nothing observable is lost today. If shared authored framing is ever genuinely wanted, it arrives as `CameraTrack` on an animation, which is where it already belongs.

**Shape.** `UserProjectState` gains a recall map keyed by state id, alongside `activeStateId`:

```
stateViews: readonly { pose: CameraPoseSnapshot; stateId: string }[]
```

An array, not a `Record`, to match the codebase's existing readonly-array-of-records style and to keep `hasOnlyKeys` validation straightforward. It needs pruning when States are deleted; `src/state/sessionReferences.ts:repairEditorSessionReferences` is the established home for exactly that (it already prunes `activeStateId` and `morphScrub.stateId` after every mutation, history move, and rehydrate).

**Blast radius — every module that must change**

*Persistence (5)*
- `src/persistence/recordCodecs/userProjectStateRecordCodec.ts` — `UserProjectState` field, encode, decode, `userProjectStateRecordSchemaVersion` bump.
- `src/state/cameraTrackValidation.ts` — reuse `isCameraPose` for decode validation. No change expected; verify it is exported through the guard surface the codec can reach.
- `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` — populate the new field in `encodeUserProjectStateRecord`; extend `ProjectRecordProjectionInput`'s `editor` pick.
- `src/persistence/projectRecordHydration.ts` — hydrate into the store.
- Version reset, per the project's no-migrations rule.

*State (4)*
- `src/state/cubicellState.ts` — `CubicellUserProjectState` and/or `CubicellEditorSession` field, `createDefaultPreferences` untouched.
- `src/state/sessionReferences.ts:repairEditorSessionReferences` — prune recalled views for dead state ids.
- `src/state/actions/documentActions.ts` — a `setStateView` / `clearStateView` action, and the restore side effect in `selectActiveStateRecipe` / `completeActiveStateSelection`.
- `src/state/index.ts` — selector export.

*UI (3)*
- `src/panels/motion/PieceStateStrip.tsx` — a per-card "set view" affordance and its `PieceStripState` field; `PieceStateStripProps` callback.
- `src/panels/motion/PieceMotionPanel.tsx` — wire capture via `useCameraSnapshotReader`, and dispatch `createRestoreViewCommand` on select.
- `src/panels/motion/usePieceMotionModel.ts` — surface which States have a recalled view.

*Not touched, deliberately:* `src/domain/**` (no document operation, no inverse, no restore op, no validator change), `src/evaluation/**`, `src/transport/**`, `src/thumbnail/**`, `src/persistence/recordCodecs/structureRecordCodec.ts`, `src/persistence/recordCodecs/poseRevisionRecordCodec.ts`. **This is the measure of the design being right:** every module listed in finding 2 as a blocker or a silent-wrongness sits in that "not touched" list.

**PR split — two.**

1. **Recall storage and capture.** Codec field + version bump, hydration, projection, store action, `repairEditorSessionReferences` pruning, and the per-card capture affordance. Ships inert: views are captured and survive reload, nothing moves the camera yet. Guard tests: round-trip through `projectRecordCodecs`, a rejected-shape decode case, and a pruning test asserting a deleted State drops its recalled view.
2. **Apply on select.** The `createRestoreViewCommand` dispatch in the select path, plus the card indicator showing which States carry a view. This is the behavioural half and the one with a live-UX gate: it changes what happens when the user clicks a State card, so it wants a hands-on pass before merge rather than review sign-off alone.

Splitting here means PR 1 is pure data with no interaction-feel risk, and PR 2 is a small, reviewable behaviour change that can be reverted on its own without losing captured data.

---

## Reuse Map

| Need | Reuse (do not build) |
| --- | --- |
| Serializable camera pose type | `src/domain/cameraTrack.ts:CameraPoseSnapshot` |
| Pose validation on decode | `src/state/cameraTrackValidation.ts:isCameraPose` |
| Read the live camera | `useCameraSnapshotReader` (`src/panels/editorCommandContext`), provided as `core.getState` by `src/studios/editor/EditorStudio.tsx`; precedent is `src/studio/CameraTrackControls.tsx` |
| Move the camera to a pose | `src/editor/commands.ts:createRestoreViewCommand` (`ViewCommand` kind `"restore"`) |
| Per-user, per-project private storage | `src/persistence/recordCodecs/userProjectStateRecordCodec.ts:UserProjectState` |
| Prune references to dead States | `src/state/sessionReferences.ts:repairEditorSessionReferences` |
| The apply seam | `src/state/actions/documentActions.ts:selectActiveStateRecipe` |
| Record shape validation idiom | `src/state/jsonGuards.ts:hasOnlyKeys` / `isId`, `recordCodecs/result.ts:isRecordEnvelope` |
| Authored framing (if ever needed) | `src/domain/cameraTrack.ts:CameraTrack` via `src/studio/cameraCapture.ts:createCameraCapture` — already built |

## Quality Map

| Area | Observation |
| --- | --- |
| `activeTransitionPlan.ts` | Cache correctness rests entirely on endpoint revision identity covering endpoint content. Undocumented as an invariant. Worth a comment naming it, since #137 and this scout both landed on it. |
| `thumbnailCache.ts` | Same class, but here the invariant **is** documented ("State poses are immutable document values. Reference identity therefore gives exact invalidation"). Good precedent; `activeTransitionPlan.ts` should read like this. |
| `structureOperations.ts` | 466 LOC, over the project's 700-line file ceiling only in aggregate but with a dense switch; the `updateState` empty-diff no-op and `createStateFromSelected` non-empty-diff refusal are subtle inverses of each other and neither is commented. |
| `workbenchValidation/assets.ts:readStates` | Rebuilds States field by field rather than validating in place, so any new field is dropped silently rather than rejected loudly. Fine today; a hazard for any future State field. |
| `thumbnail/assetPoster.ts` | Exported, production-unused, test-covered. Forward declaration for the asset browser, not dead code — do not remove. |
| Doctrine | `STUDIO.PROJECT.md` "What a State captures (locked)" and `STUDIO.ANIMATION.md` "one camera lane" are unusually explicit and mutually reinforcing. If option (b) is ever chosen, both must be amended in the same PR, not silently contradicted. |

## Plan

1. Confirm with Stuart that "saved state captures the camera" means **private recall** and not shared authored framing. This is the one question whose answer changes the whole build, and findings 3, 6, and 7 all recommend recall.
2. PR 1 — recall storage and explicit per-card capture, shipping inert.
3. PR 2 — restore on select, plus the card indicator. Live-UX gate before merge.
4. Add a one-line invariant comment to `createActiveTransitionPlanCache` naming endpoint-revision-covers-endpoint-content, so the #137 class is written down where the next person adding a field will read it.
5. Do not touch `Pose`, `StructureStateReferenceV1`, or the `State` domain type. If a later requirement genuinely needs shared framing, it lands as a `CameraTrack` on an animation, which already exists.
