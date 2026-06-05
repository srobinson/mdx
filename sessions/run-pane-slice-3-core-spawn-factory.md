---
title: Run pane Slice 3 core spawn factory
type: sessions
tags: [frontend, transport-matters, session-canvas, captured-run]
summary: Added a shared captured run ref factory and core canvas addCapturedRun action with tests and PR.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-14
updated: 2026-06-14
---

## Summary

Implemented Slice 3 of the run pane core migration on `feat/run-pane-s3` and opened draft PR #111 at commit `1f18eee`.

Changes:

- Added `createCapturedRunRef(provider, label?)` in `www/src/session-canvas/model/spawn.ts`.
- Routed `useCanvasLabStore.addCapturedRun` through the shared factory and the lab generic `spawnPane` flow.
- Added `useCanvasStore.addCapturedRun(provider)` in the core canvas store, using plain `cliLabel(provider)` for `/canvas` v1 labels and the existing generic `spawnPane(ref, { focus: true })` path.
- Added coverage in `spawn.test.ts` and `canvasStore.test.ts` for factory output, unique same provider panes, and `addCapturedRun` followed by `closePane` stopping the run.

## Architecture Decisions

- The captured run ref literal now has one owner: `model/spawn.ts:createCapturedRunRef`.
- Core `/canvas` labels stay plain `Claude` or `Codex` for v1.
- Lab numbering remains lab local through `labelFor` and `paneCounters`; the computed label is passed into the shared factory.
- Both lab and core add captured run paths use their existing `spawnPane` machinery, preserving the shared registry, lifecycle, ensureRun, and stopRun seams.

## Performance Notes

Validation gate passed with `just www check && just www test && just www build` and reported `GATE_EXIT=0`.

Build output kept the captured run store split as `capturedRunStore-JYwkzLKb.js` at 2.53 kB, gzip 1.10 kB.

## Deviations from Spec

None.

The in app Browser smoke was attempted after starting Vite at `127.0.0.1:5173`, but the `iab` browser was unavailable in this session. Automated tests and the full repo gate passed.

## Open Items

- Slice 4 still needs to wire `/canvas` spawn buttons to `useCanvasStore.addCapturedRun`.
- The existing Biome warnings for `!important` cursor rules in `pane-dock.css` remain outside this slice.
