# T3 review — PR #331 (acting-context authority flip), Fable

Scope: PR #331, head `ed095f45`, base `feat/multi-launch`, +1328/−295 across 31
files. Sources: `tm-identity-build-plan.md` §2–§5 (rewritten T3 entry), §7;
`tm-rehydrate-identity-evidence.md`; code read at the PR head checkout.
Verification run: `pnpm --filter @tm/shell test` — 175 files, 1,322 tests, all
pass.

Verdict: **0 blockers, 1 major, 5 minors. Precedence lives in exactly one
place: yes. Drift: none material (two small forward-scaffolds, one T4 deletion
pulled forward by necessity).**

## Section 4 — precedence, written once: PASS

The rule lives in `space-client/src/actingContext.ts:reduceActingContext` and
nowhere else has its own rule:

- Selection always wins and is sticky (`select` unconditional; every other
  event returns `current` when `acting`). Only `clear` (the Space-switch) or
  another `select` replaces it. Pinned by
  `actingContext.test.ts:"keeps explicit selection sticky"` and the
  route-level late-meta and late-verification tests.
- URL over locator: the `claim` arm refuses a locator claim over a pending URL
  claim.
- A claim acts only through its matching-generation `verification-result`;
  failure maps to `UNRESOLVED`, never to a lower source
  (`"discards a failed claim without substituting workdir context"`).
- `workdir-result` promotes only from `unresolved`.

The prior blocker mechanism is gone, not relocated:
`SessionCanvasRoute.tsx` deleted the meta-wins line (`isUsableIdentity` no
longer imported), deleted `storeIdentity`, deleted the meta-seeding
`adopt-default-worktree` effect, and deleted the `meta.workspaceId` fallback in
`workspaceIdentity`. The route renders from `useActingContextReceipt()` only.
Meta survives as exactly one input: `meta?.cwd`, consumed by
`canvasIdentityOwner.ts:initializeFromLaunch` only when there is no claim and
the phase is not `claimed`/`acting` — i.e. meta is never consulted outside
`unresolved` and never fills a field of another source.

The owner's `initializeFromLaunch` contains early-return gates
(`phase === "acting"` → return; `urlClaim ?? locatorClaim`; `claimed` → skip
workdir) that mirror the reducer's decisions. I read these as effect gates (they
decide whether to fire a network call, which a pure reducer cannot), not a
second rule site: every state transition still passes through
`reduceActingContext`, so a divergent gate could suppress a fetch but can never
move state against the rule. Two exceptions are noted as Minor 2 below.

Whole tuples only: `candidateFromLaunch` emits one whole candidate;
`receiptFromVerifiedLaunch` requires all fields; no code path merges fields
across candidates. No root-canvas inference on child failure:
`SpaceContextService`/`domain/actingContext.ts:resolveContextCanvas` fails with
`canvas_worktree_mismatch`/`canvas_not_found` and the client surfaces
`resolutionError`; pinned by the child-canvas reload test and the
failed-claim-atomicity test (URL, owner, caches, locator all unchanged).

## Section 3 — unrepresentability: PASS

Receipt fields non-null branded (`contract/src/space/wire.ts`); nulls exist
only on `ActingContextCandidate`. `installSelection`, `installTrustedContext`,
`activateCanvas`, and the three URL writers all take receipts or branded ids;
no launch, persistence-keying, or URL-write API accepts a candidate. No
transition maps `acting` back down except `selectSpace` (the sanctioned
Space-switch clear); `failUnexpectedGeneration` cannot hit `acting` because
`installTrustedContext` bumps the generation, so a stale error fails the
`generationIsCurrent` check. Generation watermark survives clear (state-level
`generation` counter is monotonic across `selectSpace`), and the late-boot
verification and late-meta tests pin the guard.

## Section 7 walk: PASS

- Meta-wins line: deleted (see above), not re-tuned.
- No identity fields beside the aggregate: `navigationSpaceId` and
  `spawnWorktreeId` are the two plan-sanctioned splits (browse scope,
  spawn-target default); `canvasState.ts:RetiredCanvasIdentityKey` compile pin
  intact; owner store unexported.
