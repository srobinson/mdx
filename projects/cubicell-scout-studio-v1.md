# Scout: Animation Studio v1 reuse map

Read-only scout pass against main `c32bb72`, 2026-08-08. Direction as decided:
single-lane Studio v1 per STUDIO.ANIMATION.md (one structure, Seed from
structure -> PieceSnapshot, one origin Placement, one Cue at t=0, one stage
camera lane, timeline over captured States). Citations are file plus symbol.

## 1. Reuse Map

**Animation asset, as shipped.** `AnimationAsset` (`src/domain/workbench.ts`)
holds `score: StageScore`; `isStageScore` (`src/domain/score.ts`) constrains a
StageScore to at most one `CameraTrack`. The full lifecycle is already plumbed:
`create-animation-asset` / `rename-animation-asset` / `delete-animation-asset`
(`src/domain/workbenchOperations.ts`) run through the authored reducer
(`applyDocumentOperation` case arms in `src/state/actions/authoredReducer.ts`),
have inverses (`src/domain/authoredInverse.ts`), restore operations
(`restore-animation-asset`, `restore-animation-score` in
`src/domain/documentRestoreOperations.ts`), operation validation
(`src/state/authoredOperationValidation/document.ts`), and storage change-set
routing (`src/state/projectStorageChangeSet.ts`). Nothing in `src/panels`,
`src/studios`, or `src/capabilities` dispatches any of them (searches run);
the whole rail is dormant, waiting for a surface.

**Studio mount points.** `studioCatalogData` (`src/studios/catalogData.ts`)
lists only `editor` (route `/`, renderer) and `design-system`. `studioLoaders`
and `resolveStudioDescriptor` (`src/studios/catalog.ts`) resolve a pathname to
a descriptor with editor fallback; `beginStudioLoad` splits studio and shared
renderer chunks (`sharedRendererModuleRoot`); `StudioHost`
(`src/studios/StudioHost.tsx`) mounts the loaded module. Capabilities mount
through `capabilityCatalogData` (`src/capabilities/catalogData.ts`) and
`FeatureSlot` (`src/studios/FeatureSlot.tsx`); the editor wires them in
`src/studios/editor/MotionCapabilitySlots.tsx` and `useMotionCapability.ts`.
Adding a studio is one catalog row, one loader, one module.

**Structure PieceScore and state capture.** `StructureAsset.score: PieceScore`
(`src/domain/workbench.ts`); capture flow is `createStateCapture`,
`createNewStateFromSelected`, `createStateUpdate` (`src/panels/stateCapture.ts`),
each minting an immutable `PoseRevision` via `createPoseRevision`
(`src/domain/project.ts`). `State.pose` embeds the `PoseRevision` inline;
`getStateScene` and `collectStructureCells` (`src/domain/workbench.ts`) read it
through `getPoseRevisionDocument`.

**Shared motion inspector.** `useMotionInspector`
(`src/panels/motion/useMotionInspector.tsx`) is the one routing of motion focus
to State / Transition / Build in panes, consumed by `MotionInspectorSurface`
(`src/capabilities/motion/MotionInspectorSurface.tsx`). Its model,
`usePieceMotionModel` (`src/panels/motion/usePieceMotionModel.ts`), hard-binds
`findAttachedStructureAsset(workbench)` — see Quality Map.

**Transport and evaluation.** The staged-scene seam is
`resolveStageSource` / `sampleStageSource` / `createStagedSceneReader`
(`src/transport/stagedScene.ts`), the only caller of `resolvePieceSample` and
`samplePieceAt` (`src/evaluation/pieceAt.ts`). Morph evaluation:
`sampleSceneTransition` (`src/evaluation/sceneTransition.ts`) and
`sampleSceneMorph` (`src/evaluation/sceneMorph.ts`). Camera:
`compilePieceCameraTrack` (`src/domain/pieceCameraTrack.ts`) compiles State
views, `cameraTrackSampleAt` (`src/evaluation/cameraTrackSampleAt.ts`) is a
pure sampler with a retained-frame path, `useCameraTrackFrame`
(`src/studios/editor/useCameraTrackFrame.ts`) feeds the possession seam
(`src/camera/cameraFrameWriter.ts`). All of it evaluates any piece-shaped
input; none of it knows the Editor beyond `useCameraTrackFrame` and the store
selectors.

