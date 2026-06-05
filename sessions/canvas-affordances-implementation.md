---
title: Canvas Affordances Implementation
type: sessions
tags: [frontend, session-canvas, affordances]
summary: Implemented dock, expand, frame, lab seed persistence, and PR 89 rebase reconciliation for canvas panes.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Summary

Implemented Slice 2 for `/canvas` in PR #89. The current rebased commit is `20be404`. `/canvas` panes expose frame, expand, and minimize controls through shared `PaneChrome`, render the shared `PaneDock`, and use the same hero plus grid overflow expand composition as the lab.

PR #89 was rebased after PR #91 merged to `main` as `1100b0c`. The reconciliation keeps PR #91's persistence reader semantics as canonical and keeps PR #89's wider dockable picker model in `paneRecords.ts`.

The latest PR #89 hygiene and rebase work removed dead lab layout re exports, centralized removal of transient `fly` animation intent before Zustand writes, aligned lab `resetView()` with production reset behavior, and avoided reintroducing redundant hydration guards.

Implemented the fresh `/canvas-lab` seed fix in PR #91. The final branch commit was `e037c1b`; the merge commit is `1100b0c`. Root cause: missing cache clobbered seeded panes. Fresh profiles now keep the four seeded lab panes when no persisted payload exists, while stale or invalid persisted payloads still reset safely.

PR #91 also exported the shared `isRecord()` guard from `paneRecords.ts`, removed the duplicate local helper from `canvasPanePersistence.ts`, and hardened persistence tests for valid empty payloads plus malformed payload reset behavior.

## Architecture Decisions

1. Moved expand planning from `lab/expandLayout.ts` to `model/expandLayout.ts` so production canvas code no longer imports lab modules.
2. Added `model/paneAffordances.ts` as the shared owner for dock dismissal, restore lifecycle dispatch, expand, unexpand, frame, unframe, close removal planning, and unframe camera policy.
3. Added `stripPaneFlyIntent()` and `PaneAffordanceStateTransition` as the boundary between transient animation intent and persisted Zustand state.
4. Repointed `canvasLabStore.ts` to the shared affordance helpers, leaving lab specific glue for demo pane refs, captured run labels, persistence, and fly flags.
5. Extended `canvasStore.ts` with `docked`, `expandedPaneId`, and `framing` state plus minimize, restore, close docked, expand, unexpand, frame, and unframe actions.
6. Updated `PaneWindow` to forward affordance handlers into `PaneChrome`; `CanvasSurface` now supplies real handlers and renders `PaneDock` as the `LayoutCanvas` overlay.
7. `DockedPane` can carry a full `PaneRecord` for `/canvas` restore, preserving title and timestamps while keeping the lab null ref demo path intact.
8. `DockedPane.ref` now accepts `CanvasPaneRef | null` so the production session picker can be minimized, restored, and protected from kill via `closeDisabled`.
9. Added `isCanvasPaneRef()` and kept `isDockedPane()` widened to accept picker refs plus optional `closeDisabled`.
10. `canvasPanePersistence.ts` now uses PR #91's reader unchanged after rebase. It imports shared `isRecord()` from `paneRecords.ts` and consumes the widened `isDockedPane()` guard.
11. `canvasPanePersistence` distinguishes absent payloads, including `undefined`, `null`, and `{}`, from present pane payloads. Absent payloads preserve the current seed; invalid present payloads reset.
12. A present but valid empty payload, `{ contentRefs: {}, paneRects: {}, docked: [] }`, intentionally hydrates as an empty canvas.
13. `/canvas-lab` production initial state seeds four demo panes during store initialization. Test reset helpers still use an explicit empty state.
14. Lab `resetView()` now replans layout with `expandedPaneId: null` before resetting the camera to `{ panX: 0, panY: 0, scale: 1 }`.

## Performance Notes

1. PR #89 latest rebased full build passed with `/canvas` route chunk `SessionCanvasRoute-D7dHQHaI.js` at 10.67 kB, gzip 3.87 kB, and `/canvas-lab` route chunk `CanvasLabRoute-wl9YoqQg.js` at 13.29 kB, gzip 4.44 kB.
2. PR #91 fix round full build passed with `/canvas-lab` route chunk `CanvasLabRoute-CMdkA3cr.js` at 16.91 kB, gzip 5.53 kB.
3. Earlier PR #89 full build passed with `/canvas` route chunk `SessionCanvasRoute-DKCOSXch.js` at 10.67 kB, gzip 3.87 kB, and `/canvas-lab` route chunk `CanvasLabRoute-6jwQi4L7.js` at 12.87 kB, gzip 4.35 kB.
4. Shared helpers avoid copying lab lifecycle logic into production, keeping behavior centralized and reducing future drift.

