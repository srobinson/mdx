# S3 CMDK Review

## Boundary

- Branch: `ml/s3-cmdk`
- Reviewed range: `97a80f56f1630d34b6629b50b5b24ab242e2711b..8e240663c83c80492f1fb3a1d0158fb63d23777b`
- Reviewed HEAD: `8e240663c83c80492f1fb3a1d0158fb63d23777b`
- Direct parent: `97a80f56f1630d34b6629b50b5b24ab242e2711b`
- Changed surface: 21 Canvas frontend files, 899 insertions, 157 deletions
- Review mode: read only repository inspection. No gates were run, as required by the brief.

## Verdict

`CHANGES_REQUESTED`

- Blockers: 0
- Majors: 2
- Minors: 2
- Builder trust: `MEDIUM`
- Review confidence: `HIGH` for the inspected source and test control flow

## Findings

### Major 1: Mutation safety decisions trust stale inventory and an unvalidated active Space

**Location**

- `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts::deleteExistingSpace`, lines 69 to 80
- `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts::createWorkdirWithBootstrap`, lines 83 to 107
- `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts::currentInventory`, lines 110 to 112
- `www/packages/canvas/src/launcher/useSpaces.ts::useSpaces`, lines 36 to 52

**Observation**

`currentInventory` returns any cached `["spaces"]` response without checking freshness. `createWorkdirWithBootstrap` also gives `useCanvasStore.spaceId` precedence without confirming that the ID exists in that inventory. Both delete safety and bootstrap routing therefore depend on client state that REST or MCP mutations can invalidate.

**Impact**

1. Start with cached Spaces A and B. Another REST or MCP client deletes A. The old palette still exposes `Delete B`; `deleteExistingSpace` sees two cached items and sends the delete for B. The backend intentionally permits zero Spaces, so the CMDK last Space guard is bypassed.
2. Start with active Space A. Another client deletes A and the inventory becomes empty or contains a different sole Space. `createWorkdirWithBootstrap` still uses the stale active A, sends `createWorkdir` to a missing Space, and never executes the required zero Space bootstrap or sole Space fallback.

The cache has a 30 second `staleTime`, and there is no Space mutation event that reconciles active store identity with external REST or MCP changes.

**Required correction**

Resolve mutation authority from a fresh owner inventory. Validate any explicit or active Space ID against that result before using it. With zero current Spaces, create a Space before the Workdir. With one current Space and no valid selection, use that Space. Recheck the fresh count before CMDK delete. Keep the backend zero Space contract unchanged.

Add regressions for an empty inventory with a stale active Space, a different sole inventory Space with a stale active Space, and a stale two Space cache whose current server inventory contains one Space. Assert the request target and final active state.

### Major 2: A failed second bootstrap step leaves a hidden Space and retry creates duplicates

**Location**

- `www/packages/canvas/src/workbench/spaceCommandDispatcher.ts::createWorkdirWithBootstrap`, lines 83 to 107
- `www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts::useCanvasCommandHandler`, lines 85 to 97
- `www/packages/canvas/src/workbench/CanvasCommandDispatcher.test.tsx`, lines 64 to 99

**Observation**

For zero inventory, Space creation completes at lines 94 to 97. Space activation and query invalidation occur only after `createWorkdir` succeeds. If the Workdir request rejects, the outer handler only logs the error. The created Space remains durable while the active store and cached inventory still describe zero Spaces.

**Impact**

The new valid empty Space is undisclosed to this client. An immediate retry reads the unchanged empty cache and creates another Space before retrying the Workdir, producing duplicate empty Spaces. The happy path test proves request order and root Canvas activation but does not cover failure after the first successful mutation.

**Required correction**

Define and implement the partial bootstrap policy. Either compensate by deleting the newly created Space when Workdir creation fails, or activate and refresh the created empty Space so the next attempt reuses it. Ensure query reconciliation runs on this failure path. Add an observable regression that rejects the Workdir request after successful Space creation and proves the resulting inventory, active Space, request sequence, and retry behavior.

### Minor 1: The named first step failure boundary has no regression

**Location**

- `www/packages/canvas/src/workbench/CanvasCommandDispatcher.test.tsx::composes createSpace then createWorkdir from a zero Space inventory`, lines 64 to 99

**Observation**

The suite covers only successful bootstrap. It does not reject the Space creation request and assert that no Workdir request occurs and no active identity changes.

**Impact**

The source currently awaits `createSpace`, so this boundary is correct today. The explicit failure contract lacks a red first regression and can regress without a focused signal.

**Required correction**

Add a failed `POST /v1/spaces` case that asserts one request, no Workdir request, unchanged active state, and an observable failure outcome.

### Minor 2: The Workdir row comment describes a removed Space row behavior

**Location**

- `www/packages/canvas/src/launcher/workdirRows.ts::worktreeRowActions`, lines 11 to 16

**Observation**

The comment says the dual gesture is shared by the single Worktree Space row and Worktree sub scope rows. Space rows now execute `select-space` and advance into the Worktree sub scope. Only Worktree sub scope rows call `worktreeRowActions`.

**Impact**

Future changes can rely on a gesture contract that no longer exists.

**Required correction**

Update the comment to describe the remaining Worktree sub scope behavior.

## Confirmed behavior

- `useSpaces` preserves the sole Space and returns full paged inventory, count, server disclosure state, fetch status, and refetch.
- `Create new space` and `Create new Workdir` are present during empty, single, loading, error, and multiple Space states.
- Space list, switch, rename, and delete rows require both a count greater than one and disclosed switcher state.
- Last Space prevention exists only in the frontend dispatcher. This range does not add a backend zero Space prohibition.
- Zero Space happy path awaits `createSpace`, then calls `createWorkdir` with the returned Space ID.
- A rejected `createSpace` naturally short circuits before `createWorkdir`.
- Direct Space selection updates the URL and `useCanvasStore.spaceId`, clears Canvas and Worktree identity, and supports an empty Space without Canvas tuple verification.
- Existing Canvas list construction and `select-canvas` dispatch remain unchanged.
- The rendered Command Center tests assert row presence and absence plus the reopened current Space indicator. Dispatcher tests assert bootstrap request order and the direct last delete guard.
- All 21 changed files remain below the 700 line limit.

## Builder trust

`MEDIUM`

The implementation uses the shared `@tm/core` transports, keeps the sole Space in query state, extracts focused mutation logic, preserves Canvas switching, and adds rendered palette coverage that avoids the prior mapping only test weakness. The mutation paths still treat cached inventory as safety authority and leave second step bootstrap failure unreconciled. The one commit range contains tests and implementation together, so repository history does not establish red first sequencing.
