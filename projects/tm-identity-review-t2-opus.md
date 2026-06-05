# T2 review — PR #330, `b0734c1a` (Opus)

Scope: `5a531b2c..b0734c1a`, +435/−412 across 20 files. Read-only; no edits to the
shared tree.

**Counts: 0 blockers, 2 majors, 5 minors, 2 observations.**
**A surviving identity write path exists** (Major 1), but it is not a *stray*
write path; reasoning under "Verdict on the claim".

Evidence run this session: `just check` green (tsc across every package, ruff,
mypy 701 files). `pnpm --filter @tm/shell test` green: **172 files / 1307 tests**.

---

## Verdict on the claim

The claim: after this slice a stray identity write cannot compile.

The ordinary shapes of a stray write are now compile errors, and I confirmed each
by inspection of the emitted types:

- `spaceId` / `defaultWorktreeId` / `canvasId` / `launch` are gone from
  `paneRecords.ts:CanvasModel` and therefore from `canvasState.ts:CanvasStoreState`,
  so `set({ canvasId })` inside any action in `canvasActions.ts` is an excess-property
  error even though those actions kept their unrestricted `StoreApi<CanvasStoreState>["setState"]`.
- `canvasStore.ts:CanvasStoreHook` is a hand-written interface exposing only the
  selector call signature, `getState`, and `persist`. `useRawCanvasStore` is
  module-private. The builder's `TS2551` receipt is real.
- `canvasIdentityOwner.ts:CanvasIdentity` marks all three fields `readonly`, so
  `getCanvasIdentity().canvasId = x` is `TS2540` (probed).
- `window.history.replaceState` appears at exactly one non-test site,
  `canvasIdentityOwner.ts:replaceIdentityUrl`.
- All twelve §6 mutation operations land inside the owner. The `activeCanvasId`
  module mirror is gone: `canvasStoreLifecycle.ts` is deleted, and
  `canvasIdentityOwner.ts:getActiveCanvasId` derives the persist cache key from the
  owner's store. No `setActiveCanvasId` remains anywhere.

Two paths survive that still typecheck (Majors 1 and 2). Under the brief's
mechanical rule either is a blocker. I am not scoring them that way, and the
reason matters: a *stray* write is an accidental one, and neither of these is
reachable by accident. One requires writing `Object.assign` onto the result of a
getter; the other requires calling a symbol named `...ForTests`. The slice
delivers the guarantee it was commissioned for. What it does not deliver is the
unqualified sentence, and Major 1 has a small fix that makes the sentence true,
so it should be fixed in-slice rather than qualified in prose.

---

## Major 1 — `Object.assign` onto the live identity object compiles and mutates it

`canvasIdentityOwner.ts:getCanvasIdentity` returns `useCanvasIdentityStore.getState()`,
which is the store's live internal object, unfrozen. `readonly` blocks assignment
but TypeScript does not enforce `readonly` through `Object.assign`.

Verified against the repo's own compiler (typescript 6.0.3, `--strict`): with the
`CanvasIdentity` shape, `getCanvasIdentity().canvasId = "x"` errors as expected,
and `Object.assign(getCanvasIdentity(), { canvasId: "x" })` **produces no
diagnostic**.

Failure scenario: any module calls
`Object.assign(getCanvasIdentity(), { canvasId: someOtherId })`. The write lands on
the live state object, so `getActiveCanvasId()` — which keys
`canvasCacheStorage.ts:createCanvasCacheStorage` — immediately returns the new id and
the next canvas persist write goes to a different localStorage blob, while zustand
never notifies, so `useCanvasIdentity` subscribers keep rendering the old tuple. A
silent split between the rendered identity and the persisted cache key.
`useCanvasIdentity(selector)` hands the same live object to arbitrary selectors,
so the hole is not limited to `getCanvasIdentity`.

Fix, small and DRY-positive: route every owner write through one private helper that
replaces state with a frozen object, e.g.

```ts
function setIdentity(next: Partial<CanvasIdentity>): void {
  useCanvasIdentityStore.setState(Object.freeze({ ...getCanvasIdentity(), ...next }), true);
}
```

Frozen state makes the `Object.assign` a `TypeError` at runtime (ESM is strict), and
the helper also absorbs Minor 7. Zustand never mutates state in place, so freezing is
safe.

## Major 2 — the test reset is an unguarded arbitrary identity setter, and the plan records it as closed

