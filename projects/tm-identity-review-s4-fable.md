# S4 review — PR #328 (shadow acting-context aggregate and dual-write bridge)

Reviewer: Fable (plan author seat). Head `be26765b`, base `feat/multi-launch`, 30 files, +1271/−115. Citations are file:symbol.

## Verdict summary

Blockers: 0. Majors: 1. Minors: 3.
Section 6 partition: **complete**. Drift verdict: the `ActingContextResult` move is **legitimate DRY, not scope creep**. Reload→launch bug: **still broken, as required**.

## Section 6 partition audit

Method: every row of the plan's §6 consumer table was placed against the diff plus a live grep of remaining direct identity reads (`useCanvasStore` selectors of `spaceId`/`canvasId`/`defaultWorktreeId`) at the PR head.

Migrated in S4 (3 groups, matching the builder's claim):
- `CommandCenter.tsx:CommandCenter` / `useCommandCenter.ts` / `useLauncherData.ts:useLauncherData` — `actingContextStore` selectors; browse scope from `navigationSpaceId`. Matches the table's "S4 readers" row.
- `canvasActions.ts:addCapturedRun` / `spawnTerminal` / `continueSession` via `actingContextStore:getActingWorktreeId`, with `worktreeDefaults.ts:requireWorktreeId` and its throw unchanged. Matches "S4 readers, S5".
- `CanvasWorkbench.tsx:CanvasWorkbench` reads `selectActingContextReceipt`; `CanvasPaneLayer.tsx` and `paneRecords.ts:ViewerCanvasContext` receive identity only as props/context threaded from CanvasWorkbench (verified: no direct store identity read in either), so the single migration point genuinely covers the whole table row.

Deferred (5 groups, each with the plan's own slice column agreeing):
- `SessionCanvasRoute.tsx` boot precedence → S5 (route-boot-precedence). Its store identity selectors are the only remaining direct reader greps, and they belong to exactly this deferred group.
- `canvasStoreLifecycle.ts:initializeCanvas` / `selectSpace` / `getActiveCanvasId` mirror → S5/S6.
- `viewers/registry.tsx` captured-run registration → S5 (its `canvas.spaceId` input now arrives via the receipt-fed props, behaviour-identical modulo the Major below).
- `CapturedRunPane` → `useCapturedRunBinding` → `capturedRunStore` binding chain → S5.
- `canvasCacheStorage.ts:createCanvasCacheStorage` keying → S5.

Rows in neither bucket, each accounted for: the `CanvasCommandDispatcher.ts` row is the S4 **write bridge**, not a reader, and is done (`selectActingContext`, `clearActingContextForNavigation` wired into `select-canvas`, `activateWorktree`, `activateSpace`); the grammar row (`commandRows.ts`/`commandTypes.ts` gained `anchorWorktreeId`, `workdirRows.ts:worktreeRowActions` already carries the whole triple); `useSpaces`/`useCanvases` shipped in S3; persistence rows are "never"; MCP/runtime rows are S7; Python and inspector rows are "none". **No consumer is silently absent from both buckets.**

Deferral legitimacy: all five deferrals cite the same slice the plan itself assigns them; none is deferred-because-hard. The one consumer migrated *early* is noted as Minor 2.

## MAJOR 1 — receipt-only CommandCenter read drops the seeded worktree in incomplete-tuple states (unlisted divergence)

`CommandCenter.tsx:CommandCenter` computes `activeWorktreeId` as `actingContext?.worktreeId ?? null`, i.e. receipt-or-nothing. `domain/actingContext.ts:projectActingContextReceipt` is all-or-nothing, and `urlTupleCodec.ts:defaultCanvasId` gates the store `canvasId` on `canvasIdVerified`. So in both designed-for incomplete states —
1. desktop default launch: URL tuple empty, `SessionCanvasRoute.tsx` meta-seed effect calls `adoptDefaultWorktree(meta.spaceId, meta.worktreeId)` while `canvasId` stays null;
2. the scoped-unverified reload state (the exact state this whole plan exists for): URL carries `worktree_id` but the canvas is unverified, so `canvasId` is null;

— legacy fed `defaultWorktreeId` (non-null) into `useCommandCenter`, which `workdirRows.ts:worktreeRowActions` renders as the "Current" marker on the workdir row. The receipt is null there, so the marker disappears. Observable reader behaviour change in the product's default state, and it is **not** in `actingContextStore.test.ts:EXPECTED_MISMATCH_LEDGER`, whose only entries are meta-vs-selection and child-canvas. This violates S4's behaviour-identical constraint for migrated readers.

The builder already built the correct compat path for exactly this state — `actingContextStore.ts:getActingWorktreeId` falls back to `projectedWorktreeId`, which is why `spawnTerminal`/`continueSession` stay behaviour-identical — but did not give CommandCenter the same fallback. The asymmetry is the tell that this is an oversight, not an intended ledger entry.

Fix in-slice: export a `selectActingWorktreeId` selector (`state.receipt?.worktreeId ?? state.projectedWorktreeId`) beside `selectActingContextReceipt`, use it for CommandCenter's `activeWorktreeId`, and pin with a test that seeds a worktree via `adoptDefaultWorktree` with a null `canvasId` and asserts the workdir row still shows "Current".

## Minors (fix in-slice)

1. **Duplicated test builders.** `receipt(seed)` and `candidate(value)` are copied verbatim between `space-client/src/actingContextStore.test.ts` and `space-client/src/domain/actingContext.test.ts`. Hoist to a shared testSupport module (or `@tm/contract/space/testing` if it fits its charter).
2. **Early consumer migration.** `CanvasCommandDispatcher.ts:useCanvasCommandHandler` now feeds `dispatchSpaceMutation` with `getNavigationSpaceId` instead of the legacy store `spaceId`. The §6 table schedules that consumer for S3/S5, and this is a *writer input* (create-workdir target Space). It is behaviour-identical today because every legacy write path synchronously re-mirrors `navigationSpaceId` (verified: `initializeCanvas`, the early-return branch, `adoptDefaultWorktree`, `selectSpace`, and the dispatcher selection arms all converge within the same handler), but it should either be reverted to the legacy read until S5 or pinned with a test asserting nav/legacy equality at mutation time. Same reasoning applies to the `activateSpace` re-select guard now reading `getNavigationSpaceId()`.
3. **Coverage-test blind spot.** `actingContextConsumerCoverage.test.ts` verifies the viewer-context group only via a marker in `CanvasWorkbench.tsx`. The inherited coverage of `CanvasPaneLayer.tsx`/`ViewerCanvasContext` through prop threading is real but unstated; a future direct store read added to CanvasPaneLayer would escape the enumeration silently. Add those files with a negative marker (no `useCanvasStore` identity selector) or a comment naming the prop-threading assumption.

## Constraint checks demanded by the brief

- **Legacy authoritative everywhere:** yes. Readers consume `receipt`, which is written only by `mirrorLegacyActingContext`/`clearActingContextForNavigation` from legacy state at every legacy write site (grep-verified: all production writers of `defaultWorktreeId`/`spaceId`/`canvasId` sync). `selectActingContext` writes only the shadow `context` and `navigationSpaceId`, never `receipt`.
- **Projection mirrors legacy, no subtle improvement:** yes except MAJOR 1. Notably the sticky-selection improvement lives only in the shadow `context`; `getActingContextReceipt()` stays null/legacy in the dispatcher test, correct for S4.
- **Nothing acts on a verification result:** confirmed. `verifyActingContextClaim` → `recordVerification` writes only `lastVerification`/`discardedVerificationCount`; no production code reads either; the reducer's `verification` promotion is exercised only in domain tests; the successful-verify store test pins phase `claimed` afterwards.
- **Expected-mismatch ledger:** both intended divergences present with stated reasons; detectors for late response (generation discard) and field divergence (injected-divergence tests in `canvasStore.test.ts` and `CommandCenter.spaces.test.tsx`) exist. MAJOR 1 is the one unlisted divergence.
- **Behaviour tell:** the reload→launch failure is untouched — `defaultCanvasId` still gates on `canvasIdVerified`, `resolveCanvasLaunchIdentity`/`isUsableIdentity` unchanged, verification recorded only. S4 does not fix S5's bug.
- **Drift:** moving `ActingContextResult` into `@tm/contract/space` (with a type re-export from `@tm/space`) is correct by the plan's own §2 test — both planes need the shape and browsers may not import `@tm/space` — and it deletes what would otherwise be a second declaration. Legitimate DRY.

## Quality notes

Reducer (`domain/actingContext.ts:resolveActingContext`) is clean: single guard ladder, generation monotonicity, no `acting`→`claimed` demotion, URL-over-locator ordering, corpus-driven parity test over the shared fixtures. Formatting churn in `canvasActions.ts`/`CanvasWorkbench.tsx` is repo-formatter output, ignorable. Gate evidence in the PR body (`just check`, `just test`) is the repo recipe verbatim; the authoritative pre-merge run stays with the gate seat.
