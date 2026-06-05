# Cubicell schema optimization audit

Pinned to `main` @ `ec42027`. All reads via `git show ec42027:<path>` and `git grep <pattern> ec42027`; the working tree was not read. The in-flight `chore/schema-lean` work (glide rename, `GridFormat.align` removal) is treated as done and excluded. Byte figures are `JSON.stringify(...).length` of representative values measured with node; where I did not measure I say so.

Ranked by value.

## 1. `inverseBody` is persisted, never read, and re-derived on every replay

**Owner:** `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:OutboxCommitRecordV1` carrying `src/domain/authoredOperations.ts:AppliedAuthoredOperation.inverseBody`.

Every outbox commit persists an inverse operation body per operation. The only production consumer of hydrated outbox operations is `src/state/projectPendingHydration.ts:applyProjectPendingHydration` → `src/state/projectForwardRebase.ts:replayAuthoredOperations`, which reads `applied.operation` only and re-derives the inverse through `src/state/actions/authoredReducer.ts:reduceAuthoredOperationState` (`deriveInverseBody`). The persisted copy is decoded, validated (`isAuthoredOperationBody`), and discarded. Nothing else in src reads `.inverseBody` (search: `git grep inverseBody ec42027 -- src/` — 7 hits, all encode, decode, or derivation).