- Persist blob untouched; `CANVAS_STORE_STORAGE_VERSION` still 1;
  `canvasPersistOptions.ts` not in the diff.
- No trusting a candidate: URL and locator claims verify through
  `verifyActingContext` via the T1 mirror (but see Minor 1).
- No seeding on read: PR touches no Python; verification service is the S2
  read-only surface.
- No second launch seam: `CapturedRunPane` → `createCapturedRunView` →
  `POST /v1/runs` chain unchanged.

## Both clients

CMDK selections install verified server-inventory rows synchronously
(`select-canvas` now carries `anchorWorktreeId`; the URL is written with the
anchor, which is what makes the reload claim verifiable — the receipt's anchor
stays distinct from the spawn-target default, and reload recovers the spawn
default via `verifiedSpawnTarget` → `canvas.defaultWorktreeId`). MCP service
runs adopt through `CapturedRunAdoptionReconciler` → `adoptCapturedRun`, which
now requires the same verified receipt; a pre-acting adoption attempt throws,
is caught by the reconciler's `catch` → `scheduleRetry`, and succeeds once
resolution lands. Same rule, both clients.

## T2 seam

Not weakened: identity fields absent from `CanvasStoreState`, test seams still
behind `canvasStore.testSupport`, spawn paths read
`getSpawnWorktreeId`/`getActingContextReceipt` (reads, not writes).

## Findings

### Major 1 — space-only URL boot fires a doomed claim: error banner, lost browse scope

`canvasIdentityOwner.ts:candidateFromLaunch` treats any partially scoped URL as
an acting claim. `spaceSwitchUrl` (the Space-switch URL writer) deliberately
writes `space_id` only. Reload that URL:
`{spaceId, worktreeId: null, canvasId: null}` → `verifyActingContext` →
`domain/actingContext.ts:validateActingContextCandidate` returns
`canvas_affinity_required` unconditionally for partial tuples → the route
renders a `canvas_affinity_required` alert, `navigationSpaceId` is never set
from the URL (Space browse scope lost, the palette no longer shows the Space as
current), and the no-substitution rule correctly blocks workdir fallback. At
base, this reload restored browse scope silently (and, for the cwd Space,
restored a launchable meta context). So the ordinary sequence Space-switch →
reload now shows a spurious error and strands the user in unresolved with no
recovery except a fresh selection.

The implementation follows §4's letter (a scoped candidate that fails
verification surfaces an error, nothing substitutes). The gap is that the plan
never classified a space-only URL, and the implementation classifies it as an
acting claim when it is browse scope by construction — the owner's own
`selectSpace` writes exactly this URL to mean "browsing, nothing acting".
Proposed shape, for the owner to adjudicate: a URL carrying `space_id` but no
`canvas_id` is not a candidate; boot should set `navigationSpaceId` from it and
remain `unresolved` (whether workdir resolution may then run inside a foreign
Space's browse scope is the one open sub-question — I'd say no, keep the
explicit-clear semantics). Needs an in-slice fix plus a pinning test
(reload-after-space-switch), since it re-surfaces the slice's own error string
after an ordinary state transition.

### Minor 1 — production-dead trusted-install door behind `canvasIdVerified`

`canvasIdentityOwner.ts:receiptFromVerifiedLaunch` installs `acting` without
verification when `launch.canvasIdVerified === true`. The only production
dispatcher passes `parseCanvasLaunchContext` output, which hard-codes
`canvasIdVerified: false`, so the path is unreachable today — but it is an
unverified trust door keyed to a flag T4 deletes, inside the single owner. The
CommandCenter tests that exercised it were migrated to `select-worktree`.
Delete the branch (tests seed acting via `resetCanvasStoreForTests`) or route
it through verification.

### Minor 2 — two context writes bypass the reducer

`selectSpace` and `failUnexpectedGeneration` assign
`UNRESOLVED_ACTING_CONTEXT` directly instead of dispatching the reducer's
`clear` event, which consequently has no production caller. The outcomes are
identical today, but "every transition runs through `resolveActingContext`" is
the design's stated invariant; route both through `reduceActingContext` so the
reducer stays the single site by construction, not by equivalence argument.

