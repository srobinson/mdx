---
title: SVG Zero Allocation Feasibility in Phosphene
type: research
tags: [phosphene, svg, typescript, dom, performance]
summary: TypeScript DOM types support mutable SVGPolylineElement point lists, but runtime allocation freedom depends on preallocation, base point mutation, and avoiding string attributes.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

## Executive Summary

The planned SVG renderer can use `SVGPolylineElement.points.getItem(i).x/y` as the TypeScript supported mutation surface. This is viable for preallocated point counts, but not a full zero allocation guarantee because list growth, path sampling, transform strings, and animated value reads can allocate or be read only at runtime.

## Project Metadata

- Project: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/phosphene`
- Branch: `idea/svg-renderer`
- Tooling: Vite+ scripts through `vp`; `build` runs `tsc -b && vp build` in `package.json:6-10`.
- TypeScript: `~6.0.2` in `package.json:23-33`.
- Browser compile surface: `tsconfig.app.json:4-7` targets `es2023` with `DOM`; lint browser env is enabled for TS/TSX files in `vite.config.ts:16-112`.

## Architecture

The current app is React and Three based. A reference seed for the SVG branch exists at `reference/gradient-waves.html:1-18`, describing raw DOM `<svg>` paths and DOM recreation on changes, which the planned renderer should not copy for an animation loop.

## Key Patterns

Use preallocated DOM nodes and point slots. Mutate existing `DOMPoint` records from `polyline.points`, not React props, string attributes, or new path data strings per frame.

## Detailed Findings

- fmm was unavailable for this checkout: no `.fmm.db`; `fmm_list_files` reported no database. File discovery used shell fallback.
- `SVGPolylineElement` extends `SVGAnimatedPoints` in `node_modules/typescript/lib/lib.dom.d.ts:33541-33545`.
- `SVGAnimatedPoints.points` and `animatedPoints` both type as `readonly SVGPointList` in `node_modules/typescript/lib/lib.dom.d.ts:31145-31150`. The property binding is readonly, not necessarily each point object.
- `SVGPointList.getItem(index)` returns `DOMPoint`, and indexed access also returns `DOMPoint`, in `node_modules/typescript/lib/lib.dom.d.ts:33486-33515`.
- `DOMPoint.x` and `DOMPoint.y` are mutable numbers in `node_modules/typescript/lib/lib.dom.d.ts:11793-11818`; `SVGPoint` aliases `DOMPoint` at `node_modules/typescript/lib/lib.dom.d.ts:11831-11832`.
- A local temporary TypeScript probe using `--lib ES2023,DOM --strict --noEmit` accepted `polyline.points.getItem(0).x = 1`, `.y = 2`, indexed point mutation, and even `animatedPoints.getItem(0).x = 4`. The last acceptance is a type hole, not proof that animated lists are safe to mutate.
- `SVGPointList.appendItem`, `initialize`, `insertItemBefore`, and `replaceItem` take `DOMPoint` values, so setup needs point creation, for example through `SVGSVGElement.createSVGPoint()` in `node_modules/typescript/lib/lib.dom.d.ts:33804-33808`.
- Transform churn should avoid attribute strings. TypeScript exposes `SVGAnimatedTransformList.baseVal` and `animVal` in `node_modules/typescript/lib/lib.dom.d.ts:31232-31244`; string animated attributes expose `baseVal: string` in `node_modules/typescript/lib/lib.dom.d.ts:31213-31219`, which implies string churn if used per frame.
- Path performance cannot be claimed superior from local types. `SVGPathElement` exposes `getPointAtLength()` returning a new `DOMPoint` in `node_modules/typescript/lib/lib.dom.d.ts:33366-33384`; the shared geometry interface has the same allocation shaped API at `node_modules/typescript/lib/lib.dom.d.ts:32702-32720`.

## Dependencies

Critical local dependency is the TypeScript DOM library shipped with `typescript ~6.0.2`. React and Three are present, but they do not define the SVG point list contract.

## Relevance to Helioy

For a Helioy visual renderer, the most robust SVG strategy is an imperative render target with stable nodes and preallocated point lists. React should own lifecycle, not per frame coordinate updates.

## Open Questions

- Runtime behavior should still be measured in the actual browser target because TypeScript cannot guarantee no engine allocation or layout work for `SVGPointList.getItem`.
- Need a browser probe for whether mutating `animatedPoints` throws or no ops under animation; planning should treat it as read only and mutate `points` only.
