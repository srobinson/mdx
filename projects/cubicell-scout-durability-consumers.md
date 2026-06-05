# Cubicell durability consumer enumeration and blast radius

Seat D of 4. Read-only scout. Repo `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`, branch `main`.

## Scope

Question: who touches the durability layer, and what actually breaks if the **outbox store** and the **outbox forward-rebase path** (installCommitted → `source: "outbox"`) are removed?

**Correction to the established “sync only from installCommitted” claim:** `ProjectDurabilityForwardRebase.sync` has three production call sites in `ProjectDurabilityRuntime`:

| Call site | Source | Production reachability |
|-----------|--------|-------------------------|
| `ProjectDurabilityRuntime.installCommitted` | `"outbox"` | **Dead**: no production caller of `installCommitted` |
| `ProjectDurabilityRuntime.publishHydration` when `pendingRecovery` | `"draft"` (default) | **Live**: after hydrate with pending drafts |
| `ProjectDurabilityRuntime.drainQueue` on `StalePromoteError` | `"draft"` (default) | **Live**: concurrent promote conflict recovery |

Draft-source forward rebase is load-bearing. Outbox-source forward rebase is not.

---

## 1. FULL CONSUMER TABLE

Legend: **R**=read, **W**=write, **D**=define/type, **X**=export barrel. prod/test as noted.

### 1A. Outbox object store and port API