### Minor 3 — `verifiedSpawnTarget` silently degrades on fetch failure

`canvasIdentityOwner.ts:verifiedSpawnTarget` catches any `fetchCanvas` failure
and returns the anchor worktree as the spawn default; a transient network error
silently changes where the next spawn lands (vs the canvas's
`defaultWorktreeId`). The mismatch branch returning `null` (spawn later throws
"rooted worktree") is defensible but undocumented. At least comment the two
degrade semantics; consider surfacing the fallback.

### Minor 4 — raw failure codes rendered as user-facing copy

`SessionCanvasRoute.tsx:routeAlert` renders `resolutionError` verbatim, so users
see `canvas_affinity_required` / `Error.message` strings; the type is also the
loose `ActingContextFailureCode | string`. Map codes to copy (the
`worktreeResolutionFailed` branch beside it shows the house style) and keep the
state field code-typed.

### Minor 5 — inert `adopt-default-worktree` arm and nominal `withWorktree` pin

The `adopt-default-worktree` command survives as a silent no-op with zero
production producers (its inertness is test-pinned; fine transitionally, T4
must delete the union arm). In `canvasActions.ts:adoptCapturedRun`,
`withWorktree(actingContext, worktreeId).worktreeId` reduces to `worktreeId`;
the effective guard is the null-receipt throw, and the expression suggests a
mediation that isn't happening — either pass the pinned receipt onward (the
plan's intent for the wire-sourced worktree) or drop the ceremony.

## Drift

- Deleting the meta-wins line and the meta `workspaceIdentity` fallback was
  listed under T4 but is forced by the flip (meta cannot rank once authority
  flips); not gratuitous.
- Forward scaffolding: the `locator` field on `initialize-from-launch` and the
  `"locator"` claim source are wired but unused until T4's sessionStorage
  locator; small and inert.
- No contraction beyond that; `isUsableIdentity`, `resolveCanvasLaunchIdentity`,
  `defaultCanvasId`, `canvasIdVerified` remain for T4 as planned
  (`resolveCanvasLaunchIdentity` now legitimately projects the receipt into the
  legacy launch shape for unmigrated readers).

## Builder trust verdict

High. The anchor-in-URL insight (select-canvas URLs must carry the anchor
worktree or the reload claim can never verify) is exactly the kind of
cross-boundary consequence prior slices missed, and the six evidence tests map
one-to-one onto the plan's named scenarios, including failed-selection
atomicity down to locator bytes. Test rigor is real (deferred promises for the
two race probes; cache-byte equality for atomicity). The misses are edge
classification (Major 1) and small hygiene (Minors), not shortcuts or spec
substitution.

---

# Delta re-verification — head `887de11a` (fix round)

## My major: CLOSED