`canvasIdentityOwner.ts:resetCanvasIdentityForTests`, re-exported through
`canvasStore.ts:resetCanvasStoreForTests`, takes a full `CanvasLaunchContext` and
calls `useCanvasIdentityStore.setState(identityFromLaunch(launch), true)`.
`identityFromLaunch` passes `spaceId` and `worktreeId` straight through and derives
`canvasId` via `defaultCanvasId`, so a caller supplying
`{ ...INITIAL_LAUNCH_CONTEXT, spaceId, worktreeId, canvasId, canvasIdVerified: true }`
sets the complete acting tuple. Nothing marks the function test-only; it typechecks
from any module in the package.

This is not a regression — `resetCanvasStoreForTests` had the same reach at
`5a531b2c` via `createInitialCanvasModel(launch, setActiveCanvasId)`. The finding is
that `tm-identity-build-plan.md` §6 dispositions it as
"T2's field removal closes them for identity", and after this slice that sentence is
false. Either narrow the symbol (a test-only entrypoint, or an
`import.meta.env.MODE` guard) or correct the record in the T2 PR. Leaving a false
disposition in the governing doc is the worse of the two.

## Minor 3 — the T2 gate greps are not encoded, so the seam is unpinned against the next PR

The plan's T2 gate names "a grep proving zero identity fields on `CanvasStoreState`
and `replaceState` confined to the owner module". Both hold today; I ran them. Neither
exists as a repo test. `canvasStore.test.ts:"keeps acting identity outside the canvas
store"` covers the field-absence half, at runtime, on the canvas store only — nothing
stops the next PR adding a second `window.history.replaceState` outside
`canvasIdentityOwner.ts` with a fully green suite. The confinement half is the one that
regressed historically (three URL writers in the dispatcher) and it is the half with
no test.

## Minor 4 — `dispatchIdentityCommand`'s structural store parameter is a public bypass

`canvasIdentityOwner.ts:dispatchIdentityCommand(command, canvasStore)` accepts any
value satisfying `CanvasStoreWithPersistence` — a structural type. A caller can move
the real acting identity while handing in a fabricated store, so the Space clear,
cache restore, and `persist.rehydrate()` never run against the real canvas store and
identity ends up ahead of its cache. `canvasStore.ts:dispatchCanvasIdentity` is the
intended one-argument entry point and the only production caller. The two-argument
form should not be exported; binding the store inside the owner (or having the owner
receive it once at wiring time) removes the shape entirely. Same shape existed
pre-slice on `canvasStoreLifecycle.ts:initializeCanvas`, so this is inherited, not new.

## Minor 5 — the identity owner owns the canvas store's shape type

`CanvasStoreWithPersistence` describes the *canvas* store, yet it now lives in
`canvasIdentityOwner.ts` and is imported back out by both `canvasStore.ts` and
`canvasActions.ts`. The dependency points the wrong way for a module whose whole
purpose is to not know about canvas state beyond one setter. `canvasState.ts` is the
cohesive home; the owner then imports it like everyone else.

## Minor 6 — a second exported test-only mutator on a production module

`canvasStore.ts:setCanvasStoreStateForTests` is new, exported, unguarded, and takes
`Partial<CanvasStoreState>`. It cannot write identity, so it does not touch the
guarantee, but `canvasStore.ts` now exports two production-reachable mutation
capabilities that exist only for tests. Worth at least a shared, clearly-guarded
test-support seam rather than two ad-hoc exports.

## Minor 7 — redundant spread in `adoptDefaultWorktree`

`canvasIdentityOwner.ts:adoptDefaultWorktree` calls
`setState({ ...current, spaceId: ..., defaultWorktreeId: ... })`. Zustand's `setState`
already merges, so `...current` is dead and it obscures which fields the command
actually writes — the other three commands read as precise field lists, this one does
not. Absorbed by the Major 1 helper.

---

## Behaviour identity vs `5a531b2c`

Traced path by path. **No reachable divergence found.**

- **`initialize-from-launch`, null-canvas branch.** Old wrote
  `{ canvasId: null, spaceId: launch.spaceId ?? state.spaceId, defaultWorktreeId:
  launch.worktreeId ?? state.defaultWorktreeId, launch }` then returned. New writes
  the same three-field merge to the owner and returns. Identical.
