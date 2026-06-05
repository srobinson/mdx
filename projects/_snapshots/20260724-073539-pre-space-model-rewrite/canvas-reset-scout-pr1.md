# Canvas Reset Scout PR 1

Scope: PR 1 of `docs/superpowers/plans/2026-07-05-canvas-repo-reset.md`, Tasks 0, 1, and 2 only.

Worktree: `git status --short` was clean before and after the scout.

## Reuse Map

### Import graph harness

`www/packages/shell/src/testSupport/importGraph.ts` exports these reusable symbols:

- `ImportSpecifier`
- `sourceFiles`
- `sourceFile`
- `importSpecifiers`
- `exportedNames`
- `isInside`
- `relativeTo`
- `isTestSupportSource`
- `resolveLocalSpecifier`
- `packageExportsMap`

Task 1 should reuse the harness directly:

- `sourceFiles(root)` recursively enumerates `.ts` and `.tsx` files.
- `importSpecifiers(file)` parses static imports, re-exports, dynamic imports, and `import(...)` types.
- `resolveLocalSpecifier(file, specifier, srcRoot)` resolves relative imports, `@/`, `@tm/`, `components/`, and `session-canvas/`. For `@tm/` packages, it resolves through package `exports` and fails closed for undeclared subpaths.
- `isInside(candidate, root)` is the existing path containment check.
- `relativeTo(root, file)` is the existing stable path formatter.

`www/packages/shell/src/testSupport/labBoundary.test.ts` consumes the harness like this:

- Computes `CANVAS_SRC`, `SESSION_CANVAS_ROOT`, `SRC_ROOT`, and `LAB_ROOT`.
- Enumerates `sourceFiles(SESSION_CANVAS_ROOT)`.
- Excludes lab files with `isInside(file, LAB_ROOT)`.
- For each import, calls `resolveLocalSpecifier(file, specifier, SRC_ROOT)`.
- Flags a violation when the resolved target is inside `LAB_ROOT`.
- Emits one string per violation and expects the violation list to equal `[]`.
- Separately scans lab exports with `sourceFile` and `exportedNames`.

`www/packages/shell/src/testSupport/importGraphBoundary.test.ts` consumes the harness like this:

- `crossProductViolations(fromSrc, forbiddenSrc)` enumerates `sourceFiles(fromSrc)`, resolves each local import with `resolveLocalSpecifier`, and flags targets inside `forbiddenSrc`.
- `packageInternalViolations(packageSrc, packageEntrypoint)` enumerates all package source files, resolves local imports through `packageSrcRootFor(file)`, and flags imports into a package source tree except the package entrypoint.
- `rootPackageExports` reads package manifests through `packageExportsMap`.
- The test already proves fail closed behavior for unresolved local aliases and deep package reach-ins outside an `exports` map.

The plan says the allow list should follow `labBoundary.test.ts`. Current fact: `labBoundary.test.ts` has no temporary allow list. It has the useful one string per violation pattern, then asserts `[]`. A PR 1 allow list would be new test code, but should preserve that string per violation style.

### Existing pane identity owner

There is no existing `www/packages/canvas/src/session-canvas/model/paneIdentity.ts`, no sibling identity module, no `OWNERSHIP.md`, and no `sessionCanvasBoundary` test.

`www/packages/canvas/src/session-canvas/model/paneRecords.ts` already owns the model vocabulary used by identity:

- `CanvasPaneRef`
- `PaneContentRef`
- `PickerPaneRef`
- `PaneRecord`
- `ViewerId`
- `harnessLabel`
- `locatorTail`

`harnessLabel` and `locatorTail` should be reused by `model/paneIdentity.ts`; do not duplicate their logic.

### Viewer registry ownership split

`www/packages/canvas/src/session-canvas/viewers/registry.tsx` currently owns two different concerns.

Move to `www/packages/canvas/src/session-canvas/model/paneIdentity.ts`:

- `PICKER_PANE_ID`
- `TRANSCRIPT_PANE_PREFIX`
- `SUBAGENT_PANE_PREFIX`
- `RESOURCE_PANE_PREFIX`
- `EXCHANGE_PANE_PREFIX`
- `resourceRefTitle`
- `paneIdForRef`
- `titleForRef`
- `viewerIdForRef`

Keep in `www/packages/canvas/src/session-canvas/viewers/registry.tsx`:

- `TerminalPane`
- `CapturedRunPane`
- `defineViewer`
- `registry`
- `registerViewer`
- `resolveViewer`
- `bodyDragForRef`
- `renderPaneContent`
- `PaneShell`

Reason: pane id, title, and viewer id are persisted model vocabulary. Lazy imports, React rendering, suspense fallbacks, pane shell state rendering, and body drag policy are viewer concerns.

`viewerIdForRef` should move with the model identity helpers. Evidence: `PaneRecord.viewerId` is part of the model record, `model/spawn.ts` writes it in `createPaneRecord`, and `lab/CanvasLabRoute.tsx` synthesizes `ViewerProps` with it.