`canvasIdentityOwner.ts:isSpaceBrowseLaunch` → `installBrowseScope`: a
space-only URL now installs browse scope (`navigationSpaceId` set, context
cleared through the reducer's `clear` event, no claim fired, no banner) and
deliberately does not fall through to workdir affinity — pinned by
`SessionCanvasRoute.identity.test.tsx:"keeps a space-only URL in browse scope
without applying workdir affinity"`. `selectSpace` now delegates to the same
`installBrowseScope`, so live switch and reload share one code path.

## My minors: all five CLOSED

1. `receiptFromVerifiedLaunch` deleted; the test reset (`ownerStateFromLaunch`)
   now also requires `canvasIdVerified`.
2. Every context transition now runs through `reduceActingContext` (`clear`
   carries a generation and is production-used; the direct
   `UNRESOLVED_ACTING_CONTEXT` writes are gone). Generation moved into the
   context itself — one watermark, and the workdir arm is now
   generation-guarded in the reducer (closing a hole I had not flagged).
3. `verifiedSpawnTarget` deleted outright: the verify/resolve-workdir responses
   now carry a server-computed `spawnWorktreeId` in the same snapshot
   (`SpaceContextService:completeContext`), so the client-side degrade
   heuristics are gone.
4. Failure codes map to copy (`SessionCanvasRoute.tsx:actingContextErrorMessage`);
   `resolutionError` is typed `ActingContextFailureCode | "transport_error"`.
5. `adopt-default-worktree` union arm deleted; `withWorktree` now returns a real
   `{receipt, targetWorktreeId}` launch target consumed by
   `CapturedRunPane`/`createCapturedRunView`, so the receipt genuinely travels.

## Precedence still in exactly one place: YES

`reduceActingContext` still owns every ranking decision. The new
`selectVisibleCanvasId` (claimed canvas shown read-only under
`transport_error`) is a display/degrade projection, not source ranking: the
receipt stays null, spawns stay blocked (`spawnWorktreeId` nulled), the URL is
untouched, and the "verification says no" (claim cleared, coded error) versus
"verification could not run" (claim retained, cached view + Retry with
`force`) distinction is real at the mechanism.

## No T4 creep

`urlTupleCodec.ts` untouched; `isUsableIdentity`, `resolveCanvasLaunchIdentity`,
`defaultCanvasId`, `canvasIdVerified` all still present for T4; locator still
scaffold-only; no sessionStorage locator.

## STILL OPEN — regression introduced in the fix round

`SessionCanvasRoute.tsx:workspaceIdentity` reintroduced the `meta.workspaceId`
activity fallback **without the base's `metaMatchesSelection` guard**. At base,
meta fed the activity stream only for an unscoped launch or an exact affinity
match (the guard's own comment said why); the first T3 head deleted the
fallback entirely; this head restored it unconditionally. Consequence: boot
into a scoped URL for worktree B while desktop meta is workspace A — the
spaces inventory query only starts after acting context lands
(`needsWorktreeInventory` requires `actingContext !== null`), so there is a
structural window (one inventory round trip, or permanent when
`worktreeResolutionFailed`) where acting = B, hydration = ready, and the
activity stream + `CapturedRunAdoptionReconciler` run against **A's**
workspace. The reconciler has no worktree filter
(`capturedRunAdoption.ts:candidateFromWire`), so A's MCP service runs adopt
into B's canvas and persist into B's cache — the cross-workspace contamination
family this plan exists to kill. Supporting signal: the activity tests'
stream assertions were rewritten from "the stream" to exact-URL `some(...)`
matching, which tolerates the extra meta-driven stream instead of pinning its
absence. Fix shape: gate the fallback on `actingContext === null` (or exact
affinity match with the receipt), restoring base semantics now expressible
directly against the receipt.

## Diff growth: accounted for, with the one exception above

The growth is legitimately dominated by findings: the server-side spawn target
(contract + service + router + gateway fixtures + conformance), the
transport-error resilience and hydration status (owner + route + new tests),
and the anchor-vs-target split carried through the whole launch wire
(`anchorWorktreeId` through `capturedRunStore` → `createCapturedRunView` →
runtime → `capture_rpc_routes.py:_resolved_domain_request` →
`launch_resolution.py:resolve_run_canvas`, which now verifies the canvas
anchor separately from the positional target — the both-clients parity fix,
and the right shape). E2e identity helpers and the extracted mcp-close test
are probe hardening, not weakening (assertions preserved verbatim in the new
file). The single piece of the delta not traceable to any seat's finding is
the unguarded meta fallback above — precisely where scope crept.

---

# Final delta — head `8e6f8f8e`: VERIFIED CLEAN

The cross-worktree contamination is closed by deletion, not a guard:
`SessionCanvasRoute.tsx:workspaceIdentity` no longer consults
`meta.workspaceId` at all — it derives only from the resolved launch lookup or
the acting receipt's verified inventory row, so neither the activity stream nor
the adoption reconciler can run against meta's workspace in any state.
The `worktreeResolutionFailed` case is pinned by a new assertion that no
`/activity/stream` source exists under the failure alert. Meta's sole
surviving input remains `cwd` for unscoped launches, per §7. Selection and
reload share one launch-target projection
(`contract/space/launchTarget.ts:canvasLaunchTargetWorktreeId`,
`defaultWorktreeId ?? anchor`, per the owner ruling). Nothing weakened; the
80→96 file growth is accounted for by the four named fix items.