- **Switching-canvas branch — the one real textual divergence, and it is unreachable.**
  Old replaced the model via `createInitialCanvasModel(launch, ...)`, which set
  `spaceId: launch.spaceId` and `defaultWorktreeId: launch.worktreeId` *outright*.
  New always merges `launch.spaceId ?? current.spaceId`. These differ only if a launch
  reaches this branch with `defaultCanvasId(launch) !== null` and a null `spaceId` or
  `worktreeId`. `urlTupleCodec.ts:defaultCanvasId` gates on `canvasIdVerified === true`;
  `resolveCanvasLaunchIdentity` sets that flag only after `isUsableIdentity` (all three
  non-null) and then fills both fields from the identity; `parseCanvasLaunchContext`
  always emits `canvasIdVerified: false`. So verified implies both non-null and the two
  forms coincide. Divergence unreachable — but it is latent, and it will become
  reachable the moment T3 introduces a second producer of verified launches. Worth a
  comment at the merge site.
- **Same-canvas branch.** Old issued a canvas-store `setState` merging the identity
  fields (which triggered a persist write); new issues no canvas-store write at all.
  End state and the subsequent `persist.rehydrate()` are identical; one fewer
  localStorage write.
- **Cache dance ordering preserved.** The owner still updates identity *before*
  `canvasStore.setState(createInitialCanvasModel())`, so the reset's persist-on-set
  lands under the new key and is then overwritten by the captured `cached` blob, exactly
  as `initializeCanvas` did. Restore-then-rehydrate order unchanged.
- **`select-space`.** Old: dispatcher re-select guard → `replaceState` → `selectSpace`
  reset. New: `canvasIdentityOwner.ts:selectSpace` runs guard → `replaceState` → identity
  clear → canvas reset. Same order; the guard moved into the owner as §6's consumer table
  specifies.
- **`select-worktree` / `select-canvas`.** URL write then
  `resolveCanvasLaunchIdentity(parseCanvasLaunchContext(search), identity)` then init —
  same functions, same order, now inside the owner.
- **`adopt-default-worktree`.** Guards (`defaultWorktreeId !== null` bail, cross-Space
  bail) and the `spaceId ?? current` fill are byte-equivalent to
  `worktreeDefaults.ts:adoptDefaultWorktreePatch`, which was deleted with its state type.
- **The reload→launch bug is still broken, as required.** `parseCanvasLaunchContext`
  emits `canvasIdVerified: false`, `defaultCanvasId` gates on it, so a reload from a
  scoped-unverified URL still resolves `canvasId === null` and the CMDK launch still
  hits `canvas_affinity_required`. Nothing in this slice touches that gate. No accidental
  recovery.

## Storage

Clean. `canvasStore.persistence.ts:CANVAS_STORE_STORAGE_VERSION` is untouched at `1`
by every route in the diff. `partialize`/`mergeCanvasStoreState`/`partializeExtras`/
`mergeExtras` are unchanged, and identity now *cannot* enter the blob because it is not
on `CanvasStoreState`. The `canvasId` that keys the blob lives in the owner, outside the
persisted state, and reaches `createCanvasCacheStorage` through `getActiveCanvasId`.
The pre-existing old-snapshot rehydrate test
(`canvasStore.persistence.test.ts:"rehydrates a legacy workspaceHash snapshot without
wiping its canvas"`) still passes.

## No S4 residue

Owner state is exactly the three legacy fields. No aggregate, no generation counter, no
watermark, no verification wiring, no second live store, no receipt type. `IdentityCommand`
is the closed five-arm union the plan specified, nothing more.

## Blast radius of removing `setState` from the exported hook

Contained, and nothing was weakened to pass a typecheck.

- Two call sites existed: `CanvasWorkbench.test.tsx` (×2) and
  `canvasStore.persistence.test.ts` (×1). All three rerouted to
  `setCanvasStoreStateForTests` with byte-identical payloads. No assertion softened, no
  test stubbed out or deleted.
- `useCanvasStore.subscribe`, `.getInitialState`, `.destroy`, and the selector-less
  `useCanvasStore()` form have zero callers repo-wide, so narrowing the hook to
  `{ selector, getState, persist }` cost nothing else.
- `useCanvasStore` is not in `@tm/canvas`'s `exports` map or `index.ts`, so the narrowing
  has no cross-package reach.
- Test migrations off `state.spaceId` → `getCanvasIdentity()` preserve strength: several
  moved from single-field `toBe` to whole-object `toEqual`/`toMatchObject`, which is
  stricter, not looser.

## Can the new tests fail?

