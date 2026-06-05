# S4 review — PR #328, shadow acting context bridge (opus, independent logic-and-state)

Target: `ml/identity-s4` @ `be26765b`, base `feat/multi-launch`, +1271/-115 / 30 files.
Read-only. Gate not re-run beyond `@tm/space-client` (38 tests, 4 files, green).

**1 blocker, 5 major, 6 minor.**

Verdict on the slice's own safety property: the projection is a true mirror and no
reader gains an identity legacy did not have, but that holds by an unpinned
invariant (see M-5), and two consumers now take a control-flow decision from the
shadow rather than from legacy (M-2, M-3). The stated S4 deliverable "wire claim
verification to S2, results recorded only" does not function at all (B-1).

---

## Blocker

### B-1 — the S2 verification call cannot reach S2; it 404s on every boot

`www/packages/space-client/src/spaceTransport.ts:verifyActingContext` posts to
`/v1/spaces/acting-context/verify`. That route exists only on the Fastify router
`packages/space/src/server/spaceRouter.ts:createSpaceRouter`, which `@tm/gateway`
mounts in a separate node process.

The browser's transport is same-origin and relative:
`www/packages/core/src/transport.ts:createApiTransport` is constructed with no
`baseUrl`, and nothing calls `setApiTransport` outside tests. `/v1/spaces` is
owned by Python (`api/src/transport_matters/api/v1/space_routes.py`), which
declares `/spaces`, `/spaces/{space_id}`, `/spaces/{space_id}/worktrees`,
`/spaces/{space_id}/worktrees/reconcile`, `/spaces/{space_id}/canvases` — and no
`acting-context` route. Python forwards to the gateway only through the explicit
run-lifecycle proxy (`api/v1/run_proxy.py`); there is no generic `/v1/spaces`
forward, and this PR touches no Python.

So `SessionCanvasRoute.tsx`'s new effect fires a POST that 404s on every canvas
mount with any scoped URL. `throwWithDetail` yields `Error("Not Found")`,
`actingContextFailureCode` finds no match, the throw is caught in
`actingContextStore.ts:verifyActingContextClaim`, and the store records
`{ error: "Not Found" }` forever. Nothing surfaces it, because results are
recorded only.

The diff contains its own tell: `SessionCanvasRoute.activity.test.tsx` had to add
a stub for exactly this path, returning 404, positioned ahead of the
`path.startsWith("/v1/spaces")` branch.

Why blocker rather than major: this is the mechanism S5 flips onto. Landing it
dark and non-functional means S5 will be the first slice to discover the wiring
was never real, on the slice with the least diff-readable evidence.

Fix is a routing decision, not a patch: either add a Python proxy for
`/v1/spaces/acting-context/*` alongside `run_proxy.py`, or point this one call at
the gateway origin. Whichever, the acceptance evidence must be a real response
from `SpaceContextService.verifyActingContext`, not a mocked transport.

---

## Major

### M-2 — `activateSpace` gates a legacy switch on shadow state, and clears it first

`www/packages/canvas/src/workbench/CanvasCommandDispatcher.ts:activateSpace`:

```
if (getNavigationSpaceId() === spaceId) return;
clearActingContextForNavigation(spaceId);
... replaceState ...
selectSpace(spaceId, useCanvasStore);
```

`canvasStoreLifecycle.ts:selectSpace` already calls
`clearActingContextForNavigation(spaceId)` itself, so the pre-clear is redundant
— and it is the one ordering in the slice where the shadow is written *before*
legacy. If `selectSpace` throws (its `setState` drives the persist write;
localStorage can throw), `navigationSpaceId` is already the new Space while
legacy still holds the old one. The re-select guard then reads the shadow and
returns early forever: the user cannot switch to that Space again without a
reload, and nothing detects the divergence.

This is the concrete answer to "what happens if one writer succeeds and the other
throws". Delete the pre-clear; `selectSpace` owns it, and the guard should read
whatever is authoritative.

### M-3 — the shadow decides which Space a mutation targets

Same file: `dispatchSpaceMutation({ getActiveSpaceId: getNavigationSpaceId })`
replaced `() => useCanvasStore.getState().spaceId`. Combined with M-2's guard,
two user-visible control-flow decisions (does the Space switch run; which Space a
new workdir is created in) are now taken from the shadow store.

They agree with legacy today only because every legacy identity writer is
manually paired with a `canvasStoreLifecycle.ts:syncActingContextFromCanvasState`
call. I traced all of them — `initializeCanvas` (both branches), `selectSpace`,
`adoptDefaultWorktree`, `resetCanvasStoreForTests` — and the coverage is currently
complete. Nothing enforces it. A future legacy write that forgets the pairing
silently retargets a mutation.

This is the answer to priority question 1: yes, the aggregate's value reaches
consumers, on these two paths.

### M-4 — `CommandCenter` loses the active-worktree marker in a reachable state

