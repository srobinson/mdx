# T3 review — acting context authority flip (PR #331, `ed095f45`)

Reviewer: opus (logic and state). Base `feat/multi-launch`, head `ed095f45`,
parent `98870fac`, +1330/-297 across 31 files. Read-only review; every empirical
claim below was produced in a throwaway git worktree at `ed095f45` with its own
`pnpm install`, never in the shared tree. The worktree has been removed; the two
probe files are preserved at
`…/scratchpad/t3-probe-1.test.tsx` and `t3-probe-2.test.tsx` (drop either into
`www/packages/canvas/src/workbench/` to re-run).

**Counts: 2 blockers, 5 majors, 9 minors.**

**Does any failure path lose user data? No.** Probed directly: on a failed
verification the URL, both per-canvas cache blobs, and `sessionStorage` are
byte-identical to their pre-boot values, and a later worktree switch brings every
pane back. The claim is discarded, the panes are not. What *is* lost on failure
paths is the ability to see or use them, which is what the two blockers are about.

---

## Blocker 1 — a verified reload can still not launch, when the Canvas's default worktree is NULL

`canvasIdentityOwner.ts:verifiedSpawnTarget` sets the spawn target from
`fetchCanvas(receipt.canvasId).defaultWorktreeId`, which is nullable. Every
launch path (`canvasActions.ts:addCapturedRun` / `spawnTerminal` /
`continueSession`) now reads `getSpawnWorktreeId()` and runs it through
`worktreeDefaults.ts:requireWorktreeId`, so a null default throws
`Cannot spawn a captured run without a rooted worktree`.

`default_worktree_id` is null for a large, ordinary class of canvases:
`space/store_canvas_ops.py:create_canvas` defaults it to `None` (only
`store_worktree_ops.py:ensure_worktree_root` seeds it, for worktree roots), and
both `store_worktree_ops.py` and `store_space_ops.py` actively `SET
default_worktree_id = NULL` when the referenced worktree or space membership goes
away. So: any user-created child Canvas, and any Canvas whose default worktree
was later deleted.

