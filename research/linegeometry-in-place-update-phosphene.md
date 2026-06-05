---
title: LineGeometry In Place Update Feasibility for Phosphene
type: research
tags: [phosphene, threejs, drei, linegeometry, rendering]
summary: Drei Line rebuilds LineGeometry through setPositions, while Line2 geometry can be mutated in place only by owning the geometry instance directly.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

The design claim is only partially achievable with the stack as installed. It is not achievable through drei `<Line>` as a public component contract, because the component owns geometry creation and calls `setPositions` whenever `points` identity changes. It is achievable with `Line2` and `LineGeometry` by replacing or bypassing drei `<Line>`, allocating geometry once, then mutating the interleaved backing buffer in place.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/phosphene`
- Branch reviewed: `idea/svg-renderer`
- fmm status: no `.fmm.db` in this checkout, direct local inspection used after fmm failed.
- Relevant packages: `@react-three/drei@10.7.7`, `three@0.184.0`, `three-stdlib@2.36.1`

## Detailed Findings

- Drei `Line` source: `node_modules/.pnpm/@react-three+drei@10.7.7_@react-three+fiber@9.6.1_@types+react@19.2.17_react-dom@19.2.7_53d034e53d2dc2d936de176917e96a56/node_modules/@react-three/drei/core/Line.js`.
  - Imports `LineSegments2`, `Line2`, `LineMaterial`, `LineSegmentsGeometry`, `LineGeometry` from `three-stdlib` at line 5.
  - Creates the `Line2` object at line 19.
  - Creates `LineGeometry` or `LineSegmentsGeometry` internally at lines 22 to 23.
  - Calls `geom.setPositions(pValues.flat())` at line 28.
  - Attaches that owned geometry at lines 55 to 60.
  - Public types in `core/Line.d.ts` lines 5 to 12 expose `points`, colors, material and object props, but no direct geometry ownership API.

- Three examples `LineGeometry`: `node_modules/three/examples/jsm/lines/LineGeometry.js`.
  - `LineGeometry.setPositions` lines 50 to 69 allocates a new `Float32Array` at line 55, converts polyline points to segment pairs, then calls `super.setPositions(points)` at line 69.

- Three examples `LineSegmentsGeometry`: `node_modules/three/examples/jsm/lines/LineSegmentsGeometry.js`.
  - `setPositions` lines 97 to 123 wraps the array in a new `InstancedInterleavedBuffer` at line 111, replaces `instanceStart` and `instanceEnd` attributes at lines 113 to 114, sets `instanceCount` at line 116, then recomputes bounds at lines 120 to 121.

## Verdict

Drei `<Line>` is the wrong abstraction for the claim. The claim requires replacing or bypassing drei `<Line>` with a custom component that constructs `Line2` plus `LineGeometry` once and owns the geometry buffer.

## Buffer Update Flags

For in place writes, mutate `geometry.attributes.instanceStart.data.array`, since `instanceStart` and `instanceEnd` share the same `InstancedInterleavedBuffer`. Then set `geometry.attributes.instanceStart.needsUpdate = true` or `geometry.attributes.instanceStart.data.needsUpdate = true`. `InterleavedBufferAttribute.needsUpdate` forwards to `data.needsUpdate` in `node_modules/three/src/core/InterleavedBufferAttribute.js` lines 102 to 105, and `InterleavedBuffer.needsUpdate` increments version in `node_modules/three/src/core/InterleavedBuffer.js` lines 101 to 104. For partial uploads use `data.addUpdateRange(start, count)` before `needsUpdate`, per `InterleavedBuffer.js` lines 121 to 129. Set `data.setUsage(DynamicDrawUsage)` before first render if the buffer is dynamic, because usage cannot change after initial use per lines 51 to 60 and 113 to 118.

## Open Questions

- Whether the custom renderer needs dynamic bounding boxes every frame or can use conservative static bounds.
