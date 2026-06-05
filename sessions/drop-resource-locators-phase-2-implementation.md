---
title: Drop Resource Locators Phase 2 Implementation
type: sessions
tags: [frontend, transport-matters, canvas, desktop, api]
summary: Implemented canvas file and URL drop handling, terminal paste delivery, locator pane drag delivery, and the review fix round.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-11
updated: 2026-06-11
---

## Summary

Implemented Phase 2 of file drop and resource locator support from `NOTES/captured-canvas/14-drop-resource-locators-plan.md`, then completed the follow-up review fix round.

Completed commits:

- `e9835ec` `feat(canvas): file and url drop targets with terminal paste delivery`
- `9e711df` `feat(canvas): drag a locator pane onto a terminal to paste its locator`
- `08cd5ff` `fix(canvas): address locator drop review minors`

Task 8 Step 1 verification was completed with no additional commit before the fix round. The fix round added one commit as requested.

## Architecture Decisions

- Added `www/src/session-canvas/dnd/canvasDrop.ts` as the pure drop logic seam. It owns drop classification, viewport hit testing, terminal paste delivery, and resource pane spawning decisions.
- Added `CanvasDropHint` as a canvas local status overlay for browser file drops without the Electron path bridge.
- Wired production `/canvas` drop listeners through `CanvasSurface`, using `window.transportMattersDesktop?.getPathForFile` for file path resolution and `useCanvasStore.getState().layout` for current hit testing.
- Set dragover `dropEffect` to `copy` so OS cursor feedback does not imply a blocked drop.
- Extended the engine with an optional `onMoveEnd` callback rather than adding locator knowledge to generic engine code.
- Kept locator pane drag behavior in `canvasDrop.ts`; `CanvasSurface` bridges the generic engine callback to the session canvas store.
- Corrected locator pane release to strict topmost semantics: hit the single highest-z pane under the release center, excluding the moved pane. If that pane lacks a paste handle, do not paste to a lower terminal.
- Extracted `locatorTail` into `model/paneRecords.ts` and reused it from both registry titles and URL image content titles.

## Performance Notes

- `LayoutCanvas` and `PaneLayer` keep the new move-end callback optional.
- `CanvasSurface` wraps `onMovePaneEnd` in `useCallback` so the memoized pane layer does not get a fresh callback on every render.
- No bundle or Lighthouse measurement was requested for this slice.

## Verification

Observed gates before the fix round:

- `cd api && just test`: `1316 passed in 28.32s`, exit 0.
- `cd www && npx vitest run`: `104 passed`, `710 tests passed`, exit 0.
- `cd www && npx tsc --noEmit`: exit 0.
- `cd desktop && pnpm test`: `7 passed`, `29 tests passed`, exit 0.

Observed fix round checks:

- Failing-before targeted check: `cd www && npx vitest run src/session-canvas/dnd/canvasDrop.test.ts src/session-canvas/viewers/terminal/CapturedRunPane.test.tsx` failed because the stacked non-terminal-over-terminal test still pasted through to the lower terminal.
- Targeted post-fix check: `cd www && npx vitest run src/session-canvas/dnd/canvasDrop.test.ts src/session-canvas/viewers/terminal/CapturedRunPane.test.tsx src/session-canvas/model/paneRecords.test.ts src/session-canvas/viewers/resource/ResourcePane.test.tsx`: `4 passed`, `34 tests passed`, exit 0.
- Full requested gate: `cd www && npx vitest run`: `104 passed`, `712 tests passed`, exit 0.
- Full requested gate: `cd www && npx tsc --noEmit`: exit 0.

## Deviations from Spec

- Task 6 also updated `www/src/session-canvas/components/pane-dock.css` so `CanvasDropHint` has canvas local overlay styling. The plan requested styling in the canvas shell overlay stylesheet but did not list that CSS file in the commit command.
- Manual desktop smoke and push were intentionally skipped because the orchestrator directive assigned only Task 8 Step 1 to this worker.
- The initial Task 7 implementation walked lower z hits to find a paste handle. The review fix corrected this to strict topmost hit semantics in `08cd5ff`.

## Open Items

- Orchestrator owns Task 8 manual desktop smoke.
- Orchestrator owns pushing `fix/spawned-terminals` and any PR workflow.