**Thumbnails.** `resolveAssetPosterState` and `resolveAssetThumbnailSet`
(`src/thumbnail/assetPoster.ts`) already accept `AnimationAsset` and by design
return null for it ("camera-only Animations reference no State"). Rendering:
`createStateThumbnailCache` (`src/thumbnail/thumbnailCache.ts`),
`createOrthographicThumbnailRenderer` (`src/thumbnail/thumbnailRenderer.ts`).

**Persistence records and codecs.** The animation record exists:
`animationRecordSchemaVersion = 1`, `encodeAnimationRecord` /
`decodeAnimationRecord` (`src/persistence/recordCodecs/animationRecordCodec.ts`)
over `simpleAssetRecordCodec.ts`, validated by `isAnimationAsset`
(`src/state/workbenchValidation.ts`). Pose revisions are first-class records:
`poseRevisionRecordCodec.ts` (`poseRevisionRecordSchemaVersion = 3`), an
IndexedDB `poseRevisions` store inside the promote transaction
(`issuePromoteReads` in `src/persistence/indexedDbCommit.ts`), and a
same-id-same-bytes registry (`extendPoseRevisionRegistry`,
`PoseRevisionConflictError` in `src/persistence/poseRevisionRegistry.ts`).
`workbenchPoseRevisions` (`src/persistence/projectRecordProjection.ts`)
collects the records each projection derives from live states.

**Version bump and reset.** Wire compatibility is per-record `schemaVersion`
constants (`committedRecordSchemaVersion = 3` in
`src/persistence/storageRecordTypes.ts`, plus the codec constants above). A
mismatch fails decode into `RejectedProjectRecord`
(`src/persistence/projectRecordHydration.ts`); `hydrateProjectState`
(`src/state/projectDurabilityHydration.ts`) throws on a failed result and the
app starts fresh. New records bump their constant; no migration branches.

**None found (searches run):** `PieceSnapshot`, `CueTrack`, and a domain
`Placement` do not exist anywhere in `src`. The recursion vocabulary is design
capital only.

## 2. Quality Map

- **The dormant animation rail is a regression trap in reverse.** Ops, codec,
  validation, inverse, and restore for `AnimationAsset` all ship with zero UI
  reachability. v1 must activate this path, not build a parallel one; any
  cleanup pass that "removes dead code" here would delete the v1 foundation.
- **`getCameraTrack` (`src/domain/workbench.ts`) has no caller** outside the
  domain barrel. It is the intended studio read of an animation's own camera
  track; it becomes live in slice 6 below.
- **`useCameraTrackFrame` mislabels its possession identity**: it fills
  `frame.animationAssetId` with the attached *structure's* id. Harmless while
  the Editor is the only camera producer; the moment a real animation camera
  lane exists, two producers share one identity field with different meanings.
- **Editor coupling in the shared inspector.** `usePieceMotionModel` reads
  `findAttachedStructureAsset` and `state.editor.activeStateId` directly, so
  the "one owner" promise of `useMotionInspector` currently means "one owner
  inside the Editor". Studio reuse requires a piece-source seam in the model,
  not a copied inspector. Same pattern in `resolveStageSource`
  (`src/transport/stagedScene.ts`), which resolves only the attached structure.
- **Scene-switch dual semantics** (the known symptom): `MorphSettings.cutAt`
  is read against two clocks in `sampleSceneMorph` (per-cell class-local
  progress for discrete cell fields, global progress for frame, polarity,
  projection), and against a third meaning in cut mode
  (`sampleSceneTransition`). When the Studio re-times snapshot transitions it
  must patch the same `MorphSettings` through `patchTransition`
  (`src/domain/stateTransition.ts`), never introduce a fourth semantic.
- **Docs ahead of code.** STUDIO.PROJECT.md's locked Browser, spaces, and tabs
  have no counterpart: one route, no tab bar, editor fallback in
  `resolveStudioDescriptor`. STUDIO.ANIMATION.md's pool language
  ("`currentPoseRevisionId`") does not match code, where `State.pose` embeds
  the whole revision. ANIMATION.md's status section matches the code.

## 3. The pose-revision pool

