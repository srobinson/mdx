---
title: Run pane Slice 4 canvas spawn buttons
type: sessions
tags: [frontend, transport-matters, session-canvas, captured-run]
summary: Added core canvas Spawn Claude and Spawn Codex actions wired to the shared captured run spawn path, then fixed toolbar pointer interception.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented Slice 4 of the run pane core migration on branch `feat/run-pane-s4`, PR #112. Commit `ef74593` added the `/canvas` `Spawn Claude` and `Spawn Codex` command bar actions. Fix commit `195a8fa` resolved the e2e regression where the widened command bar shell intercepted pointer events meant for pane chrome.

## Architecture Decisions

- Kept `CanvasCommandBar` presentational. It imports the `CliName` type and the pure `cliLabel(provider)` helper, but no store.
- Reused the Slice 3 core spawn path. `CanvasSurface` selects `addCapturedRun` from `useCanvasStore` and passes it directly to the command bar.
- Kept capability or availability gating out of `/canvas` v1, matching the Slice 4 directive. The lab remains the capability gated surface.
- Relied on native `<button type="button">` semantics for Enter and Space activation and the existing `.canvas-button:focus-visible` tokenized focus ring.
- Promoted the lab command bar click-through pattern to the shared canvas command bar: the spanning `.canvas-command-bar` shell uses `pointer-events: none`, while real interactive descendants restore `pointer-events: auto`. The lab duplicate was deleted to keep one source.

## Performance Notes

- No new runtime dependency was added.
- The production build passed. Relevant build output after the fix included `CapturedRunPane-CXvJpnxs.js` at 1.71 kB, gzip 0.82 kB, and `capturedRunStore-JYwkzLKb.js` at 2.53 kB, gzip 1.10 kB.
- Validation passed:
  - `pnpm --dir www test -- src/session-canvas/components/CanvasCommandBar.test.tsx src/session-canvas/components/CanvasSurface.test.tsx`
  - `pnpm --dir www typecheck`
  - `pnpm --dir www exec playwright test tests/e2e/canvas-persistence.spec.ts --project=chromium --reporter=line` reproduced the pointer interception before the fix.
  - `pnpm --dir www exec playwright test tests/e2e/canvas-persistence.spec.ts --reporter=line` passed after the fix across Chromium, Firefox, and WebKit.
  - `just www test-e2e` passed, 42 tests across Chromium, Firefox, and WebKit.
  - `just www check && just www test && just www build` passed.
  - Headless Playwright smoke against `http://127.0.0.1:5173/canvas`: spawn buttons visible and focusable, `Spawn Claude` seeds a pane.

## Deviations from Spec

None. The in-app Browser connector was unavailable, so the UI smoke used local headless Playwright after the required Browser attempt.

## Open Items

- Existing Biome warnings remain in `www/src/session-canvas/components/pane-dock.css` for cursor `!important` rules. They predate this slice and did not block the gate.
- Live capability gating and live-run roster polish remain out of scope for Slice 4 v1.
