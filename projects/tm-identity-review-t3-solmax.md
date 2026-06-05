# PR #331 T3 identity review

Reviewed `98870fac1dd21c47752b2115aeafdcae7e938954..ed095f456d42b32994e48e72690ce607e5971066`
read only. The source worktree was pristine at review start.

## Four answers

1. **Exact precedence: NO.** The main rank is encoded in
   `canvasIdentityOwner.ts:initializeFromLaunch` and
   `actingContext.ts:reduceActingContext`: an acting selection is sticky, URL
   precedes locator, and workdir resolution is last. Exact compliance fails at
   `canvasIdentityOwner.ts:candidateFromLaunch`,
   `canvasIdentityOwner.ts:verifiedSpawnTarget`, and
   `workdirRows.ts:buildWorktreeRows`. An intentional Space only URL is treated
   as an incomplete acting claim, a failed Canvas metadata read substitutes the
   anchor Worktree as the spawn default, and an inactive inventory Worktree can
   be installed as trusted acting context. No meta field filling or cross source
   field merging was found.

2. **Failure atomicity: NO.** The primary typed verification failure in
   `canvasIdentityOwner.ts:verifyClaim` preserves the URL and Canvas cache
   entries. The complete boot path is not atomic. A failure in
   `canvasIdentityOwner.ts:verifiedSpawnTarget` installs a substituted spawn
   target, while `SessionCanvasRoute.tsx:SessionCanvasRoute` can prune a
   remembered run before the verified Canvas cache is rehydrated. The restored
   pane then starts a replacement run through
   `useCapturedRunBinding.ts:useCapturedRunBinding`.

3. **Required red before green scenarios: YES.**
   `SessionCanvasRoute.identity.test.tsx:SessionCanvasRoute acting context authority`
   contains all six tests covering the four requested scenario groups. With
   only the head test and support file transplanted onto the exact parent, all
   six failed. All six pass at the exact head. Scenario (a) asserts the complete
   props supplied to a mocked `CapturedRunPane`; it does not perform the
   original live capture POST.

4. **CMDK and MCP director: NO.** Both ultimately reach the Python capture
   resolution boundary, and the MCP service path remains unchanged. The CMDK
   Canvas path is incorrect at `registry.tsx:capturedRunLaunchContext`: it
   replaces the receipt's Canvas anchor Worktree with the pane spawn Worktree.
   `launch_resolution.py:resolve_run_canvas` rejects that tuple with
   `canvas_worktree_mismatch`. Full receipt propagation for MCP service launches
   is explicitly deferred by the build plan, so the two clients also retain
   distinct input shapes in this slice.

## Verdict

**1 blocker, 3 majors, 3 minors. Do not merge at this head.**

## Findings

### Blocker 1: the required Chromium gate regressed

**Location:** `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:SessionCanvasRoute`

**Observation:** The route now dispatches the raw, unverified URL launch. That
correctly makes the owner call the new acting context verifier, but the existing
browser fixtures still mock only metadata, inventory, sessions, and run
surfaces. Most do not serve `/v1/spaces/acting-context/verify` or the follow up
Canvas read.

**Impact:** PR #331 currently has a failed required `frontend e2e` check: 13
failed and 10 passed. Persisted panes do not rehydrate, so Canvas drag,
persistence, vitals, desktop keybinding, and spawn palette tests all fail.

**Basis:** On an isolated port, the unchanged
`canvas-drop-ux.spec.ts:33` test passed at the exact parent and failed at the
head because `drop-ux-report.txt` never reappeared. GitHub Actions shows the
same missing panes across the full Chromium job.

**Caveat:** The production server implements the verifier. This proves a
browser harness integration regression and a red required gate. It does not by
itself prove that a running desktop with its real API fails.

**KISS repair:** Add one shared browser identity authority fixture that serves
verification and Canvas metadata, then use it from every Canvas E2E spec.
Avoid copying the two new route mocks into each file.

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L117-L125

### Major 1: per pane Worktree pins corrupt the Canvas anchor tuple

**Location:** `www/packages/canvas/src/viewers/registry.tsx:capturedRunLaunchContext`

**Observation:** `withWorktree(receipt, worktreeId)` replaces
`ActingContextReceipt.worktreeId`. That receipt field identifies the Worktree
which anchors the Canvas. The pane field identifies the target checkout for
the run. They are allowed to differ.

**Impact:** For Canvas C anchored to Worktree A with default or pinned Worktree
B, CMDK sends `{space: S, worktree: B, canvas: C}`. The backend verifies that
C is anchored to B, finds A, and returns HTTP 409
`canvas_worktree_mismatch`. The captured run never starts.

**Basis:** The new registry test deliberately constructs anchor A and pane
Worktree B, then asserts only the frontend object. The existing backend
regression confirms the resulting tuple is rejected before capture
preparation.