Failure scenario, probed and confirmed (`t3-probe-1.test.tsx`, PROBE 1):
reload a scoped URL for a child Canvas whose `defaultWorktreeId` is null →
verification succeeds → `readCanvasIdentityForTests().canvasId` is correct, the
persisted panes are restored → `addCapturedRun("claude")` **throws**. PROBE 1b is
the same test with a non-null `defaultWorktreeId` and it launches, which isolates
the cause to this one line. This is the evidence doc's symptom (`panes back,
cannot launch`) reproduced after the fix, in a different message.

The slice's own child-Canvas test is the one that should have caught it:
`SessionCanvasRoute.identity.test.tsx` "reloads a child Canvas without
substituting its Worktree root Canvas" hard-codes `canvasResponse(CHILD_CONTEXT,
null)` and then asserts only that the canvasId is right and the panes exist. It
models the broken case exactly and asks the proxy question (are panes present?)
instead of the user question (can I launch?).

Sharpening the defect: the two `verifiedSpawnTarget` exits are backwards. When
`fetchCanvas` *throws*, the bare `catch` returns `receipt.worktreeId` — a valid,
launchable anchor. When it *succeeds* with a null default, it returns `null` and
the user cannot launch. A network blip leaves the product more usable than a
successful read.

Fix shape (one line): `return canvas.defaultWorktreeId ?? receipt.worktreeId;`,
with the mismatch branch collapsing too — the mismatch it guards
(`canvas.anchorWorktreeId !== receipt.worktreeId`) is exactly what the server
already rejected as `canvas_worktree_mismatch` in
`packages/space/src/domain/actingContext.ts:resolveContextCanvas`, so that arm is
unreachable via a verified receipt. Pin it with PROBE 1 + PROBE 1b.

## Blocker 2 — an unreachable control plane is treated as a stale claim, and empties the canvas

`canvasIdentityOwner.ts:failUnexpectedGeneration` handles everything
`spaceTransport.ts:requestActingContext` rethrows — 503 from T1's degrade, a
network error, a malformed body, any bug — by dropping to
`UNRESOLVED_ACTING_CONTEXT`. Because the cache restore and `persist.rehydrate()`
only ever run from `applyResolution` → `activateCanvas`, an unresolved boot never
rehydrates at all.

Failure scenario, probed and confirmed (PROBE 3): boot a scoped URL with a
populated cache, `/v1/spaces/acting-context/verify` answers 503 →
`useCanvasStore.getState().panes` is empty, the route renders an alert, and the
cache blob in `localStorage` is untouched. The user sees an empty canvas and a
cryptic string; their panes are on disk and invisible.

This conflates two different facts. "The server says your tuple is invalid"
(a domain `failureCode`) justifies discarding the claim — that is the plan's
no-substitution rule and it is implemented correctly in
`failGeneration`. "I could not reach the server" justifies nothing; the claim is
not known to be stale. T1 exists precisely because this surface was unreachable
once already, and `run_proxy.py`-style degrades are a designed, expected state.

Fix shape: on a transport error keep the `claimed` phase (or a distinct
`degraded` phase), retry, and give the alert a Retry affordance like the
`worktreeResolutionFailed` one directly beside it. Do not discard on anything
that is not an `ActingContextFailureCode`. Pin with PROBE 3.

---

## Majors

**M1 — selecting a Space raises a spurious `canvas_affinity_required`.**
`canvasIdentityOwner.ts:candidateFromLaunch` returns a claim when *any* of the
three fields is non-null. `urlTupleCodec.ts:spaceSwitchUrl` deliberately writes a
Space-only URL, and `selectSpace` clears the context, so the very next render
re-parses that URL, claims `{spaceId, null, null}`, and posts it to verify, which
answers `canvas_affinity_required` by construction
(`packages/space/src/domain/actingContext.ts:validateActingContextCandidate`).
Probed and confirmed (PROBE 2): a plain CMDK Space selection puts
`canvas_affinity_required` on screen — the exact string from the evidence doc,
now produced by a healthy path. Plan §4 rule 2 says the URL candidate is
consulted "when scoped", and §7 says whole tuples only; `candidateFromLaunch`
should require a complete tuple (or at minimum treat an intentional Space-only
URL as "no claim").

**M2 — raw failure codes are the user-facing error text.**
`SessionCanvasRoute.tsx` renders `{actingContextError}` directly into
`role="alert"`, so users read `worktree_not_found` / `canvas_affinity_required` /
a transport message. The sibling `worktreeResolutionFailed` branch, three lines
below, is a written sentence with a Retry button. The new test even asserts the
raw code is on screen (`await screen.findByText(/canvas_not_found/)`), which
enshrines it. Map codes to sentences.

**M3 — the activity/vitals workspace fallback was deleted, out of T3's scope.**
`SessionCanvasRoute.tsx:workspaceIdentity` lost its `meta.workspaceId` branch, so
`activityWorkspaceId` is empty unless an acting context exists *and* the worktree
is found in the `/v1/spaces` inventory. Any inventory failure, and every
pre-resolution or failed-resolution state, now means no activity stream: no run
vitals, no status bars, no adoption of MCP-launched runs (the reconciler is
created from `activityWorkspaceId`). The rename of the covering test — "falls
back to meta.workspaceId for the activity stream on a desktop canvas" → "uses
verified workdir inventory" — records the removal without arguing it. Identity
ranking is T3's subject; the workspace id for the activity stream is not part of
the acting triple, and the plan's consumer table does not list this fallback for
removal.

**M4 — one of T2's boundary pins no longer proves anything.**
`canvasIdentityBoundary.test.tsx:pinIdentityWriteErrors` pin 10 reads
`// @ts-expect-error The identity owner does not expose its live state object` /
`Object.assign(ownerModule.getCanvasIdentity(), …)`. T3 deleted
`getCanvasIdentity` from `canvasIdentityOwner.ts`, so the suppressed error is now
`TS2339: Property 'getCanvasIdentity' does not exist` — a missing symbol, not the
copy-on-read protection the comment claims. Verified by stripping every directive
and reading the true errors: 13 pins, 12 unchanged and single-cause (TS2322 /
TS2345 / TS2540 / TS2551), 1 degraded. Worth noting alongside it that the T3
readers *do* hand out the live object: `selectActingReceipt` returns
`context.receipt` itself, where T2's `getCanvasIdentity` returned a fresh
projection. Readonly fields cover the typed path, so this is a pin repair
(retarget it at `getActingContextReceipt`), not a second blocker.

