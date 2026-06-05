# Spec: Animation Studio v1

Implementation spec against main `c32bb72`, 2026-08-08. Authority for reuse
bindings: `cubicell-scout-studio-v1.md`. Design contract: STUDIO.ANIMATION.md
(2026-07-14/15 sections). Citations are file plus symbol.

**Bound decisions (closed, do not reopen):**

- **D1** Snapshots pin through the pose-revision pool; no inline pose copies.
- **D2** Second catalog route `/animation` with a minimal open/create
  affordance; the full Browser is deferred.
- **D3** Per-slice schema bumps and reset; no migrations, no batching.
- **D4** The stage camera lane is the animation's own `CameraTrack` authored
  by capture-current-view; the compiled piece track stays Editor preview.
- **D5** Studio re-timing is `patchTransition` (`src/domain/stateTransition.ts`)
  against the snapshot's copied `PieceScore`; no fourth `cutAt` semantic.

**Scope pins:** single lane, one snapshot, one implicit origin Placement, one
implicit Cue at t=0. No recursion, no multilane, no placement authoring, no
`CueTrack`.

**Implicit-cue representation.** The snapshot's Placement is persisted as a
record with a durable id (`originPlacement: { id, snapshotId }` on
`AnimationAsset`); the Cue is a derivation rule, not a record: the placement
implies `{ startMs: 0, offsetMs: 0, timeScale: 1, loop: false }` at sample
time. A future `CueTrack` row references `placementId`, so the durable
placement id is the adoption seam. Tradeoff, accepted: introducing `CueTrack`
extends the `StageScore` track union and bumps the animation record anyway;
under the no-migrations posture a wire break is a version constant and a
reset, so persisting a cue record today buys nothing. The placement id is the
cheap future-proofing; the cue record is not.

**Gates, all slices.** Inner loop: `pnpm check` and `pnpm test`. Merge
authority: `pnpm test:all` and `pnpm check:budget`. Every new test lands with
a controlled-red proof: break the guarded invariant deliberately, show the
test fail, restore, show it pass. Test counts are not reported; gates are
pass/fail plus wall time.

## Slice 1 — Pool retention

**Goal.** `State.pose` becomes a revision id into a project-scoped
pose-revision pool; revisions outlive the states that minted them.

**Bindings.** `State.pose`, `getStateScene`, `collectStructureCells`
(`src/domain/workbench.ts`); `PoseRevision`, `createPoseRevision`,
`getPoseRevisionDocument` (`src/domain/project.ts`); minting in
`createStateCapture`, `createNewStateFromSelected`, `createStateUpdate`
(`src/panels/stateCapture.ts`); `workbenchPoseRevisions`
(`src/persistence/projectRecordProjection.ts`); `poseRevisions` store inside
`issuePromoteReads` (`src/persistence/indexedDbCommit.ts`);
`extendPoseRevisionRegistry`, `PoseRevisionConflictError`
(`src/persistence/poseRevisionRegistry.ts`).

**Deliverables.** `State.pose: PoseRevision` becomes
`State.poseRevisionId: string`; a pool keyed by revision id joins project
state; every read path resolves through the pool (one lookup helper replacing
inline access, `getPoseRevisionDocument` adapted to it); the capture path
still mints via `createPoseRevision` and now also inserts into the pool;
`workbenchPoseRevisions` projects the pool instead of deriving from live
states. Superseded revisions are retained (no GC in v1, see Non-Goals).

**Wire.** `structureRecordSchemaVersion` 2 to 3
(`src/persistence/recordCodecs/structureRecordCodec.ts`); bump alongside it
every codec whose decoded payload transitively validates `State.pose` shape,
traced from `isState` (`src/state/workbenchValidation.ts`): candidates are
`committedRecordSchemaVersion`, `draftRecordSchemaVersion`,
`localHistoryRecordSchemaVersion`, `outboxCommitRecordSchemaVersion`; confirm
each by tracing at implementation time. One reset covers all (D3).

**Tests.** Capture, update, reload round-trips byte-exact through the pool
(red proof: skip pool insertion, hydration must fail). A superseded revision
remains resolvable after the state repoints (red proof: delete on repoint).
Pool membership in the atomic write: the pool's records ride inside the
promote transaction, so a quota abort leaves the prior baseline intact (red
proof: exclude the pool store from the promote transaction, the gate must
fail; the quota-abort invariant itself is pre-existing and not re-proven).