| path:symbol | store/type | R/W | prod/test |
|-------------|------------|-----|-----------|
| `src/persistence/indexedDbSchema.ts:indexedDbProjectStoreNames` | outbox store name in wire list | D | prod |
| `src/persistence/indexedDbSchema.ts:createIndexedDbProjectSchema` | creates `outbox` + indexes | W | prod |
| `src/persistence/indexedDbSchema.ts:outboxCommitIndex` | outbox index `byCommit` | D | prod |
| `src/persistence/indexedDbSchema.ts:outboxBranchSequenceIndex` | outbox index `byBranchSequence` | D | prod |
| `src/persistence/indexedDbOutbox.ts:loadIndexedDbOutbox` | outbox store | R | prod (only via port) |
| `src/persistence/indexedDbOutbox.ts:discardIndexedDbOutbox` | outbox store | W | prod (only via port) |
| `src/persistence/indexedDbProjectStorage.ts:createIndexedDbProjectStorage` | wires `loadOutbox`/`discardOutbox` | R/W | prod |
| `src/persistence/indexedDbCommit.ts:issuePromoteReads` | reads superseded outbox row | R | prod |
| `src/persistence/indexedDbCommit.ts:issuePromoteWrites` | add/delete outbox rows on promote | W | prod **LIVE write** |
| `src/persistence/memoryProjectStorage.ts:createMemoryProjectStorage` | in-memory outbox Map | R/W | prod |
| `src/persistence/memoryProjectStorage.ts:loadOutbox` | outbox Map | R | prod |
| `src/persistence/memoryProjectStorage.ts:discardOutbox` (inline) | outbox Map | W | prod |
| `src/persistence/memoryProjectStorage.ts:promote` path | outbox Map | W | prod **LIVE write** |
| `src/persistence/storagePort.ts:ProjectStoragePort.loadOutbox` | port contract | D | prod |
| `src/persistence/storagePort.ts:ProjectStoragePort.discardOutbox` | port contract | D | prod |
| `src/persistence/storagePort.ts:ProjectOutboxEnvelope` | outbox envelope type | D | prod |
| `src/persistence/storagePort.ts:ProjectStorageReceipt.outboxSequence` | receipt field from outbox autoincrement | D | prod |
| `src/persistence/storageRecords.ts:storageReceipt` | sets `outboxSequence` | W | prod |
| `src/persistence/storageRecordTypes.ts:StoredOutboxBytes` | stored row shape | D | prod |
| `src/persistence/storageRecordTypes.ts:PreparedStorageCommit.outbox` | prepared promote payload | D | prod |
| `src/persistence/storageRecordTypes.ts:ProjectHeaderBytes.outbox` | header type | D | prod |
| `src/persistence/storageRecordTypes.ts:RawProjectHeader.outbox` | header type | D | prod |
| `src/persistence/storedOutbox.ts:decodeStoredOutbox` | row decoder | R | prod |
| `src/persistence/storedOutbox.ts:projectOutboxEnvelope` | row → envelope | R | prod |
| `src/persistence/storedOutbox.ts:requiredProjectOutboxEnvelope` | strict envelope | R | prod |
| `src/persistence/storageRecordPreparation.ts:prepareStorageCommit` | builds `outbox` payload for authored promote | W | prod **LIVE** |
| `src/persistence/storageFingerprint.ts:storageFingerprint` | digests `commit.outbox?.bytes` | R | prod |
| `src/persistence/promoteContract.ts:PromoteInput.supersededOutbox` | promote input | R | prod |
| `src/persistence/promoteContract.ts:validateOutboxSource` | outbox-rebase guard | R | prod (install/outbox-rebase only) |
| `src/persistence/promoteContract.ts:createPromotePlan` | supersededOutboxSequence | R | prod |
| `src/persistence/indexedDbFailureValidation.ts:decodePreparedCommit` | expects prepared `outbox` key | R | prod |
| `src/persistence/indexedDbProjectReads.ts:loadIndexedDbProject` | hardcodes `outbox: []` (never reads store) | — | prod |
| `src/persistence/indexedDbProjectReads.ts:loadIndexedDbProjectHydrationBytes` | hardcodes `outbox: []` | — | prod |
| `src/persistence/storageRecordReads.ts:rawProjectHeader` / assemble paths | hardcodes `outbox: []` | — | prod |
| `src/persistence/memoryProjectStorage.ts` load paths | hardcodes `outbox: []` for hydration | — | prod |
| `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase.sync` | `loadOutbox`/`discardOutbox` when source outbox | R/W | prod **DEAD path** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.installCommitted` | only caller of outbox-source sync | — | prod **DEAD entry** |
| `src/state/cubicellStore.ts:createCubicellStore` | exposes `installCommitted` on runtime | — | prod **unwired to UI** |
| `src/state/browserRuntimeRetention.ts:CubicellStoreRuntime` | types `installCommitted` | D | prod |

### 1B. Outbox commit codec (shared with drafts; name is a trap)

| path:symbol | store/type | R/W | prod/test |
|-------------|------------|-----|-----------|
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:outboxCommitRecordSchemaVersion` | codec wire | D | prod |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:OutboxCommitRecord` | codec type | D | prod |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:OutboxCommitOperation` | codec type | D | prod |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:OutboxCommitOperations` | codec type | D | prod |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:encodeOutboxCommitRecord` | encode envelope ops | W | prod **LIVE (drafts + outbox payload)** |
| `src/persistence/recordCodecs/outboxCommitRecordCodec.ts:decodeOutboxCommitRecord` | decode | R | prod |
| `src/persistence/recordCodecs/index.ts` | re-exports codec | X | prod |
| `src/persistence/index.ts` | re-exports recordCodecs | X | prod |
| `src/persistence/pendingDrafts.ts:preparePendingAppendSeed` | encodes pending via `encodeOutboxCommitRecord` | W | prod **LIVE draft path** |
| `src/persistence/projectPendingValidation.ts:decodeProjectPendingEnvelope` | builds outbox-commit shape for draft ops | R | prod **LIVE** |
| `src/persistence/projectRecordProjection.ts:projectWorkbenchRecords` | projects `outbox` field (callers pass `[]`) | W | prod |
| `src/persistence/projectRecordHydration.ts:decodeOutbox` | decodes record-set outbox (always empty in load) | R | prod |
| `src/persistence/projectRecordHydration.ts:HydratedProjectRecords.outbox` | hydrated field, unused after decode | D | prod dead field |
| `src/persistence/projectRecordHydration.ts:HydratedProjectPending.envelopes.operations` | typed as `OutboxCommitOperation[]` | D | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectStorageHead` authored ops | `OutboxCommitOperations` | D | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectPendingEnvelope` | draft envelope | D | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectPendingWrite` | staging write | D | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectStorageRebase` | draft \| outbox rebase discriminant | D | prod |
| `src/persistence/projectStorageRebaseValidation.ts:isProjectStorageRebase` | validates both sources | R | prod |
| `src/state/projectForwardRebase.ts:replayAuthoredOperations` | takes `OutboxCommitOperations` | R | prod **LIVE** |
| `src/state/projectForwardRebase.ts:planForwardRebaseEnvelope` | draft + outbox rebase planner | R | prod **LIVE draft** |
| `src/state/projectForwardRebase.ts:pendingBranchEnvelopes` | draft branch ordering | R | prod **LIVE** |
| `src/state/projectPendingHydration.ts:applyProjectPendingHydration` | replays draft envelopes | R | prod **LIVE** |
| `src/state/projectCommitProjectionCore.ts:projectSnapshot` | passes `outbox: []`, strips from snapshot | — | prod |

