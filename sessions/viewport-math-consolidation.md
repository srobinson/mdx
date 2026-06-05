---
title: Viewport Math Consolidation
type: sessions
tags: [backend, transport-matters, canvas, viewport, dry, refactor]
summary: Consolidated duplicated canvas viewport math into a canonical engine module.
status: active
source: backend-engineer
confidence: high
created: 2026-06-24
updated: 2026-06-24
---

## Summary

Consolidated the duplicated canvas viewport math functions `clampScale`, `panViewport`, and `zoomViewportAt` into `www/src/engine/viewport.ts` on branch `refactor/consolidate-viewport-math`, commit `5de4850`.

Before extraction, a byte comparison confirmed the copies in `www/src/ambient/engine/viewport.ts` and `www/src/engine/reducers/layoutState.ts` were identical. `www/src/ambient/engine/viewport.ts` now acts as a compatibility facade over the canonical engine viewport contract. `www/src/engine/reducers/layoutState.ts` imports `clampScale` from the canonical module. `www/src/engine/react/useCanvasViewport.ts` imports viewport math plus keyboard and wheel constants from the canonical module.

## API Contract

No backend API contract changed. The frontend engine module now exposes viewport math through:

```typescript
// www/src/engine/viewport.ts
export function clampScale(scale: number): number;
export function panViewport(viewport: CanvasViewport, deltaX: number, deltaY: number): CanvasViewport;
export function zoomViewportAt(
  viewport: CanvasViewport,
  factor: number,
  screenX: number,
  screenY: number,
): CanvasViewport;
```

`www/src/engine/index.ts` re-exports the canonical viewport module for existing engine consumers.

## Database Changes

None.

## Security Considerations

No authentication, authorization, storage, or network behavior changed. This was a pure frontend math refactor with no new input boundary.

## Performance Notes

No runtime behavior changed. The refactor removes duplicate definitions and keeps viewport operations as small pure functions. File sizes remain below the project limit: `www/src/engine/viewport.ts` is 40 LOC, `www/src/engine/reducers/layoutState.ts` is 174 LOC, and `www/src/engine/react/useCanvasViewport.ts` is 147 LOC.

## Verification

- Confirmed byte identical pre-extraction copies for `clampScale`, `panViewport`, and `zoomViewportAt`.
- Confirmed zero duplicate function definitions remain with `rg` after the refactor.
- Ran `git diff --check`, clean.
- Ran `just check`, passed for desktop, www, and api.
- Ran `just test`, passed: desktop 46 tests, www 1057 tests, api 1749 tests.
- Sent bus reply: `done: refactor/consolidate-viewport-math 5de4850 3 viewport fns consolidated to www/src/engine/viewport.ts, zero dup defs, gate green`.

## Open Items

None.