**History:** introduced in `2aa9362` (feat(persistence): cut over to committed IndexedDB storage, #107) and never gained a reader since (`git log -S inverseBody` — that single commit). This is a designed-ahead artifact of the storage cutover, not a lost feature: the live inverse path is the replay-time re-derivation, and the rejected-replay path (`heldPending`) discards state without consulting inverses.

**Cost today:** one full `AuthoredOperationBody` per operation per pending commit. Not measured per document, but for capture/restore operations the body embeds complete compact poses (`authoredBodyPoseRevisions` enumerates them), so the dead copy can be the dominant share of an outbox record — kilobytes per destructive op.

**Smallest correct change:** stop persisting it. `encodeOutboxCommitRecord` writes `{ operation }` only; decode validates `hasOnlyKeys(candidate, ["operation"])` and reconstructs `AppliedAuthoredOperation` by re-deriving at replay (which already happens). Bump `outboxCommitRecordSchemaVersion`. `AppliedAuthoredOperation` stays as the in-memory shape.

**Confidence:** high that it is unread today; high that removal is safe (replay already proves derivability on the only read path).

## 2. `GridFormat.overflow` — a second `align`: persisted, validated, never honored

**Owner:** `src/domain/grid.ts:GridOverflow` / `GridFormat.overflow`.

The `"allow" | "clamp" | "hide"` union has no behavioral consumer anywhere. The only reads are the default completion (`grid.ts:withGridFormatDefaults`) and the two validation clauses (`src/state/workbenchValidation/pose.ts:isGridFormat`, `isPersistedGridFormat`). No writer exists outside the default (`git grep '"overflow:"' ec42027 -- src/` — none beyond `grid.ts`; no operation, panel, or preference authors it).

**History:** introduced in `5f70895` (feat: add grid based cube placement) together with the grid itself and never consumed since (`git log -S GridOverflow` — that single commit, no later additions or removals). Same class as `align`: unauthored and unhonored since inception. Cruft, not a lost feature — clamp/hide semantics were never implemented anywhere to lose.

**Cost today:** 18 bytes per persisted pose (`"overflow":"allow"`), one dead three-member union, two validation clauses.

**Smallest correct change:** delete exactly as `align` is being deleted: type, field, defaults, both validation clauses. Rides the same schema-version bumps the align removal already makes if reconciled into that branch.

**Reconciliation note:** the in-flight branch's replacement test for the format-crossing guard uses `overflow` as its surviving probe (`allow` → `hide`). Removing `overflow` requires re-probing that test with a field that stays (`cellSize`, `gap`, or `origin`).

**Confidence:** high.

## 3. `compactPose` stores the grid verbatim with every default explicit

**Owner:** `src/persistence/recordCodecs/compactPose.ts:CompactPoseV1.g` (`encodeCompactPose`).

The codec is rigorous about cells — default size/offset/rotation/scale encode as `null`, default edges and faces are omitted — and then persists `g: pose.grid` untouched: 142 bytes per pose at pure default today (126 after align removal, 108 after overflow too), including 23 bytes of `"gapOverrides":{"x":{},"y":{},"z":{}}` and the `{"format":{...}}` single-member wrapper. `p` and `r` are also always present at their defaults. This is per pose revision and per draft working pose, so a structure with N states carries N copies.

**Smallest correct change:** encode the grid the way cells are encoded — omit fields equal to `defaultGridFormat` (or `null` the whole `g` when fully default) and complete at decode via `src/domain/grid.ts:withGridFormatDefaults`, which exists for exactly this and already backs the partial-format read path (`pose.ts:isPersistedGridFormat` → `completePersistedPose`). Omit `p`/`r` when default. Bump `poseRevisionRecordSchemaVersion` and `draftRecordSchemaVersion` (compact pose is embedded in both, plus local history steps transitively).

**Confidence:** high on correctness; the read-time completion machinery already exists.

## 4. Full `MorphSettings` persisted per transition with defaults explicit

**Owner:** `src/domain/morphSettings.ts:MorphSettings`, validated by `src/state/scoreValidation.ts:isMorphSettings`, persisted inside `StructureRecordV1.document.score`.

`isMorphSettings` requires every key, so each authored transition persists ~270 bytes even when fully default (three complete `ClassMotion` objects, `cutAt: 0.5`, `durationMs: 1200`). Authoring is already patch-shaped (`patchMorphSettings` normalizes partials), so storage could hold the authored deltas and complete at read time.

**Smallest correct change:** persist `Partial<MorphSettings>` (deep-partial on the three class motions) and complete against `defaultMorphSettings` at decode; keep the in-memory shape total. Bump `structureRecordSchemaVersion` and `authoredOperationSchemaVersion` (patch-transition bodies).

**Confidence:** medium-high. The saving is real (defaults dominate authored transitions), but this trades schema bytes for a completion step in the codec and a validator rewrite; it is the largest of these changes.

## 5. Per-operation envelope duplication in outbox commits

**Owner:** `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:encodeOutboxCommitRecord` / `decodeOutboxCommitRecord`.

The record stores `actorId`, `clientId`, `id` (commitId), `projectId` at the envelope, copied from the first operation — and every operation still persists its own `actorId`, `clientId`, `commitId`, and `target.projectId`, which decode then rejects unless identical to the envelope's. The duplicated identity block measures ~150 bytes per operation (of a ~247-byte id-and-target block).

**Smallest correct change:** strip the four fields from each persisted operation at encode and reinject from the envelope at decode before `validateAuthoredOperation`. Bump `outboxCommitRecordSchemaVersion` (combines with finding 1 into one bump).

**Confidence:** medium-high. The equality validation proves the fields carry no independent information.

## 6. `StructureRecordV1.document.id` and `document.kind` duplicate the envelope

**Owner:** `src/persistence/recordCodecs/structureRecordCodec.ts:encodeStructureRecord` / `decodeStructureRecord`.

Decode rejects unless `document.id === record.id` and `document.kind === "structure"` (which also duplicates `recordKind`). ~40 bytes per structure record, one record per structure.

**Smallest correct change:** omit both from the persisted document; reinject at decode before `isStructureAsset`. Bump `structureRecordSchemaVersion`.

**Confidence:** high. Low value; worth taking only while the version is already moving.

## 7. `LocalHistoryStepV1.project` stores the full manifest on every step

**Owner:** `src/persistence/recordCodecs/localHistoryRecordCodec.ts:LocalHistoryStepV1` (`encodeBranch` / `entryProject`).

Each history step persists a complete `ProjectManifest` (~156 bytes with one asset, growing with the roster) even when identical across steps, up to `documentHistoryLimit` (100) in each of `past` and `future` — a ~31 KB ceiling per history record for an unchanged manifest. `entryProject` already proves derivability for the unchanged case: `entry.project ?? reconcileProjectAssets(fallback, ...)`.

**Smallest correct change:** persist `project: null` when the step's manifest `jsonValuesEqual`s the present manifest and fall back through the existing `entryProject` path at hydration. Bump `localHistoryRecordSchemaVersion`.

**Confidence:** medium. The ops themselves are RFC6902 diffs, so the manifest is the last uncompressed per-step payload; correctness depends on hydration ordering, which walks steps newest-first and has the present manifest in hand.

## Shapes that lie (category 5)

- `glide` — already being fixed on `chore/schema-lean`; nothing further found of that kind among persisted names.
- `src/domain/score.ts:TransitionMode` — the `"cut"` member is unreachable from the Editor (the inspector never authors `mode`), but the code carries an explicit NOTE adjudicating it as kept animation-studio capability. Already a recorded decision; no change proposed. If it stays long-term, `mode` is a defaults-stored-explicitly candidate (`"auto"` on every authored transition).
- `src/domain/grid.ts:GridState` — a single-member wrapper (`{ format: GridFormat }`) that persists an extra nesting level (`"g":{"format":{...}}`, ~11 bytes/pose) and has no second member anywhere in history. Cosmetic; fold only if finding 3 rewrites the grid encoding anyway.
- Optional fields that are never absent: none found. `State.view`, `AssemblyTrack.easing/exit/quantize/orderMode`, `MorphSettings.arriveForm/departForm` are all genuinely optional with live absent cases.

## Checked and alive (searches run, no finding)

- `Pose.frameId` — read by grid-lock capture guards (`structureOperations.ts:captureAllowed`, `documentRestoreOperations.ts:poseMatchesGridLock`) and scene restore.
- `gridLock`, `posterStateId` — read across `documentRestoreOperations.ts` and `structureOperations.ts`.
- `AssemblyTrack.orderMode` — read by `panels/AssemblyControls.tsx`; `cadence`/`exit`/`easing`/`quantize` — read by `domain/assemblyTiming.ts` and `evaluation/scoreAt.ts`.
- `ClassMotion.quantize` — read by `evaluation/sceneMorph.ts:quantizeProgress`.
- `CubeFaceState.opacity` — read by `evaluation/sceneMorph.ts` ink tweens and `sharedEdgeTweens.ts`.
- Cell ids — minted durable ids (`createGridResizePlan`), not derivable from coords; compact cell encoding already omits all defaults.
- `PoseRevisionRecordV1` metadata (`assetId`, `stateId`) — read by `createPoseRevision` consumers and integrity checks; not derivable when history references revisions no current structure holds.
- Draft record — `WorkingAttachment` is minimal (attached: one id; detached: one score).
- Row-level denormalization in `storageRecordTypes.ts` (`revision`, `lastCommitId`, ids beside opaque bytes) — legitimate index keys for reads that must not parse `documentBytes`; not flagged.

## Summary

The schema is tight at the cell level and leaky at the envelope level. The two structural findings are `inverseBody` (dead weight on every commit, potentially kilobytes) and `overflow` (a second `align`, same removal recipe). Findings 3–7 are all one recipe — omit defaults and envelope-duplicated fields at encode, complete at decode — and each rides a version bump that is free here. If only one change ships, ship finding 1.