`canvasStore.test.ts:"keeps acting identity outside the canvas store"` is five runtime
assertions (`"spaceId" in state` … `"setState" in useCanvasStore`), each of which flips
on a real regression. I did **not** execute it red — the tree is shared with the builder
and this review is read-only. By inspection all five are false at `5a531b2c`'s parent
state: the store carried `spaceId`/`defaultWorktreeId`/`canvasId`/`launch` in
`createInitialCanvasModel`, and `useCanvasStore` *was* the raw zustand store, which
carries `setState`. It is a genuine guarantee test, not a tautology.

Its limit, per Minor 3: it pins the runtime shape of the canvas store, not the
compile-time restriction and not `replaceState` confinement.

## Observations (no action required beyond a PR line)

1. **Operation #7 is redefined, not relocated.** At `5a531b2c`,
   `canvasStoreLifecycle.ts:resolveLaunchCanvasId` seeded the cache key from
   `window.location.search` at module load. The owner seeds from
   `INITIAL_LAUNCH_CONTEXT`, so the key is `null` until the route dispatches
   `initialize-from-launch`. Traced: both versions take the switching branch at first
   init (the old store's `canvasId` field was also null at creation), so the reset +
   cache-restore + `rehydrate()` sequence and the end state are unchanged. The only
   difference is that store writes occurring before the route effect now no-op instead
   of landing under the URL key — the safer side, and `createCanvasCacheStorage` already
   no-ops on a null id. §6 describes #7 as "absorbed"; it was re-specified. Worth one
   line in the PR so the next reader does not have to re-derive it.
2. **`activateTestWorktree` no longer pins the switch URL's pathname.**
   `SessionCanvasRoute.testSupport.tsx` previously hardcoded `worktreeSwitchUrl("/canvas", …)`;
   it now goes through the owner, which reads `window.location.pathname`. Suite is green
   and this is closer to production, but the pathname is no longer pinned in tests.

## Recommendation

Fix Major 1 in-slice (the frozen-write helper, which also absorbs Minor 7), and resolve
Major 2 by correcting the §6 disposition or narrowing the symbol. Minors 3–6 are
craftsmanship and belong in this slice. None of it blocks the seam: the choke point is
real and the twelve operations are inside it.

---

# Delta re-verification — head `dc7f1de6` (+692/−459, 25 files)

**verified clean.** Deltas only; the slice review above stands.

**1. Are the pins real pins?** Yes. `canvasIdentityBoundary.test.tsx` is in the tsc
program (confirmed via `tsc -b --listFiles`; it enters through `tsconfig.test.json`),
and an unused `@ts-expect-error` is `TS2578` under this repo's toolchain (probed
directly). So each of the four negative cases fails the build the moment its
underlying restriction is removed. The mechanisms behind them are real, not
suppressions: `canvasState.ts:CanvasStorePatch` marks the four retired fields
`?: never`, which is what makes both the literal and the functional-updater forms
errors, and `paneAffordances.ts:dismissPane` was genericized over the patch type so
the restriction reaches through the dismissal seam too.

One narrow gap, not open today: the third pin's error is `TS2339` on the *name*
`getCanvasIdentity`, so it pins that identifier rather than the general property
"no accessor returns the live object". A future accessor under a different name
would carry no pin. Every exported accessor today returns a primitive, so nothing
is currently exposed.

**2. My own blocker — closed.** `Object.assign(getCanvasIdentity(), …)` is
impossible because there is no longer any exported handle to the live object.
Enumerated the owner's full export list: three hooks and three getters, all
returning `SpaceId | null` / `WorktreeId | null` / `CanvasId | null` primitives;
`readIdentity()` and `useCanvasIdentityStore` are module-private; the caller-supplied
selector form (`useCanvasIdentity(selector)`) is gone, which also closes the
selector route; and the test port's `read` returns `{ ...readIdentity() }`, a copy.
The handle is not relocated. Legitimate readers are fully served — the six
accessors cover every consumer, and `useCanvasStore` now copies on both the
selector and `getState` paths, pinned by two runtime tests.

`resetCanvasIdentityForTests` is guarded: it moved into
`canvasStore.testSupport.ts` behind `assertTestEnvironment()`
(`import.meta.env.MODE !== "test"` throws), reachable only through a
module-private port registered once, with double-registration throwing.
Compile-time callable, runtime-blocked — the shape I recommended.