**Done:** a state's geometry is a pool reference, superseded revisions
survive reload, and quota failure cannot half-write the pool.

## Slice 2 — PieceSnapshot and Seed from structure

**Goal.** An animation owns a detached copy of a structure's piece: snapshot
states pinned to pool revision ids plus a copied `PieceScore`.

**Bindings.** `AnimationAsset`, `mapAnimationAsset`
(`src/domain/workbench.ts`); `PieceScore`, `findStateTransitionTrack`
(`src/domain/score.ts`); the authored rail to extend:
`src/domain/workbenchOperations.ts`, reducer arms in
`src/state/actions/authoredReducer.ts`, inverses in
`src/domain/authoredInverse.ts`, restore in
`src/domain/documentRestoreOperations.ts`, validation in
`src/state/authoredOperationValidation/document.ts`, change-set routing in
`src/state/projectStorageChangeSet.ts`; codec
`src/persistence/recordCodecs/animationRecordCodec.ts` with
`isAnimationAsset` (`src/state/workbenchValidation.ts`).

**Deliverables.** Domain `PieceSnapshot` (snapshot-local states pinned to
`poseRevisionId`, copied `PieceScore` addressing snapshot-local state ids,
source references for provenance); `AnimationAsset` gains
`pieceSnapshots: PieceSnapshot[]` (exactly one in v1) and `originPlacement`
per the implicit-cue representation above; one authored operation
`seed-animation-from-structure` copying the source `PieceScore`, pinning
current revision ids, and creating the origin placement, wired through every
rail station listed. Snapshot-local ids never reference the source namespace
(the STUDIO.ANIMATION.md namespace boundary).

**Wire.** `animationRecordSchemaVersion` 1 to 2; `isAnimationAsset` validates
the new shape. New operation kinds are additive and need no operation-record
bump.

**Tests.** A seeded animation reloads and its snapshot evaluates identically
to the source structure at seed time (red proof: pin a wrong revision id).
Editing the source structure after seeding does not move the snapshot (red
proof: resolve through the source state instead of the pin). Inverse and
restore round-trip the seed operation with a deletion-shaped red: drop the
seed operation's inverse field and the suite must fail.

**Done:** seeding copies the piece into the animation, pinned to the pool,
and source edits can no longer reach it.

## Slice 3 — Studio mount

**Goal.** The Animation Studio exists as a routed surface and the dormant
asset lifecycle becomes reachable.

**Bindings.** `studioCatalogData`, `sharedRendererModuleRoot`
(`src/studios/catalogData.ts`); `studioLoaders`, `resolveStudioDescriptor`,
`beginStudioLoad` (`src/studios/catalog.ts`); `StudioHost`
(`src/studios/StudioHost.tsx`); `capabilityCatalogData`
(`src/capabilities/catalogData.ts`); `FeatureSlot`
(`src/studios/FeatureSlot.tsx`); lifecycle ops `create-animation-asset`,
`rename-animation-asset`, `delete-animation-asset`
(`src/domain/workbenchOperations.ts`); roster read via
`getProjectAssetRoster` (`src/domain/workbench.ts`).

**Deliverables.** One catalog row (`animation`, route `/animation`, renderer
true), one loader entry, one `AnimationStudio` module on the shared renderer;
a minimal open/create affordance listing the project's animations and
dispatching create (which triggers Seed from structure when a structure is
chosen), rename, delete. No Browser, no tabs (D2).

**Wire.** None.

**Tests.** `resolveStudioDescriptor("/animation")` resolves the new
descriptor and unknown routes still fall back to the editor (red proof:
remove the catalog row). Create, rename, delete fire from the studio
affordance itself, asserted at the dispatch boundary rather than re-testing
the shipped reducer arms (red proof: the affordance absent, the test must
fail).

**Done:** the dormant animation rail has a live surface at `/animation`.

## Slice 4 — Snapshot playback

**Goal.** The studio's staged scene evaluates the snapshot through the
existing transport, not a parallel evaluator.

