---
title: Launcher NavFrame Stack Implementation
type: sessions
tags: [frontend, launcher, navframe, command-center]
summary: Implemented the launcher NavFrame stack and restore origin behavior in PR 152.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

## Summary

Implemented Slice B of the launcher design on `feat/launcher-nav-frame` and opened PR #152. The launcher now uses a single `NavFrame[]` as the source of truth for scope, query, and highlighted row state. Back navigation restores the parent frame's query and highlighted row, so returning from Settings lands on the Settings domain row instead of resetting to the first row. Follow-up commit `59897f7` removed the unused controlled `highlighted` prop from `useLauncherRows` and its call site.

## Architecture Decisions

- Added pure NavFrame helpers in `www/src/session-canvas/launcher/commandModel.ts`: `createRootNavFrame`, `createScopeNavFrame`, `domainRowValue`, `pushFrame`, `popFrame`, `topFrame`, and `updateTopFrame`.
- Replaced flat `scope` and `query` state in `useCommandCenter.ts` with a local `useNavFrameStack` helper so the main hook stays below the refactoring threshold.
- Kept `applyGesture` lifecycle based. Descend now stamps the activated row value into the parent frame before pushing the child frame.
- Inverted `useLauncherRows.ts` to controlled highlighted state. Its auto highlight effect writes through the frame backed setter.
- Added equality guards in the frame backed setters to avoid re-render loops when the auto highlight effect repeats the existing value.

## Performance Notes

No bundle or runtime performance regression was measured. The stack operations are small immutable array updates. Verification completed with `just check`, `just test`, and `just test-e2e`.

## Deviations from Spec

None. `COMMAND_INTERACTIONS` remains empty for this slice, and Slice C theme cycling was not implemented.

## Open Items

- PR #152 is open for orchestrator review at head `59897f7`.
- Cycle theme interactive behavior remains deferred to Slice C.
