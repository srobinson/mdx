---
title: Phosphene Three Polyline Resource S6
type: sessions
tags: [frontend, phosphene, renderer, three, performance]
summary: Replaced drei Line usage with renderer owned Line2 resources and in place interleaved buffer writes.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Summary

Implemented Slice 6 for phosphene by replacing the remaining drei `<Line>` JSX path with `ThreePolylineResource`, a renderer owned Line2 resource that owns `Line2`, `LineGeometry`, `LineMaterial`, and one shared dynamic interleaved segment buffer. Waveform and Waterfall now mount only groups; `ThreeRenderer.mount` and `reconcile` allocate and attach line resources, while `draw` mutates retained buffers, transforms, colors, widths, and visibility.

## Architecture Decisions

- Added `src/render/three/ThreePolylineResource.ts` as the Line2 ownership boundary under the three backend.
- Seeded `instanceStart` and `instanceEnd` as two `InterleavedBufferAttribute` views over one `InstancedInterleavedBuffer` with stride 6.
- Reused a retained update range object after an initialization time `addUpdateRange`, avoiding per frame range object allocation while still producing partial buffer uploads.
- Kept visual parity with drei Line by using `Line2`, `LineGeometry`, and `LineMaterial` defaults explicitly: `worldUnits=false`, `dashed=false`, `vertexColors=false`, `transparent=false`, `toneMapped=true`, LineMaterial linewidth, and resize driven resolution.
- Moved `barMaterial.ts` into `src/render/three/` so the remaining three coupled shader module lives inside the render boundary.
- Deleted the old seed point helper and removed the orphaned export from `writeSpectrumLayerStyles`.

## Performance Notes

- Closed the known Line2 `setPositions` per frame allocation path. `rg` shows no source `setPositions` calls remain outside the resolved backlog note.
- The line path now mutates the retained Float32Array in place and marks only the affected interleaved buffer range dirty.
- Gates passed on 2026-06-15:
  - `vp check`: all 43 files formatted, no warnings, lint errors, or type errors in 31 files.
  - `vp lint .`: exit 0, no output.
  - `vp build`: built in 303ms with the pre-existing large chunk warning.
  - `vp test`: 5 files passed, 25 tests passed.

## Deviations from Spec

- None. SVG backend work remains deferred to S7.

## Open Items

- Visual pixel parity was preserved by matching the Line2 stack and material configuration, but no browser screenshot diff was requested or run in this slice.
- Bundle size remains above the general frontend guideline because of three and postprocessing; `NOTES/BACKLOG.md` already tracks this as housekeeping.
