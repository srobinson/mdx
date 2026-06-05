# Cubicell Durable Core Architecture Audit

Baseline verified: `main` at `71098b4ee21117d8431e71288edef42f61908854`, with a clean checkout before the audit. Scope was read only across `src/domain/`, `src/persistence/`, `src/evaluation/`, the named product documents, and the storage contract.

## Verdict

**RESTRUCTURE**

The appropriate scope is a boundary restructure that retains the durable machinery. Several ownership boundaries should move before hosted persistence, recursive composition, and deterministic export add more consumers.

The three strongest pieces of evidence are:

1. The live aggregate model stops at a flat Structure plus a camera only Animation. The load bearing target is recursive composition through Piece, Placement, and Cue. That target requires project scoped pose revisions, snapshot owned pieces, local cell identity plus instance paths, recursive time and transform evaluation, semantic GeometrySource, and immutable export closure. Evidence: `src/domain/workbench.ts:AnimationAsset`, `src/domain/workbench.ts:Library`, `src/domain/scene.ts:CubicellScene`, `src/domain/score.ts:StageTrack`, `ARCHITECTURE.md:Scene Model Direction`, `CUBICELL.md:Grid First Product Model`, `STUDIO.ANIMATION.md:Piece motion and reuse`, `STUDIO.ANIMATION.md:Recursive composition model`, `TYPOGRAPHY.md:Proposed authored model`, and `PROJECT.EXPORT.md:Common job contract`.
2. Revision identity can diverge from revision content in memory. Persistence detects the conflict later, while caches already trust revision identity or object identity. This has produced two defect opportunities and is systemic. Evidence: `src/domain/project.ts:PoseRevision`, `src/domain/project.ts:createPoseRevision`, `src/domain/project.ts:getPoseRevisionDocument`, `src/transport/activeTransitionPlan.ts:createActiveTransitionPlanCache`, `src/thumbnail/thumbnailCache.ts:createStateThumbnailCache`, and `src/persistence/poseRevisionRegistry.ts:extendPoseRevisionRegistry`.
3. The expensive foundations are healthy and reusable. Atomic promotion, semantic operations, revision checks, adapter boundaries, bounded local history, and pure evaluation are sound seams. Evidence: `src/persistence/storagePort.ts:ProjectStoragePort`, `src/persistence/promoteContract.ts:createPromotePlan`, `src/persistence/indexedDbCommit.ts:issuePromoteWrites`, `src/domain/authoredOperations.ts:AuthoredOperation`, `src/evaluation/pieceAt.ts:resolvePieceSample`, and `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`.

The durable core survives recursive composition as reusable machinery. Its aggregate, identity, evaluation, and capacity boundaries must be reshaped for recursion before the feature lands.

Recommended direction: keep the persistence transaction core, operation reducers, cube geometry domain, camera track, PieceScore, and pure local evaluation. Replace the runtime aggregate graph and revision ownership in place, add recursive evaluation above the local Piece evaluator, then build hosted sync and export on the revised model.

## Walls

No WALL findings.

Two plausible wall candidates have concrete incremental paths:

1. Durable migrations can be added by preserving old record unions, dispatching decode by version, transforming complete Project closures, committing the transformed closure atomically, then advancing the encoder version. The current database upgrader must first stop recreating every store. No existing boundary prevents that sequence.
2. Recursive composition can be reached by introducing project scoped pose revision references, local cell identity plus instance paths, then PieceSnapshot, Placement, and CueTrack, then generalizing the pure evaluator from one Piece to a recursive closure. The current pure reducer and evaluator seams survive that sequence.

Both paths are substantial. Neither reaches a structural dead end.

## Taxes

### TAX: Recursive composition requires an aggregate and address reshape

`src/domain/workbench.ts:Library` stores project wide arrays of States, Structures, and Animations. A Structure owns State identifiers while each State carries its owning asset identifier and an embedded PoseRevision. `src/domain/workbench.ts:AnimationAsset` owns only a `StageScore`, and `src/domain/score.ts:StageTrack` currently aliases `CameraTrack`. `src/domain/scene.ts:CubicellScene` owns one flat cell array and one grid.

The target is larger:

