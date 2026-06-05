---
title: Keybindings Registry Engine
type: sessions
tags: [frontend, keybindings, transport-matters]
summary: Added the desktop keybinding registry engine and completed the PR #147 fix round.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-19
---

## Summary

Implemented the desktop scoped keybinding registry and engine under `www/src/keybindings/`, mounted it around the product `/canvas` route, and migrated launcher shortcuts plus dock and fullscreen Escape handling into registry commands. The PR #147 fix round is committed and pushed as `b03240b` on `feat/keybindings-registry-engine`.

## Architecture Decisions

- `KeybindingEngineProvider` owns one bubble phase `window` listener through `tinykeys` and is mounted only on the desktop canvas branch.
- `COMMANDS` declares launcher and UI commands with `when` gates and priority based arbitration.
- Launcher and dock surfaces register singleton target adapters. Fullscreen surfaces register into a per provider target set so multiple detail panes can coexist and Escape closes the actual open fullscreen target.
- `useCommandCenter` keeps its capture phase Escape path unchanged. The registry ignores already prevented events so palette Escape wins before dock or fullscreen.
- Playwright e2e specs share a `pressMod` helper so `$mod` assertions run correctly across Chromium, Firefox, and WebKit.
- Canvas surface tests wrap renders in `KeybindingEngineProvider` with an explicit Mac test platform so `$mod` assertions do not depend on the host OS.

## Performance Notes

No measured performance optimization was involved. `tinykeys` adds a small dependency and the engine is mounted only on `/canvas`, not the stress route.

## Deviations from Spec

The root justfile has no `test-e2e` recipe. The e2e gate lives in `www`, so final verification used `cd www && just test-e2e`.

## Open Items

- Biome still reports the pre-existing `!important` warnings in `www/src/session-canvas/components/pane-dock.css`; `just check` exits cleanly.
- Future slices can add overrides, gesture state, and native menu projection from the broader keymap strategy spec.

## Verification

- Focused vitest: passed. `src/keybindings/engine.test.ts` and `src/session-canvas/components/CanvasSurface.test.tsx` reported 8 tests passed.
- `just check`: passed. Desktop typecheck/tests, www format/lint/typecheck, and api ruff/mypy completed. Desktop tests reported 29 passed.
- `just test`: passed. Desktop 29 tests, www 947 tests, and api 1570 tests, for 2546 unit tests passed.
- `cd www && just test-e2e`: passed. Playwright reported 60 tests passed across Chromium, Firefox, and WebKit.
