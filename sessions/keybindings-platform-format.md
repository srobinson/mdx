---
title: Keybindings Platform and Format Slice
type: sessions
tags: [frontend, transport-matters, keyboard, desktop]
summary: Implemented the additive desktop keybinding platform resolver and formatter foundation.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

## Summary

Implemented slice 1 of the desktop-only keybinding foundation on `feat/keybindings-platform-format`, opened as PR #146. Initial implementation landed at `8a53e02`; review fixes landed at `c767d3a`.

The slice adds `www/src/keybindings/platform.ts` and `www/src/keybindings/format.ts`, extends the existing Electron preload bridge with `transportMattersDesktop.platform`, and updates renderer bridge typing in `www/src/desktopHost.ts`. No keydown handlers or components were rewired.

The review fix changed navigator platform fallback to treat an empty `userAgentData.platform` as missing, shared `globalWindow()` from `desktopHost.ts`, documented the imminent slice 2 `resolveModToken()` consumer, and added edge tests for unknown platform defaulting plus empty binding formatting.

## Architecture Decisions

- The renderer platform resolver is memoized through `getKeybindingPlatform()` so the desktop bridge or browser fallback is read once.
- The desktop bridge wins over navigator data. Navigator user agent data is only a browser-development fallback when the bridge is absent.
- `$mod` precompilation lives in `precompileModTokens()`, returning `Meta` for macOS and `Control` elsewhere.
- `resolveModToken()` remains exported because the slice 2 registry engine is expected to import it as the public concrete `$mod` accessor.
- `formatBinding()` is the single label formatter, with Apple symbol ordering on macOS and `Ctrl+Alt+Shift+Key` word labels on Windows and Linux.
- `DESKTOP_BRIDGE_KEY`, `globalWindow()`, and the bridge interface are exported from `desktopHost.ts` to avoid duplicating the bridge name, browser-global seam, and shape.

## Performance Notes

No runtime wiring was added, so there is no bundle path or UI performance impact yet. The new modules are small pure utilities and are not imported by app surfaces in this slice.

Verification for the review fix:

- `just check`: `/tmp/keymap-foundation-fix-just-check.log`, `EXIT=0`
- `just test`: `/tmp/keymap-foundation-fix-just-test.log`, `EXIT=0`, including 29 desktop tests, 941 web tests, and 1570 API tests
- `just www test-e2e`: `/tmp/keymap-foundation-fix-just-test-e2e-rerun2.log`, `EXIT=0`, 54 Playwright tests passed

## Deviations from Spec

The root `justfile` does not expose a direct `test-e2e` recipe. The e2e gate was run through the existing root proxy as `just www test-e2e`, which executes the `www` `just test-e2e` recipe.

Two prior e2e attempts failed on different existing canvas or launcher tests, then the same full gate passed without code changes. The passing gate is recorded above.

## Open Items

- Slice 2 should add the registry and engine, then migrate the launcher trio and Escape without touching the intercept web app route hotkeys.
- Future command overrides can use the platform and formatting primitives, but no command remapping UI exists in this slice.
