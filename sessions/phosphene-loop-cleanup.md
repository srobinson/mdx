---
title: Phosphene Loop Cleanup
type: sessions
tags: [frontend, phosphene, renderer, loop, svg, three]
summary: Extracted the shared per frame phosphene tick and removed direct three-mesh-bvh dependency.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

## Summary

Implemented the mailbox directed loop cleanup slice in `phosphene` on `idea/svg-renderer`.

Changed files:

- `src/render/PhospheneLoop.ts`
- `src/Waveform.tsx`
- `src/Waterfall.tsx`
- `src/Spectrum.tsx`
- `src/render/svg/SvgHost.tsx`
- `src/Visualizer.tsx`
- `src/defaults.ts`
- `src/pathShape.ts`
- `vite.config.ts`
- `package.json`
- `pnpm-lock.yaml`
- `tests/phospheneLoop.test.ts`

Loop decision: extract. The three R3F drivers and the SVG driver all repeated the same per frame body, `form.update(frame, signal, look)` followed by `renderer.draw(frame)`, so the shared body now lives in `tickPhospheneLoop`. Three still uses R3F `useFrame` with `frameloop="always"`; SVG owns the requestAnimationFrame hook exported as `usePhospheneLoop`.

Cleanup completed:

- Removed the direct `three-mesh-bvh` dependency from `package.json` and refreshed `pnpm-lock.yaml` with `vp install`.
- Confirmed no `three-mesh-bvh` imports remain in `src`, `tests`, or `package.json`. The lockfile still contains `three-mesh-bvh@0.8.3` as a transitive `three-stdlib` dependency.
- Added `DEFAULT_ARC_SPAN_DEG` in `src/pathShape.ts` and used it from `src/defaults.ts`, `makePathShape`, and `isClosedPathShape`.
- Excluded ignored `.versions/**` snapshot trees from `vp test`; removing the direct dependency exposed an archived ignored test import there.
- Added a focused test for the shared tick order.

## Architecture Decisions

- Kept the renderer driver split from the synthesis design: R3F owns the three.js frame clock, SVG owns a RAF hook, both call one shared tick.
- Made the three Canvas `frameloop="always"` explicit to document the Bloom composer constraint without changing runtime behavior.
- Kept `audio.ts:useAudioInput` untouched to avoid widening the slice into signal lifecycle ownership.
- Put the arc default beside path shape construction so shape semantics and defaults cannot drift.

## Performance Notes

- No intended runtime behavior change.
- `vp build` transformed 678 modules and completed in 319 ms.
- The existing large chunk warning remains: `dist/assets/index-5yXnCpr1.js` is 1,413.09 kB, gzip 400.03 kB.

## Deviations from Spec

- None from the requested loop design.
- Test config gained an explicit `.versions/**` exclude because `.versions/` is ignored archival content but Vitest still discovered it after the direct `three-mesh-bvh` dependency was removed.

## Open Items

- Bundle size still exceeds the project target because the production JS chunk remains about 400 kB gzip; this warning predates the loop cleanup slice.

## Verification

- `vp install`: PASS, removed direct `three-mesh-bvh 0.9.10`.
- `vp check`: PASS, all 50 files formatted, 38 files lint/type clean.
- `vp lint .`: PASS, exit 0.
- `vp build`: PASS, 678 modules transformed, built in 319 ms, existing chunk size warning remains.
- `vp test`: PASS, 6 files, 37 tests.
- `git diff --check`: PASS.