**M5 — the captured-run viewer test moved from the render to a helper.**
`registry.test.ts` previously asserted the props the rendered element passes to
`CapturedRunPane`; it now calls the newly exported
`registry.tsx:capturedRunLaunchContext` directly. The export exists only for the
test, and the branch that actually changed — `CapturedRunViewer` replacing the
pane with "Verified Canvas context is unavailable." when `actingContext` is null
— has no test at all, in a slice where an unresolved context is a reachable
state (blocker 2). That the change forced `resetCanvasStoreForTests(
TEST_VERIFIED_LAUNCH)` into seven `SessionCanvasRoute.test.tsx` cases is the
measure of how reachable it is.

---

## Minors (all in scope, all cheap)

1. `canvasActions.ts:adoptCapturedRun` computes
   `withWorktree(actingContext, worktreeId).worktreeId`, which is exactly
   `worktreeId`. The wire-sourced worktree from
   `capturedRunAdoption.ts:candidateFromWire` enters the pane record unchanged;
   the only real effect is the null-guard throw. Either say that plainly, or make
   the constructor actually validate. As written it reads as mediation and is not.
2. `canvasIdentityOwner.ts:dispatchIdentityCommand` keeps an
   `adopt-default-worktree` arm that silently returns, with no production
   dispatcher left (only `canvasStore.test.ts`). A no-op command in a closed union
   is a landmine; delete the arm and the union member.
3. `CanvasIdentityOwnerState.resolutionError: ActingContextFailureCode | string`
   collapses to `string`; the failure-code half documents an intent the type does
   not carry. Use `ActingContextFailureCode | "transport_error"` or a small union.
4. The 14-line `receipt(seed)` fixture builder is duplicated verbatim in
   `space-client/src/actingContext.test.ts` and
   `SessionCanvasRoute.identity.test.tsx`. §2 of the plan puts shared parity
   fixtures on `@tm/contract/space/testing`, which exists.
5. `adoptCapturedRun`'s new throw lands in `capturedRunAdoption.ts:attempt`'s bare
   `catch`, which spends one of four retry slots per attempt and then goes
   `dormant` until a fresh snapshot. Using an exception as a "not ready" signal
   burns a bounded retry budget; return early, or have the reconciler check
   readiness.
6. A failed claim re-verifies: probed, one boot issues two identical
   `/verify` POSTs (PROBE 6) because failure returns to `unresolved` and the
   `[launch, meta?.cwd]` effect re-fires when meta lands. Harmless today, unbounded
   in principle.
7. `space-client/src/actingContext.ts:reduceActingContext` guards
   `verification-result` with `current.generation !== event.generation` but guards
   `workdir-result` with phase alone. Only the owner's `generationIsCurrent` check
   stops a stale workdir receipt from installing. The reducer is the pure rule; it
   should carry the same guard.
8. `canvasIdentityOwner.ts:ownerStateFromLaunch` (test-support reset) builds an
   `acting` context from any complete tuple, ignoring `canvasIdVerified`, while
   production requires it (`receiptFromVerifiedLaunch`). Tests can start in states
   production cannot reach.
9. `verifiedSpawnTarget`'s bare `catch` swallows programming errors as well as
   network ones — and in this slice it did: the headline reload test passes only
   because `/v1/canvases/…` is unstubbed, `response.canvas` is `undefined`, and
   the resulting `TypeError` is caught. See the note under "Did the tests fail?".

---

## Answers to the brief

**1. Can any failure path cost a pane, a layout, or a cache entry?** No stored
state is lost on any path I could construct. `applyResolution` is the only writer
of the cache-restore primitive, and `installSelection` / `failGeneration` /
`failUnexpectedGeneration` touch neither `localStorage` nor the persist blob;
`activateCanvas` reads the target blob *before* `canvasPort.reset()` and writes it
back after, so a switch cannot wipe the incoming canvas, and it never touches the
outgoing one. Probed on the failure path: URL, both canvas blobs, and
`sessionStorage` unchanged. The costs are functional, not durable: blocker 1
(panes restored, cannot launch) and blocker 2 (panes on disk, canvas renders
empty).