- Structures own States and PieceScore.
- Animations own PieceSnapshots, Placements, CueTrack, and CameraTrack.
- Pose revisions are project scoped immutable records shared by reference.
- Recursive grids need Piece, GridCell content, Placement, and instance paths.
- Export needs a dependency complete immutable source closure.

The addendum's coordinate derived identity premise does not match the audited head. At `71098b4`, `src/domain/lattice.ts:shiftCells` changes coordinates while retaining `CubeCell.id`, and `src/domain/score.ts:repairScore` drops missing identifiers and appends new ones without a rename map. `src/domain/scene.ts:createGridResizePlan` creates durable identifiers independently of coordinates. The earlier coordinate rename model has already been removed.

This makes the local identity change a normal refactor. A cube identifier can remain local to one Piece. Recursion adds a second address:

```ts
type InstancePath = {
  placementIds: readonly string[];
  localCellId: string;
};
```

Scores continue to address local cell identifiers. Reuse may evaluate the same local identifier under many Placement paths. Selection, hit results, rendered instances, world Moment values, and history references that cross Piece scope must use the instance path.

Current evaluation confirms the boundary. `src/evaluation/scoreAt.ts:Moment` stores presence and part colors in maps keyed only by cube identifier. `src/evaluation/scoreAt.ts:scoreAt` evaluates one flat scene. Recursion needs two layers:

1. A local Piece evaluator that retains the current `scoreAt` and scene morph behavior.
2. A composition evaluator that maps parent time through Cue, evaluates the child Piece, composes the Placement transform, and emits instance addressed results.

The conceptual composition is:

```text
childTime = (parentTime - cue.startMs) * cue.timeScale + cue.offsetMs
localMoment = evaluatePiece(pieceId, childTime)
placedMoment = compose(instancePath, placementTransform, localMoment)
```

Flatten only at the renderer or immutable export snapshot boundary. Keeping a local Moment avoids rewriting score and morph math around global strings.

The persistence asset split is reusable, but the current documents do not absorb recursion unchanged:

- `src/persistence/recordCodecs/structureRecordCodec.ts:StructureRecordV1` stores State references plus Structure fields.
- `src/persistence/recordCodecs/animationRecordCodec.ts:AnimationRecordV1` stores the current camera only AnimationAsset.
- `src/persistence/recordCodecs/poseRevisionRecordCodec.ts:PoseRevisionRecordV1` binds each revision to one asset and State.
- PieceSnapshot, Placement, CueTrack, snapshot local States, geometry drift, motion drift, and roster drift do not exist in `src`.
- `src/domain/stateTransition.ts:repairStateTransitionTrack` repairs orphan keyframes and count. `src/domain/stateTransition.ts:repairStructureStateTransitionTrack` rebuilds a Structure sequence from current State order. Neither performs the target three way snapshot update.

The unmerged `feat/typography-domain` branch provides useful feasibility evidence. `feat/typography-domain:src/domain/typography.ts:GeometrySource` models literal or semantic text geometry, and `feat/typography-domain:src/domain/typography.ts:createTextCellId` derives stable generated local identity from source, text unit, glyph, and local sample. Its merge base is `c6a2c2e`, before the current durability system, so it proves the domain direction rather than persistence integration.

The incremental path is:

1. Define PieceId, PlacementId, local cell identity, and InstancePath. Adapt the current flat scene as one root Piece with one implicit root Placement.
2. Add `GeometrySource` to Pose and retain literal cells as the current source kind.
3. Make State carry `poseRevisionId` and make the project revision pool authoritative.
4. Move State ownership into the Structure aggregate or a Structure keyed normalized partition.
5. Add PieceSnapshot and Placement to AnimationAsset.
6. Add CueTrack beside CameraTrack in StageScore.
7. Keep local Piece evaluation unchanged, then add recursive Cue time mapping and Placement transform composition above it.
8. Add a three way snapshot refresh operation that treats geometry, motion, and roster drift independently.
9. Version Structure, Animation, pose revision, operation, history, and outbox records together. Reset during pre release.

The path remains viable because operations, score evaluation, and storage already separate Project and asset revisions. The recurring cost appears if the move waits. Every new export source, hosted record, history entry, operation validator, and Studio feature would first bind to the flat graph and later require conversion.