## Dependency Map

### Production model to viewers imports

`www/packages/canvas/src/session-canvas/model/canvasStore.ts`

- Imports from `../viewers/registry`: `PICKER_PANE_ID`, `paneIdForRef`, `titleForRef`.
- Uses `PICKER_PANE_ID` to protect the picker from close.
- Uses `titleForRef` when docking a pane and when spawning a pane.
- Uses `paneIdForRef` as the `runSpawnPaneFlow` dedupe key.
- Uses `PICKER_PANE_ID` when parking a protected picker pane in the dock path.

`www/packages/canvas/src/session-canvas/model/spawn.ts`

- Imports from `../viewers/registry`: `paneIdForRef`, `viewerIdForRef`.
- Uses both in `createPaneRecord`.

`www/packages/canvas/src/session-canvas/model/canvasStore.persistence.ts`

- Imports from `../viewers/registry`: `titleForRef`.
- Uses it in `paneRecordsFromRefs` when rebuilding missing pane records from persisted refs.

No other production `model/*` file imports `viewers/registry`.

### Model tests and persistence tests reaching viewer identity

`www/packages/canvas/src/session-canvas/model/paneRecords.test.ts`

- Imports `paneIdForRef`, `titleForRef`.
- Asserts locator resource pane ids and titles.

`www/packages/canvas/src/session-canvas/model/canvasStore.test.ts`

- Imports `PICKER_PANE_ID`.
- Asserts focus, open set, and expand behavior around the picker pane id.

`www/packages/canvas/src/session-canvas/lab/canvasLabStore.persistence.test.ts`

- Imports `titleForRef`.
- Uses it to assert titles survive reload.

`www/packages/canvas/src/session-canvas/viewers/registry.test.ts`

- Imports `paneIdForRef`, `resolveViewer`, `titleForRef`, `viewerIdForRef`.
- Owns most current identity expectations. These identity cases should move to a model level `paneIdentity.test.ts`. Keep viewer resolution cases around `resolveViewer`.

`www/packages/canvas/src/session-canvas/viewers/placeholder/PlaceholderPane.test.tsx`

- Imports `titleForRef` from `../registry`.
- Uses it to prove subagent title flow. After the move, it should import title identity from the model or pass an explicit title fixture.

### Other non model consumers

`www/packages/canvas/src/session-canvas/components/CanvasSurface.tsx`

- Imports `bodyDragForRef`, `PICKER_PANE_ID`, `renderPaneContent`.
- After Task 2, import `PICKER_PANE_ID` from `model/paneIdentity` and keep `bodyDragForRef` plus `renderPaneContent` from `viewers/registry`.

`www/packages/canvas/src/session-canvas/components/PaneDock.tsx`

- Imports `titleForRef`.
- Should import it from `model/paneIdentity`.

`www/packages/canvas/src/session-canvas/lab/canvasLabStore.ts`

- Imports `paneIdForRef`.
- Should import it from `model/paneIdentity`.

`www/packages/canvas/src/session-canvas/lab/CanvasLabRoute.tsx`

- Imports `bodyDragForRef`, `renderPaneContent`, `titleForRef`, `viewerIdForRef`.
- Keep `bodyDragForRef` and `renderPaneContent` in viewer registry.
- Move `titleForRef` and `viewerIdForRef` imports to `model/paneIdentity`.

## Quality Map

### Clean move

The identity extraction is mechanically clean. The functions being moved are pure with stable inputs:

- `paneIdForRef(ref: CanvasPaneRef): PaneId`
- `titleForRef(ref: CanvasPaneRef): string`
- `viewerIdForRef(ref: CanvasPaneRef): ViewerId`

They can depend on model types plus the existing `harnessLabel` and `locatorTail` helpers. No React, Zustand, DOM, storage, lazy import, or viewer component is needed.

### Hidden coupling

`www/packages/canvas/src/session-canvas/model/paneRecords.ts` defines `ViewerRegistration.render` as returning `React.ReactNode`. That is React type coupling inside the model even though there is no `react` import. A boundary test that only checks imports will not catch it.

`www/packages/canvas/src/session-canvas/model/canvasStore.ts` and `www/packages/canvas/src/session-canvas/model/capturedRunStore.ts` import Zustand. The Task 1 rule "model must not import React or Zustand" will fail immediately unless PR 1 adds a temporary allow list or scopes that rule to future work.

`www/packages/canvas/src/session-canvas/dnd/canvasDrop.ts`, `www/packages/canvas/src/session-canvas/dnd/paneDndCallbacks.ts`, and `www/packages/canvas/src/session-canvas/dnd/useCanvasDropTargets.ts` import `../viewers/terminal/pasteRegistry`. That is the dnd to terminal viewer boundary leak named by the plan. It is adjacent debt, not part of the pane identity move.

`viewerIdForRef` can drift if it becomes a switch in `paneIdentity.ts` while `viewers/registry.tsx` keeps independent `id` values in each registration. Avoid duplicate truth by making the model mapping canonical and keeping tests that assert `resolveViewer(ref).id === viewerIdForRef(ref)`.