**2. Can the new tests fail?** They are real tests and they pass (6/6), and the
full frontend suite is green at this head (`pnpm --filter @tm/shell test`: 176
files, 1326 tests, in a clean worktree at `ed095f45`). Two problems. First, the
headline reload test passes for the wrong reason: `installIdentityTransport`
never stubs `/v1/canvases/…`, so `fetchCanvas` reads `undefined.canvasId`, throws,
and `verifiedSpawnTarget`'s catch returns the anchor worktree. The assertion
`defaultWorktreeId: CONTEXT_A.worktreeId` is therefore satisfied by an accident of
the mock, and the success path of the function under test is never executed —
which is why blocker 1 survived it. Second, the child-canvas test asks the proxy
question (panes present) on the exact fixture that cannot launch. On red-first:
these live in a new file that cannot compile against the parent commit, so the
directional claim is weak by construction; the assertions themselves are the
evidence, and two of six do not assert what the user does.

**3. Races and ordering.** The generation guard holds. `beginGeneration` /
`installTrustedContext` bump a monotonic counter on the owner (not on the
context, so it correctly survives the reset to `unresolved`), and both awaits in
`verifyClaim` re-check `generationIsCurrent` after resuming; every write between a
check and a `setState` is synchronous, so there is no interleaving window. I could
not defeat it: a late verification after a newer selection is discarded (the
builder's test, and PROBE 5's A→B→A), a second in-flight verification supersedes
the first, and a failed verification cannot resurrect a discarded generation. The
reducer-level gap in minor 7 is defence-in-depth, not a live race.

**4. Worktree switching.** Intact. Probed (PROBE 5): A→B→A restores A's panes,
projects A's identity, and launches. The early return in `installSelection`
compares the whole receipt plus the spawn target, so re-selecting the current
worktree is a genuine no-op rather than the evidence doc's silent dead end.

**5. T2's seam.** `CANVAS_STORE_STORAGE_VERSION` is still 1;
`canvasStore.persistence.ts`, `canvasPersistOptions.ts`, and
`canvasPanePersistence.ts` are untouched by this diff, so nothing new entered the
persist blob. Of the boundary pins, 12 of 13 still fail for their stated single
cause; one degraded (M4). One test was retired rather than weakened —
`canvasStore.test.ts`'s three meta-seeding cases are gone with the mechanism they
described, replaced by a pin that the retired projection cannot make a context
launchable, which is the right assertion for T3.

---

## Disposition

Both blockers are small, local fixes with probes already written. M1 and M2 are
the difference between a boot that reports "I couldn't verify your Canvas" and one
that shows the user `canvas_affinity_required` after they simply picked a Space;
they are worth fixing in-slice. M3 should be either reverted or argued in the PR
body, because it narrows a capability the plan did not scope. M4 and M5 are the
test-integrity items and are cheap.

---

# Delta re-verification — head `887de11a`

Deltas only. Same method: throwaway worktree at `887de11a` with its own install,
removed afterwards; probe preserved at `…/scratchpad/t3-delta-probe.test.tsx`.

**Both blockers closed at the mechanism. No open findings from this seat.**

## Blocker 1 — closed, and closed in the right plane

`verifiedSpawnTarget` and `spaceTransport.ts:fetchCanvas` are deleted outright.
The spawn target is now computed by the control plane and rides the verification
response: `packages/space/src/domain/actingContext.ts:resolveContextSpawnTarget`
returns `defaultWorktreeId ?? receipt.worktreeId`, and
`ActingContextResult` (`contract/src/space/wire.ts`) carries a non-nullable
`spawnWorktreeId`, so the null case cannot reach the browser as a null. Better
than the one-line fix I proposed: when the default *does* differ from the anchor,
`SpaceContextService.ts:completeContext` re-reads that worktree and
`resolveContextSpawnTarget` re-checks owner, Space and lifecycle, so a stale or
foreign default fails closed instead of becoming a launch target. The second
round trip is gone with it.