## Verification

1. Initial PR #89 targeted tests passed: `cd www && pnpm exec vitest run src/session-canvas/model/canvasStore.test.ts src/session-canvas/SessionCanvasRoute.test.tsx src/session-canvas/lab/canvasLabStore.test.ts src/session-canvas/lab/canvasLabLayout.test.ts src/session-canvas/components/PaneDock.test.tsx`, 5 files, 52 tests.
2. Reproduced the stale cache bug with Playwright by seeding `transport-matters-canvas-lab` with a legacy `kind: "session"` content ref; `/canvas-lab` crashed with `No viewer registered for session` before the fix.
3. Verified the stale cache fix with Playwright using the same seed; `/canvas-lab` mounted and reset safely.
4. Regression tests for stale cache passed: `cd www && pnpm exec vitest run src/session-canvas/lab/CanvasLabRoute.test.tsx src/session-canvas/lab/canvasLabStore.persistence.test.ts src/session-canvas/persistence/canvasPanePersistence.test.ts`, 3 files, 25 tests.
5. Required PR #89 gate passed after the stale cache fix: `cd www && just check && just test && pnpm build`, 100 files, 673 tests.
6. PR #91 failed before the fix with `cd www && pnpm exec playwright test --project=chromium`, 5 of 8 failures caused by missing `lab-1` on fresh profiles.
7. PR #91 targeted unit tests passed after the first fix: `cd www && pnpm exec vitest run src/session-canvas/persistence/canvasPanePersistence.test.ts src/session-canvas/lab/canvasLabStore.persistence.test.ts src/session-canvas/lab/canvasLabStore.test.ts`, 3 files, 49 tests.
8. PR #91 E2E passed after the first fix: `cd www && pnpm exec playwright test --project=chromium`, 8 passed.
9. PR #91 first full gate passed: `just check && just test && just build`; desktop 6 files and 28 tests, www 100 files and 669 tests, api 1301 tests, all builds green.
10. PR #91 fix round targeted test passed: `cd www && pnpm exec vitest run src/session-canvas/persistence/canvasPanePersistence.test.ts`, 1 file, 12 tests.
11. PR #91 fix round full gate passed: `just check && just test && just build`; desktop 6 files and 28 tests, www 100 files and 671 tests, api 1301 tests, all builds green.
12. PR #89 final hygiene gate passed before rebase: `cd www && pnpm exec vitest run src/session-canvas/lab/canvasLabStore.test.ts src/session-canvas/model/canvasStore.test.ts src/session-canvas/lab/canvasLabLayout.test.ts && pnpm typecheck`, 3 files, 44 tests, typecheck green.
13. PR #89 final full gate passed before rebase: `just check && just test && just build`; desktop 6 files and 28 tests, www 100 files and 674 tests, api 1301 tests, all builds green.
14. PR #89 rebase reconciliation typecheck passed: `cd www && pnpm typecheck`.
15. PR #89 rebased Chromium E2E passed: `cd www && pnpm exec playwright test --project=chromium`, 8 passed.
16. PR #89 rebased full gate passed: `just check && just test && just build`; desktop 6 files and 28 tests, www 100 files and 679 tests, api 1301 tests, all builds green.
17. Browser plugin smoke was attempted, but the in app browser reported unavailable for `iab`.
18. Local dev HTTP smoke passed for `http://localhost:5173/canvas` and `http://localhost:5173/canvas-lab`, both 200 text/html.

## Deviations from Spec

1. No design spec specific to this slice existed in `~/.mdx/design/`; the implementation followed the bus directive and existing lab behavior as the source of truth.
2. `/canvas` supports minimizing the built in session picker so all panes receive the same minus affordance. The docked picker cannot be killed from the dock because the picker remains protected canvas chrome.

## Open Items

1. In app browser visual verification remains blocked until the Browser `iab` surface is available.
2. Future production `/canvas` persistence remains out of scope for PR #89.
