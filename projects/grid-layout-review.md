# Review — Pane Chrome Frame/Expand Icon Polish

**PR:** #217 · branch `feat/canvas-pane-chrome-frame-icons` · HEAD `bc3b1a1` (pre-PR main `471f987`)
**Diff:** +272/-57 across 12 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only, tree untouched)
**Date:** 2026-07-06

## Verdict: **PASS** — 0 blockers / 0 majors / 0 minors

All three changes land correctly: Frame now animates through the unified viewport-motion
path, the Frame/Expand icons gate on open-pane count `>= 3`, and the expanded pane hides
Frame while keeping Expand. Animation is a real CSS transition, the gating matrix is
correct and fully unit-tested, and the e2e spec adjustment is legitimate. Two positive
behavior observations and one verification note below (no defects).

Evidence:
- `pnpm --filter @tm/shell test` (full suite) → **1108 passed** (155 files).

---

## Audit findings (four points, hardest first)

### 1. Frame animation is real, shared cleanly with expand — PASS

`planPaneFrame` already returned `fly: "camera"`, but pre-PR `framePane` called
`commitPaneAffordanceTransition(planPaneFrame(...), set)` with **no** `onFly`, so
`commitPaneAffordanceTransition` stripped the fly intent (`stripPaneFlyIntent`) and the
frame snapped instantly. The fix wires it through:
- `framePane` → the new `commitPaneTransition` helper → `commitPaneAffordanceTransition(t,
  set, (intent) => setPaneFlyIntent(set, intent))` → `paneFlyIntent = "camera"` →
  `CanvasWorkbench` `viewportMotion={paneFlyIntent === "camera"}` → `CanvasPaneLayer`
  `framing={viewportMotion}` → `LayoutCanvas` `.canvas-world--framing`.
- `.canvas-world--framing` is a **real** transition: `transition: transform 320ms
  cubic-bezier(0.22,1,0.36,1)` (with `prefers-reduced-motion: reduce → none`). The
  320ms matches `PANE_FLY_INTENT_MS`, and `setPaneFlyIntent` resets the intent to `"none"`
  after that window so the class is applied only during the transition. The framed
  viewport is set in `layout` while the class animates the transform — concurrent, not a
  bypass/snap.
- **Expand still animates, no regression**: `expandPane` routes through the same
  `commitPaneTransition` helper; `planPaneExpand` returns `fly: "pane-motion"` →
  `paneMotion={reorderActive || paneFlyIntent === "pane-motion"}` drives the sibling
  reflow.
- **DRY**: one `commitPaneTransition` closure serves `expandPane`, `framePane`,
  `unexpand`, `unframe` — not copied per-action.
- Tested: `CanvasPaneLayer.test.tsx` "passes the camera motion flag to the engine framing
  transition".

### 2. Icon gating matrix — PASS

`CanvasPaneLayer` computes `frameExpandEnabled = openPaneIds(layout).length >= 3` — from
**open** panes (not docked, not picker-special-cased beyond being an open node), exact
`>= 3` boundary. When disabled, it withholds the callbacks (`onExpand`/`onFrame`
`undefined`); `PaneWindow` makes them optional; `PaneChrome` renders Frame on
`onFrame && !expanded` and Expand on `onExpand` (with `pressed={expanded}`). Matrix:
- open `< 3`: both `undefined` → both hidden.
- open `>= 3`, not expanded: both passed → both shown.
- open `>= 3`, expanded: Frame hidden (`&& !expanded`), Expand shown (toggles to unexpand).

All four cells are unit-tested: `CanvasPaneLayer.test.tsx` ("withholds … fewer than
three", "passes … at least three") and `PaneChrome.test.tsx` ("hides frame on an expanded
pane while keeping expand available to unexpand").

### 3. No regression — PASS

- The double-click header gesture (`onHeaderDoubleClick` → `onHeaderActivate` →
  `framePane`/`expandPane`) is unchanged and still works.
- `IconToggle`/`IconButton` aria-labels (`Frame ${title}`, `Expand ${title}`) and keyboard
  access are intact when rendered.
- No change to spawn/close/minimize/dock semantics; `clearCanvas` and `resetViewport`
  correctly reset `paneFlyIntent: "none"`.
- **e2e spec is a legitimate adjustment, not weakened**: `canvas-persistence.spec.ts` adds
  a third session (`gamma-session`), clicks it to open a 3rd pane so the Frame/Expand
  icons appear, and **adds** a `Gamma session` visibility assertion. No assertion is
  removed or weakened; the existing `Expand Alpha session` flow now has the ≥3 panes it
  needs. (`keybindings-desktop.spec.ts` is not touched despite the brief listing it — no
  weakening there either.)

### 4. Gates — PASS (unit); e2e run is a CI gate (see note)

Full unit suite green (1108/155). The new unit tests assert the full gating matrix and
the camera-motion path. The e2e spec change is verified sound (point 3).

---

## Observations (positive, not defects)

- **Close/minimize of an expanded pane now animates the reflow.** `closePane` and
  `minimizePane` gained the same `onFly` wiring, and `finalizePaneDismissal` returns
  `fly: "pane-motion"` when collapsing the expanded pane — previously stripped, now
  applied. This is a small behavior change beyond the three stated, but it is consistent
  with the unified motion (dismissing an expanded pane animates like unexpand) and is an
  enhancement, not a break.
- **The double-click gesture and the icon threshold differ at 2 panes.** The Frame icon
  needs `openPaneIds >= 3`, but `planPaneFrame` only requires `openPaneIds > 1`, so a
  double-click can still frame with exactly 2 panes even though the icon is hidden. This
  is spec-sanctioned ("the gesture still works") and harmless; noted for awareness.

## Verification note

Read-only throughout; `git status` clean. Playwright is not installed in this review
environment (`shell/node_modules/.bin/playwright` absent), so I could not execute the
chromium e2e **run** locally — I verified the e2e spec diff is a legitimate,
coverage-adding adjustment, but the actual chromium/webkit/firefox e2e green must be
confirmed from CI before merge.