Size estimate: six to ten focused pull requests now. Waiting until hosted persistence and export exist adds SQL, journal replay, export job compatibility, and user data migration to the same move.

Evidence: `src/domain/lattice.ts:shiftCells`, `src/domain/score.ts:repairScore`, `src/domain/workbench.ts:State`, `src/domain/workbench.ts:StructureAsset`, `src/domain/workbench.ts:AnimationAsset`, `src/domain/workbench.ts:Library`, `src/domain/scene.ts:CubicellScene`, `src/domain/score.ts:PieceScore`, `src/domain/score.ts:StageScore`, `src/evaluation/scoreAt.ts:Moment`, `src/evaluation/scoreAt.ts:scoreAt`, `src/persistence/recordCodecs/structureRecordCodec.ts:StructureRecordV1`, `src/persistence/recordCodecs/animationRecordCodec.ts:AnimationRecordV1`, `STUDIO.PROJECT.md:Terminology`, `STUDIO.ANIMATION.md:Piece motion and reuse`, `STUDIO.ANIMATION.md:Recursive composition model`, and `TYPOGRAPHY.md:Identity`.

### TAX: Recursive scale has no capacity contract

STORAGE.md defines a durable and performance gate for one active 4,500 cell asset. The target documents define recursive Pieces and repeated Placements without a stated limit for:

- Recursion depth.
- Child Pieces per Piece.
- Placements per Stage.
- Active Cues per frame.
- Assets per Project.
- States per Structure.
- Evaluated cells per semantic GeometrySource.
- Total visible instances after Placement expansion.

Reference reuse keeps authored storage compact. Evaluation and rendering still multiply. With `c` leaf cells, branching factor `b`, and depth `d`, visible instances can reach `c * b^d`. A 100 cell Piece placed four times per level reaches 25,600 instances at depth four and 409,600 at depth six. One 4,500 cell Piece placed ten times produces 45,000 rendered instances while storing one source.

The model also needs cycle rules. A Piece graph that can reference itself directly or indirectly makes evaluation nonterminating unless the domain rejects cycles or applies an explicit recursion boundary.

A capacity contract is required before recursive documents become durable:

1. Require an acyclic Piece and Placement graph, with cycle validation at operation and hydration boundaries.
2. Declare a maximum authored depth even when the graph is acyclic.
3. Gate total evaluated instances and active Cues per frame.
4. Keep GeometrySource evaluation cached by immutable source identity.
5. Share immutable Piece and pose data across Placements while keeping instance transforms separate.
6. Record expanded instance count, traversal depth, source evaluation bytes, frame cost, and export memory.
7. Add production gates above the current 4,500 cell single Piece baseline.

Without these limits, schema evolution can preserve bytes correctly while loading a document the evaluator or renderer cannot safely expand.

Evidence: `STORAGE.md:Performance budgets`, `STORAGE.md:Decision`, `STUDIO.ANIMATION.md:Recursive composition model`, `TYPOGRAPHY.md:Performance`, `TYPOGRAPHY.md:Open decisions`, `src/evaluation/scoreAt.ts:Moment`, and `src/domain/scene.ts:CubicellScene`.

### TAX: Pose revision identity does not structurally cover content

`src/domain/project.ts:PoseRevision` is a Pose intersected with `assetId`, `id`, and `stateId`. `src/domain/project.ts:createPoseRevision` accepts an existing identifier and arbitrary Pose, then spreads both into a new value. The type and constructor therefore allow two values with one identifier and different bytes.

`src/persistence/poseRevisionRegistry.ts:extendPoseRevisionRegistry` rejects that conflict during projection or hydration. That check protects durable state. It occurs after runtime consumers may already have cached work.

The consumers make two valid assumptions that the model does not enforce:

- `src/transport/activeTransitionPlan.ts:createActiveTransitionPlanCache` reuses topology when endpoint revision identities match.
- `src/thumbnail/thumbnailCache.ts:createStateThumbnailCache` uses Pose reference identity because its contract says Pose values are immutable.

The repeated defect class is systemic. The cache patterns are appropriate only after revision identity and content immutability are enforced by construction.

The structurally safe shape is:

```ts
type PoseRevisionId = string;

type PoseRevisionRecord = {
  id: PoseRevisionId;
  document: Readonly<Pose>;
  contentHash: string;
};

type State = {
  id: string;
  name: string;
  poseRevisionId: PoseRevisionId;
};
```

One revision registry owns records. A mint function always allocates a fresh identifier. The decode boundary may accept an identifier plus bytes, but must intern and verify it before publishing the record. No general runtime constructor should accept an existing identifier with new content. Caches can then use revision identifier, content hash, or interned document reference according to their lifetime.

Moving this now touches State, Structure operations, history, codecs, hydration, and piece evaluation. Moving it after PieceSnapshot and export would also touch every snapshot and export closure. This is the highest priority restructure.

Evidence: `src/domain/project.ts:PoseRevision`, `src/domain/project.ts:createPoseRevision`, `src/domain/project.ts:getPoseRevisionDocument`, `src/domain/structureOperations.ts:StructureDocumentOperation`, `src/persistence/recordCodecs/poseRevisionRecordCodec.ts:PoseRevisionRecordV1`, `src/persistence/poseRevisionRegistry.ts:extendPoseRevisionRegistry`, `src/evaluation/pieceAt.ts:resolvePieceSample`, `src/transport/activeTransitionPlan.ts:createActiveTransitionPlanCache`, and `src/thumbnail/thumbnailCache.ts:createStateThumbnailCache`.

### TAX: The first durable schema migration has no safe landing path

The ten persistence schema constants are all version 1. Each codec accepts exactly one version through `src/persistence/recordCodecs/result.ts:isRecordEnvelope`. Stored project and asset byte types also pin to one `committedRecordSchemaVersion`.

The IndexedDB database is already version 4, but `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema` deletes every object store and recreates it. `src/persistence/indexedDbProjectStorage.ts:openDatabase` runs that function for every database upgrade.

This is correct under the current pre release reset rule. The first requirement to preserve user data turns it into a migration tax.

The concrete path is:

1. Replace the destructive upgrade callback with an `oldVersion` switch before any persistent user data exists.
2. Retain versioned wire unions such as `ProjectRecordV1 | ProjectRecordV2`.
3. Decode old records into a migration input without admitting them directly to current domain state.
4. Keep IndexedDB version change work structural: create stores and indexes without decoding large documents.
5. Load and validate the complete Project closure, including referenced pose revisions, history, drafts, outbox, and user state, through the existing worker and segmented byte path.
6. Transform authored references rather than expanding recursive or semantic geometry.
7. Write prepared current records to shadow stores or a new generation, then atomically publish the generation marker.
8. Preserve the old generation until the new closure rehydrates successfully.
9. Add fixtures for every supported starting version and prove interrupted upgrade recovery.

Nothing blocks this extension. The first migration has broad reach because version dispatch and closure migration are absent. Later migrations become normal once that framework exists.

The 4,500 cell durable baseline makes main thread record transformation unacceptable. Recursive Placement references should remain compact during migration. GeometrySource evaluation belongs after hydration and must not be materialized into every migrated record.

Size estimate: one foundation pull request plus one migration pull request for the first real shape change. Each later record version should be a focused codec plus migration fixture.

Evidence: `src/persistence/recordCodecs/result.ts:isRecordEnvelope`, `src/persistence/storageRecordTypes.ts:committedRecordSchemaVersion`, `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema`, `src/persistence/indexedDbProjectStorage.ts:openDatabase`, `src/persistence/projectRecordHydrationAsync.ts:hydrateProjectRecordsAsync`, `src/persistence/storageRecordPreparationAsync.ts:prepareStorageCommitAsync`, `STORAGE.md:Performance budgets`, and every constant exported from `src/persistence/recordCodecs/`.

### TAX: The collaboration route is real, with unresolved second writer semantics

The preserved route has substance:

- Authored operations carry actor, client, commit, target, observed revision, and semantic body.
- Sequence edits use durable identifiers and relative anchors.
- The storage port exposes outbox loading, committed installation, and atomic promotion.
- Stale local branches replay through the same reducer.
- Project and asset revisions provide optimistic concurrency.
- Presence remains outside authored state.