**Caveat:** The older registry also spliced the pane Worktree beside the Canvas
ID. The underlying endpoint mismatch therefore predates this commit. It
remains an in scope T3 acceptance failure because this PR introduces the
receipt constructor, explicitly separates anchor from spawn default, and
claims the complete launch path.

**KISS repair:** Keep the verified receipt unchanged. Carry
`targetWorktreeId` beside it through the capture request. Validate the receipt's
anchor and resolve the target checkout as separate facts.

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/viewers/registry.tsx#L160-L164

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/api/src/transport_matters/api/v1/launch_resolution.py#L95-L106

### Major 2: a failed or stale Canvas lookup still installs the claim

**Location:** `www/packages/canvas/src/model/canvasIdentityOwner.ts:verifiedSpawnTarget`

**Observation:** Acting context verification and Canvas default lookup are two
requests. After verification succeeds, an anchor mismatch returns `null` and
any exception returns the receipt anchor. `verifyClaim` installs the receipt in
both cases without surfacing an error.

**Impact:** A transient 503, malformed response, deletion, or reanchoring
between the requests can activate stale Canvas C. The catch silently changes a
default of B, or an intentional `null` default, into anchor A. The next CMDK
launch targets the wrong checkout or becomes launchable when the Canvas was
intentionally unrooted.

**Basis:** The first new reload test supplies no valid Canvas response for its
root Canvas. Its generic mock returns an object with no `canvas` field, which
throws and exercises this fallback. The test therefore locks in the unsafe
substitution. The build plan requires semantic staleness to fail visibly and
prohibits fallback substitution.

**Caveat:** This path requires a second request failure or a row change after a
successful verification snapshot.

**KISS repair:** Return the Canvas spawn default alongside the receipt from the
same read snapshot. Until that contract exists, fail closed on fetch,
shape, or anchor mismatch. Never substitute the anchor as a default.

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/model/canvasIdentityOwner.ts#L250-L261

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/model/canvasIdentityOwner.ts#L352-L367

### Major 3: startup reconciliation can restore a pruned pane as a new run

**Location:** `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:SessionCanvasRoute`

**Observation:** Captured run reconciliation starts independently of the
asynchronous identity verification and per Canvas cache rehydrate. If the
remembered run is no longer attachable, reconciliation removes its global run
record and asks the currently blank Canvas store to remove the pane. The pane
exists only in the target Canvas cache at that moment, so the pane removal does
nothing. Later verification rehydrates that stale pane.

**Impact:** Once reconciliation releases rendering,
`useCapturedRunBinding` sees the pane but no run record and calls `ensureRun`.
A reload can therefore replace a deliberately pruned terminal with a new
agent run.

**Basis:** Deterministic sequence: persist a run record globally and its pane
only in C's cache; hold URL verification; return `EXITED` from the run lookup;
let reconciliation prune; resolve verification. The code path restores the
pane after its binding was removed. Existing reconciliation tests seed panes
in memory, while identity reload tests seed cache without a remembered run, so
the two startup paths are never composed.

**Caveat:** This finding is established by the state and effect ordering. No
new focused automated reproduction was written during this read only review.

**KISS repair:** Expose identity and cache hydration readiness, and start
reconciliation only after the target Canvas is active and rehydrated. Add one
composed regression with a cached pane and remembered exited run.

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L117-L155

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/infrastructure/runtime/useCapturedRunBinding.ts#L40-L58

### Minor 1: a Space only URL reload loses the selected browse scope

**Location:** `www/packages/canvas/src/model/canvasIdentityOwner.ts:candidateFromLaunch`

**Observation:** `selectSpace` deliberately writes
`/canvas?space_id=S` and clears acting context. On reload,
`candidateFromLaunch` treats the one field as an acting candidate. Verification
returns `canvas_affinity_required`; the failure path does not restore
`navigationSpaceId`.

**Impact:** Reloading an intentional Space selection shows an acting context
error and CMDK loses the selected Space browse scope.

**Basis:** The URL writer and the boot decoder disagree about the same supported
route. The plan separates `navigationSpaceId` from acting identity and limits
URL verification to a scoped whole tuple.

**Caveat:** No acting identity is incorrectly launched. The user can recover by
selecting the Space again.

**KISS repair:** Decode a Space only URL into navigation scope. Reserve acting
verification for a complete triple, and do not let workdir context replace the
explicit browse scope.

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/model/canvasIdentityOwner.ts#L338-L351

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/model/canvasIdentityOwner.ts#L368-L379

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/space-client/src/urlTupleCodec.ts#L96-L107

### Minor 2: CMDK locally trusts inactive inventory Worktrees

**Location:** `www/packages/canvas/src/launcher/workdirRows.ts:buildWorktreeRows`

**Observation:** A Worktree row is enabled whenever `missing === false`.
`lifecycleState` is ignored. Selecting the row synchronously constructs a
trusted receipt in `canvasIdentityOwner.ts:dispatchIdentityCommand`.

**Impact:** During a `creating` or `deleting` transition, CMDK can mark the row
acting even though `SpaceContextService` and the Python launch resolver return
`worktree_unavailable`.

