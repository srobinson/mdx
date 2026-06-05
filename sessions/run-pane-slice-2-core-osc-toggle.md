---
title: Run Pane Slice 2 Core OSC Toggle
type: sessions
tags: [frontend, transport-matters, session-canvas, run-pane]
summary: Lifted the captured run OSC color replies toggle into core state and added lab boundary tests.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented Slice 2 of the run pane lab to canvas core migration on branch `feat/run-pane-s2`.
The captured run OSC color replies toggle now lives in `model/capturedRunStore.ts` as persisted core state.
`CapturedRunPane.tsx` reads the setting from the core store and imports no lab modules.
The lab UI still exposes the toggle, but writes through `canvasLabStore.setOscColorReplies`, which delegates to the core store.

PR: `https://github.com/littleorgans/transport-matters/pull/110`
Commit: `aec12b4`

## Architecture Decisions

* Core captured run state owns `oscColorReplies` with default `true`, `setOscColorReplies`, versioned persistence, and migration defaulting older payloads to enabled.
* Lab retained only the UI affordance and delegation action. Lab persistence no longer stores `oscColorReplies`.
* `ControlsPanel.tsx` owns the `OscColorReplyToggle` component so the lab toggle reads core state and writes through the lab store boundary.
* Added `labBoundary.test.ts` using the TypeScript AST to catch static imports, dynamic imports, and import type references from non lab `session-canvas` files into `session-canvas/lab`.
* The no legacy assertion blocks recreated lab run store exports, lifecycle registration, legacy lab files, and exported captured run ref factories.

## Performance Notes

`just www build` completed successfully. The build kept the captured run pane and captured run store in separate chunks, with `capturedRunStore` at 2.53 kB and 1.10 kB gzip in the reported Vite output.

## Deviations from Spec

The spec named `lab/ControlsPanel.tsx` for the lab toggle. The live toggle was previously embedded in `CanvasLabRoute.tsx`, so the implementation extracted an `OscColorReplyToggle` export into `ControlsPanel.tsx` and rendered it from the existing command bar slot.

The in app Browser smoke was attempted against local `/canvas-lab`, but the Browser connector returned unavailable for `iab`. Verification relied on unit tests, boundary tests, typecheck, and the full repo gate.

## Open Items

* Slice 3 should add the core captured run ref factory and remove the remaining lab specific captured run ref construction from `canvasLabStore.addCapturedRun`.
* Slice 4 should add product route spawn buttons on `/canvas` after the core factory exists.
