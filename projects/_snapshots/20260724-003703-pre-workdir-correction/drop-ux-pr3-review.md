# PR#221 Review — Pane Drag Source Adapter (drop-UX PR 3)

- Branch: `feat/canvas-pane-drag-sessions`, HEAD `1b5435b`
- Pre-PR baseline: `ffc1c3c`
- Diff: +275/-43, 6 files
- Reviewer: `transport-matters:general:2:2.2`
- Method: read-only (`git show`/`git diff`, targeted vitest, boundary+depLint suites, e2e attempt)

## Verdict: APPROVE — 0 blockers / 0 majors / 1 minor

First behavior-visible slice is clean. Drop execution is byte-for-byte
preserved; the PR changes only which feedback store the pane path publishes to.
One non-blocking perf-churn minor.

---

## Audit results (hardest first)

### 1. Behavior-preserving execution — PASS
`git show ffc1c3c:.../paneDndCallbacks.ts` vs HEAD: `onDragEnd` delivery body is
identical. The paste-wins-over-reorder branch (`terminal && locator` →
`terminal.paste(...)`), the reorder branch (`overId !== activeId && overId !==
getExpandedPaneId()` splice + `commitReorder`), the expanded-hero exclusion, and
the viewport coordinate conversion (`dragWorldPoint` → `pointerToWorld`) are all
unchanged. The only edit inside `onDragEnd`/`onDragCancel` is
`clearDropTarget()` → `endDragSession()`. `deliveryTargetAt` (symbol) is
untouched and still governs the release outcome. No paste/spawn/reorder drift.

### 2. Migration correctness — PASS
- `paneDndCallbacks.ts` and `CanvasPaneDnd.tsx` no longer import or write
  `dropTargetStore` (removed `setDropTarget`/`clearDropTarget`/`useDropTargetStore`).
  The pane path now publishes only to `dragSessionStore`
  (`beginDragSession`/`updateDragSessionTarget`/`endDragSession`).
- Native/dock paths untouched: `useCanvasDropTargets.ts`, `PaneDock.tsx`,
  `dockDragSource.ts` are absent from the diff and still reference
  `useDropTargetStore` (verified by rg). Each source writes exactly one store,
  so the coexisting old `CanvasDropTargetOverlay` and new
  `CanvasDragSessionOverlay` never double-render and there is no feedback gap.

### 3. Target + origin rules — PASS
`resolveCanvasDragTarget` (symbol) returns a pane `place` target with label
``Drop to place ${name}`` ONLY when `targetPaneId !== null && sourceLocator !==
null && resolvePasteHandle(targetPaneId) !== null`. These are the exact three
conditions `deliveryTargetAt` uses to deliver, so live feedback lights iff a
release would actually paste (feedback/execution parity). Normal panes (no paste
handle) fall through to `{ kind: "none" }`. `onDragStart` seeds origin
`{ kind: "pane", paneId: activeId }`, rendered by `renderOriginLayer`. Unit test
`move over a paste-handle pane publishes a place target for locator panes` and
e2e `pane resource drag over normal pane shows no pane target` confirm both arms.

### 4. Cleanup — PASS
`endDragSession()` fires on `onDragEnd`, `onDragCancel`, and the `CanvasPaneDnd`
unmount effect (`() => { setPaneDragCursor(null); endDragSession(); }`). Tests
assert `session === null` after cancel and after a paste-delivery end.

### 5. Cursor — PASS
`paneDragCursorMode(effect: CanvasDragEffect)` returns `deliver` for `copy`, else
`move`, matching the old terminal→deliver semantics (`place` resolves to effect
`copy`). Cursor is derived post-`onDragMove` from the session effect, so it is
not the only feedback (overlay carries the target). `paneDragCursorMode`/
`setPaneDragCursor` are used only in `CanvasPaneDnd.tsx` (verified by rg); the
not-yet-migrated native/dock cursor path is untouched.

### 6. E2E — PASS (spec sound; not executable in this env)
`canvas-drop-ux.spec.ts` has the three required tests, all real (not
skipped/weakened): `pane resource drag shows origin and terminal place target`,
`pane resource drag over normal pane shows no pane target`, `pane drag cancel
clears origin and target overlays`. Fixtures are correct (terminal seeds a paste
handle; the "Normal pane" is a `session-timeline` pane with none). Assertions
target the real overlay classes (`--pane-origin`, `--pane-target`,
`__origin-title`, `Drop to place …`, and `Paste into` count 0).
Execution note: the Chromium run failed at `expect('.canvas-route-shell')
.toBeVisible()` in `beforeEach`. The pre-existing `canvas-persistence.spec.ts`
fails identically at the same page-load gate, so this is an environmental
server/build issue in this session, not a PR#221 defect.

### 7. Boundaries — PASS
No `dnd`/`interactions/dnd` production import of `viewers` or `terminal` (rg
clean); paste capability comes via `interactions/pasteTargetRegistry`.
`importGraphBoundary` + `depLint` suites green (11 tests).

## Verification run
- `vitest run paneDndCallbacks CanvasDragSessionOverlay dragSessionStore resolveCanvasDragTarget dragCursor` → 5 files, 41 passed.
- `vitest run importGraphBoundary depLint` → 2 files, 11 passed.
- e2e Chromium → blocked at page load (environmental; baseline spec fails the same way).

---

## Findings

### MINOR — per-tick overlay churn: dropped change-guard
`www/packages/canvas/src/interactions/dnd/dragSessionStore.ts` →
`updateDragSessionTarget` (called by `paneDndCallbacks.onDragMove`).

The retired `writeTerminalTarget` was explicitly change-guarded ("Per-tick
writes are change-guarded so a held pointer does not churn the overlay store with
identical terminal targets"). The replacement `onDragMove` calls
`updateDragSessionTarget` every tick, and that action always builds a fresh
session object (`{ ...state.session, target, effect }`) even when `target`/
`effect` are unchanged. `CanvasDragSessionOverlay` subscribes via
`useDragSessionStore(selectDragSession)` (returns `state.session`), so it
re-renders on every `onDragMove` tick — including the origin layer, which never
changes during a drag — producing identical DOM.

Impact: feedback-render churn only; drop execution and rendered output are
unaffected. Not a blocker.

Suggested fix (DRY, also benefits the PR 4 native/dock adapters): guard inside
`updateDragSessionTarget` to return the same state when the incoming `target`
(shallow/structural compare) and `effect` equal the current session's, mirroring
the old change-guard.