### 1C. ProjectDurability family (coordinator, not just outbox)

| path:symbol | store/type | R/W | prod/test |
|-------------|------------|-----|-----------|
| `src/state/projectDurability.ts:createProjectDurabilityCoordinator` | durability entry | D | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityCoordinator` | public API type | D | prod |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime` | runtime | D | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.enqueue` | authored save | W | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.checkpoint` | checkpoint save | W | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.checkpointUserProjectState` | user state | W | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.hydrate` | startup load | R | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.installCommitted` | remote install | W | prod **DEAD** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.recoverToLastCommitted` | recovery | W | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.retry` | retry failed | W | prod **LIVE** |
| `src/state/projectDurability.ts:ProjectDurabilityRuntime.reserveAuthored` | queue capacity | R | prod **LIVE** |
| `src/state/projectDurabilityForwardRebase.ts:ProjectDurabilityForwardRebase` | rebase engine | R/W | prod **LIVE draft / DEAD outbox** |
| `src/state/projectDurabilityHydration.ts:ProjectDurabilityStoreAccess` | store port for durability | D | prod |
| `src/state/projectDurabilityHydration.ts:applyHydratedRecords` | hydrate apply | W | prod **LIVE** |
| `src/state/projectDurabilityHydration.ts:hydrateCommittedEnvelopeState` | rebase hydrate | R | prod **LIVE** |
| `src/state/projectDurabilityHydration.ts:ensureFullRoster` | roster complete | R | prod **LIVE** |
| `src/state/projectDurabilityPendingAction.ts:ProjectDurabilityPendingAction` | save action mutex | D | prod **LIVE** |
| `src/state/projectDurabilityRecovery.ts:preflightCommittedRecovery` | recovery preflight | R | prod **LIVE** |
| `src/state/projectDurabilityRevisions.ts:ProjectCommittedRevisions` | committed revision map | R/W | prod **LIVE** |
| `src/state/projectDurabilitySaveState.ts` helpers | save UI state | D | prod **LIVE** |
| `src/state/projectDurabilityUnits.ts:createDurabilityUnit` | unit model | D | prod **LIVE** |
| `src/state/projectDurabilityUserState.ts:createUserProjectStateUnit` | user-state unit | D | prod **LIVE** |
| `src/state/cubicellStore.ts:createCubicellStore` | wires coordinator | W | prod **LIVE** |
| `src/state/actions/authoredDispatcher.ts` | enqueue/checkpoint/reserve | W | prod **LIVE** |
| `src/state/actions/checkpointDispatcher.ts` | checkpoint | W | prod **LIVE** |
| `src/state/actions/editorActions.ts` | user-state checkpoint | W | prod **LIVE** |
| `src/state/actions/documentActions.ts` | undo/redo checkpoint | W | prod **LIVE** |
| `src/state/actions/localDurabilityPublisher.ts:createLocalDurabilityPublisher` | publish order | D | prod **LIVE** |
| `src/app/PersistenceStatus.tsx` | surfaces saveState/pendingRecovery | R | prod **LIVE** |

### 1D. Envelope / commit types (ProjectStorageCommit stack)

| path:symbol | store/type | R/W | prod/test |
|-------------|------------|-----|-----------|
| `src/persistence/storagePort.ts:ProjectStorageCommit` | commit contract | D | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectStorageHead` | authored \| checkpoint | D | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectStorageChangeSet` | change set | D | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectStorageRebase` | draft \| outbox rebase | D | prod |
| `src/persistence/storagePort.ts:ProjectStoragePort.promote` | main write path | W | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectStoragePort.installCommitted` | install write | W | prod **DEAD entry** |
| `src/persistence/storagePort.ts:ProjectStoragePort.stagePending` | draft stage | W | prod **LIVE** |
| `src/persistence/orderedCommitQueue.ts:BranchCommitQueues` | serializes promote/install | W | prod **LIVE** |
| `src/persistence/orderedCommitQueue.ts:installCommitted` | install queue entry | W | prod **DEAD** |
| `src/state/projectCommitProjection.ts` / `projectCommitProjectionCore.ts` | builds commits | W | prod **LIVE** |
| `src/persistence/storageRecordPreparation.ts:prepareStorageCommit` | prepare | W | prod **LIVE** |
| `src/persistence/storageRecordPreparationAsync.ts` / worker | async prepare | W | prod **LIVE** |
| `src/persistence/promoteContract.ts:createPromotePlan` | promote plan | R/W | prod **LIVE** |
| `src/persistence/indexedDbCommit.ts:promoteIndexedDbCommit` | IDB promote | W | prod **LIVE** |

### 1E. poseRevisions store and persistence types (not outbox; load-bearing)

| path:symbol | store/type | R/W | prod/test |
|-------------|------------|-----|-----------|
| `src/persistence/indexedDbSchema.ts` store `poseRevisions` | store | D | prod |
| `src/persistence/indexedDbCommit.ts` pose put/get | poseRevisions | R/W | prod **LIVE** |
| `src/persistence/indexedDbProjectReads.ts` load poses | poseRevisions | R | prod **LIVE** |
| `src/persistence/memoryProjectStorage.ts` pose Map | poseRevisions | R/W | prod **LIVE** |
| `src/persistence/storageRecordTypes.ts:StoredPoseRevisionBytes` | row type | D | prod |
| `src/persistence/recordCodecs/poseRevisionRecordCodec.ts` | codec | R/W | prod **LIVE** |
| `src/persistence/poseRevisionRegistry.ts:extendPoseRevisionRegistry` | conflict guard | R/W | prod **LIVE** |
| `src/persistence/projectRecordProjection.ts` pose projection | pose records | W | prod **LIVE** |
| `src/persistence/projectRecordHydration.ts:decodePoses` | pose decode | R | prod **LIVE** |
| `src/persistence/promoteContract.ts:validatePoses` | pose integrity | R | prod **LIVE** |
| `src/persistence/committedPoseIntegrity.ts:assertCommittedPoseIntegrity` | integrity | R | prod **LIVE** |
| `src/persistence/storagePort.ts:ProjectAssetRecords.poseRevisions` | asset load | D | prod |
| `src/persistence/storagePort.ts:ProjectHydrationBytes.poseRevisions` | hydration bytes | D | prod |

Domain `PoseRevision` (`src/domain/project.ts:createPoseRevision`, `getPoseRevisionDocument`, structure/workbench/authored ops, panels, thumbnails) is the live authoring model. It is **not** removable with outbox. Full domain call graph omitted as rows; it is ambient across domain/state/UI.

### 1F. Wire version constant

| path:symbol | store/type | R/W | prod/test |
|-------------|------------|-----|-----------|
| `src/persistence/indexedDbSchema.ts:indexedDbProjectStorageVersion` (=8) | wire | D | prod |
| `src/persistence/indexedDbProjectStorage.ts` open DB | uses version | R | prod |
| `src/persistence/index.ts` re-export via indexedDbProjectStorage | X | prod |
| `tests/indexedDbSchema.test.ts` | asserts version === 8 | R | test |
| `tests/committedStoreBrowserDriver.ts` | asserts open version | R | test |
| `tests/projectStorageBrowserDriver.ts:indexedDbProjectStoreNames` | store list incl outbox | R | test |

### 1G. Test consumers (outbox / install / forward-rebase / durability)

| path:symbol | store/type | R/W | prod/test |
|-------------|------------|-----|-----------|
| `tests/projectStorageContract.ts` | outbox sequences, pose load, outbox excluded from hydration | R | test |
| `tests/projectStorage.test.ts` | memory storage contract | R | test |
| `tests/indexedDbStorage.browser.test.ts` | IDB contract + store names | R | test |
| `tests/projectStorageBrowserDriver.ts` | fixtures with `records.outbox`, store counts | R/W | test |
| `tests/projectStorageFixtures.ts` | builds fixture outbox | W | test |
| `tests/projectStorageRebase.test.ts` | outbox source promote + installCommitted | R/W | test |
| `tests/projectRebaseContract.ts` | loadOutbox + installCommitted contracts | R/W | test |
| `tests/projectForwardRebase.test.ts` | planForwardRebaseEnvelope + codec | R | test |
| `tests/projectDurabilityRebase.test.ts` | draft-source StalePromote rebase | R/W | test |
| `tests/cubicellStoreDurabilityRecovery.test.ts` | draft recovery | R/W | test |
| `tests/cubicellStoreDurabilityRetry.test.ts` | createProjectDurabilityCoordinator | R/W | test |
| `tests/committedStoreBrowserDriver.ts` | installCommitted, outbox rows, forward rebase crash resume | R/W | test |
| `tests/committedStoreHydration.test.ts` | loadOutbox after rebase | R | test |
| `tests/committedStore.browser.test.ts` | browser durability surface | R | test |
| `tests/committedStorePersistence.test.ts` | outboxSequence, pendingRecovery | R | test |
| `tests/indexedDbFailureValidation.test.ts` | decodeStoredOutbox | R | test |
| `tests/projectStorageRecordBrowserDriver.ts` | reads outbox store / pose store | R | test |
| `tests/projectRecordCodecs.test.ts` | outbox-commit + pose codecs | R | test |
| `tests/recordCodecMetrics.ts` | includes outbox/pose metrics | R | test |
| `tests/browserRuntimeRetention.test.ts` | stubs installCommitted | — | test |
| `tests/cubicellStorePersistence.test.ts` | durability integration | R/W | test |
| `tests/saveRecoveryBrowserDriver.ts` | poseRevisions corruption | W | test |
| `tests/poseRevisionIntegrity*.ts` | pose integrity | R | test |
| `tests/indexedDbSchema.test.ts` | wire version 8 | R | test |

---

## 2. LOAD-BEARING vs INCIDENTAL (production, if outbox store + outbox-source rebase removed)

| Production consumer | Classification | Why |
|---------------------|----------------|-----|
| Every authored `promote` writing outbox rows | **Incidental write** | Writes accumulate; nothing in production reads them. Removing write shrinks promote; does not break save. |
| `loadOutbox` / `discardOutbox` / `discardIndexedDbOutbox` | **Incidental / dead** | Only outbox-source `ForwardRebase.sync`. |
| `installCommitted` (durability + storage + queue) | **Incidental / dead** | Exposed on runtime; no app/UI caller. |
| Outbox branch of `ProjectDurabilityForwardRebase.sync` | **Incidental / dead** | Only from installCommitted. |
| `validateOutboxSource` / `rebase.source === "outbox"` branches | **Incidental** | Only outbox rebase promotes. |
| Draft-source `ForwardRebase.sync` | **Load-bearing** | StalePromoteError recovery + pendingRecovery drain. **Breaks if whole class removed.** |
| `encodeOutboxCommitRecord` / `OutboxCommitOperations` | **Load-bearing (misnamed)** | Pending draft staging, head prepare, replay. **Do not delete with outbox store.** |
| `ProjectStorageCommit` / promote / stagePending | **Load-bearing** | Core single-user save path. |
| `ProjectDurability` enqueue/hydrate/checkpoint/retry/recover | **Load-bearing** | Entire local durability. |
| `poseRevisions` store + codecs | **Load-bearing** | Structure state poses. Independent of outbox. |
| Hydration hardcoding `outbox: []` | **Already incidental** | Load never touches outbox store. |
| `outboxSequence` on receipt | **Incidental number** | Tests assert 1,2,3…; production ignores. Can zero-fill after cut. |
| `HydratedProjectRecords.outbox` | **Incidental dead field** | Decoded then unused. |
| Wire version 8 + store list | **Load-bearing schema** | Removing store requires **wire bump** (owner: encouraged, no migration). |

**Net production break from removing outbox store + outbox-source rebase only:** none of the live single-user save/hydrate/draft-rebase path. App keeps saving via drafts + promote.

**Net production break from removing all of `ProjectDurabilityForwardRebase`:** concurrent conflict recovery and pending draft recovery after hydrate.

---

## 3. TYPE FALLOUT

### Becomes unreferenced only if outbox store + installCommitted + outbox-source rebase are fully deleted

| Type / symbol | Notes |
|---------------|-------|
| `StoredOutboxBytes` | store row |
| `ProjectOutboxEnvelope` | loadOutbox return |
| `loadIndexedDbOutbox` / `discardIndexedDbOutbox` | IDB helpers |
| `ProjectStoragePort.loadOutbox` / `discardOutbox` | port methods |
| `ProjectStorageRebase` outbox arm (`source: "outbox"`, `triggerCommitId`) | can collapse to draft-only or delete rebase field variants carefully |
| `validateOutboxSource` | promoteContract |
| `ProjectDurabilityCoordinator.installCommitted` / runtime method | + `CubicellStoreRuntime.installCommitted` |
| `orderedCommitQueue.installCommitted` / writeKind `"install"` | if install is only for remote outbox path |
| `PreparedStorageCommit.outbox` | promote payload field |
| `ProjectHeaderBytes.outbox` / raw header outbox | already always empty on load |
| `ProjectRecordSet.outbox` / `HydratedProjectRecords.outbox` / `ProjectHydrationBytes.outbox` | projection/hydration scaffolding |
| `outboxCommitIndex` / `outboxBranchSequenceIndex` | schema indexes |
| `"outbox"` in `indexedDbProjectStoreNames` | store name |

### Shared traps (survive outbox removal; rename or keep)

| Shared type | Used by removed path | Used by surviving path |
|-------------|----------------------|------------------------|
| `OutboxCommitOperations` / `OutboxCommitOperation` / `OutboxCommitRecord` | outbox store payload | **draft pending**, `ProjectStorageHead`, replay, projection |
| `encodeOutboxCommitRecord` / `decodeOutboxCommitRecord` | outbox bytes | **draft staging**, pending validation, tests |
| `outboxCommitRecordSchemaVersion` / `recordKind: "outbox-commit"` | name implies store | **serialized draft envelope shape** |
| `ProjectPendingEnvelope` | structurally same ops as outbox envelope | **drafts** |
| `ProjectStorageRebase` draft arm | sibling of outbox arm | **draft forward rebase** |
| `planForwardRebaseEnvelope` / `replayAuthoredOperations` | outbox sync uses them | **draft sync + pending hydration** |
| `ProjectDurabilityForwardRebase` class | outbox source branch | **draft source branch** |
| `ProjectStorageReceipt.outboxSequence` | from outbox autoincrement | still returned on every promote |
| `PreparedStorageCommit` / `ProjectStorageCommit` | install path | **every promote** |
| `poseRevisions` / `PoseRevision*` / domain `PoseRevision` | unrelated store | **must keep** |
| `indexedDbProjectStorageVersion` | bumps when store list changes | **must bump on cut** |

---

## 4. TEST INVENTORY

| Test | If outbox + outbox-rebase removed | Guards invariant that still matters? |
|------|-----------------------------------|--------------------------------------|
| `tests/projectStorageContract.ts` outbox sequence asserts | **Fail** (sequence semantics) | Weak: sequence is incidental; pose/hydration parts still matter |
| `tests/projectStorage.test.ts` / `indexedDbStorage.browser.test.ts` store name lists + sequences | **Fail** partial | Store presence list yes for wire; sequence no |
| `tests/projectStorageRebase.test.ts` outbox source + installCommitted | **Fail / delete** | Only if multi-client install returns; **not** single-user product |
| `tests/projectRebaseContract.ts` loadOutbox / install | **Fail / delete** | Same; draft parts of contract still matter if split |
| `tests/committedStoreBrowserDriver.ts` outbox forward rebase / crash resume install | **Fail / delete** | Outbox multi-client story only |
| `tests/committedStoreHydration.test.ts` loadOutbox after rebase | **Fail** outbox asserts | Draft hydration still matters |
| `tests/projectForwardRebase.test.ts` | **Keep** (planner is draft-shared) | **Yes**: remint + ordered envelopes |
| `tests/projectDurabilityRebase.test.ts` | **Keep** | **Yes**: StalePromote draft rebase |
| `tests/cubicellStoreDurabilityRecovery.test.ts` | **Keep** | **Yes**: recovery |
| `tests/cubicellStoreDurabilityRetry.test.ts` | **Keep** | **Yes**: retry |
| `tests/indexedDbFailureValidation.test.ts` decodeStoredOutbox | **Fail / delete** | Outbox row validation only |
| `tests/projectRecordCodecs.test.ts` outbox-commit codec | **Keep** (rename later) | **Yes** if drafts still use that record kind |
| `tests/projectStorageFixtures.ts` outbox in fixtures | **Shrink** | Fixture plumbing |
| `tests/projectStorageBrowserDriver.ts` outbox fixture fields | **Shrink** | Promote path still needs fixtures |
| `tests/browserRuntimeRetention.test.ts` installCommitted stub | **Shrink** | Retention of runtime, not outbox |
| `tests/committedStorePersistence.test.ts` outboxSequence | **Adjust** | Promote success still matters |
| `tests/indexedDbSchema.test.ts` version 8 | **Update** on wire bump | Wire version pin |
| `tests/poseRevision*` / save recovery pose tests | **Keep** | **Yes**: pose store |
| `tests/cubicellStorePersistence.test.ts` | **Keep** (if not outbox-only cases) | **Yes**: main durability |

### Silent-guard risk after cut

| Invariant | Current only guard | Risk |
|-----------|-------------------|------|
| Outbox rows discarded after remote install | install/outbox rebase browser tests | Acceptable loss if feature removed |
| Outbox sequence monotonicity | projectStorageContract | Acceptable |
| Draft forward rebase after StalePromote | `projectDurabilityRebase.test.ts` + cubicell durability recovery | **Must keep** |
| Pending draft envelope codec integrity | outbox-commit codec tests | **Must keep** (despite name) |
| Pose revision content-address conflict | poseRevisionIntegrity + promoteContract | **Must keep** |
| Hydration never loads outbox store | implicit (`outbox: []` hardcode) + contract assert “outbox excluded from committed hydration” | After cut, invariant is vacuously true; no silent loss |

---

## 5. HIDDEN COUPLING

1. **Name lie:** `OutboxCommit*` and `recordKind: "outbox-commit"` are the **pending draft operation envelope codec**, not outbox-store-only. Deleting “outbox codec” breaks drafts.

2. **Barrel export:** `src/persistence/recordCodecs/index.ts` and `src/persistence/index.ts` re-export the codec broadly. Many imports look like “persistence surface” without saying outbox store.

3. **Promote always allocates outbox payload:** `prepareStorageCommit` builds `PreparedStorageCommit.outbox` for every authored promote even though hydration never reads the store.

4. **Fingerprint couples digest to outbox bytes:** `storageFingerprint` includes `commit.outbox?.bytes`. Removing the field changes digests / idempotent promote identity for new commits (acceptable with wire bump; do not half-remove).

5. **Dual-source class:** `ProjectDurabilityForwardRebase` mixes draft and outbox. Surgical cut is the `source === "outbox"` branch + installCommitted, not the file.

6. **Receipt field name:** `outboxSequence` is the promote receipt counter derived from outbox autoincrement; survives conceptually as a sequence even if store dies.

7. **Install writeKind:** `writeKind: "install"` skips draft head validation and outbox-source draft consumption; exists for remote install, not local edit.

8. **Docs (non-code but shape assertions):** `STORAGE.md`, `MODEL.v2.md`, `PERFORMANCE.md`, `STUDIO.PROJECT.md` describe outbox as live multi-client path. Not executable consumers; will mislead after cut.

9. **Domain `PoseRevision` vs store `poseRevisions`:** easy false-positive blast radius. Domain type is authoring core; store is content-addressed pose blob table. Neither is the outbox.

10. **Fixtures assert serialized shapes:** `tests/projectStorageFixtures.ts`, `projectRecordCodecs.test.ts`, `recordCodecMetrics.ts` bake outbox arrays into record sets.

11. **No domain barrel export of durability:** `src/domain/index.ts` exports `PoseRevision` only; durability stays under state/persistence. Low cross-domain export trap.

---

## 6. VERDICT

**`cut with 6 traps`** for **outbox store + installCommitted + outbox-source forward rebase** only:

1. **Trap:** `OutboxCommit*` codec is shared with live drafts (do not delete codec; rename later optional).
2. **Trap:** `ProjectDurabilityForwardRebase` draft source is load-bearing (keep class; drop outbox branch).
3. **Trap:** promote preparation + fingerprint still emit/digest outbox payload fields until prepared commit shape is slimmed.
4. **Trap:** `outboxSequence` + fixture/test sequence assertions.
5. **Trap:** wire version must bump (`indexedDbProjectStorageVersion` + store list recreate).
6. **Trap:** install/`writeKind: "install"` + `ProjectStorageRebase` outbox arm + runtime `installCommitted` surface form a dead multi-client seam that tests still treat as product.

**Not** `clean cut`: too many shared names and dual-use types.

**Not** `not separable` for the outbox store itself: production never reads it; writes are pure waste under single-user directives.

**Would become `not separable` if “forward-rebase path” means the entire `ProjectDurabilityForwardRebase` / `projectForwardRebase` module:** draft rebase and pending hydration depend on it.

### Recommended cut shape (for other seats; not executing)

- Drop store `"outbox"`, port load/discard, installCommitted API, outbox-source sync branch, prepared `outbox` field, always-empty hydration outbox arrays.
- Keep draft pending, `encodeOutboxCommitRecord` (rename optional), draft-source forward rebase, poseRevisions, full ProjectDurability save path.
- Wire bump to 9 (owner: no migration).

---

## Counts (for bus reply)

- Production consumer symbols in table sections 1A–1F (rows): **~95** (many live durability; **~25** outbox-store-specific / dead-install).
- Test consumer files primarily tied to outbox/install/outbox-rebase: **~12**; durability/draft/pose tests that must remain: **~15+**.
- Traps: **6**.
- Verdict: **cut with traps**.