`registerViewer` is exported from `viewers/registry.tsx`, but no repo caller uses it. It is not exported through `@tm/canvas`. Treat it as an internal extension hook or delete it in a later viewer registry cleanup; PR 1 does not need to decide.

### Duplication and dead code

No duplicate identity implementation currently exists. All pane id and title logic is centralized in `viewers/registry.tsx`, but that central location is the boundary violation.

`registerViewer` is the only dead code candidate in this area. It has no call sites in `www/packages/canvas/src`, `www/packages/shell/src`, `www/packages/host/src`, `www/packages/inspector/src`, or `packages`.

## Verification Map

### Existing command status

`cd www/packages/shell && pnpm exec vitest run "paneRecords|canvasStore|registry|sessionCanvasBoundary"`

- Observed result: exit code 1.
- Vitest reported no test files found.
- Cause: the quoted pipe string is treated as a file filter, not a regular expression over test names or paths.
- Current tree also has no `sessionCanvasBoundary` test yet.

`pnpm --filter @tm/canvas typecheck`

- Observed result: exit code 0.
- It resolves `@tm/canvas` from `pnpm-workspace.yaml`.
- It runs the package script `tsc -b --noEmit`.

### Named tests present now

Present:

- `www/packages/canvas/src/session-canvas/model/paneRecords.test.ts`
- `www/packages/canvas/src/session-canvas/model/paneRecords.contract.test.ts`
- `www/packages/canvas/src/session-canvas/model/canvasStore.test.ts`
- `www/packages/canvas/src/session-canvas/model/canvasStore.persistence.test.ts`
- `www/packages/canvas/src/session-canvas/viewers/registry.test.ts`

Absent:

- `www/packages/canvas/src/session-canvas/sessionCanvasBoundary.test.ts`

Additional broad matches for `registry`:

- `www/packages/canvas/src/engine/layout/registry.test.ts`
- `www/packages/canvas/src/session-canvas/viewers/terminal/pasteRegistry.test.ts`

Recommended verification spelling for PR 1 after adding `sessionCanvasBoundary.test.ts`:

```sh
cd www/packages/shell
pnpm exec vitest run \
  ../canvas/src/session-canvas/model/paneRecords.test.ts \
  ../canvas/src/session-canvas/model/paneRecords.contract.test.ts \
  ../canvas/src/session-canvas/model/canvasStore.test.ts \
  ../canvas/src/session-canvas/model/canvasStore.persistence.test.ts \
  ../canvas/src/session-canvas/viewers/registry.test.ts \
  ../canvas/src/session-canvas/sessionCanvasBoundary.test.ts
pnpm --filter @tm/canvas typecheck
```

## Plan

1. Add `www/packages/canvas/src/session-canvas/OWNERSHIP.md` exactly around the plan's ownership terms: workbench, model, viewers, interactions, launcher, infrastructure, lab, allowed direction, forbidden imports, pane identity in model, registry as renderer.

2. Add `www/packages/canvas/src/session-canvas/sessionCanvasBoundary.test.ts` using `sourceFiles`, `importSpecifiers`, `resolveLocalSpecifier`, `isInside`, and `relativeTo` from `www/packages/shell/src/testSupport/importGraph.ts`.

3. In the boundary test, start with rules that PR 1 can make true without widening scope:

- `session-canvas/model` must not import `session-canvas/viewers`.
- `session-canvas/persistence` must not import `session-canvas/viewers`.
- product files must not import `session-canvas/lab`.

4. If the full plan rules are included immediately, add explicit temporary allow list entries for the current Zustand and dnd terminal paste registry violations. The React namespace use in `model/paneRecords.ts` needs a text or AST check beyond import graph resolution.

5. Create `www/packages/canvas/src/session-canvas/model/paneIdentity.ts` with the canonical identity helpers:

- `PICKER_PANE_ID`
- `paneIdForRef`
- `titleForRef`
- `viewerIdForRef`

6. Update imports:

- `model/canvasStore.ts` imports all identity helpers from `model/paneIdentity`.
- `model/spawn.ts` imports `paneIdForRef` and `viewerIdForRef` from `model/paneIdentity`.
- `model/canvasStore.persistence.ts` imports `titleForRef` from `model/paneIdentity`.
- `components/CanvasSurface.tsx` imports `PICKER_PANE_ID` from `model/paneIdentity`.
- `components/PaneDock.tsx`, `lab/canvasLabStore.ts`, `lab/CanvasLabRoute.tsx`, and affected tests import id and title helpers from `model/paneIdentity`.

7. Keep `viewers/registry.tsx` as rendering registry only. It should still resolve renderers and body drag policy. Move identity assertions out of `viewers/registry.test.ts` to a model identity test, then keep only viewer resolution and rendering registry assertions there.

8. Run the corrected Vitest file list and `pnpm --filter @tm/canvas typecheck`.