A second writer would not corrupt storage silently. Revision mismatch stops its stale commit. The client can fetch the current head and replay its pending operations.

Three concrete behaviors remain unresolved before that becomes collaboration:

1. Coarse inverse operations such as `restore-structure-sequence`, `restore-structure-asset`, and `restore-animation-score` replace aggregate state captured before another writer's edits. Replaying one at the current revision can erase unrelated remote work.
2. Same field edits can both replay successfully, producing server ordered last arrival semantics without a user level conflict decision. Rename, camera segment patch, and transition patch are examples.
3. The trusted server reducer, hosted journal, acknowledgement worker, and remote conflict surface described by STORAGE.md do not exist.

The route therefore supports optimistic sequential writers after conflict policy is added. Live coauthoring still needs finer inverse intent, operation preconditions, or explicit conflict resolution for aggregate replacement operations. A CRDT is not required by the current evidence.

The incremental path is:

1. Add the hosted commit function and acknowledgement worker.
2. Delete acknowledged outbox entries.
3. Reconstruct remote heads from checkpoint plus journal.
4. Add operation specific replay preconditions.
5. Replace coarse collaborative inverse bodies with current revision semantic inverses.
6. Surface rejected or ambiguous replay.
7. Add Broadcast delivery only after durable catch up is complete.

Evidence: `src/domain/authoredOperations.ts:AuthoredOperation`, `src/domain/structureSequenceOperations.ts:KeyframeAnchor`, `src/domain/documentRestoreOperations.ts:DocumentRestoreOperation`, `src/domain/authoredInverse.ts:deriveInverseBody`, `src/persistence/storagePort.ts:ProjectStoragePort`, `src/state/projectDurability.ts:ProjectDurabilityRuntime.syncForwardRebase`, and `STORAGE.md:Live collaboration path`.

### TAX: Durable retention is incomplete for serious use

Three collections have different growth behavior:

- Local history is bounded at 100 steps and its persisted codec enforces the same bound.
- Outbox receives one record per authored promotion. It is deleted only through explicit discard or replacement during outbox rebase because hosted acknowledgement is not implemented.
- Local commits receive one row per promotion or checkpoint. No ordinary deletion path exists.
- Pose revisions are append only. Content hash verifies integrity, but does not deduplicate equal content or collect unreachable revisions.

The following scenario is a scale model, not a measured usage claim:

- Two authored hours per day.
- One committed edit every ten seconds.
- 720 authored commits per day, or 262,800 per year.
- An outbox envelope averaging 0.5 to 2 KB yields roughly 125 to 500 MB per year while no hosted acknowledgement drains it.
- Local commit metadata at roughly 0.2 to 0.4 KB yields another 50 to 100 MB per year.
- Ten 4,500 cell State captures per day produce 3,650 immutable poses. Default compact cell tuples are roughly 65 to 100 bytes before styled part overrides, which puts pose storage around 1.1 to 1.6 GB per year. Styled cells raise that range.

Outbox growth becomes bounded by offline duration once hosted acknowledgement exists. Local commit retention and pose revision garbage collection still need explicit policies. Pose cleanup must preserve revisions reachable from current States, snapshots, drafts, outbox, local history, and the recovery window.

Recommended retention work:

1. Delete acknowledged outbox entries in the hosted worker transaction boundary.
2. Retain local commit receipts only through the idempotency and recovery window, then prune by project and commit sequence.
3. Implement mark and sweep for pose revisions across every durable root.
4. Use content hash for optional dedup only after identity and provenance rules are explicit.
5. Record bytes and age by store so the policy is measured.

Evidence: `src/persistence/indexedDbCommit.ts:issuePromoteWrites`, `src/persistence/indexedDbCommit.ts:completeReceiptWrite`, `src/persistence/indexedDbOutbox.ts:discardIndexedDbOutbox`, `src/persistence/storageRecordTypes.ts:StoredLocalCommit`, `src/persistence/storageRecordTypes.ts:StoredPoseRevisionBytes`, `src/persistence/recordCodecs/localHistoryRecordCodec.ts:encodeLocalHistoryRecord`, `src/state/documentHistory.ts:documentHistoryLimit`, and `STORAGE.md:Pose revisions`.

## Grooming

