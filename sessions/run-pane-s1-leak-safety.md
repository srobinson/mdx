---
title: Run Pane Slice 1 Leak Safety
type: sessions
tags: [frontend, transport-matters, run-pane, captured-run, canvas]
summary: Implemented run-pane Slice 1 by moving captured run lifecycle and store ownership into canvas core.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented Slice 1 of the run-pane lab to canvas-core migration on `feat/run-pane-s1-leak-safety`, commit `2f616a6`, PR #107. The captured run store now lives under `www/src/session-canvas/model/`, and captured-run cleanup is registered as a static core lifecycle policy instead of a lab route side effect.

## Architecture Decisions

- Kept the captured run persistence key unchanged while relocating `capturedRunStore` from `lab/` to `model/`.
- Added `model/capturedRunLifecycle.ts` as the single captured-run lifecycle policy owner.
- Seeded `PANE_LIFECYCLE_POLICIES["captured-run"]` in `model/paneLifecycle.ts` so `/canvas` and `/canvas-lab` both resolve close, minimize, and restore policy from core load.
- Kept `registerLifecycle` exported for runtime overrides, but removed the sole production side-effect registration path by deleting `lab/labLifecycle.ts`.
- Used `import type { PaneLifecyclePolicy }` in `capturedRunLifecycle.ts` to keep the policy back-edge type-only and avoid a runtime cycle.

## Performance Notes

- No measured runtime performance change. The final build remained green, and xterm stayed isolated in the lazy terminal chunks.
- Build output was inspected from `just www build`; the change adds the light captured run store to the eager canvas lifecycle path as expected by the spec.

## Deviations from Spec

- None. Slice 1 only was implemented. OSC color replies, spawn factory work, and `/canvas` spawn buttons remain untouched for later slices.

## Open Items

- Slice 2 still needs to remove the remaining viewer to lab import by lifting `oscColorReplies` into the core captured run store.
- Slice 3 still needs the core captured-run ref factory and `useCanvasStore.addCapturedRun`.
- Slice 4 still needs `/canvas` spawn buttons.

## Verification

- Baseline before changes: `just www check && just www test` passed.
- Targeted lifecycle coverage was added for static policy resolution, on-canvas close, dock close, and dock-close after persistence-only rehydration with no spawn or viewer mount.
- Final gate passed: `just www check && just www test && just www build`.
- Existing Biome warnings for `pane-dock.css` cursor `!important` rules were present before this work and remain unchanged.
