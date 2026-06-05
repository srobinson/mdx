# T2 review — PR #330 (Fable)

Target: PR #330, `ml/identity-t2`, head `b0734c1a`, base `feat/multi-launch`, +435/−412, 20 files. Reviewed against the rewritten §5 T2 and §6 of `tm-identity-build-plan.md`, the S4 design call Adjudication, and `docs/ARCHITECTURE.md`. Checkout matched the PR head; tree clean.

**Verdict: 0 blockers, 0 majors, 2 minors, 1 nit. Section-6 discharge complete: 12/12 genuinely routed. Drift: none.**

Gates re-run by the reviewer: `just check` exit 0 (tsc all packages, ruff, mypy 701 files); `just test-affected` 39 files / 384 tests passed; `importGraphBoundary.test.ts` 17/17. Full `just check && just test` remains grok's pre-merge gate per the warroom split.

## Section 6 discharge — the twelve operations

Each verified against the code, not the PR claim. "Routed" is genuine in every case: the legacy write site is deleted, not wrapped; nothing writes identity underneath a forwarding shim.

| # | Legacy operation | Where it went | Verified how |
|---|---|---|---|
| 1 | `createInitialCanvasModel` identity fields at module load | fields deleted from the model; owner store initializes via `canvasIdentityOwner.ts:identityFromLaunch(INITIAL_LAUNCH_CONTEXT)` | `canvasState.ts:createInitialCanvasModel` takes no launch, returns no identity; runtime pin `canvasStore.test.ts` "keeps acting identity outside the canvas store" |
| 2 | `initializeCanvas` null-canvas branch | `canvasIdentityOwner.ts:initializeFromLaunch` early return after identity set | branch-for-branch match: coalesced spaceId/worktreeId, no cache touch, no rehydrate |
| 3 | `initializeCanvas` switching branch | same function, `switchingCanvas` path: identity set → cached-blob capture → `createInitialCanvasModel()` reset → restore → `persist.rehydrate()` | ordering identical to the deleted `canvasStoreLifecycle.ts:initializeCanvas`, including capture-before-reset so persist-on-set cannot clobber the target canvas blob |
| 4 | `initializeCanvas` same-canvas branch | same function, non-switching path | keeps panes, refreshes identity coalesced, restore+rehydrate as before |
| 5 | `canvasStoreLifecycle.ts:selectSpace` | `canvasIdentityOwner.ts:selectSpace` | re-select guard absorbed from `activateSpace` and runs before the URL write, exactly the old order; identity nulled before the model reset so the persist write stays disabled, matching the old mirror ordering |
| 6 | `canvasActions.ts:adoptDefaultWorktree` → `adoptDefaultWorktreePatch` | `canvasIdentityOwner.ts:adoptDefaultWorktree` | guard-for-guard identical (existing default wins; cross-Space meta rejected; spaceId coalesce); `worktreeDefaults.ts` patch helpers deleted; all four behaviour tests preserved |
| 7 | `resolveLaunchCanvasId` module-load mirror assignment | deleted; owner store is the sole representation | the old URL parse was provably dead: store creation immediately overwrote the mirror to null via `createInitialCanvasModel(INITIAL_LAUNCH_CONTEXT, setActiveCanvasId)` before the first read. T2 deletes rather than reproduces it; behaviour identical |
| 8 | `initializeCanvas` direct `activeCanvasId` assignment | owner `setState` in `initializeFromLaunch`; `getActiveCanvasId` now derives from the owner store | `canvasStore.ts` feeds `createCanvasStorePersistOptions(getActiveCanvasId)` unchanged — the mirror became the owner's cache-key derivation, as §5 T2 specifies |
| 9 | `setActiveCanvasId` callback through `createInitialCanvasModel` | deleted; every path that invoked it (store init, selectSpace, switching reset, test reset) now sets the owner store directly | grep: zero references to `setActiveCanvasId` outside the deleted file |
| 10 | dispatcher `select-canvas` URL write | `canvasIdentityOwner.ts:dispatchIdentityCommand` `select-canvas` arm → `replaceIdentityUrl(canvasSwitchUrl(...))` | dispatcher arm reduced to `dispatchCanvasIdentity(command)`; URL-write-then-parse order preserved |
| 11 | `activateSpace` URL write | owner `selectSpace` | guard → URL → identity → model reset, matching old order |
| 12 | `activateWorktree` URL write | owner `select-worktree` arm → `worktreeSwitchUrl` then `initializeFromSelection` | `initializeVerifiedCanvas` deleted; same `resolveCanvasLaunchIdentity(parse(post-replace search), identity)` composition |

