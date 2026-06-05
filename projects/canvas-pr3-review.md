# Canvas PR 3 Review — Store Decomposition

**PR:** #209 · branch `refactor/canvas-store-split` · HEAD `62fdc69` (pre-split main `78ebf42`)
**Scope audited:** Task 3 / "PR 3: Store Decomposition" of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`
**Diff:** +627/-483 across 4 files (all `session-canvas/model/`)
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only, tree untouched)
**Date:** 2026-07-05

## Verdict: **PASS** — 0 blockers / 0 majors / 0 minors

Behavior-preserving. `canvasStore.ts` is split into `canvasState.ts` (shape +
`createInitialCanvasModel`), `canvasActions.ts` (all actions + helpers), and
`canvasStoreLifecycle.ts` (module-level canvasId mirror, legacy import,
`initializeCanvas`); `canvasStore.ts` remains the thin Zustand assembly. Every
extracted unit is byte-equivalent in logic and sequencing to pre-split. Verified by
line-by-line diff of `git show 78ebf42:...canvasStore.ts` against the four files,
plus the unmodified 717-line store test suite passing green.

Evidence of green:
- `pnpm exec vitest run canvasStore canvasStore.persistence sessionCanvasBoundary` → **43 passed** (3 files).
- `pnpm --filter @tm/canvas typecheck` → exit 0.
- Zero test files changed in the PR (`git diff --name-only` → no `*test*`).

---

## Audit findings (four points, hardest first)

### 1. Persist / rehydrate ordering preserved byte-for-byte — PASS

**Module-load legacy-import-before-`create()` invariant holds.** Pre-split,
`activeCanvasId = resolveLaunchCanvasId()` and the one-time
`importLegacyCanvasCache(activeCanvasId, localStorage)` ran at module load, before
`create()`. Post-split these sit in `canvasStoreLifecycle.ts` (`resolveLaunchCanvasId`
+ the `if (window && localStorage)` import block), which `canvasStore.ts` imports.
ES module evaluation runs an imported module's body before the importer's body, so
the legacy import still fires before `create()` in `canvasStore.ts`. The import chain
`canvasStore -> canvasStoreLifecycle -> canvasState` has no side effect in
`canvasState` (only a frozen const and a function), so nothing reorders.

**`initializeCanvas` sequence is identical, step for step** (pre-split action vs
`canvasStoreLifecycle.initializeCanvas`): `defaultCanvasId(launch)` →
`switchingCanvas` compare (`get()`→`getState()`) → `activeCanvasId = canvasId` →
`importLegacyCanvasCache` → `canvasCacheKey` → `getItem(cacheKey)` → branch
`setState(createInitialCanvasModel(launch, setActiveCanvasId))` (switching) vs
`setState((state) => ({...state, canvasId, spaceId: launch.spaceId ?? state.spaceId,
defaultWorktreeId: launch.worktreeId ?? state.defaultWorktreeId, launch,
workspaceHash}))` (same canvas) → conditional `setItem(cacheKey, cached)` restore →
`persist.rehydrate()`. No reordered assignment, no moved side effect, no changed
init-vs-restore precedence.

**`activeCanvasId` mutation parity.** Pre-split `createInitialCanvasModel` always set
the module var; post-split it calls an optional `setActiveCanvasId?` callback. All
three call sites that correspond to pre-split's mutation points pass the setter:
`canvasStore.ts` store creation, `canvasStore.ts` `resetCanvasStoreForTests`, and
`canvasStoreLifecycle.ts` `initializeCanvas` switching branch. No call site omits it,
so the double-set (direct assign in `initializeCanvas` + callback in
`createInitialCanvasModel`, both to the deterministic `defaultCanvasId(launch)`) is
preserved.

**Risk path is actually exercised, not untested-green.** The passing suite calls
`initializeCanvas` 12 times, including "switching to a new canvas starts isolated,
not a clone of the previous canvas" (the switching + rehydrate branch), the
worktree-less desktop mount order, and re-init worktree-adoption precedence;
`persist.rehydrate()` is driven directly. Unmodified against the split → strong
behavior-preservation signal on top of the diff.

### 2. Thin assembly preserved — PASS

`canvasStore.ts` (43 lines) exports `useCanvasStore` and `resetCanvasStoreForTests`,
re-exports `CanvasStoreState`/`SpawnPaneOptions`, and composes state + actions inside
`create(persist(...))`. Persistence wiring stays at the store edge:
`createCanvasStorePersistOptions(getActiveCanvasId)` is still the 2nd arg to
`persist()`, and `canvasStore.persistence.ts` is untouched (not in the diff). The
`getActiveCanvasId` getter replaces the pre-split `() => activeCanvasId` closure with
identical lazy-read semantics. The three new files are pure extraction — no new
behavior.

### 3. No scope bleed — PASS

Exactly 4 files changed, all under `session-canvas/model/`. No React component
touched (no PR 5 bleed), no `dnd`/`viewers` (no PR 4), no `CanvasSurface`, no
`persistence/*`. Zero test files modified: the 717-line `canvasStore.test.ts` runs
unchanged (imports `resetCanvasStoreForTests, useCanvasStore` from `./canvasStore`
and `PICKER_PANE_ID` from `./paneIdentity` — surface preserved), so no assertion
changed, only the implementation moved beneath it.

### 4. DRY / boundary — PASS

Helpers (`insertPane`, `planCanvasLayout`, `focusCanvasPane`, `canvasPaneRef`,
`isCapturedRunRef`, `applyCanvasPaneRemoval`) are defined once, in `canvasActions.ts`;
none re-declared in the other files. No action or state definition is duplicated
across the split. None of the three new files imports `viewers` (grep clean).
`sessionCanvasBoundary` (`model !-> viewers`, `persistence !-> viewers`) passes; the
new `canvasActions`/`canvasState`/`canvasStoreLifecycle` imports are all
model/engine-internal, introducing no `model -> viewers` edge.

---

## Considered and dismissed (not findings)

- **`getStore()` returns `useCanvasStore` typed as the narrower
  `CanvasStoreWithPersistence` (Pick of getState/setState/persist.rehydrate)** where
  pre-split passed the full Zustand hook to `dismissPane`/`initializeCanvas`. This is
  a type-level narrowing only; the runtime object is the identical `useCanvasStore`.
  Typecheck passes, so `dismissPane` and the lifecycle fn receive everything they use.
  No behavior impact.

## Verification note

Read-only throughout: `git show` for pre-split state, no branch switch, no temp
files. `git status` clean after review.