### GROOM: Extract the rebase and synchronization owner before the next feature

`src/state/projectDurability.ts` is 686 lines. `src/state/projectDurability.ts:ProjectDurabilityRuntime` spans most of the file and owns queue admission, staging, projection, draining, hydration, recovery, stale rebase, retry, save state, and pending action ownership.

The methods remain bounded, and prior extractions are coherent. The file sits fourteen lines below the hard ceiling, while hosted acknowledgement and remote install are the next planned concerns.

Extract `syncForwardRebase`, `promoteRebasedEnvelope`, and their branch replay state into a dedicated coordinator that consumes `ProjectStoragePort` and a narrow state callback. Keep queue ownership and save action tokens in ProjectDurabilityRuntime.

This is a normal pull request and should precede hosted synchronization work.

Evidence: `src/state/projectDurability.ts:ProjectDurabilityRuntime`, `src/state/projectDurability.ts:ProjectDurabilityRuntime.syncForwardRebase`, and `src/state/projectDurability.ts:ProjectDurabilityRuntime.promoteRebasedEnvelope`.

### GROOM: Centralize the record codec registry before adding version 2

Record kind dispatch is spread between codec exports, projection, hydration, storage preparation, and validation. Add one typed registry that maps record kind to current encoder, supported decoders, and migration function. Keep each codec in its current focused file.

This does not require a framework. A typed object and exhaustive checks are sufficient. It reduces the first migration's manual fan out and makes unsupported versions report one consistent error.

Evidence: `src/persistence/recordCodecs/index.ts`, `src/persistence/projectRecordHydration.ts:hydrateProjectRecords`, `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords`, and `src/persistence/storageRecordPreparation.ts:prepareStorageCommit`.

## Fine

### FINE: Atomic local durability is healthy

The storage port is narrow and adapter neutral. Promotion validates expected Project and asset revisions, pose immutability, roster changes, pending branch ownership, and idempotent commit identity before one IndexedDB transaction writes project, assets, pose revisions, history, user state, drafts, outbox, and receipt.

Keep this subsystem. It is the strongest reason to avoid a rebuild.

Evidence: `src/persistence/storagePort.ts:ProjectStoragePort`, `src/persistence/promoteContract.ts:createPromotePlan`, `src/persistence/indexedDbCommit.ts:issuePromoteWrites`, `src/persistence/indexedDbCommit.ts:completeReceiptWrite`, and `src/persistence/memoryProjectStorage.ts:applyPromote`.

### FINE: Semantic operation and revision foundations are healthy

Operations are serializable, target stable Project or asset identities, carry observed revision, and apply through pure domain reducers. Ordered edits use identifiers and relative anchors. The operation schema is already version 2, which proves that operation evolution is practical during pre release.

Keep the envelope and reducer pattern. Refine operation granularity for collaboration rather than replacing it.

Evidence: `src/domain/authoredOperations.ts:AuthoredOperation`, `src/domain/workbenchOperations.ts:applyDocumentOperation`, `src/domain/structureSequenceOperations.ts:StructureSequenceDocumentOperation`, `src/domain/relativeOrder.ts:RelativeOrderAnchor`, and `src/state/authoredOperationValidation.ts:validateAuthoredOperation`.

### FINE: PieceScore, CameraTrack, and pure evaluation are reusable

Piece motion is Structure owned, camera motion is stage owned, and evaluation has no persistence or React dependency. Scene morph topology and schedule are separated, score sampling is deterministic, and camera keyframes use explicit segments.

Recursive composition will add a level above these functions. Their internal math and contracts can remain.

Evidence: `src/domain/score.ts:PieceScore`, `src/domain/cameraTrack.ts:CameraTrack`, `src/evaluation/scoreAt.ts:scoreAt`, `src/evaluation/pieceAt.ts:resolvePieceSample`, `src/evaluation/sceneTransition.ts:sampleResolvedSceneTransition`, and `src/evaluation/sceneMorph.ts:prepareSceneMorphTopology`.

### FINE: Local history is bounded and ownership checked

In memory and persisted history share the 100 step limit. Hydration validates Project ownership and pose revision consistency while preserving independent valid steps around rejected entries.

Keep this boundary. Extend its durable root traversal when snapshots and placements arrive.