`grep -rn replaceState` over production sources: exactly one call site, `canvasIdentityOwner.ts:replaceIdentityUrl` (the other hit is a doc comment in `urlTupleCodec.ts`). Zero references remain to `initializeCanvas`, `adoptDefaultWorktree`, `setActiveCanvasId`, `adoptDefaultWorktreePatch`, or `canvasStoreLifecycle` anywhere in `www/`.

**Was the reconciled counting rule right?** Yes. My scout's 10 undercounted the mirror by treating its three assignment sites as one representation; the code at `b0734c1a` confirms the three sites were distinct operations (one of them dead, see #7) and all three are gone. No thirteenth writer surfaced: the raw identity store `useCanvasIdentityStore` is module-private, `dispatchIdentityCommand` plus `resetCanvasIdentityForTests` (test-only, per the rule's exclusion) are the entire write surface, and the excluded per-pane pin flows still read identity only through `getCanvasIdentity()` (`canvasActions.ts:addCapturedRun` / `continueSession` / `spawnTerminal`), never write it.

## The setState escape and the compile guarantee

`canvasStore.ts` now keeps the raw store (`useRawCanvasStore`) module-private and exports a `CanvasStoreHook` wrapper carrying only the selector call signature, `getState`, and `persist: { rehydrate }`. `setState` is absent from both the type and the runtime object (`Object.assign` of a function with exactly those two properties); `canvasStore.test.ts` pins `"setState" in useCanvasStore === false` at runtime. Identity writes anywhere are compile errors because the fields no longer exist on `CanvasStoreState` — the adjudication's "field removal is the smaller proof", delivered as specified. Canvas actions keep their unrestricted setter over the remaining non-identity state, exactly as the adjudication allows. Tests that previously leaned on raw `setState` migrated to `setCanvasStoreStateForTests`, an explicitly test-named export consistent with the rule's exclusion of test paths.

## Behaviour parity, including the bug that must stay broken

- **Reload→launch stays broken, as required.** The `defaultCanvasId` gate (`urlTupleCodec.ts`) is untouched: a canvasId acts only when `canvasIdVerified === true`, and the sole production constructor of a verified context is `resolveCanvasLaunchIdentity`. An unverified reload URL still resolves to a null owner canvasId, no cache rehydrate, and the same `canvas_affinity_required` failure. The `SessionCanvasRoute.tsx` meta-wins line is untouched (T4 deletes it; T3 fixes the bug).
- **The one textual behaviour delta is provably unobservable.** The old switching-canvas branch wrote `launch.spaceId`/`launch.worktreeId` wholesale; the owner coalesces (`launch.spaceId ?? current.spaceId`) in all branches. The switching branch only runs when `defaultCanvasId(launch)` is non-null, which requires `canvasIdVerified: true`, which `resolveCanvasLaunchIdentity` grants only after filling the full tuple — so the coalesce never sees a null on that branch. Verified by grep: `canvasIdVerified: true` has exactly one production construction site.
- **Op 7's deletion is a dead-code removal, not a change** (mirror overwritten to null during store creation in the old code before any consumer read it).
- **The deleted `launch` model field had zero readers**: `ViewerCanvasContext.launch` flows from `SessionCanvasRoute` → `CanvasWorkbench` → `CanvasPaneLayer` props (`resolvedLaunch`), never from the store.
- **Per-field null semantics preserved**: `CommandCenter.tsx` reads three independent selectors (`selectActiveSpaceId` / `selectActiveWorktreeId` / `selectActiveCanvasId`), so a worktree-only tuple still marks "Current" (`commandRows.test.ts` pins intact).
- **Persistence untouched**: `canvasStore.persistence.ts` not in the diff; `CANVAS_STORE_STORAGE_VERSION` unchanged; the persist-OLD-snapshot test ("rehydrates a legacy workspaceHash snapshot without wiping its canvas") passes; write-suppression ordering (identity nulled/keyed before every model reset) matches the old mirror ordering in all three reset paths.

