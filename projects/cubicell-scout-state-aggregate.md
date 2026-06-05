# Scout A: The Saved-State Aggregate

Baseline: cubicell main @ 71098b4, clean checkout. Read-only pass, 2026-07-29.
Scope: what a State is, its durable shape, and its persistence. Camera runtime
is Scout B; consumers are Scout C.

## Findings

### 1. Exact durable shape of a saved State

Domain aggregate, owned by `src/domain/workbench.ts`:

- `State` = `{ assetId, id, name, pose: PoseRevision }`
- `PoseRevision` (`src/domain/project.ts`) = `Pose & { assetId, id, stateId }`,
  doc comment: "Immutable pose content plus the asset and State that created it."
- `Pose` (`src/domain/scene.ts`) = `Omit<CubicellScene, "score">` =
  `{ cells: CubeCell[], frameId: CoordinateFrameId, grid: GridState, polarity: ScenePolarity, projection: ProjectionMode }`
- Owning aggregate root `StructureAsset` (`src/domain/workbench.ts`) =
  `{ gridLock, id, kind: "structure", name, posterStateId, score: PieceScore, stateIds }`

Durable records, owned by `src/persistence/recordCodecs/`:

- `StructureRecordV1` (`structureRecordCodec.ts`): `document` is the
  StructureAsset minus `stateIds`, plus `states: StructureStateReferenceV1[]`
  where `StructureStateReferenceV1 = { id, name, poseRevisionId }`. The pose
  itself is not inline; it is a reference.
- `PoseRevisionRecordV1` (`poseRevisionRecordCodec.ts`): the immutable pose
  content, carried as `StoredPoseRevisionBytes` with `contentHash`
  (`src/persistence/storageRecordTypes.ts`).

Grouped:

- **Scene content**: the PoseRevision (cells, frameId, grid, polarity,
  projection). Immutable, content-hashed, referenced by id, deduplicable.
- **Authored settings**: on the owning StructureAsset, not the State:
  `score: PieceScore` (ordered state sequence and per-transition morph),
  `gridLock`, `posterStateId`.
- **Identity and ordering**: UUIDv4 durable ids minted before the reducer
  (`createDurableId`, policy in STORAGE.md "Durable identity"); order lives in
  the structure document's `states` array; `revision` numbers order commits.
- **Metadata**: `name`, `projectId`, `recordKind`, `schemaVersion`.

Version constants: `structureRecordSchemaVersion = 1`,
`poseRevisionRecordSchemaVersion = 1` (per codec), envelope
`committedRecordSchemaVersion = 1` (`storageRecordTypes.ts`).

Camera appears nowhere in any of these shapes. The only durable camera in the
system is authored stage camera: `CameraTrack` keyframes
(`src/domain/cameraTrack.ts`) inside an `AnimationAsset.score` StageScore,
found via `findCameraTrack` (`src/domain/score.ts`).

### 2. Deliberate exclusions, documented

The exclusion of camera is documented and locked, in two places:

STUDIO.PROJECT.md, section "What a State captures (locked)":

> A State captures **scene content plus projection** (orthographic or
> perspective), and nothing about the camera. The viewpoint is stage-owned and
> never baked into a State, so a State stays reusable content that any
> animation can frame from any angle. The camera model itself lives in
> ANIMATION.md, not here.

STORAGE.md, "State ownership" table: `Presence | Selection, hover, cursor,
playhead, viewport camera | Memory only | Ephemeral Realtime`, followed by:

> Authored camera keyframes are asset state. The editor viewport camera is
> private session state.

