---
title: Phosphene T0.1 Review Fixes
type: sessions
tags: [frontend, phosphene, webgl, audio, review-fix]
summary: Fixed point cloud disposal and microphone lifecycle issues from the T0.1 review.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-07
updated: 2026-06-07
---

## Summary

Implemented the T0.1 review fixes for the existing `public/head.glb` renderer. The detailed grid halftone face remains in scope. No model swap was made.

## Architecture Decisions

- Added manual disposal for the generated point cloud `BufferGeometry` and `ShaderMaterial` because the `<points>` primitive uses `dispose={null}`.
- Hardened the microphone hook with a synchronous starting and active guard, a start token, mounted state tracking, and cleanup for late resolving `getUserMedia` calls.
- Added a `disable()` path in the audio contract so all tracks and the `AudioContext` can be stopped by either explicit disable or unmount.
- Changed audio signal updates to mutate the existing `bands` tuple in place, avoiding per frame array allocation.
- Kept `public/head.glb` as the active mesh per orchestrator scope.

## Performance Notes

- `vp check` passed.
- `vp test` passed, 2 files and 2 tests.
- `vp build` passed.
- Headless WebGL dev verification passed with `?audio=0.6`: screenshot mean luminance 53.48, lit ratio 0.2421, max 255.
- Fake microphone click verification passed with button state `Mic live` and no visible error.

## Deviations from Spec

None. Optional chunked grid building was deferred because the directive named it optional and quick only.

## Open Items

- The synchronous 61,600 ray grid build still happens on mount and can be revisited if startup latency becomes a priority.
- The production bundle remains above the general 200 KB gzip frontend target because the WebGL stack dominates size.
