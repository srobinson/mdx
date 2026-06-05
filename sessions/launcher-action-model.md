---
title: Launcher Action Model Refactor
type: sessions
tags: [frontend, transport-matters, launcher, command-center]
summary: Implemented Slice A of the launcher declarative action interaction model with behavior preserved.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

## Summary

Implemented Slice A of the launcher action model in `transport-matters` on branch `feat/launcher-action-model`, commits `346e30b` and review follow-up `3f813cd`, PR #151.

The launcher now has a pure action to interaction table in `commandModel.ts`. `retry-agents` is a command center local effect rather than a canvas command. `useCommandCenter.ts` routes Enter, click, and ArrowRight through a generic lifecycle interpreter while preserving current behavior. Review follow-up `3f813cd` dropped exports from the four internal interaction table constants, keeping only the public model types and `interactionFor` exported.

## Architecture Decisions

- Added `Lifecycle`, `Interaction`, `LauncherEffect`, effect `RowAction`, internal lifecycle constants, and exported `interactionFor` to `commandModel.ts`.
- Kept `COMMAND_INTERACTIONS` empty for Slice A so `cycle-theme` remains a one shot `run-close` command.
- Repointed the retry row to `{ kind: "effect", effect: "retry-agents" }` and removed the downstream `CanvasSurface` no-op command case.
- Extracted `useLauncherActionInterpreter` so `useCommandCenter` stayed below the repository LOC threshold while the dispatcher switches only on `Lifecycle`.
- Preserved Slice A navigation behavior: descend still sets scope directly and clears query; Left and Backspace still pop to `root`.

## Performance Notes

No performance optimization was involved. Bundle size and runtime performance were not expected to change materially because this is a behavior preserving dispatcher refactor.

## Deviations from Spec

The spec said existing launcher tests should pass unchanged. One `commandModel.test.ts` assertion had to change from the old retry command shape to the new effect row shape because Slice A explicitly removes `retry-agents` from `LauncherCommand`. User visible behavior is unchanged.

## Open Items

- Slice B should introduce the NavFrame stack.
- Slice C should make `cycle-theme` interactive by adding its command interaction override.

## Verification

- `just check` passed.
- `just test` passed: desktop 29, www 973, api 1570, total 2572.
- `cd www && just test-e2e` passed: 63.
