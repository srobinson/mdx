# PR #330 review: T2 private identity owner

Reviewed `5a531b2cc114982ab401bb588b9f04038e1621d7..b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c`.

Verdict: **2 Blockers, 2 Majors, 1 Minor.**

## Four answers

1. **Is the compile proof complete? No.**

   `www/packages/canvas/src/model/canvasState.ts:CanvasStoreState` no longer contains `spaceId`, `defaultWorktreeId`, or `canvasId`. A fresh identity patch now fails with TS2353, independently of the hidden public setter. The reported TS2551 proves only that `www/packages/canvas/src/model/canvasStore.ts:CanvasStoreHook` omits `setState`.

   The stronger claim still fails. `www/packages/canvas/src/model/canvasActions.ts:CanvasStoreSet` accepts functional updates whose returned objects are structurally wider than `CanvasStoreState`. This write produced zero diagnostics against the exact Canvas tsconfig and TypeScript 6.0.3:

   ```ts
   set((state) => ({
     ...state,
     spaceId,
     defaultWorktreeId,
     canvasId,
   }));
   ```

   Zustand installs those extra keys at runtime. Field removal therefore does not make every identity write outside the owner fail compilation.

2. **Is the write surface genuinely closed? No.**

   Four independent surfaces remain:

   - `canvasActions.ts:CanvasStoreSet` and `CanvasStoreActionDeps.getStore` retain the unrestricted raw Canvas setter.
   - `canvasIdentityOwner.ts:getCanvasIdentity` and `useCanvasIdentity` expose the live, unfrozen Zustand identity object. Mutable structural aliases, `Object.assign`, and `Reflect.set` all typecheck.
   - `canvasIdentityOwner.ts:resetCanvasIdentityForTests` and `canvasStore.ts:resetCanvasStoreForTests` directly replace authoritative identity outside `IdentityCommand`.
   - `canvasStore.ts:setCanvasStoreStateForTests` accepts a nonfresh, structurally wider patch, while `useCanvasStore.getState` exposes the live Canvas object. Both can recreate legacy identity keys in the Canvas state.

   The raw identity store is module private, the public Canvas hook has no `setState`, and the `activeCanvasId` mirror is gone. Those facts do not close the remaining paths.

3. **Are all twelve routed, and is twelve still the right number? Yes on routing. No on twelve as the current count.**

   The adjudicated base inventory remains twelve and all twelve are accounted for. Consolidation reduces the current direct production mutation count to five under the same rule:

   1. `canvasIdentityOwner.ts:useCanvasIdentityStore` initialization.
   2. `canvasIdentityOwner.ts:initializeFromLaunch` state write.
   3. `canvasIdentityOwner.ts:selectSpace` state write.
   4. `canvasIdentityOwner.ts:adoptDefaultWorktree` state write.
   5. `canvasIdentityOwner.ts:replaceIdentityUrl`.

   Test resets, representable setter capabilities, and per pane Worktree pins remain excluded from this production operation count. They remain relevant to the closed surface audit in answer 2.

4. **Is current product behavior identical to `5a531b2c` for the named paths? Yes.**

   Reload, Worktree switching, launch targeting, cache selection, rehydration, and pane restoration retain the base behavior. The reload to launch defect remains broken:

   - `www/packages/space-client/src/urlTupleCodec.ts:parseCanvasLaunchContext` still marks the URL Canvas unverified.
   - `canvasIdentityOwner.ts:useCanvasIdentityStore` starts from null identity on a fresh page.
   - Without a complete usable source, `urlTupleCodec.ts:resolveCanvasLaunchIdentity` remains unverified.
   - `urlTupleCodec.ts:defaultCanvasId` returns null.
   - `canvasIdentityOwner.ts:initializeFromLaunch` returns before cache selection and rehydration.
   - The later launch therefore still lacks verified Canvas affinity and can reach the existing `canvas_affinity_required` failure.

   The focused identity, switching, persistence, dispatcher, and route files passed 70 of 70 tests through the repository's shell Vitest configuration.

## Findings