Evidence: `src/state/documentHistory.ts:documentHistoryLimit`, `src/persistence/recordCodecs/localHistoryRecordCodec.ts:encodeLocalHistoryRecord`, and `src/persistence/recordCodecs/localHistoryRecordCodec.ts:hydrateLocalHistoryRecord`.

### FINE: Owned file and function health passes the stated thresholds

No TypeScript file in `src/domain/`, `src/persistence/`, or `src/evaluation/` exceeds 700 lines. The largest owned source file is `src/domain/cubeOperations.ts` at 603 lines. The largest persistence coordinator in scope is `src/persistence/projectRecordHydration.ts` at 538 lines, with an 82 line public coordinator and focused private decode stages. The memory and IndexedDB adapters share promote validation instead of copying the transaction contract.

No dead path or harmful parallel implementation was proven in the audited slice.

Evidence: `src/domain/cubeOperations.ts:applySceneOperation`, `src/persistence/projectRecordHydration.ts:hydrateProjectRecords`, `src/persistence/promoteContract.ts:createPromotePlan`, `src/persistence/memoryProjectStorage.ts:applyPromote`, and `src/persistence/indexedDbCommit.ts:executeIndexedDbCommit`.

## Evidence

| Question | Answer | Primary evidence |
| --- | --- | --- |
| Schema evolution | TAX. Normal incremental extension after a migration framework replaces destructive upgrade. | `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema`; `src/persistence/recordCodecs/result.ts:isRecordEnvelope` |
| Collaboration | TAX. The route is real for optimistic sequential writers. Coarse inverse replay and hosted infrastructure remain. | `src/domain/authoredOperations.ts:AuthoredOperation`; `src/domain/documentRestoreOperations.ts:DocumentRestoreOperation`; `src/persistence/storagePort.ts:ProjectStoragePort` |
| Recursive composition | TAX. The durable machinery survives. The aggregate, address, evaluation, record, snapshot merge, and capacity boundaries require reshaping. | `src/domain/scene.ts:CubicellScene`; `src/evaluation/scoreAt.ts:Moment`; `src/persistence/recordCodecs/animationRecordCodec.ts:AnimationRecordV1`; `STUDIO.ANIMATION.md:Recursive composition model` |
| Local and instance identity | TAX overall. Local cube identity is already durable and coordinate independent at the audited head. Instance paths are the required new address. | `src/domain/lattice.ts:shiftCells`; `src/domain/score.ts:repairScore`; `TYPOGRAPHY.md:Identity` |
| Aggregate boundaries | TAX. Structure and camera ownership are sound. State, PoseRevision, Animation, Piece, Placement, Cue, GeometrySource, and instance path boundaries need restructuring. | `src/domain/workbench.ts:Library`; `src/domain/project.ts:PoseRevision`; `src/domain/score.ts:StageScore`; `TYPOGRAPHY.md:Proposed authored model` |
| Recursive capacity | TAX. The 4,500 cell single asset gate has no recursive depth, fanout, cycle, or expanded instance counterpart. | `STORAGE.md:Performance budgets`; `STUDIO.ANIMATION.md:Recursive composition model`; `TYPOGRAPHY.md:Open decisions` |
| Identity covers content | TAX. Systemic model weakness. Persistence detects divergence too late for runtime caches. | `src/domain/project.ts:createPoseRevision`; `src/persistence/poseRevisionRegistry.ts:extendPoseRevisionRegistry`; `src/transport/activeTransitionPlan.ts:createActiveTransitionPlanCache` |
| Unbounded growth | TAX for outbox, local commits, and pose revisions. FINE for local history. | `src/persistence/indexedDbCommit.ts:issuePromoteWrites`; `src/persistence/indexedDbOutbox.ts:discardIndexedDbOutbox`; `src/state/documentHistory.ts:documentHistoryLimit` |
| Module health | FINE in the owned slice. One adjacent coordinator needs immediate grooming at 686 lines. | `src/persistence/projectRecordHydration.ts:hydrateProjectRecords`; `src/state/projectDurability.ts:ProjectDurabilityRuntime` |

Decision: preserve the durable core, restructure the aggregate and revision model before the next major capability, and do not restart from zero.