## Placement and boundaries

The owner landed at `@tm/canvas` `src/model/canvasIdentityOwner.ts` — the path my scout recommended; the adjudication bound only the ownership properties, and §2's placement test supports this home: the owner stores inputs only this client possesses and must reach canvas-internal seams (`createInitialCanvasModel`, `canvasCacheKey`, the private raw store handle), which `@tm/space-client` could reach only via a dependency cycle. Pure rules stayed in `@tm/space-client` (`worktreeSwitchUrl`, `spaceSwitchUrl`, `canvasSwitchUrl`, `parseCanvasLaunchContext`, `resolveCanvasLaunchIdentity`, `defaultCanvasId`), imported through the package root — no deep imports. The owner is not on the canvas `exports` map, so it is unreachable from outside the package; `importGraphBoundary.test.ts` 17/17. The injection shape is clean: `canvasStore.ts:dispatchCanvasIdentity` binds the private raw store into the owner's `dispatchIdentityCommand`, keeping the store handle inside one module instead of exporting it.

## Drift and shim check

- **No S4 residue**: no aggregate state, no phases, no generation counter, no verification wiring, no comparator. The owner's state is exactly the three legacy-shaped fields.
- **No compat shim**: no re-export of the deleted lifecycle module, no mirrored identity field anywhere, `INITIAL_LAUNCH_CONTEXT` moved (not duplicated) to the owner. The §7 blocker mechanism (a mirrored field beside the owner) cannot recur without a compile error.
- Additions beyond the letter of T2 are confined to the wrapper hook type and two test-only helpers — scope-appropriate mechanism, not drift.

## Findings

**Minor 1 — the placement decision is not recorded in the PR.** §5 T2: "the choice is recorded in the T2 PR." The PR body states what moved but not the `@tm/canvas`-vs-`@tm/space-client` call or its §2 rationale, and the seam scouts split on exactly this. Fix in-slice: one paragraph in the PR description (owner needs canvas-internal seams; space-client would need a reverse dependency; pure rules stayed in space-client).

**Minor 2 — the negative compile proof is not pinned in the repo.** The PR claims TS2551 on `useCanvasStore.setState`; the guarantee currently rests on the `CanvasStoreHook` type omitting the member plus the runtime `in` check. A widened wrapper type in a future edit would regress silently at the type level while the runtime pin still passes (the runtime object and the type can drift independently). Fix in-slice: one `// @ts-expect-error` line asserting `useCanvasStore.setState` fails to compile, beside the existing runtime pin in `canvasStore.test.ts`.

**Nit — `canvasIdentityOwner.ts:adoptDefaultWorktree`** spreads `...current` into `setState` while the sibling writers pass partials; zustand merges either way. Align for consistency.

## Builder trust verdict

High. The slice is exactly the adjudicated shape with zero scope creep: every legacy write site deleted rather than wrapped, orderings (guard→URL→identity→reset, capture-before-reset) preserved branch-for-branch, the one intentional dead-code deletion (op 7) correct, and test migrations faithful — including converting tests to the command surface rather than punching test holes, with the two unavoidable escapes explicitly test-named. The self-claimed gates reproduced cleanly. The two minors are documentation/pinning gaps, not code defects.