The doc matches the code exactly (Pose includes `projection`, excludes
camera). Other exclusions: `score` (Pose omits it; assembly order is asset
state), selection/hover/panel state (STORAGE.md authored operation contract:
"Selection, hover, panel state, and other private context stay outside the
authored operation"), and undo history (private per-user records).

### 3. Git archaeology: never existed, never removed

- `git log -S 'ViewPose' -- src/persistence src/domain src/state`: zero hits.
  Probe verified with a control: `git log -S 'poseRevision' -- src/persistence`
  hits 17a10de and 2aa9362, so the empty result is a real absence.
- `git log -S 'camera' -i -- src/persistence`: zero hits, and `rg -i camera
  src/persistence` finds nothing today. Camera has never touched the
  persistence layer in any commit.
- The `State` type was born in a3e6ff1 (`feat(animation): establish scene
  morph and asset timeline foundation`) already as
  `{ assetId, id, name, pose }`. No camera field at birth, none since.
- Camera authorship entered the domain at c532388 (`feat(animation): add
  authored camera tracks`) as Animation stage tracks, deliberately not on
  State.
- The boundary language was consolidated and locked at ac9e098
  (`docs(studio): consolidate product structure and fold camera
  target-binding`).

Verdict: "never existed," not "existed and was removed." The exclusion was an
explicit, repeated product decision.

### 4. Write path and read path

Capture (pure projection of store state, no live runtime objects):

- `createStateCapture` (`src/panels/stateCapture.ts`) builds the
  `capture-state` authored operation from `workbench.workingPose` via
  `createPoseRevision`, minting all durable ids up front.
- The pure reducer `captureState` (`src/domain/structureOperations.ts`)
  appends the State to the library and its keyframe to the piece score.
- Durable record build: `projectWorkbenchRecords`
  (`src/persistence/projectRecordProjection.ts`). Its input
  `ProjectRecordProjectionInput` is store fields only (workbench, project,
  editor, panelLayout, history, outbox). It emits `ProjectRecordSet` via
  `encodeStructureRecord` and friends; staging and promotion travel as
  `PreparedStorageCommit` (`storageRecordTypes.ts`) through the ordered commit
  queue into IndexedDB (`indexedDbCommit.ts`).

Read back (symmetric pure projection):

- `hydrateProjectRecords` (`src/persistence/projectRecordHydration.ts`), run
  in a worker via `hydrateProjectRecordsAsync`, decodes all records into
  `HydratedProjectRecords`.
- `applyHydratedRecords` (`src/state/projectDurabilityHydration.ts`) publishes
  the result into Zustand with `store.setState`.

The camera runtime never intersects this path in either direction.

### 5. Domain position: camera is presentation, co-located at most

Position, argued, not hedged: **the viewport camera is not part of the State
aggregate's invariant.** A State is fully described without it.

- **Ubiquitous language**: the locked definition says a State is reusable
  scene content that "any animation can frame from any angle." Making camera
  part of what a State *is* changes the noun. It would also collide with the
  existing durable camera authority: the Animation StageScore camera lane
  frames States; a State-baked camera creates two owners of framing with no
  precedence rule.
- **Invariants**: the State's real invariants are pose-revision integrity,
  immutability, and referential identity (`hasUniquePoseRevisionIds`,
  `poseRevisionMatchesState`, content hashes). Camera pose churns on every
  orbit gesture. Inside the pose revision it would destroy the immutability
  economics: a new revision per nudge, content-hash churn, GC pressure, and
  camera motion becoming shared authored operations, directly violating
  STORAGE.md's rule that presence stays outside authored operations.
- **Collaboration seam**: STORAGE.md classifies viewport camera as Presence
  (ephemeral Realtime later). Baking it into shared authored content would
  sync one user's viewpoint to everyone, which is wrong for the collaboration
  model V1 is deliberately preserving a route to.

Stuart's ask ("a saved state should capture the current camera position")
resolves to one of two different features, and the record it lands in differs:

- **(a) Per-user recall**: "restore where I was looking when I return to this
  State." That is workspace-session state: extend `UserProjectState`
  (`src/persistence/recordCodecs/userProjectStateRecordCodec.ts`, currently
  `{ activeAssetId, activeStateId, panelLayout, projectId, userId }`) with a
  viewport pose keyed by state or asset. Private, per user, durable, never
  synced as content. Smallest blast radius; requires consciously amending the
  STORAGE.md Presence row, which currently pins viewport camera to memory
  only.
- **(b) Authored framing**: "this State should be presented from here"
  (posters, thumbnails, default framing). That is an optional
  `framing?: CameraPoseSnapshot` co-located on the State record
  (`StructureStateReferenceV1`), never inside the pose revision. Shared and
  versioned with the structure document. A State without framing stays valid,
  so the aggregate invariant is unchanged; this is co-location, not aggregate
  membership.

What breaks if camera is read as aggregate-invariant: cross-animation reuse,
pose-revision immutability, the presence/authored separation, and the
collaboration story. What breaks under co-location: nothing structural; the
cost is defining the fallback when absent and deciding whether `update-state`
also recaptures camera. The decision Stuart owns: is the wanted behavior (a)
private recall or (b) authored presentation? Different records, different
privacy, different sync semantics.

Either way, reuse the existing serializable camera vocabulary:
`CameraPoseSnapshot` (`src/domain/cameraTrack.ts`), doc comment
"Dependency-neutral, serializable camera pose shared by every boundary." Do
not mint a second camera pose type.

### 6. Versioning cost: code matches the no-migrations rule

The procedure for changing a durable shape:

1. Change the record type in its codec.
2. Bump that codec's schema version constant. All ten sit at `1`:
   `committedRecordSchemaVersion` (`storageRecordTypes.ts`),
   `projectRecordSchemaVersion`, `structureRecordSchemaVersion`,
   `animationRecordSchemaVersion`, `poseRevisionRecordSchemaVersion`,
   `draftRecordSchemaVersion`, `localHistoryRecordSchemaVersion`,
   `localCheckpointRecordSchemaVersion`, `outboxCommitRecordSchemaVersion`,
   `userProjectStateRecordSchemaVersion` (each in its
   `src/persistence/recordCodecs/` file).
3. Bump `indexedDbProjectStorageVersion` (currently `4`,
   `src/persistence/indexedDbSchema.ts`). The upgrade handler
   `createIndexedDbProjectSchema` deletes every existing object store and
   recreates the schema. That deletion loop is the reset path.

There is no migration code anywhere in `src/persistence`. Decoders accept only
the current `schemaVersion` and reject otherwise (surfaced as
`RejectedProjectRecord`; a failed project hydration throws in
`hydrateProjectState`, `src/state/projectDurabilityHydration.ts`). STORAGE.md
codifies the rule: "During pre release development, an incompatible shape can
reset local data rather than introduce legacy readers or parallel migration
paths." Code and standing rule agree. Cost of adding a camera field: a type
change, one or two constant bumps, and a local reset. Choosing shape (a)
confines the bump to the user-project-state record; shape (b) touches the
structure record.

## Reuse Map

- `CameraPoseSnapshot` (`src/domain/cameraTrack.ts`): the serializable camera
  pose. The only camera shape any new durable field should use.
- `UserProjectState` + codec (`userProjectStateRecordCodec.ts`): the existing
  per-user, per-project durable home for shape (a).
- `StructureStateReferenceV1` (`structureRecordCodec.ts`): the per-State
  record row for shape (b).
- `createStateCapture` (`src/panels/stateCapture.ts`): the single capture
  entry point; camera capture, if authored, belongs in this operation builder,
  not a second path.
- Validation home: `src/state/workbenchValidation` (codecs delegate shape
  checks there); `src/state/jsonGuards` for primitives.
- `compactPose` (`recordCodecs/compactPose.ts`): existing compact wire
  encoding pattern if pose bytes are touched.

## Quality Map

- The persistence domain is healthy: codecs are small (60 to 146 LOC), one
  schema path, no parallel implementations, no dead camera remnants.
- `src/persistence/projectRecordHydration.ts` is 538 LOC. Any new field's
  decode/validation added there should watch the 700 limit; prefer pushing
  validation into `workbenchValidation` as the existing codecs do.
- Doc/code agreement is exact today (locked State definition matches `Pose`
  field for field). Whichever camera shape is chosen, STUDIO.PROJECT.md's
  locked section and STORAGE.md's Presence row must be amended in the same
  change, or the docs start lying.

## Plan

Suggested order for the design phase (not executed; this pass was read-only):

1. Stuart decides (a) per-user recall vs (b) authored framing; they are
   different features and can also both exist.
2. Amend STORAGE.md ownership table and STUDIO.PROJECT.md locked section to
   record the new boundary deliberately.
3. Extend the chosen record with `CameraPoseSnapshot`, bump its schema version
   constant plus `indexedDbProjectStorageVersion`, reset local data. No
   migration branches.
4. Wire capture through `createStateCapture` (and `createStateUpdate` if
   update recaptures camera); wire restore through the hydration consumers
   (Scout C's territory).
5. Verify: codec round-trip test alongside the existing
   `tests/projectRecordCodecs.test.ts`, plus a reset-on-version-bump test.