**3. Fresh attempt to break the current head — I could not find a surviving path.**
Enumerated: every `useCanvasIdentityStore.setState` site is inside
`canvasIdentityOwner.ts`; `connectCanvasIdentityOwner` throws on a second call, so a
hostile port either loses the race or breaks boot loudly rather than silently;
`useCanvasStore.persist` is typed to `{ rehydrate }` and rehydration cannot reach
identity anyway; the `?: never` patch type holds through spreads and functional
updaters; `window.history.replaceState` is at one site and now has an encoded test
(`importGraphBoundary.test.ts`) asserting the site list equals exactly
`["model/canvasIdentityOwner.ts"]`, which closes my Minor 3. Explicit casts still
work, but that is true of any TypeScript boundary and was never in scope.

**4. Fix-round blast radius — nothing weakened.** Full suite went 172 files/1307
tests → **173/1310**: one new file and three new tests, zero removed. Tests that
used `getCanvasIdentity()` now import `readCanvasIdentityForTests as
getCanvasIdentity`, so every assertion is textually unchanged. `just check` green,
and the tree is still clean afterwards (no formatter drift — much of the +692 is
print-width reflow, not logic). Reload→launch bug still broken: the
`defaultCanvasId`/`canvasIdVerified` gate in `initializeFromLaunch` is untouched.
`canvasStore.persistence.ts` is not in the delta at all, so
`CANVAS_STORE_STORAGE_VERSION` is still 1. No S4 residue: owner state is still
exactly the three fields, no aggregate, no generation counter.

Behaviour delta is nil: `initializeFromLaunch` is line-identical except that
`canvasStore.setState(createInitialCanvasModel())` became `canvasPort.reset()`,
which is that same call behind the port. `dismissPane` lost the raw store and now
receives `{ getState: get, setState: set }` — it only ever used those two.

**5. Count sanity — correct, and they are the right five.** Current production
identity mutation operations: owner store initialization (`create(() =>
identityFromLaunch(INITIAL_LAUNCH_CONTEXT))`), `initializeFromLaunch`,
`selectSpace`, `adoptDefaultWorktree`, and `replaceIdentityUrl` (one site now
serving all three switch commands, down from three dispatcher writes). A sixth
`setState` exists at `canvasIdentityOwner.ts:220` inside the registered test port;
it is correctly excluded under the same rule that excluded tests from the original
twelve, and it is env-gated at its only entry point.

**Residual notes, neither blocking.** (a) `canvasStore.testSupport.ts` ships in the
production bundle, because both `canvasIdentityOwner.ts` and `canvasStore.ts`
self-register into it at module load — dead weight that tree-shaking cannot drop,
and a production module importing a test-support module is an inversion worth
revisiting in T4. (b) `useCanvasStore` now spreads state on every selector call, so
a drag at 60fps copies a ~15-key object per subscribed component per frame; cheap,
but it is a new per-frame allocation on the canvas's hottest path.

---

# Final delta — head `315dd50d` (+886/−549, 27 files)

**verified clean.** Reflection-based escapes treated as out of scope per the
orchestrator's ruling; nothing below depends on that carve-out.

**1. The omission mechanism holds where `?: never` did not.** Probed all four
propositions against this repo's tsc in one file, exit 0 (so every
`@ts-expect-error` was consumed and the control line produced no error):
`{ canvasId: null }` and `{ canvasId: undefined }` both fail against
`Partial<Omit<State, RetiredKey>>`; `{ canvasId: undefined }` **passes** against
the old `Partial<State> & { canvasId?: never }`, which is exactly the leak this
round closes — `?: never` widens to `never | undefined`, so the undefined form was
assignable; and a function is rejected by the patch-only setter (weak-type rule).

No second mechanism survives. `RetiredCanvasIdentityFields` is gone; the only
`?: never` left in the package is `icons/createIcon.tsx`, an unrelated
discriminated union. `CanvasStorePatch`, `CanvasStoreSnapshot`, `CanvasStoreSet`,
and `CanvasStoreGet` each have exactly one declaration site, all in
`canvasState.ts`. Functional updaters remain only in `themeStore`,
`runVitalsStore`, and `capturedRunStore` — different stores, none holding identity —
so the removal is correctly scoped rather than half-applied.

One note on the shape, not a defect: `Omit<CanvasStoreState, RetiredCanvasIdentityKey>`
omits keys that `CanvasStoreState` no longer has, so it is a no-op on the type and
the real enforcement is ordinary excess-property checking on object literals. That
is the right enforcement and the `Omit` documents intent, but it is worth knowing
the `Omit` is not itself load-bearing.