`launcher/CommandCenter.tsx`:

```
const activeSpaceId = actingContext?.spaceId ?? navigationSpaceId;   // has a fallback
activeWorktreeId: actingContext?.worktreeId ?? null,                 // has none
```

`actingContextStore.ts:getActingWorktreeId` exists precisely to fall back to
`projectedWorktreeId`; this reader does not use it. The asymmetry with the line
directly above shows the null-receipt window was handled for `spaceId` and missed
for `worktreeId`.

The receipt is null whenever legacy `canvasId` is null, which includes the state
where meta does not match the URL selection (`resolveCanvasLaunchIdentity` returns
`canvasIdVerified: false`) — S5 evidence case (b), a live state — and the
meta-less desktop. Legacy `defaultWorktreeId` is non-null there. Before this PR
`workdirRows.ts:buildWorktreeRows` marked that worktree "Current"; now it marks
nothing.

A visible behaviour change in a slice that forbids behaviour change. One-line fix:
read `projectedWorktreeId` the same way `activeSpaceId` reads `navigationSpaceId`.

### M-5 — the invariant that makes the `CanvasWorkbench` migration safe is unpinned

`workbench/CanvasWorkbench.tsx` now derives `canvasId`/`spaceId` from the receipt.
Those two props are the sole source of `viewers/registry.tsx`'s
`props.canvas.spaceId` / `props.canvas.id`, which flow through `CapturedRunPane` →
`useCapturedRunBinding` → `capturedRunStore.ensureRun` →
`core/transport.ts:createCapturedRunView` into `POST /v1/runs`.

The receipt is all-or-nothing while the three legacy fields are independent, so
this is only safe if `receipt === null ⟺ legacy.canvasId === null`. It holds, but
by a chain nothing states: `canvasStoreLifecycle.ts:initializeCanvas` sets a
non-null `canvasId` only from `urlTupleCodec.ts:defaultCanvasId`, which requires
`canvasIdVerified`, which `resolveCanvasLaunchIdentity` sets only from an
`isUsableIdentity` tuple — so a non-null `canvasId` implies non-null space and
worktree.

Without it, the launch POST would carry `spaceId: null` beside a non-null
`worktreeId` and trip `capture_rpc_routes.py:_resolved_domain_request`'s
`worktree_affinity_required`, where today it stops at `canvas_affinity_required`
regardless. Same outcome, by luck of ordering.

This invariant is the whole safety argument for the highest-blast-radius reader in
the slice. It deserves one assertion in
`domain/actingContext.test.ts:projectActingContextReceipt` (or better, a canvas
store test driving `initializeCanvas` on an unverified launch and asserting both
`canvasId` and the projection are null together), not a chain a reader has to
reconstruct.

### M-6 — the expected-mismatch ledger cannot detect an unlisted mismatch

`actingContextStore.test.ts:"pins the two intended shadow mismatches to a named
ledger"` builds `actualMismatches` from two hand-written scenarios, then asserts
that set equals `Object.keys(EXPECTED_MISMATCH_LEDGER)`. No corpus is scanned, so
a third divergence cannot appear in `actualMismatches` and cannot fail the test.
The ledger is a list of things allowed to be wrong, which is the exact failure
mode the brief named.

Three specific holes:

- It compares `canvasId` only. A `spaceId`- or `worktreeId`-only divergence is
  invisible.
- The "child canvas" case passes `{ worktreeId: null, canvasId: null }`, an empty
  legacy projection, not a child canvas. Any selection mismatches against it, so
  the assertion cannot fail for the reason the ledger states.
- The ledger's two entries do justify *why* each mismatch is expected (good), but
  the only enforced property of that justification is
  `reason.length > 20`.

The plan's S4 gate asked for parity fixtures "across the corpus". The corpus is
exercised in `domain/actingContext.test.ts` against the reducer, but never against
the legacy-vs-shadow pair, which is what a parity ledger is for.

---

## Minor

### m-7 — the "field-divergence detectors" assert the opposite property

`model/canvasStore.test.ts:"reads the acting receipt when legacy worktree fields
are injected with divergence"` and
`launcher/CommandCenter.spaces.test.tsx:"marks the receipt projection current when
legacy fields diverge"` both inject divergence with a bare `useCanvasStore.setState`
that bypasses `syncActingContextFromCanvasState`, then assert **the shadow wins
over legacy**.

