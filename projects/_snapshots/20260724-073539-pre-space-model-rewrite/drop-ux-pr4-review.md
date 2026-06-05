# PR#222 Review — Native + Dock Source Adapters (drop-UX PR 4)

- Branch: `feat/canvas-native-dock-sessions`, HEAD `73e9897`
- Pre-PR baseline: `9735aac` (merged PR 3)
- Diff: +617/-138, 8 files
- Reviewer: `transport-matters:general:2:2.2`
- Method: read-only (`git show`/`git diff`, targeted vitest, boundary+depLint, spec analysis)

## Verdict: REQUEST CHANGES — 1 blocker / 0 majors / 1 minor

Dock migration is clean and behavior-preserving. The **native file** path has a
real regression: it tries to read the file locator during dragover (unreadable
in protected mode), so in the desktop app it now sets `dropEffect="none"` for
file drags, which changes the drop feedback and — per the HTML DnD spec —
suppresses the drop event, breaking native file drops that worked before.

---

## Audit results (hardest first)

### 1. Behavior-preserving execution — MIXED (dock PASS, native file FAIL)
- `onDrop` routing is byte-for-byte unchanged: pane-ref drops still go through
  `handleDockDrop` and everything else through `handleCanvasDrop` using the
  screen-space `point` (`useCanvasDropTargets.ts` → `onDrop`). Those handlers
  are not in the diff. The only edits at the top of `onDrop` are
  `clearDropTarget()` → `endDragSession(); setDropHint(null)`.
- Dragover target detection is equivalent: old `paneIdAtPoint(layout, point)` ≡
  new `resolveCanvasDragTarget({ point: pointerToWorld(viewport, point) })`
  because `paneIdAtPoint` is defined as `paneIdAtWorldPoint(layout,
  pointerToWorld(viewport, point))` (`canvasDrop.ts`).
- `dropEffect` mapping (`dropEffectFor`): copy for pane place, copy for native
  open, move for dock restore, none otherwise — matches the required mapping for
  URL and dock. **But see the Blocker: the native FILE path never reaches
  copy/open in production, so its `dropEffect` regresses to `none`.**

### 2. Migration complete + no gap — PASS
No production caller writes `dropTargetStore` anymore (rg: only the store's own
`setDropTarget`/`clearDropTarget` definitions remain; zero callers). The old
`CanvasDropTargetOverlay` is still mounted beside `CanvasDragSessionOverlay`
(`CanvasWorkbench.tsx:147-148`) but, with no writers, its target is always null,
so it renders nothing (harmless; deleted in PR 5). The new overlay renders pane,
dock, and native sources. No feedback gap.

### 3. Native rules — PARTIAL (see Blocker)
Native sources publish `{kind:"native", payload}` with `origin:{kind:"none"}`
(`nativeDragSource`, `onDragOver`). URL handling is correct: the uri-list is
readable during dragover, so a URL resolves to pane `place` over a paste pane or
surface `open` otherwise, `dropEffect` copy. The desktop-bridge hint appears only
at a target candidate and clears on dragleave/drop (unit + e2e). The FILE path is
where rule fidelity breaks (Blocker).

### 4. Dock protected mode + origin — PASS
Dock dragover still consults the in-memory holder via `readActiveDockDrag()` →
`dockDragSource(entry)` (browsers hide the custom payload during protected
dragover), and the dock locator resolves synchronously from `entry.ref`, so dock
place/restore feedback and `dropEffect` (copy/move) are correct and unchanged.
`PaneDock.rowDragStart` begins a dock session with `origin:{kind:"dock"}`;
`rowDragEnd` calls `endDragSession`. Origin rendering shows the dashed
`canvas-dock__origin-placeholder` at the original index plus the faded
`canvas-dock__row--origin` (opacity 0.48) row — matches the approved treatment,
with CSS class hooks present (`pane-dock.css`). Kill button keeps
`draggable={false}` + `onPointerDown={killPointerDown}`, so a kill press never
initiates a drag.

### 5. Cleanup — PASS
`endDragSession` fires on native drop (`onDrop`), native dragleave
(`onDragLeave`), effect teardown (return cleanup), and dock drag end
(`rowDragEnd`). Tests assert `session === null` after drop and dragleave.