**2. Ordinary rehydrate cannot reinstall a retired key — verified independently.**
Read the whole merge chain rather than taking the claim. `partialize` builds a fixed
literal from `partializeCanvasState` plus `partializeExtras` (`{ paneCounters }`);
nothing spreads state, so the blob cannot gain an identity key on the way out.
`mergePersistedCanvasState` returns `{ ...current, ...mergeCanvasState(...),
...mergePersistedExtras(...) }`, where `mergeCanvasState` returns a seven-key
literal and `mergeExtras` returns `{ paneCounters }` — the persisted blob is never
spread into state, so unknown keys in an old blob are dropped by construction, not
by filtering. `rebuildPersistedCanvasState` is the only reader of the raw value and
it returns a typed `RebuiltCanvasState`. The new persistence test writes a blob
carrying all four retired keys and asserts each is absent after `rehydrate()`,
which pins the accident-shaped path with a test that would have gone red against a
spread-based merge.

**3. Removing functional updaters — no caller lost anything, behaviour unchanged.**
This is the delta I scrutinised hardest, because `set(fn)` applies against state at
apply time whereas `const s = get(); set(f(s))` snapshots first. Walked every
conversion: `dropCapturedRunPane`, `closeDockedPane`, `restorePaneAtIndex`,
`focusPane`, `setPaneFlyIntent`, all five viewport actions, `park`, `seed`, and
`dismissPane`. In each, everything between the `get()` and the `set()` is pure
(layout planning, list filters, `removeNode`, `markNodeClosing`), and zustand's
`setState` is synchronous with no queueing, so the snapshot cannot go stale. The
two deferred paths read fresh state inside their own callback:
`setPaneFlyIntent`'s timeout now does `get().paneFlyIntent`, and `dismissPane`'s
timeout still calls `store.getState()`. `restorePaneAtIndex` correctly keeps
`invokeDockedPaneRestoreLifecycle` *before* its `get()`.

Nothing was stubbed or weakened to compile — the bodies are the same logic with the
wrapper removed. One behaviour difference, in the safe direction:
`dropCapturedRunPane`'s no-op case now returns without calling `set` at all, where
`set(() => ({}))` previously still notified subscribers and triggered a persist
write. State is identical either way, so no render can differ. The type change is
what forced completeness here: `commitPaneAffordanceTransition` receives `set` and
could not have compiled had it kept an updater.

**4. Pins are single-cause.** Ten pins, each with one identifiable removal that
makes it stop erroring: the two patch pins (identity key becomes known on
`CanvasStorePatch`), the updater pin (`CanvasStoreSet` re-accepts a function), five
readonly pins on the action getter / public `getState` / selector input / full-state
selector result / partialize state / merge state (`Readonly` dropped from that
surface), the owner pin (`getCanvasIdentity` re-exported), and the raw-setter pin
(`setState` returns to `CanvasStoreHook`). The isolation work in `d67491f4` is
real and worth noting: the readonly and raw-setter pins now assert on `cwd`, a
*live* key, so they can only error for the reason claimed — previously
`useCanvasStore.setState({ canvasId: null })` could have errored for either of two
reasons and would have kept passing after a partial regression.

The one pin that remains name-scoped rather than property-scoped is still the owner
pin (`TS2339` on the identifier `getCanvasIdentity`): a future accessor under a
different name returning the live object would carry no pin. Every exported
accessor returns a primitive today, and the eleven-surface audit in the test's
header comment is an accurate enumeration — I checked each of the eleven against
the code rather than trusting the list.

**5. Behaviour identity holds.** `canvasIdentityOwner.ts` is untouched in this
delta, so the `defaultCanvasId`/`canvasIdVerified` gate is byte-identical and the
reload→launch failure is still broken. `canvasStore.persistence.ts` is not in the
delta at all, so `CANVAS_STORE_STORAGE_VERSION` is still 1. No S4 residue. Suite
1310 → **1311**, one net new test, none removed; `just check` green and the tree
clean afterwards.

`replaceCanvasStoreState` is a genuine improvement over the previous merge-based
reset: `setState(..., true)` now removes an already-installed stray key rather than
merging over it, which the new "replacement reset removes an already installed
retired key" test pins directly.

**Residual note, unchanged in kind from the last round.** The per-frame allocation
on the canvas's hottest path grew: `get()` returns `{ ...getState() }` and
`movePane`/`resizePane` then spread that again into the patch, on top of the
selector-side copy. Three shallow copies of a ~15-key object per drag frame per
subscribed pane, where the functional updater previously needed one. Correct, and
almost certainly imperceptible, but it is the kind of thing worth measuring once if
drag ever feels heavy rather than rediscovering later.