They are accurate descriptions of what the migrated readers now do, and they are
useful as such. They are not detectors: they pin the inverse of "legacy stays
authoritative", and they would pass unchanged if a legacy writer lost its sync
pairing (M-3's failure mode). Rename them, or make them assert parity after a
*real* legacy write instead of a synthetic one.

### m-8 — the reader-coverage enumeration is tautological and one entry is wrong

`model/actingContextConsumerCoverage.test.ts` asserts `toHaveLength(3)` and
`toHaveLength(5)` against the literal array declared immediately above it. Its
only load-bearing assertion is a substring grep for a marker.

Separately, `viewer-registration` is listed `status: "deferred", target: "S5"`,
but `CanvasWorkbench.tsx` (listed `migrated`) is the sole supplier of the identity
that registration consumes (M-5). The entry misdescribes what S4 changed.

### m-9 — the generation guard is skipped from `unresolved`

`domain/actingContext.ts:resolveActingContext` line 72 guards
`event.generation < current.generation` only when `current.phase !== "unresolved"`.
After a `clear` (which bumps the store's generation), a stale in-flight `acting` or
`workdir-resolution` event from an older generation installs unguarded.

Unreachable today — `mirrorLegacyActingContext` is the only producer of `acting`
and it is synchronous — but the store carries the real guards
(`beginClaim`, `recordVerification` compare generations outside the reducer), so
the pure reducer does not hold the property on its own. S5 trusts this reducer.

### m-10 — recorded verification results will be empty in practice

`recordVerification` discards on any generation change, and the boot path bumps
generation routinely: `SessionCanvasRoute`'s `adoptDefaultWorktree` effect calls
`syncActingContextFromCanvasState` after the verify has started, and a completing
mirror increments. So `discardedVerificationCount` will be non-zero for benign
reasons and `lastVerification` usually null. Even with B-1 fixed, the "recorded
only" surface carries almost no signal.

### m-11 — the parity corpus failure branch has no teeth

`domain/actingContext.test.ts:"maps the complete shared verification corpus"`
asserts only `actual.phase !== "acting"` on the failure branch. The reducer returns
`current` (`claimed`) for every failure, so the assertion cannot distinguish a
correct rejection from a reducer that ignores verification results wholesale.
`fixture.expectation_status` (`shipped` | `proposed`, added in S1 specifically to
mark the unmatched-workdir case) is never consulted.

### m-12 — unrelated churn bundled into a behaviour slice

`model/canvasActions.ts` and `workbench/CanvasWorkbench.tsx` carry ~6 pure
formatting reflows (`set((state) => ({ ... }))` bodies, a `bounds` literal, a
`findByRole` options object) with no semantic content, and
`launcher/commandRows.test.ts` → `canvasRows.test.ts` is a file split for a
one-field addition. The split is clean (no coverage lost, verified line by line),
but it inflates the diff a reviewer has to judge for behaviour identity.

---

## Confirmations requested by the brief

**Persistence.** `model/canvasStore.persistence.ts:CANVAS_STORE_STORAGE_VERSION`
reads `1` and is untouched by the diff; `partializeExtras` is unchanged. Nothing
reaches persisted shape by another route: `actingContextStore` is a bare
`create()` with no `persist` middleware, no entry in canvas
`infrastructure/persistence/storageKeys.ts`, and no localStorage access. The only
new localStorage interaction in the diff is the pre-existing cache save/restore
already inside `initializeCanvas`. Clean.

**Behaviour tell — S4 does not fix the reload→launch bug.** `defaultCanvasId`
still gates on `canvasIdVerified`; the `SessionCanvasRoute.tsx` meta-wins line is
untouched; `isUsableIdentity` and `resolveCanvasLaunchIdentity` are unchanged. The
receipt is null exactly when legacy `canvasId` is null (M-5), so no reader gains
an identity legacy did not have, and `_resolved_domain_request` still rejects the
unverified-canvas launch at `canvas_affinity_required`. The product does not
recover on reload. Correct for this slice.

**Is legacy authoritative on every path?** For the identity *values* consumed by
readers: yes, via the mirror, with M-5's invariant load-bearing and M-4 one
reachable exception. For *control flow*: no — M-2 and M-3 hand two decisions to the
shadow.

**Can the two writers silently diverge?** Yes, and nothing detects it. Every
writer pairing is manual (M-3); the one inverted ordering wedges a user action on
a throw (M-2); the divergence tests assert the shadow winning rather than parity
(m-7); and the ledger cannot surface an unlisted case (M-6).

**The generation counter.** It guards the late-verification case correctly at the
store level — `recordVerification` requires an exact generation match, and
`actingContextStore.test.ts:"discards a late verification result after a newer
explicit selection"` genuinely drives a slow verifier past a `selectActingContext`
and pins `discardedVerificationCount`. Two caveats: the reducer alone does not
hold the property (m-9), and in production the counter will fire mostly on benign
mirror bumps (m-10).

**Is the receipt projection a true mirror?**
`domain/actingContext.ts:projectActingContextReceipt` normalises nothing, fills no
default, reorders nothing — it is a null-gated field copy. The only semantic
difference from legacy is completeness: it is all-or-nothing where the three legacy
fields are independent. That difference is invisible to two of the three migrated
readers (M-5's invariant) and visible in the third (M-4).