Mostly built already. Revisions are immutable, identity-keyed, first-class
records with their own store, codec, and conflict registry. What the pool adds
is retention beyond the current state pose (today a superseded revision
survives only in history diffs and the outbox), snapshot pinning, and
reachability GC. Owners it touches, sized in slices:

- **State shape** (`State.pose` in `src/domain/workbench.ts`, minting in
  `src/panels/stateCapture.ts`, reads via `getPoseRevisionDocument`): moving to
  id-plus-pool is a wire change and a bump. One slice.
- **Snapshot pinning**: new `PieceSnapshot` type holding snapshot states pinned
  to revision ids plus a copied `PieceScore`; joins `AnimationAsset` and its
  codec. One slice, depends on the pool.
- **GC reachability**: `workbenchPoseRevisions`
  (`src/persistence/projectRecordProjection.ts`) currently derives records from
  live states each projection; a pool inverts this into reachability from
  states, snapshots, history, and outbox. One slice, can trail.
- **Project record set and quota**: `poseRevisions` store and the atomic
  promote transaction (`src/persistence/indexedDbCommit.ts`, fault kind
  `"quota"` aborts whole) already give the all-or-nothing write the spec
  requires. No new mechanism, only membership.

Total: three slices, the third deferrable past v1 (a single user cannot strand
meaningful garbage before GC lands).

## 4. Plan

**Decisions for the owner (recommended defaults):**

- **D1 — snapshot fidelity.** Pin snapshots through the pose-revision pool
  (spec-true) rather than inline pose copies. Recommended: yes; the pool is
  two slices and the spec explicitly forbids inline copies.
- **D2 — how an animation opens.** No Browser exists. Recommended: a second
  catalog route (`/animation`) plus a minimal open/create affordance in the
  studio shell; defer the full Browser.
- **D3 — bump granularity.** Each shipping slice bumps its own record
  constant and resets (no-migrations rule). Recommended: per-slice bumps,
  no batching.
- **D4 — stage camera v1.** The animation's own `CameraTrack` in its
  StageScore, authored by capture-current-view (the `CameraCaptureControl`
  precedent), sampled by `cameraTrackSampleAt`. Recommended over reusing the
  compiled piece track: the piece track is Editor preview; the stage lane is
  the animation's contract.
- **D5 — transition overrides in v1.** The snapshot owns a full copied
  PieceScore, so studio re-timing is `patchTransition` against snapshot state.
  Recommended: include; it is reuse, not new surface.

**Ordered v1 slices** (smallest first, each independently shippable):

1. **Pool retention.** `State.pose` becomes a revision id into a project
   `poseRevisions` pool; capture path unchanged in shape. Bump. Gate: capture,
   update, reload round-trips exactly; quota abort leaves prior baseline.
2. **PieceSnapshot + Seed from structure.** Domain type, one authored
   operation copying the PieceScore and pinning revision ids, joins
   `animationRecordCodec`. Bump. Gate: seeded animation reloads and evaluates
   identically to its source structure; source edit does not move the snapshot.
3. **Studio mount.** Catalog row, loader, `AnimationStudio` shell on the
   shared renderer; activates `create-animation-asset`. Gate: open, create,
   rename, delete an animation from the running app.
4. **Snapshot playback.** A piece-source seam in `resolveStageSource` so the
   studio's staged scene evaluates the snapshot via `resolvePieceSample`;
   transport reuse as-is. Gate: play/scrub parity with the Editor on the same
   piece, measured against `samplePieceAt` output.
5. **Inspector seam.** Extract the asset source from `usePieceMotionModel`;
   `useMotionInspector` serves the studio right rail unchanged. Gate: the
   Editor rail renders byte-identical DOM before and after the refactor.
6. **Stage camera lane.** Author `CameraTrack` on the animation's StageScore;
   a studio counterpart of `useCameraTrackFrame` sampling via `getCameraTrack`;
   fix the possession identity field. Gate: captured keyframes play through
   the possession seam; Editor piece-camera behavior untouched.
7. **Poster and library polish.** Extend `resolveAssetPosterState` to resolve
   an animation's poster through its snapshot's first state. Gate: animation
   thumbnails render in the open/create affordance.

Slices 1 and 2 are the campaign-critical path; 3 through 6 are the studio
itself; 7 is finish. First consumer (the campaign track one visual) is
reachable after slice 6.