### 6. E2E — PASS (spec sound; not executable in this env)
`canvas-drop-ux.spec.ts` gains the four required tests, all real (not
skipped/weakened): `native url drag uses shared target overlay with no origin`,
`unresolved native file drag shows hint only at a target candidate`, `dock row
drag fades row and shows dashed placeholder`, `dock row drag over terminal uses
shared place target`. Note: these run in a plain browser (no desktop bridge), so
none exercises the desktop file path that regresses (see Blocker). e2e was not
executed here — the pre-existing baseline spec fails identically at
`.canvas-route-shell` page load (environmental, verified in the PR 3 review).

### 7. Boundaries — PASS
No `dnd`/`interactions` production import of `viewers`/`terminal`.
`importGraphBoundary` + `depLint` green.

## Verification run
- `vitest run useCanvasDropTargets PaneDock dockDragSource CanvasDragSessionOverlay dragSessionStore resolveCanvasDragTarget canvasDrop importGraphBoundary depLint` → 10 files, 75 passed.

---

## Findings

### BLOCKER — native file dragover sets `dropEffect="none"`, breaking desktop file drops
`www/packages/canvas/src/dnd/useCanvasDropTargets.ts` → `nativeDragSource` /
`firstTransferredFile` / `firstFileLocator`, consumed by `onDragOver`.

`nativeDragSource` builds the file locator from `transfer.files[0]`
(`firstTransferredFile`) during **dragover**. In protected-mode dragover
`DataTransfer.files` is empty in both the browser and Electron — the code's own
comments state "neither exposes its payload until drop." So for `payload:"files"`
the locator is always `null` during dragover, regardless of the desktop bridge.
`resolveCanvasDragTarget` then returns `hint` (at a candidate) or `none`, both
with `effect:"none"`, and `dropEffectFor("none")` sets
`dataTransfer.dropEffect = "none"`.

Consequences vs. the `9735aac` baseline:
- **Feedback regression (confirmed):** the old code used `canResolveDroppedFiles()`
  (a capability check, not the unreadable file) to show a `surface`/open target
  with `dropEffect="copy"` for file dragover when the bridge is present. The new
  code dropped that capability proxy (removed the `canResolveDroppedFiles`
  import), so inside the desktop app a file dragover now shows the "File drops
  need the desktop app. URL drags work here." hint — while running in the desktop
  app — and a no-drop cursor.
- **Drop suppression (high-confidence, needs desktop verification):** per the
  WHATWG HTML drag-and-drop model, after a canceled `dragover` the current drag
  operation is set from `dropEffect`; `dropEffect="none"` ⇒ current drag
  operation `none` ⇒ the `drop` event does not fire (dragleave fires instead).
  Old code set `dropEffect="copy"` for all native drags, so the drop fired and
  `handleCanvasDrop` resolved the path (available on drop) and spawned/pasted.
  With the new `none`, releasing a real OS file over the canvas (or over a
  terminal for paste) in the desktop app would no longer fire `drop`, so no pane
  is spawned and no paste occurs. This is a change to what a native file drop
  *does*, which the plan's global constraint forbids.

False confidence: the unit test `keeps resolved file drags on the native open
path when the bridge can resolve paths` passes only because the fake
`DataTransfer` exposes `files` during dragover; real browsers/Electron do not, so
that branch is dead in production. No unit or e2e test covers the desktop file
dragover path.

Suggested fix: restore the capability proxy for file dragover. When
`payload:"files"` and no file is readable yet, branch on
`canResolveDroppedFiles()`: bridge present ⇒ treat as pane `place` over a paste
pane / surface `open` otherwise, `effect:"copy"` (so the drop fires and the path
resolves on drop); bridge absent ⇒ keep the `hint`/`none`. The resolver as
written cannot see the bridge, so this belongs in `nativeDragSource`/the dragover
wiring, and should be locked with a bridge-present, files-empty-during-dragover
test plus a desktop e2e or manual check that a real file drop still spawns/pastes.

### MINOR — per-tick session churn (carried from PR 3, now also on native/dock)
`www/packages/canvas/src/interactions/dnd/dragSessionStore.ts` →
`updateDragSessionTarget` (called by `onDragMove`/`onDragOver`).

`updateDragSessionTarget` always allocates a fresh session object even when
`target`/`effect` are unchanged, so `CanvasDragSessionOverlay`
(`useDragSessionStore(selectDragSession)`) re-renders on every dragover tick with
identical DOM. `useCanvasDropTargets.publishDragSession` already guards the
*begin* transition with `sameDragSessionIdentity`, but the per-tick target update
is unguarded. This was raised in the PR 3 review; the DRY fix (guard for
unchanged `target`+`effect` inside `updateDragSessionTarget`) resolves it for
pane, native, and dock at once. Feedback-render churn only; not blocking.