Probed (P1): child-canvas reload restores the cached panes, projects
`defaultWorktreeId` as the anchor, `addCapturedRun` succeeds, and zero
`/v1/canvases/…` requests are issued. Coverage: the `SpaceContextService` fake
repository returns `defaultWorktreeId: null` for every canvas, so all 38 service
tests plus the pg-integration and router tests exercise the fallback.

## Blocker 2 — closed, and the distinction is structural

The two failures are now different code paths producing different state, not one
path with two labels:

- domain failure → `canvasIdentityOwner.ts:failGeneration` → context to
  `unresolved`, `spawnWorktreeId: null`, `hydrationStatus: "blocked"`, no
  `activateCanvas`, no Retry.
- transport failure → `failUnexpectedGeneration` → the `claimed` phase is
  **kept**, `resolutionError: "transport_error"`, `hydrationStatus: "pending"`,
  and `activateCanvas` runs on the claimed canvasId so the cache is restored and
  rehydrated. `selectVisibleCanvasId` returns the claim's canvasId in exactly
  this state, and `canvasStore.ts` now keys the persist storage off
  `getCanvasCacheId`, so degraded-mode writes stay keyed to the right canvas
  instead of leaking into a null key.

Probed both sides (P2, P3): on 503 the panes are present, the alert reads
"Couldn't verify this Canvas right now. The saved view remains available." with a
working Retry, and `readCanvasIdentityForTests().canvasId` is still null — so the
saved view is visible without anything becoming launchable against an unverified
claim, which is the correct pair of properties. On `canvas_not_found` the panes
are *not* restored and there is no Retry.

**No persisted-state loss at this head.** Re-checked on both failure kinds: URL,
both per-canvas cache blobs, and `sessionStorage` byte-identical to their
pre-boot values.

## My other findings, spot-checked

M2 closed (`actingContextErrorMessage` maps all ten codes plus transport to
sentences; the test now asserts "This Canvas no longer exists." instead of the raw
code). M3 closed (the `meta.workspaceId` branch is back in `workspaceIdentity`).
M4 closed and verified by stripping every directive from
`canvasIdentityBoundary.test.tsx`: 13 pins, 13 single-cause, the retargeted one
now failing as `TS2540: Cannot assign to 'canvasId' because it is a read-only
property`. M5 closed (`registry.test.ts` renders again and asserts the props
`CapturedRunPane` receives). Minors 1–4 and 7–8 closed:
`withWorktree` now returns a real `ActingContextLaunchTarget` instead of an
identity function, the `adopt-default-worktree` arm is gone, `resolutionError` is
a closed union, the receipt fixture moved to
`@tm/contract/space/testing:actingContextTestReceipt`, the reducer's
`workdir-result` carries the generation guard, and `ownerStateFromLaunch` now
honours `canvasIdVerified`.

## Cross-cutting

Four original scenarios green and switching intact (P4: A→B→A restores A's panes
and launches). Full frontend suite green at this head: 179 files, 1328 tests.
`CANVAS_STORE_STORAGE_VERSION` still 1; the whole 80-file delta touches neither
`canvasStore.persistence.ts` nor `infrastructure/persistence/`, so nothing entered
the persist blob. No test weakened to pass: the one deleted block
(`canvasStore.test.ts` "retired meta identity projection") died with the
`adopt-default-worktree` command it drove, and its assertion — an unresolved
context cannot launch — still lives in `canvasStore.capturedRuns.test.ts`
("requires a worktree root").

## Diff growth: accounted for