**Bindings.** `resolveStageSource`, `sampleStageSource`,
`createStagedSceneReader`, `useStagedScene` (`src/transport/stagedScene.ts`);
`AttachedPieceSource`, `resolveAttachedPieceSource`, `resolvePieceSample`,
`samplePieceAt` (`src/evaluation/pieceAt.ts`); `sampleSceneTransition`
(`src/evaluation/sceneTransition.ts`), `sampleSceneMorph`
(`src/evaluation/sceneMorph.ts`).

**Deliverables.** The seam cuts deeper than the resolver. At `c32bb72`,
`AttachedPieceSource` is typed against a `StructureAsset` and
`resolvePieceSample` resolves keyframe endpoints through `findState` and
`getStateScene` against the live workbench, so snapshot-local state ids would
miss and playback would silently degrade to the authored working scene. The
slice therefore delivers: a snapshot variant of `AttachedPieceSource`;
`sampleStageSource` handling that variant; state resolution in
`resolvePieceSample` parameterized over the piece's own state set (snapshot
states for the studio, workbench states for the Editor); and the
`createStagedSceneReader` / `useStagedScene` binding of editor `morphScrub`
and transport acknowledged in scope, since the studio reader supplies its own
session sources. Playback maps stage time through the implicit cue (identity
in v1).

**Wire.** None.

**Tests.** Scrub parity: for the same piece content, the studio path and the
Editor path produce identical `samplePieceAt` output across a sampled sweep
of times (red proof: perturb the snapshot's score copy). A snapshot whose
source state has diverged stages the snapshot pose, not the working scene
(red proof: resolve endpoints through the live workbench). The
comparison-scrub and authored fallbacks in `resolveStageSource`, and the
Editor's `morphScrub` binding through the reader, are unchanged for the
Editor and covered by the parity gate.

**Done:** the snapshot plays and scrubs through the same transport seam the
Editor uses, with proven sample parity.

## Slice 5 — Inspector seam and re-timing

**Goal.** One motion inspector serves both studios; the studio edition edits
the snapshot's own score.

**Bindings.** `useMotionInspector` (`src/panels/motion/useMotionInspector.tsx`);
`MotionInspectorSurface` (`src/capabilities/motion/MotionInspectorSurface.tsx`);
`usePieceMotionModel` (`src/panels/motion/usePieceMotionModel.ts`);
`patchTransition` (`src/domain/stateTransition.ts`); `MorphSettings` clocks in
`sampleSceneMorph` (`src/evaluation/sceneMorph.ts`).

**Deliverables.** Extract the asset source from `usePieceMotionModel`
(currently `findAttachedStructureAsset` plus `state.editor.activeStateId`)
behind a piece-source parameter mirroring the slice 4 seam; the Editor keeps
its bindings, the studio binds the snapshot and its own focus state. Studio
re-timing dispatches a snapshot-scoped transition-patch operation (the
snapshot namespace twin of the structure transition edit) that applies
`patchTransition` to the copied `PieceScore` (D5); it patches existing
`MorphSettings` fields only, never a new `cutAt` reading.

**Wire.** None; new operation kinds are additive.

**Tests.** The Editor right rail renders byte-identical DOM before and after
the extraction, asserted on serialized render output (red proof: reorder one
inspector row). A studio re-time patches the snapshot score and leaves the
source structure's score untouched (red proof: route the patch to the source
asset id).

**Done:** the shared inspector is genuinely shared, and studio re-timing
lands only on the snapshot's copy.

## Slice 6 — Stage camera lane

**Goal.** The animation's own camera: capture-current-view authors keyframes
onto its `StageScore`, and playback possesses the camera through them.

**Bindings.** `getCameraTrack` (`src/domain/workbench.ts`, currently
caller-less); `isStageScore`, `findCameraTrack` (`src/domain/score.ts`);
`CameraCaptureControl` precedent (Motion dock); `cameraTrackSampleAt`
(`src/evaluation/cameraTrackSampleAt.ts`); `useCameraTrackFrame` and
`loadCameraTrackSampler` (`src/studios/editor/useCameraTrackFrame.ts`);
`cameraFrameWriter` (`src/camera/cameraFrameWriter.ts`);
`compilePieceCameraTrack` (`src/domain/pieceCameraTrack.ts`) stays
Editor-only (D4).