### Blocker 1: unrestricted functional setters defeat field removal

**Location:** `www/packages/canvas/src/model/canvasActions.ts:CanvasStoreSet`, line 73; `www/packages/canvas/src/model/canvasStore.ts:useRawCanvasStore`, lines 24 to 33.

**Observation:** Every Canvas action receives `StoreApi<CanvasStoreState>["setState"]`. TypeScript performs excess property checks on a fresh direct patch, but structural return assignment permits extra keys from functional updaters and wider variables.

Two probes against the exact app configuration produced zero diagnostics:

```ts
set((state) => ({
  ...state,
  spaceId,
  defaultWorktreeId,
  canvasId,
}));

set((state) => {
  const next = { cwd: state.cwd, spaceId };
  return next;
});
```

Zustand merges these keys into the live Canvas object.

**Impact:** A future Canvas action can compile while recreating a second mutable identity representation. The central T2 acceptance property, compiler enforced totality, does not hold. T3 and T4 cannot safely rely on this seam.

**Caveat:** No current production action performs such a write. Direct field access and fresh direct patches fail as expected.

**Recommendation:** Pass Canvas actions one restricted setter capability that forbids the three identity keys for direct patches, wider variables, and functional returns. Keep the restriction at the single store construction seam.

[Head source](https://github.com/littleorgans/transport-matters/blob/b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c/www/packages/canvas/src/model/canvasActions.ts#L72-L80)

### Blocker 2: the private owner's live state object escapes

**Location:** `www/packages/canvas/src/model/canvasIdentityOwner.ts:useCanvasIdentity`, lines 72 to 74; `getCanvasIdentity`, lines 76 to 78.

**Observation:** Both APIs pass out the exact object returned by the private Zustand store. `CanvasIdentity` marks its fields `readonly`, but TypeScript permits standard structural mutation paths:

```ts
Object.assign(getCanvasIdentity(), {
  spaceId,
  defaultWorktreeId,
  canvasId,
});

const mutable: { spaceId: SpaceId | null } = getCanvasIdentity();
mutable.spaceId = spaceId;

useCanvasIdentity((identity) =>
  Object.assign(identity, { canvasId }),
);
```

All three forms produced zero diagnostics. Zustand 5.0.14 implements `getState` as a return of the internal state reference.

**Impact:** A caller can alter authoritative identity without an `IdentityCommand`, URL replacement, cache selection, Canvas reset, rehydration, or a Zustand notification. Reactive and imperative readers can remain inconsistent.

**Caveat:** Direct syntax such as `getCanvasIdentity().spaceId = value` fails with TS2540, and every current caller reads only.

**Recommendation:** Expose named scalar hooks and scalar imperative readers. Do not pass the internal identity object to caller supplied selectors or getters.

[Head source](https://github.com/littleorgans/transport-matters/blob/b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c/www/packages/canvas/src/model/canvasIdentityOwner.ts#L66-L82)

### Major 1: production source exports a direct identity reset

**Location:** `www/packages/canvas/src/model/canvasIdentityOwner.ts:resetCanvasIdentityForTests`, lines 125 to 129; `www/packages/canvas/src/model/canvasStore.ts:resetCanvasStoreForTests`, lines 55 to 60.

**Observation:** `resetCanvasIdentityForTests` calls the private owner's raw `setState` with replacement enabled. `resetCanvasStoreForTests` exposes that operation through a second production source module.

**Impact:** Any Canvas source can replace all three authoritative fields outside the closed command union. This path performs none of the paired URL, cache, or rehydration work.

**Caveat:** Neither helper is exported from the `@tm/canvas` package root. Current callers are tests and test support.

**Recommendation:** Remove identity reset from production exports. Give tests an isolated owner or drive the public command surface.

[Owner reset](https://github.com/littleorgans/transport-matters/blob/b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c/www/packages/canvas/src/model/canvasIdentityOwner.ts#L124-L129)  
[Wrapper reset](https://github.com/littleorgans/transport-matters/blob/b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c/www/packages/canvas/src/model/canvasStore.ts#L54-L60)

### Major 2: Canvas test setter and public getter can recreate legacy fields

**Location:** `www/packages/canvas/src/model/canvasStore.ts:setCanvasStoreStateForTests`, lines 62 to 64; `useCanvasStore.getState`, lines 41 to 48.

**Observation:** The test helper is a raw Canvas setter. This structurally wider patch compiles:

```ts
const patch = {
  cwd: null,
  spaceId,
  defaultWorktreeId,
  canvasId,
};
setCanvasStoreStateForTests(patch);
```

This also compiles:

```ts
Object.assign(useCanvasStore.getState(), {
  spaceId,
  defaultWorktreeId,
  canvasId,
});
```

**Impact:** Either path installs the retired identity keys into the live Canvas object, recreating the representation that T2 intends to make impossible.

**Caveat:** Typed readers ignore the injected keys, persistence partialization excludes them, and current helper calls contain only valid Canvas fields.

**Recommendation:** Replace the broad test setter with an exact, narrow test capability. Return a detached snapshot from the public imperative getter, or expose only named imperative reads and actions.

[Head source](https://github.com/littleorgans/transport-matters/blob/b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c/www/packages/canvas/src/model/canvasStore.ts#L41-L64)

### Minor 1: URL ownership remains an absence convention

**Location:** `www/packages/canvas/src/model/canvasIdentityOwner.ts:replaceIdentityUrl`, lines 191 to 193.

**Observation:** The owner contains the sole current production `history.replaceState` call. Canvas sources can still call the global History API directly, and all three tuple URL builders remain public `@tm/space-client` exports.

**Impact:** A future URL only writer can compile and diverge the route tuple from owner state and cache selection.

**Caveat:** The T2 plan explicitly calls for an absence grep for `replaceState`. Current source passes that check. No current production bypass exists.

**Recommendation:** Put the existing absence check into a structural test or lint boundary so the convention fails in CI.

[Head source](https://github.com/littleorgans/transport-matters/blob/b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c/www/packages/canvas/src/model/canvasIdentityOwner.ts#L190-L193)

## Base twelve to current owner mapping

| # | Base operation at `5a531b2c` | Current disposition |
|---:|---|---|
| 1 | `canvasState.ts:createInitialCanvasModel` store initialization | `canvasIdentityOwner.ts:useCanvasIdentityStore` initialization |
| 2 | `canvasStoreLifecycle.ts:initializeCanvas` null Canvas branch | `canvasIdentityOwner.ts:initializeFromLaunch` |
| 3 | `initializeCanvas` switching Canvas branch | Same owner write, followed by isolated Canvas reset and rehydrate |
| 4 | `initializeCanvas` same Canvas branch | Same owner write and rehydrate without reset |
| 5 | `canvasStoreLifecycle.ts:selectSpace` | `canvasIdentityOwner.ts:selectSpace` |
| 6 | `canvasActions.ts:adoptDefaultWorktree` | `canvasIdentityOwner.ts:adoptDefaultWorktree` |
| 7 | `canvasStoreLifecycle.ts:resolveLaunchCanvasId` module assignment | Mirror removed; owner initialization and scalar projection cover it |
| 8 | Direct `activeCanvasId` assignment in `initializeCanvas` | Owner write in `initializeFromLaunch` |
| 9 | `setActiveCanvasId` callback assignment | Mirror and callback removed; cache key projects through `getActiveCanvasId` |
| 10 | Canvas activation URL write | `IdentityCommand` `select-canvas`, then `replaceIdentityUrl` |
| 11 | Space activation URL write | `IdentityCommand` `select-space`, then `replaceIdentityUrl` |
| 12 | Worktree activation URL write | `IdentityCommand` `select-worktree`, then `replaceIdentityUrl` |

## Current write surface inventory

### Intended production paths

- `canvasStore.ts:dispatchCanvasIdentity` accepts the five `IdentityCommand` variants.
- `canvasIdentityOwner.ts:dispatchIdentityCommand` dispatches them.
- `canvasIdentityOwner.ts:useCanvasIdentityStore` performs initialization.
- `canvasIdentityOwner.ts:initializeFromLaunch` changes launch derived identity and cache selection.
- `canvasIdentityOwner.ts:selectSpace` changes Space identity and clears the Canvas.
- `canvasIdentityOwner.ts:adoptDefaultWorktree` fills an absent default Worktree.
- `canvasIdentityOwner.ts:replaceIdentityUrl` performs all three current URL transitions.

### Paths that still typecheck

- Functional updater returns and wider variables passed to any `CanvasStoreSet`.
- Raw `CanvasStoreWithPersistence.setState` reached through `CanvasStoreActionDeps.getStore`.
- Wider variables passed to `setCanvasStoreStateForTests`.
- Mutable structural aliases, `Object.assign`, and `Reflect.set` through `getCanvasIdentity`.
- Mutation inside a caller supplied `useCanvasIdentity` selector.
- `Object.assign` and equivalent mutation through `useCanvasStore.getState` or a Canvas selector.
- `resetCanvasIdentityForTests`.
- `resetCanvasStoreForTests`.
- Direct History API writes, optionally using the public tuple URL builders.

## Behavior equivalence

### Reload

A hard reload still begins with null owner identity. The URL tuple remains unverified, and no new verification wiring exists in this PR. A focused codec probe returned:

```json
{"verified":false,"cacheCanvasId":null,"spaceId":"space-1","worktreeId":"wt-1"}
```

`initializeFromLaunch` therefore returns before cache rehydration. The known reload to launch failure remains.

### Worktree and Canvas switching

Both commands still replace the URL first, resolve the verified launch from that URL and selected tuple, update identity, select the target cache, reset only when the Canvas changes, restore the captured blob, and rehydrate.

### Launching

Captured run, continuation, and terminal launch paths read the owner default Worktree at:

- `canvasActions.ts:addCapturedRun`
- `canvasActions.ts:continueSession`
- `canvasActions.ts:spawnTerminal`

The per spawn Worktree override remains separate. Worktree only and Space only values retain the prior per field current marker semantics.

### Pane restoration

Pane model, persistence reconstruction, minimize, restore, and restore at index logic are unchanged. Only the identity props now come from owner selectors.

## Persistence and non goals

- `www/packages/canvas/src/model/canvasStore.persistence.ts` is byte identical across the range.
- `www/packages/canvas/src/infrastructure/persistence/canvasPersistOptions.ts`, `canvasCacheStorage.ts`, and `storageKeys.ts` are byte identical.
- `CANVAS_STORE_STORAGE_VERSION` remains `1`.
- The persist whitelist and blob projection remain unchanged.
- The only new state is the expected three field private identity owner.
- No generation counter, watermark, receipt, aggregate, verification request, mismatch comparator, shadow store, or dual write bridge appears in the diff.
- No modified test name was removed. The seven changed suites moved from 95 tests to 96.

## Verification

- PR #330 remained open and non draft at exact head `b0734c1a63cdbf536d86c8ad9c8cf66e6233dd7c`.
- The reviewed worktree was pristine before review.
- `git diff --check 5a531b2c..b0734c1a` passed.
- Read only TypeScript compiler probes used TypeScript 6.0.3 and the Canvas app tsconfig.
- A direct fresh identity patch produced TS2353.
- `useCanvasStore.setState` produced TS2551.
- Direct assignment through `getCanvasIdentity` produced TS2540.
- Functional Canvas setters, wider structural patches, mutable identity aliases, `Object.assign`, selector mutation, and `Reflect.set` produced zero diagnostics.
- The five focused files passed through the repository shell Vitest projects: 5 files, 70 tests.
- An earlier direct Canvas package Vitest invocation bypassed the shell jsdom projects and failed on missing `window` and `localStorage`. It was an invalid harness invocation, not a product failure.
- All nine GitHub checks were green at the reviewed head, including frontend, frontend e2e, desktop, standalone, backend, product plane, packaging, and wheel Gateway spawn.
- No local broad gate was run.