The largest new chunk, `anchorWorktreeId` threaded through
`capture_rpc_routes.py:PrepareCaptureRequest` → `launch_resolution.py:resolve_run_canvas`
→ `runtime/ports.ts:PrepareCaptureInput` → `runtimeRouter.ts` → `RunManager` →
`CaptureRpcClient`, is a forced consequence of the blocker-1 fix rather than new
scope. Once the spawn target may legitimately differ from the Canvas anchor, a
launch carrying only `worktreeId` makes `resolve_run_canvas` compare the Canvas's
anchor against the *spawn* worktree and 409 `canvas_worktree_mismatch` on every
such launch; the server needs both. The many one-line runtime files are that one
field passing through hops that already existed. It is also distinguishable from
§9's deferred launch-context propagation: one field is added to the existing
canvas-launch shape, the pair-shaped service launch is untouched, and nothing
requires a receipt or rejects pair authority. `test_capture_rpc_worktree_resolution.py:
test_prepare_keeps_canvas_anchor_separate_from_launch_worktree` pins the
divergence end to end. The e2e helper (`tests/e2e/canvasIdentity.ts`) is the
plan's own T3 gate item ("one live browser A/B probe"), and existing canvas specs
need it now that panes require a verified context.

One coverage gap, worth a line and no more: every `spawnWorktreeId` assertion in
`packages/space` equals the anchor, because the service-test fake always reports
`defaultWorktreeId: null`. `resolveContextSpawnTarget`'s divergent branch and its
three failure exits (`worktree_not_found`, `space_mismatch`,
`worktree_unavailable` on the *default* worktree) are unexercised node-side. The
downstream consumer of that divergence is covered on the Python side, so this is
a missing unit pin on new code, not an unknown behaviour.

The only item I would call incidental to any finding is the
`TM_PLAYWRIGHT_PORT` env var in `playwright.config.ts`.

---

# Final delta — head `8e6f8f8e`

My item: are the divergent spawn branch and its three failure exits pinned
node-side, and would each pin fail if its branch regressed? **Yes to both**,
established by mutation, not by reading. Four new pins in
`SpaceContextService.test.ts` ("SpaceContextService Canvas launch target"), each
mutation run in a throwaway worktree at `8e6f8f8e` and reverted:

| Mutation to `domain/actingContext.ts:resolveContextSpawnTarget` | Result |
|---|---|
| divergent branch dropped (spawn target always the anchor) | all 4 pins fail |
| `worktree === null` returns the anchor instead of failing | only `rejects a default Worktree with 'missing'` fails |
| Space check deleted | only `…with 'another Space'` fails |
| lifecycle check deleted | only `…with 'an unavailable lifecycle'` fails |

So each pin is sensitive to exactly its own branch, and the divergence itself
cannot be silently removed. Incidental confirmation from the first attempt: the
identically-worded guard in `resolveClaimedWorktree` is independently pinned by
three parity fixtures, so the two `worktree_not_found` exits are separately
covered.

Both blockers remain closed at this head: my delta probe (child-canvas reload
launches with zero `/v1/canvases/…` requests; transport degrade keeps the panes,
offers Retry, and leaves nothing launchable; domain failure blocks with no pane
restore; A→B→A intact) passes 4/4, and URL, both canvas caches and
`sessionStorage` are unchanged on both failure kinds.

Cross-cutting: full frontend suite green (179 files, 1329 tests); T2 pins 13/13
still single-cause by strip-check, the retargeted one still
`TS2540 … 'canvasId' … read-only`; `CANVAS_STORE_STORAGE_VERSION` is 1 and
`canvasStore.persistence.ts` plus `infrastructure/persistence/` are untouched
across the entire `98870fac..8e6f8f8e` range; no test deleted or weakened in this
delta (it is purely additive on the test side).

Growth 80 → 96 files maps onto the four stated items: the control-plane workdir
resolver for the director (`controlplane_gateway_space.py` and the `run_proxy` /
`launch_service` / `run_models` wiring plus its tests), the shared
`contract/space/launchTarget.ts:canvasLaunchTargetWorktreeId` now used by both the
node domain and `select-canvas` (with `CanvasCommandDispatcher.test.tsx` pinning
it), my four pins, and the activity-affinity change; the e2e/visual/smoke fixture
moves are those changes reaching suites whose panes now need a verified context.
Nothing in it is unaccounted for.

One factual note on my own earlier M3, not an objection: the `meta.workspaceId`
fallback restored at `887de11a` is removed again here. That is fable's
cross-worktree contamination call and I do not relitigate it; worth recording that
the resulting no-stream state is now surfaced by the `worktreeResolutionFailed`
alert with its Retry rather than failing silently, which answers the substance of
M3 without the fallback.