**Deliverables.** An authored operation appending a captured view keyframe to
the animation's `CameraTrack` (creating the track on first capture, keeping
`isStageScore` true); a studio counterpart of `useCameraTrackFrame` reading
via `getCameraTrack` and sampling with `cameraTrackSampleAt` into the
possession seam; the possession identity fix: the frame field currently named
`animationAssetId` is renamed to the identity it actually carries, and each
producer fills its own (Editor writes the attached structure id, studio
writes the animation id), so two producers never collide in one mislabeled
field. The rename reaches the existing camera suites:
`tests/cameraTrackPlayback.test.tsx` and `tests/cameraTrackAuthority.test.ts`
assert the old field name, so updating their assertions to the renamed field
is a deliverable of this slice, not collateral.

**Wire.** None: `CameraTrack` keyframes are already valid `StageScore` data
under `isAnimationAsset`; the identity fix is runtime-only.

**Tests.** Captured keyframes sample through the possession seam in stage
order (red proof: drop the retained-frame path). Editor piece-camera behavior
is preserved: the updated camera suites pass with their assertions rebound to
the renamed field, asserting the same possession behavior, and the producer
identity assertion distinguishes the two producers (red proof: swap the
ids).

**Done:** the stage camera is the animation's own authored lane, sampled by
the shipped sampler, with producer identity made honest.

## Slice 7 — Poster and library polish

**Goal.** Animations are recognizable in the open/create affordance.

**Bindings.** `resolveAssetPosterState`, `resolveAssetThumbnailSet`
(`src/thumbnail/assetPoster.ts`); `createStateThumbnailCache`
(`src/thumbnail/thumbnailCache.ts`); `createOrthographicThumbnailRenderer`
(`src/thumbnail/thumbnailRenderer.ts`).

**Deliverables.** `resolveAssetPosterState` resolves an animation's poster
through its snapshot's first state (derived, not persisted; the null-return
comment for camera-only animations is superseded); the slice 3 affordance
renders the thumbnails.

**Wire.** None.

**Tests.** An animation with a snapshot resolves a poster state; one without
resolves null (red proof: resolve through the source structure's states).

**Done:** the animation library shows what each animation is.

## Non-Goals (deferred recursion vocabulary)

`CueTrack` and any cue record; multilane and per-asset lanes; placement
authoring, stage-lattice transforms, and placement animation; nested
`Placement` / `GridCell.content` piece recursion and instance paths; Canon
(one snapshot placed twice) and Fork / Make independent; the staleness
three-way update (geometry drift, motion drift, roster delta); camera target
binding to a placement; the STUDIO.PROJECT.md Browser, spaces, and tabs;
pose-revision GC (reachability from states, snapshots, history, outbox), safe
to trail v1 for a single user.

## Risk register

- **Dormant-rail deletion trap.** The `AnimationAsset` rail ships with zero
  UI reachability until slice 3; any dead-code cleanup before then deletes
  the v1 foundation. Mitigation: slices 2 and 3 land close together, and the
  rail is named load-bearing in the scout report.
- **Camera identity collision.** `useCameraTrackFrame` fills
  `frame.animationAssetId` with a structure id today; slice 6 must land the
  rename with the second producer, never after it.
- **Fourth `cutAt` semantic.** `MorphSettings.cutAt` already reads against
  three clocks; slice 5 patches existing fields through `patchTransition`
  only. Any new timing meaning is a spec change, not a slice detail.
- **Pool growth without GC.** Retention with no GC grows the `poseRevisions`
  store monotonically. Acceptable for a single user in v1; GC is the first
  post-v1 slice if quota pressure appears (`"quota"` fault surfacing is the
  signal).
- **Inspector regression by refactor.** Slice 5's byte-identical DOM gate is
  the guard; the extraction ships only with its controlled-red proof.
- **Docs drift.** After slice 1, STUDIO.ANIMATION.md's
  `currentPoseRevisionId` language matches code; until then the doc is ahead
  of the wire. Do not "fix" the doc backwards in the interim.

## Campaign linkage

Slices 1 and 2 are campaign-critical: the pool and the snapshot are what let
the campaign track one visual pin geometry that survives further editing.
Slices 3 through 6 are the studio itself; the first consumer, the full music
visual of campaign track one, is reachable after slice 6. Slice 7 is finish.