**Basis:** Inventory includes lifecycle state. The shared verifier accepts only
`active`, and the plan classifies inactive Worktrees as semantically stale.

**Caveat:** This behavior existed before the head and is limited to lifecycle
transition windows. It remains relevant because T3 now declares inventory
selection locally verified.

**KISS repair:** Make the row actionable only when `missing === false` and
`lifecycleState === "active"`. Pin the same transition state in the row and
owner tests.

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/launcher/workdirRows.ts#L186-L202

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/model/canvasIdentityOwner.ts#L164-L183

### Minor 3: touched test files violate the hard 700 line threshold

**Locations:**

- `www/packages/canvas/src/launcher/commandRows.test.ts`, 743 lines at parent,
  744 at head.
- `www/packages/canvas/src/workbench/SessionCanvasRoute.activity.test.tsx`,
  674 lines at parent, 712 at head.

**Observation:** The repository instructions prohibit adding to an existing
file over 700 lines and prohibit new growth past 700. Both files were changed
without the required split.

**Impact:** The change violates a hard repository convention and keeps
unrelated command, activity, MCP, and identity scenarios in oversized suites.

**Basis:** The supplied `AGENTS.md` says these thresholds have no exceptions.

**Caveat:** This is a maintainability failure, not a runtime defect.

**KISS repair:** Move the new identity related command assertion and the new MCP
close or identity activity scenarios into focused sibling suites. Preserve the
existing shared test support.

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/launcher/commandRows.test.ts#L396-L404

https://github.com/littleorgans/transport-matters/blob/ed095f456d42b32994e48e72690ce607e5971066/www/packages/canvas/src/workbench/SessionCanvasRoute.activity.test.tsx#L635-L644

## Required regression proof

| Scenario group | Exact parent with head test transplanted | Exact head |
| --- | --- | --- |
| Scoped URL reload, cache restore, CMDK launch props | Failed, identity remained null | Passed |
| Frozen meta A, explicit selection and persistence B | Failed, B never became acting | Passed |
| Child Canvas reload without root substitution | Failed, child identity remained null | Passed |
| Stale meta, late boot result, failed verification atomicity | All three failed | All three passed |

Commands and observed results:

- Head:
  `pnpm --filter @tm/shell exec vitest run ../canvas/src/workbench/SessionCanvasRoute.identity.test.tsx ../space-client/src/actingContext.test.ts ../space-client/src/spaceTransport.test.ts`
  produced 3 passed files and 26 passed tests.
- Parent with only the head identity test and support file:
  `pnpm --filter @tm/shell exec vitest run ../canvas/src/workbench/SessionCanvasRoute.identity.test.tsx`
  produced 1 failed file and all 6 tests failed.
- Exact parent browser probe on an isolated port:
  `canvas-drop-ux.spec.ts:33` passed, 1 test.
- Exact head GitHub Chromium job: 13 failed and 10 passed.
- Frontend tuple unit proof:
  `pnpm --filter @tm/shell exec vitest run ../canvas/src/viewers/registry.test.ts`
  passed 4 tests and confirms the frontend emits the overwritten Worktree.
- Backend tuple rejection proof:
  `test_prepare_rejects_canvas_from_another_worktree` passed and confirms that
  the backend returns 409 before capture preparation.

The shell Vitest suite was also observed green at 175 files and 1,322 tests.
The full repository `just check && just test` gate and the requested live
desktop A/B browser probe were not rerun in this review. GitHub currently has
eight successful checks and one failed `frontend e2e` check.

## Boundary and invariant review

- Exact head remained
  `ed095f456d42b32994e48e72690ce607e5971066`; base and parent remained
  `98870fac1dd21c47752b2115aeafdcae7e938954`.
- `canvasIdentityBoundary.test.tsx` is byte identical at parent and head.
  Identity is absent from `CanvasStoreState`; the private owner remains the
  sole identity writer.
- The T2 boundary contains 13 `@ts-expect-error` pins at both SHAs, rather than
  the ten named in the brief. Removing them produced the same 13 diagnostics at
  parent and head, one diagnostic per pin. `@tm/canvas` and
  `@tm/space-client` typechecks passed.
- `CANVAS_STORE_STORAGE_VERSION` remains `1`. Canvas persistence files and the
  persisted blob shape are unchanged. Acting identity was not added to the
  Canvas blob.
- `SpaceContextService` verification remains read only and uses one repeatable
  read snapshot. The repository performs `SELECT` queries only. No seeding or
  create on resolve path was found.
- Verification checks ownership, whole tuple affinity, and Worktree lifecycle.
  It deliberately does not use checkout presence, matching the requested
  narrow verification boundary.
- Locator persistence is deferred to T4. T3 contains the locator ordering seam,
  but its failure test uses an arbitrary `sessionStorage` probe rather than a
  production locator entry.
- Reflection escapes were outside this review scope, as directed.
- `git diff --check` passed. The source worktree remained pristine.
